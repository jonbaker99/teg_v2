"""Simulation dashboard: /simulation (TEG simulator driven by analysis.simulation)."""

import logging
import threading
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from teg_analysis.analysis import simulation as sim
from teg_analysis.analysis import win_probability as wp
from teg_analysis.core.players import get_player_dict
from webapp.chart_utils import get_chart_style
from webapp.deps import register_cache_clearer
from webapp.routes.history import _wrap_player_name

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

LOW_EFF_N = 5.0
# (column label, lower bound, upper bound) on GrossVP; tails are bucketed.
_OUTCOMES = [("Eagle or better", None, -2), ("Birdie", -1, -1), ("Par", 0, 0),
             ("+1", 1, 1), ("+2", 2, 2), ("+3", 3, 3), ("+4 or worse", 4, None)]


# --- cached loaders ----------------------------------------------------------

@lru_cache(maxsize=1)
def _history() -> pd.DataFrame:
    return sim.load_history(teg_nums=[50])  # TEG 50 is test data


def _history_before(history: pd.DataFrame, target: int) -> pd.DataFrame:
    """Only TEGs before the target feed the model, fallbacks included."""
    earlier = history[history["TEGNum"] < target]
    return earlier if not earlier.empty else history


@lru_cache(maxsize=16)
def _target(teg_num: int, players: tuple | None = None):
    """Target tournament; ``players`` is a sorted tuple of codes, None = default roster."""
    return sim.load_target_tournament(teg_num, list(players) if players is not None else None)


@lru_cache(maxsize=1)
def _target_options() -> tuple:
    return tuple(sim.available_target_tegs())


@lru_cache(maxsize=4)
def _live_state(teg_num: int, replay: bool) -> tuple:
    """(TegState, names) for an in-progress TEG, or a finished one replayed."""
    state = wp.load_teg_state(teg_num, _history(), from_scores=replay)
    names = state.names if not replay else {p: get_player_dict().get(p, p) for p in state.players}
    return state, names


_LIVE_POINTS: dict[tuple, dict] = {}  # (teg, replay, round, hole) -> point; cleared with the data caches
_LIVE_GEN = [0]  # bumped on every clear, so a point computed from old data is never stored


def _live_point(teg_num: int, replay: bool, rnd: int, hole: int) -> dict:
    """{"net": {Pl: p}, "gross": {Pl: p}, "_frame": tidy rows} after hole ``hole`` of
    round ``rnd`` (default model, fixed seed). Memoised so the page can show every
    point already worked out straight away."""
    key = (int(teg_num), bool(replay), int(rnd), int(hole))
    if key in _LIVE_POINTS:
        return _LIVE_POINTS[key]
    gen = _LIVE_GEN[0]
    state, _ = _live_state(teg_num, replay)
    if key[2:] not in set(wp.checkpoints(state)):
        raise ValueError(f"No checkpoint at round {rnd} hole {hole}")
    df = wp.win_probs_at(state, rnd, hole, n_sims=sim.DEFAULT_SIMS, seed=1)
    pt = {m: {str(r.player): float(r.win_prob) for r in g.itertuples()}
          for m, g in df.groupby("measure", sort=False)}
    point = {**pt, "_frame": df}
    if gen == _LIVE_GEN[0]:
        _LIVE_POINTS[key] = point
    return point


def _pct_label(p: float) -> str:
    """Whole-percent display string: "<1%", "0%", ">99%" at the edges."""
    pct = 100.0 * float(p)
    if pct <= 0:
        return "0%"
    if pct < 0.5:
        return "<1%"
    if pct < 100 and int(pct + 0.5) >= 100:
        return ">99%"
    return f"{int(pct + 0.5)}%"


def finalised_win_chances(teg_num: int) -> dict | None:
    """{"after_round": n, "trophy": {full name: pct}, "jacket": {full name: pct}} for the TEG
    in progress, as at its last finalised round; None if teg_num isn't in progress or it fails."""
    try:
        if wp.in_progress_teg() != int(teg_num):
            return None
        state, names = _live_state(int(teg_num), False)
        rnd = len(state.done)
        point = _live_point(int(teg_num), False, rnd, 18 if rnd else 0)

        def label(measure: str) -> dict:
            return {names.get(code, code): _pct_label(p) for code, p in point[measure].items()}

        return {"after_round": rnd, "trophy": label("net"), "jacket": label("gross")}
    except Exception:
        logger.exception("finalised win chances failed")
        return None


_LIVE_NOW: dict[tuple, tuple] = {}  # (teg, seed, staged signature) -> (public dict, {Pl: mean})


def _staged_for(teg_num: int):
    """The live round's entered holes, or None (also when the registry can't be read)."""
    from teg_analysis.analysis import live_round
    try:
        return live_round.staged_holes(teg_num)
    except Exception:
        logger.exception("staged holes unavailable")
        return None


def _staged_signature(staged) -> tuple:
    if staged is None or len(staged) == 0:
        return ()
    return tuple(sorted(tuple(int(v) if not isinstance(v, str) else v for v in r)
                        for r in staged.itertuples(index=False)))


def live_snapshot() -> tuple:
    """(TegState, Snapshot, staged holes) for the TEG in progress, entered holes included.

    Raises ValueError when no TEG is in progress."""
    teg = wp.in_progress_teg()
    if teg is None:
        raise wp.NoTegInProgress("No TEG is in progress.")
    state, _ = _live_state(teg, False)
    staged = _staged_for(teg)
    return state, wp.snapshot(state, staged), staged


def _completed_tegs() -> list[int]:
    return sorted(sim._tegnums(sim._read_csv(sim.COMPLETED_TEGS_CSV)))


def _clear_caches() -> None:
    _LIVE_GEN[0] += 1
    _LIVE_POINTS.clear()
    _LIVE_NOW.clear()
    _live_state.cache_clear()
    default_prediction.cache_clear()
    _history.cache_clear()
    _target.cache_clear()
    _target_options.cache_clear()


register_cache_clearer(_clear_caches)


# --- input parsing -----------------------------------------------------------

def _int(value, default):
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError, OverflowError):
        return default


def _parse_settings(qp, targets: list[int], history: pd.DataFrame) -> dict:
    """Read controls from the query string. Errors are collected, never raised."""
    errors: list[str] = []
    default = sim.default_target_teg()
    fallback = default if default in targets else targets[0]
    target = _int(qp.get("target"), fallback)
    if target not in targets:
        target = fallback

    # Only TEGs before the target feed the model (no peeking at the answer).
    completed = [t for t in sim.completed_teg_numbers(history) if t < target] \
        or sim.completed_teg_numbers(history)
    defaults = sim.default_teg_weights(completed)
    weights: dict[int, float] = {}
    for t in completed:
        raw = qp.get(f"w_{t}")
        if raw is None:
            weights[t] = defaults[t]
            continue
        try:
            w = float(str(raw).strip() or 0)
        except ValueError:
            errors.append(f"Weight for TEG {t} must be a number.")
            w = 0.0
        if w < 0 or w > 1e6 or not np.isfinite(w):
            errors.append(f"Weight for TEG {t} must be between 0 and 1,000,000.")
            w = 0.0
        weights[t] = w
    if not errors and sum(weights.values()) <= 0:
        errors.append("All TEG weights are zero. Give at least one TEG a weight above 0.")

    default_tgt = _target(target)
    tgt = default_tgt
    all_names = get_player_dict()
    selected = set(default_tgt.players)
    if qp.get("pl_set"):
        picked = set(qp.getlist("pl"))
        chosen = [c for c in default_tgt.candidates if c in picked]
        selected = set(chosen)
        if not chosen:
            errors.append("Pick at least one player.")
        elif selected != set(default_tgt.players):
            tgt = _target(target, tuple(sorted(chosen)))
    player_options = [{"code": c, "name": all_names.get(c, c), "checked": c in selected}
                      for c in default_tgt.candidates]
    played = {pl: {int(t) for t in g["TEGNum"].unique()}
              for pl, g in history[history["TEGNum"].isin(completed)].groupby("Pl")}
    player_weights: dict[str, dict[int, float]] = {}
    player_rows = []
    for pl in tgt.players:
        name = tgt.names.get(pl, pl)
        custom_on = qp.get(f"po_{pl}") not in (None, "", "0", "false")
        pw: dict[int, float] = {}
        if custom_on:
            for t in completed:
                if t not in played.get(pl, set()):
                    continue
                raw = qp.get(f"pw_{pl}_{t}")
                if raw is None:
                    pw[t] = weights[t]
                    continue
                try:
                    w = float(str(raw).strip() or 0)
                except ValueError:
                    errors.append(f"Custom weight for {name}, TEG {t} must be a number.")
                    w = 0.0
                if w < 0 or w > 1e6 or not np.isfinite(w):
                    errors.append(f"Custom weight for {name}, TEG {t} must be between 0 and 1,000,000.")
                    w = 0.0
                pw[t] = w
            if not errors and played.get(pl) and sum(pw.values()) <= 0:
                errors.append(f"Custom weights for {name} are all zero. "
                              "Give at least one TEG a weight above 0 or untick Custom.")
            if played.get(pl):
                player_weights[pl] = pw
        player_rows.append({
            "code": pl, "name": name, "name_html": _wrap_player_name(name),
            "custom": custom_on, "played": played.get(pl, set()),
            "weights": {t: _fmt_num(pw.get(t, weights[t])) for t in completed}})

    method = qp.get("method") or sim.DEFAULT_METHOD
    if method not in sim.METHODS:
        method = sim.DEFAULT_METHOD
    mh_raw = qp.get("min_holes")
    min_holes = sim.DEFAULT_MIN_HOLES
    if mh_raw not in (None, ""):
        mh = _int(mh_raw, None)
        if mh is None or not 1 <= mh <= 500:
            if method == "window":
                errors.append("Min holes must be a whole number between 1 and 500.")
        else:
            min_holes = mh

    preset = qp.get("bands_preset") or "4 bands"
    if preset not in sim.SI_BAND_PRESETS:
        preset = "4 bands"
    custom = (qp.get("bands_custom") or "").strip()
    boundaries = sim.SI_BAND_PRESETS[preset]
    if custom:
        try:
            boundaries = sim.parse_si_boundaries(custom)
        except ValueError as exc:
            if method == "bands":
                errors.append(f"SI bands: {exc}. Use whole numbers like 4,9,14.")

    k_raw = qp.get("shrinkage")
    k = sim.DEFAULT_SHRINKAGE if k_raw in (None, "") else None
    if k is None:
        try:
            k = float(k_raw)
        except ValueError:
            k = None
        if k is None or k < 0 or not np.isfinite(k):
            if method == "bands":
                errors.append("Shrinkage k must be a number, zero or more.")
            k = sim.DEFAULT_SHRINKAGE

    fa_raw = qp.get("field_alpha")
    field_alpha = sim.DEFAULT_FIELD_ALPHA
    if fa_raw not in (None, ""):
        try:
            field_alpha = float(str(fa_raw).strip())
        except ValueError:
            field_alpha = None
        if field_alpha is None or not np.isfinite(field_alpha) or not 0 <= field_alpha <= 200:
            errors.append("Field blend must be a number between 0 and 200.")
            field_alpha = sim.DEFAULT_FIELD_ALPHA
    fa_text = _fmt_num(field_alpha) if fa_raw in (None, "") else str(fa_raw).strip()

    n_raw = qp.get("n_sims")
    n_sims = _int(n_raw, sim.DEFAULT_SIMS) if n_raw not in (None, "") else sim.DEFAULT_SIMS
    clamp_note = None
    if n_sims < 1:
        n_sims = sim.DEFAULT_SIMS
        errors.append("Number of simulations must be at least 1.")
    elif n_sims > sim.MAX_SIMS:
        n_sims = sim.MAX_SIMS
        clamp_note = f"Simulations capped at {sim.MAX_SIMS:,}."

    seed_raw = (qp.get("seed") or "").strip()
    seed = None
    if seed_raw:
        seed = _int(seed_raw, None)
        if seed is None or seed < 0:
            errors.append("Seed must be a whole number, zero or more.")
            seed = None

    return {
        "method": method, "methods": sim.METHODS, "min_holes": min_holes,
        "player_weights": player_weights, "player_rows": player_rows,
        "target": target, "targets": targets, "completed": completed,
        "weights": weights, "defaults": defaults, "preset": preset,
        "presets": list(sim.SI_BAND_PRESETS), "custom": custom,
        "boundaries": boundaries, "k": k, "n_sims": n_sims, "seed": seed,
        "seed_text": seed_raw, "clamp_note": clamp_note, "errors": errors,
        "tgt": tgt, "player_options": player_options,
        "field_alpha": field_alpha, "field_alpha_text": fa_text,
    }


def _weight_shares(weights: dict[int, float]) -> dict[int, float]:
    total = sum(weights.values())
    return {t: (w / total * 100 if total > 0 else 0.0) for t, w in weights.items()}


def _fmt_num(x: float) -> str:
    return f"{x:g}"


def _build(history: pd.DataFrame, tgt, s: dict) -> "sim.ScoreDistributions":
    before = _history_before(history, s["target"])
    dists = sim.build_distributions(
        before, tgt.players, s["weights"],
        s["boundaries"], s["k"], method=s["method"], min_holes=s["min_holes"],
        player_weights=s["player_weights"] or None, field_alpha=s["field_alpha"])
    # a debutant gets the group's scoring centred on their handicap, and a warning
    return wp.anchor_newcomers(dists, before, tgt.handicaps)


def _status_notes(tgt) -> list[str]:
    notes = []
    if tgt.handicaps_draft:
        notes.append(f"Handicaps are a draft calculation; TEG {tgt.teg_num} handicaps haven't been saved yet.")
    if tgt.random_rounds > 0:
        fixed = {int(r) for r in tgt.holes["Round"].unique()} if len(tgt.holes) else set()
        missing = [r for r in range(1, tgt.n_rounds + 1) if r not in fixed]
        label = "round" if len(missing) == 1 else "rounds"
        notes.append(f"No scorecard yet for {label} {', '.join(map(str, missing))}: each simulation "
                     f"draws a random par-72 course from the {len(tgt.course_pool)} on file.")
    return notes


# --- distributions -----------------------------------------------------------

def _shade(frac: float, max_frac: float = 1.0) -> str:
    """Heat intensity 0-1 as ``--heat``; simulation.css turns it into a theme-aware tint."""
    heat = max(0.0, min(1.0, frac)) * max_frac
    return f"--heat: {heat:.3f};"


def _distribution_rows(dists: "sim.ScoreDistributions", player: str, used=frozenset()) -> list[dict]:
    probs = dists.probs[dists.probs["Pl"] == player]
    cells = dists.cells[dists.cells["Pl"] == player]
    rows = []
    for c in cells.sort_values(["Par", "Band"]).itertuples():
        pr = probs[(probs["Par"] == c.Par) & (probs["Band"] == c.Band)]
        vals = []
        for _label, lo, hi in _OUTCOMES:
            m = pd.Series(True, index=pr.index)
            if lo is not None:
                m &= pr["GrossVP"] >= lo
            if hi is not None:
                m &= pr["GrossVP"] <= hi
            p = float(pr.loc[m, "Prob"].sum())
            vals.append({"text": f"{p * 100:.0f}%", "style": _shade(p / 0.6)})
        rows.append({
            "label": f"Par {c.Par} / {c.BandLabel}", "cells": vals, "n": int(c.N),
            "eff": f"{c.EffN:.1f}", "low": c.EffN < LOW_EFF_N, "mean": f"{c.MeanVP:+.2f}",
            "source": c.Source, "window": c.Window, "used": (int(c.Par), int(c.Band)) in used,
        })
    return rows


def _distributions_context(qp) -> dict:
    try:
        history = _history()
        targets = list(_target_options())
        if not targets:
            return {"fatal": "No upcoming TEG scorecard is set up yet."}
        s = _parse_settings(qp, targets, history)
        tgt = s["tgt"]
        ctx = {"s": s, "dist_errors": s["errors"], "players": [], "outcomes": [o[0] for o in _OUTCOMES]}
        if s["errors"]:
            return ctx
        dists = _build(history, tgt, s)
        player = qp.get("dist_player")
        if player not in tgt.players:
            player = tgt.players[0]
        bands = sim.assign_si_band(tgt.holes["SI"].to_numpy(), dists.boundaries)
        used = {(int(p), int(b)) for p, b in zip(tgt.holes["Par"], bands)}
        has_marks = len(tgt.holes) > 0
        rows = _distribution_rows(dists, player, used)
        ctx.update({
            "players": [(p, tgt.names.get(p, p)) for p in tgt.players],
            "dist_player": player,
            "dist_rows": rows,
            "dist_warnings": dists.warnings,
            "dist_has_low": any(r["low"] for r in rows),
            "dist_window": s["method"] == "window",
            "dist_marks": has_marks,
        })
        return ctx
    except ValueError as exc:  # setup problems (missing handicap, no scorecard pool)
        logger.warning("Simulation setup: %s", exc)
        return {"fatal": f"Can't simulate yet: {exc}. Check the TEG setup (roster and handicaps)."}
    except Exception:
        logger.exception("simulation distributions failed")
        return {"fatal": "Couldn't build the sampling distributions."}


# --- results -----------------------------------------------------------------

def _caption(res, s, n_holes: int) -> str:
    shares = _weight_shares(s["weights"])
    used = [f"{t} ({shares[t]:.0f}%)" for t in sorted(s["weights"], reverse=True) if s["weights"][t] > 0]
    how = (f"rolling SI window, min {s['min_holes']} holes" if s["method"] == "window"
           else "fixed SI bands")
    custom = [r["name"] for r in s["player_rows"] if r["code"] in s["player_weights"]]
    extra = f"; custom weights for {', '.join(custom)}" if custom else ""
    return (f"{res.n_sims:,} simulations of TEG {res.teg_num} ({n_holes} holes) "
            f"using TEG{'s' if len(used) > 1 else ''} {', '.join(used)} ({how}){extra}.")


def _summary_rows(res, measure: str) -> list[dict]:
    df = sim.summary_table(res)
    df = df.sort_values("ExpPosGross" if measure == "gross" else "ExpPosStableford",
                        kind="stable").reset_index(drop=True)
    return [{
        "name_html": _wrap_player_name(r.Player), "hc": r.Handicap,
        "gross_vp": f"{r.MeanGrossVP:+.1f}",
        "gross_range": f"{r.P10Gross - res.par_total:+.0f} to {r.P90Gross - res.par_total:+.0f}",
        "stab": f"{r.MeanStableford:.1f}",
        "stab_range": f"{r.P10Stableford:.0f}-{r.P90Stableford:.0f}",
        "win_gross": f"{r.WinGross * 100:.1f}%", "win_stab": f"{r.WinStableford * 100:.1f}%",
        "eagle": f"{getattr(r, 'EagleChance', float('nan')) * 100:.1f}%",
        "blobs": f"{getattr(r, 'ExpBlobs', float('nan')):.1f}",
    } for r in df.itertuples()]


def _courses_drawn(res, tgt) -> list[dict]:
    """Share of random rounds that drew each pool course, most drawn first."""
    used = res.courses_used
    if used is None or used.size == 0 or not tgt.course_pool:
        return []
    counts = np.bincount(used.ravel().astype(int), minlength=len(tgt.course_pool))
    total = counts.sum()
    rows = [{"name": tgt.course_pool[i][0], "pct": f"{counts[i] / total * 100:.1f}%", "n": int(counts[i])}
            for i in range(len(tgt.course_pool))]
    return sorted(rows, key=lambda r: (-r["n"], r["name"]))


def _grid_rows(res, measure: str) -> tuple[list[int], list[dict]]:
    grid = sim.position_grid(res, measure)
    vmax = float(grid.to_numpy().max()) or 1.0
    rows = []
    for name, vals in grid.iterrows():
        rows.append({"name_html": _wrap_player_name(name), "cells": [
            {"text": f"{v * 100:.1f}%", "zero": v < 0.0005, "style": _shade(v / vmax)}
            for v in vals]})
    return list(grid.columns), rows


def _chart_json(res, measure: str) -> str:
    import plotly.graph_objects as go
    import plotly.express as px

    dist = sim.total_distribution(res, measure, smooth=True)
    palette = px.colors.qualitative.Plotly
    fig = go.Figure()
    offset = res.par_total if measure == "gross" else 0  # gross is shown vs par
    for i, (name, g) in enumerate(dist.groupby("Player", sort=False)):
        g = g.sort_values("Total")
        fig.add_trace(go.Scatter(
            x=g["Total"] - offset, y=(g["Fraction"] * 100).round(2), mode="lines", name=name,
            line=dict(color=palette[i % len(palette)], width=2),
            hovertemplate=("%{x:+d}" if measure == "gross" else "%{x}") + ": %{y:.1f}%<extra>" + name + "</extra>"))
    fig.update_layout(
        xaxis_title="Gross vs par" if measure == "gross" else "Total Stableford points",
        yaxis_title="% of simulations", hovermode="x unified",
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0, title_text=""),
        margin=dict(r=12, t=10, b=40, l=44))
    if measure == "gross":
        fig.update_xaxes(tickformat="+d")
    fig.layout.xaxis.fixedrange = True
    fig.layout.yaxis.fixedrange = True
    fig.update_layout(**get_chart_style("streamlit"))
    return fig.to_json()


def _pp(v: float) -> str:
    t = f"{v:+.1f}"
    return "0.0" if t in ("+0.0", "-0.0") else t


def _signed(v: int) -> str:
    return f"{v:+d}" if v else "0"


def _impact_context(res) -> dict:
    """Context for the "Impact of handicap changes" expander (never raises)."""
    try:
        old = sim.previous_handicaps(res.teg_num)
        if not old:
            return {"message": f"No TEG {res.teg_num - 1} handicaps to compare with."}
        imp = sim.handicap_change_impact(res, old)
        names = [res.names.get(p, p) for p in imp.players]
        out = {
            "prev": res.teg_num - 1, "teg": res.teg_num,
            "cols": [_wrap_player_name(n) for n in names],
            "message": imp.skipped_reason,
            "unchanged": [res.names.get(p, p) for p in imp.players
                          if p not in imp.movers and p not in imp.no_previous],
            "no_previous": [res.names.get(p, p) for p in imp.no_previous],
            "n_movers": len(imp.movers),
        }
        if not imp.movers:
            out["message"] = out["message"] or "No handicaps changed, so there is nothing to split."
            return out
        if imp.shapley is not None:
            out["rows"] = [{
                "name_html": _wrap_player_name(res.names.get(p, p)),
                "change": f"{imp.old_handicaps[p]}\u2192{imp.new_handicaps[p]}",
                "cells": [_pp(v) for v in imp.shapley[i]]} for i, p in enumerate(imp.movers)]
            out["total"] = [_pp(v) for v in imp.total_change]
            out["single_sum"] = [_pp(v) for v in imp.single_sum]
        out["win_old"] = [f"{v * 100:.1f}%" for v in imp.win_old]
        out["win_new"] = [f"{v * 100:.1f}%" for v in imp.win_new]
        return out
    except Exception:
        logger.exception("simulation handicap impact failed")
        return {"message": "Couldn't work out the impact of handicap changes."}


def _equalising_context(res) -> dict:
    """Context for the "Handicaps that equalise chances" expander (never raises)."""
    try:
        df = sim.equalising_handicaps(res)
        return {"target": int(sim.EQUALISING_TARGET), "rows": [{
            "name_html": _wrap_player_name(r.Player), "current": r.CurrentHC,
            "equal": r.EqualisingHC, "change": _signed(int(r.Change)),
            "unrounded": f"{r.Unrounded:.1f}" + ("" if r.Reachable else " *"),
            "pts": f"{r.PtsPerRound:.1f}", "win": f"{r.WinStableford * 100:.1f}%",
        } for r in df.itertuples()], "unreachable": bool((~df.Reachable).any())}
    except Exception:
        logger.exception("simulation equalising handicaps failed")
        return {"message": "Couldn't work out equalising handicaps."}


def _run_context(qp) -> dict:
    try:
        history = _history()
        targets = list(_target_options())
        if not targets:
            return {"fatal": "No upcoming TEG scorecard is set up yet."}
        s = _parse_settings(qp, targets, history)
        if s["errors"]:
            return {"run_errors": s["errors"]}
        tgt = s["tgt"]
        dists = _build(history, tgt, s)
        res = sim.run_simulation(dists, tgt, s["n_sims"], s["seed"], keep_scores=True)
        measures = []
        for key, label in (("stableford", "Stableford"), ("gross", "Gross")):
            cols, grid = _grid_rows(res, key)
            measures.append({
                "key": key, "label": label, "summary": _summary_rows(res, key),
                "grid_cols": cols, "grid": grid, "chart_json": _chart_json(res, key)})
        odds = [{
            "name_html": _wrap_player_name(r.Player),
            "trophy": r.TrophyOdds, "trophy_pct": f"{r.Trophy * 100:.1f}%",
            "jacket": r.JacketOdds, "jacket_pct": f"{r.Jacket * 100:.1f}%",
            "spoon": r.SpoonOdds, "spoon_pct": f"{r.Spoon * 100:.1f}%",
        } for r in sim.odds_table(res).itertuples()]
        return {
            "odds": odds,
            "measures": measures,
            "caption": _caption(res, s, len(tgt.holes) + 18 * tgt.random_rounds),
            "courses": _courses_drawn(res, tgt),
            "clamp_note": s["clamp_note"], "warnings": dists.warnings,
            "teg_num": res.teg_num,
            "impact": _impact_context(res), "equalise": _equalising_context(res),
        }
    except ValueError as exc:  # setup problems (missing handicap, no scorecard pool)
        logger.warning("Simulation setup: %s", exc)
        return {"fatal": f"Can't simulate yet: {exc}. Check the TEG setup (roster and handicaps)."}
    except Exception:
        logger.exception("simulation run failed")
        return {"fatal": "Couldn't run the simulation."}


# --- live win chances ---------------------------------------------------------

MEASURE_KEYS = wp.MEASURES


def _cp_key(rnd: int, hole: int) -> str:
    return f"{rnd}-{hole}"


def _cp_label(rnd: int, hole: int) -> str:
    return "Start" if rnd == 0 else f"R{rnd} hole {hole}"


def _live_queue(done: list[int]) -> list[list]:
    """Hole checkpoints still to work out, in the order the page fills them in.

    Round ends come with the page (for the table); the rest go in hole order,
    so the chart draws from left to right.
    """
    return [[r, h] for r in sorted(done) for h in range(1, 18)]


def _leading_run(points: dict, order: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Checkpoints from the start up to the first gap: the part of the chart drawn so far."""
    run = []
    for r, h in order:
        if _cp_key(r, h) not in points:
            break
        run.append((r, h))
    return run


def _live_chart_json(points: dict, measure: str, players: list[str], names: dict,
                     order: list[tuple[int, int]]) -> str:
    import plotly.express as px
    import plotly.graph_objects as go

    labels = [_cp_label(r, h) for r, h in order]
    have = _leading_run(points, order)
    palette = px.colors.qualitative.Plotly
    fig = go.Figure()
    for i, pl in enumerate(players):
        name = names.get(pl, pl)
        fig.add_trace(go.Scatter(
            x=[_cp_label(r, h) for r, h in have],
            y=[round(points[_cp_key(r, h)][measure][pl] * 100, 1) for r, h in have],
            mode="lines", name=name, line=dict(color=palette[i % len(palette)], width=2),
            hovertemplate="%{y:.1f}%<extra>" + name + "</extra>"))
    ends = [lab for lab, (r, h) in zip(labels, order) if r == 0 or h == 18]
    fig.update_layout(
        yaxis_title="Win chance (%)", hovermode="x unified",
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0, title_text=""),
        margin=dict(r=12, t=10, b=40, l=44))
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=labels,
                     range=[-0.5, len(labels) - 0.5], tickmode="array", tickvals=ends,
                     ticktext=["Start" if e == "Start" else "End " + e.split(" ")[0] for e in ends])
    fig.update_yaxes(range=[0, 100], ticksuffix="%")
    fig.layout.xaxis.fixedrange = True
    fig.layout.yaxis.fixedrange = True
    fig.update_layout(**get_chart_style("streamlit"))
    return fig.to_json()


def _now_context(stableford: bool, done: int) -> dict | None:
    """Rows for the "now" table while the live round has scores entered, else None."""
    try:
        pred, _ = _live_now()
    except Exception:
        logger.exception("mid-round live chances failed")
        return None
    if pred["live_round"] is None:
        return None
    rows = []
    for p in pred["players"]:
        net, gross = p["NetSoFar"], p["GrossVsParSoFar"]
        rows.append({
            "name_html": _wrap_player_name(p["Player"]),
            "trophy": f"{p['TrophyChancePct']:.1f}%", "trophy_change": _pp(p["TrophyChangePp"]),
            "jacket": f"{p['JacketChancePct']:.1f}%", "jacket_change": _pp(p["JacketChangePp"]),
            "net": str(net) if stableford else _signed(net), "gross": _signed(gross),
            "thru": p["Thru"],
        })
    return {"round": pred["live_round"], "rows": rows,
            "thru": " / ".join(str(r["thru"]) for r in rows),
            "since": "the start" if done == 0 else f"the end of round {done}"}


def _live_context(qp) -> dict:
    """Context for the Live tab: latest win chances, plus everything the page needs
    to fill in the hole-by-hole chart."""
    import json

    live = wp.in_progress_teg()
    completed = _completed_tegs()
    held = sorted({int(t) for t in _history()["TEGNum"].unique()})
    # a replay needs at least one earlier TEG to build prior form from
    replay_options = sorted((t for t in completed if any(e < t for e in held)), reverse=True)
    replay_teg = None
    if qp.get("teg"):
        try:
            replay_teg = int(qp.get("teg"))
        except ValueError:
            replay_teg = None
        if replay_teg not in replay_options:
            replay_teg = None
    ctx = {"live_teg": live, "next_teg": sim.default_target_teg(), "replay_options": replay_options,
           "last_completed": completed[-1] if completed else None,
           "w_by_round": [f"{wp.blend_weight(n) * 100:.0f}%" for n in (1, 2, 3)]}
    teg = replay_teg or live
    if teg is None:
        return {**ctx, "not_live": True}
    replay = replay_teg is not None
    try:
        state, names = _live_state(teg, replay)
        done = len(state.done)
        cps = [(0, 0)] + [(r, 18) for r in state.done]
        points = {_cp_key(r, h): _live_point(teg, replay, r, h) for r, h in cps}
    except ValueError as exc:
        logger.warning("Live win chances: %s", exc)
        return {**ctx, "fatal": f"Can't work out live chances for TEG {teg} yet: {exc}."}
    except Exception:
        logger.exception("live win chances failed")
        return {**ctx, "fatal": "Couldn't work out the live win chances."}

    stableford = state.stableford
    frame = points[_cp_key(*cps[-1])]["_frame"]
    latest = frame.pivot(index="player", columns="measure", values=["win_prob", "banked"])
    prev = points[_cp_key(*cps[-2])] if done else None

    def change(pl, m):
        if prev is None:
            return ""
        pp = (latest.loc[pl, ("win_prob", m)] - prev[m][pl]) * 100
        return "0.0" if abs(pp) < 0.05 else f"{pp:+.1f}"

    order = latest.assign(_b=latest[("banked", "net")] * (1 if stableford else -1)).sort_values(
        [("win_prob", "net"), "_b"], ascending=False).index
    players = [str(p) for p in order]
    rows = []
    for pl in players:
        net_b, gross_b = latest.loc[pl, ("banked", "net")], latest.loc[pl, ("banked", "gross")]
        rows.append({
            "name_html": _wrap_player_name(names.get(pl, pl)),
            "trophy": f"{latest.loc[pl, ('win_prob', 'net')] * 100:.1f}%",
            "trophy_change": change(pl, "net"),
            "jacket": f"{latest.loc[pl, ('win_prob', 'gross')] * 100:.1f}%",
            "jacket_change": change(pl, "gross"),
            "net_banked": (f"{net_b:.0f}" if stableford else _signed(int(net_b))) if done else "",
            "gross_banked": _signed(int(gross_b)) if done else "",
        })
    measures = [{"key": "net", "label": "TEG Trophy" if stableford else "TEG Trophy (net)"},
                {"key": "gross", "label": "Green Jacket"}]
    live_data = None
    if done:
        axis = wp.checkpoints(state)
        for (t, rp, r, h), v in list(_LIVE_POINTS.items()):  # anything already worked out
            if t == teg and rp == replay:
                points.setdefault(_cp_key(r, h), v)
        clean = {k: {m: v[m] for m in MEASURE_KEYS} for k, v in points.items()}
        for m in measures:
            m["chart_json"] = _live_chart_json(clean, m["key"], players, names, axis)
        scores = {}
        for r in state.holes.itertuples():
            scores.setdefault(_cp_key(r.Round, r.Hole), {})[r.Pl] = [int(r.GrossVP), int(r.Net)]
        live_data = json.dumps({
            "teg": teg, "replay": replay, "stableford": stableford,
            "players": players, "names": {p: names.get(p, p) for p in players},
            "axis": [[r, h] for r, h in axis], "points": clean, "scores": scores,
            "queue": [q for q in _live_queue(state.done) if _cp_key(q[0], q[1]) not in clean],
            "total": len(axis) - 1}).replace("</", "<\\/")
    now = _now_context(stableford, done) if not replay else None
    return {
        **ctx, "now": now, "teg": teg, "replay": replay, "done": done, "rows": rows,
        "measures": measures,
        "newcomers": [names.get(p, p) for p in wp.newcomers(state.prior)],
        "total": len(wp.checkpoints(state)) - 1,
        "stableford": stableford, "live_data": live_data,
        "since": ("the start" if done == 1 else f"round {done - 1}") if done else "",
    }


# --- default prediction (used by TEGBot) ---------------------------------------

@lru_cache(maxsize=1)
def default_prediction(seed: int = 1) -> dict:
    """The page's default simulation of the next TEG, as plain data.

    Fixed seed so TEGBot gives the same odds every time it is asked; the page itself
    reruns with a fresh seed, so its figures can differ by a point or two.
    Raises ValueError when the next TEG isn't set up enough to simulate."""
    history = _history()
    targets = list(_target_options())
    if not targets:
        raise ValueError("No upcoming TEG scorecard is set up yet.")
    s = _parse_settings({"seed": str(seed)}, targets, history)
    if s["errors"]:
        raise ValueError("; ".join(s["errors"]))
    tgt = s["tgt"]
    res = sim.run_simulation(_build(history, tgt, s), tgt, s["n_sims"], s["seed"])
    summary = sim.summary_table(res).set_index("Pl")
    odds = []
    for r in sim.odds_table(res).itertuples():
        odds.append({
            "Player": r.Player, "Handicap": summary.loc[r.Pl, "Handicap"],
            "TrophyChancePct": round(r.Trophy * 100, 1), "TrophyOdds": r.TrophyOdds,
            "JacketChancePct": round(r.Jacket * 100, 1), "JacketOdds": r.JacketOdds,
            "SpoonChancePct": round(r.Spoon * 100, 1), "SpoonOdds": r.SpoonOdds,
            "ExpectedStableford": round(float(summary.loc[r.Pl, "MeanStableford"]), 1),
            "ExpectedGrossVsPar": round(float(summary.loc[r.Pl, "MeanGrossVP"]), 1),
        })
    return {"teg_num": res.teg_num, "simulations": res.n_sims, "players": odds,
            "notes": _status_notes(tgt)}


def _ranks(values: dict[str, float], higher_better: bool) -> dict[str, str]:
    """Competition ranks, ties shared ("2=")."""
    out = {}
    for pl, v in values.items():
        better = sum((o > v) if higher_better else (o < v) for o in values.values())
        ties = sum(o == v for o in values.values())
        out[pl] = f"{better + 1}{'=' if ties > 1 else ''}"
    return out


_LIVE_NOW_LOCK = threading.Lock()  # one run at a time: the Live tab and TEGBot share results


def _live_now(seed: int = 1) -> tuple:
    """(public dict, {"gross": {Pl: expected gross vs par per 18}, "net": {Pl: expected
    Stableford or net vs par per 18}}) for the TEG in progress, with entered holes
    counted. Cached per staged-holes signature."""
    teg = wp.in_progress_teg()
    if teg is None:
        raise wp.NoTegInProgress("No TEG is in progress.")
    state, names = _live_state(teg, False)
    staged = _staged_for(teg)
    key = (int(teg), int(seed), _staged_signature(staged))
    with _LIVE_NOW_LOCK:
        if key not in _LIVE_NOW:
            _compute_live_now(teg, seed, state, names, staged, key)
        return _LIVE_NOW.get(key) or _compute_live_now(teg, seed, state, names, staged, None)


def _compute_live_now(teg, seed, state, names, staged, key) -> tuple:
    """Run the live simulation; store it under ``key`` (None: don't store)."""
    gen = _LIVE_GEN[0]
    snap = wp.snapshot(state, staged)
    df = wp.win_probs_live(state, staged, n_sims=sim.DEFAULT_SIMS, seed=seed, spoon=True)
    done = snap.rounds_done
    prev = _live_point(teg, False, done, 18 if done else 0)
    by = {m: g.set_index("player") for m, g in df.groupby("measure", sort=False)}
    played = any(snap.holes_played.values())
    net_rank = _ranks(snap.net, snap.stableford) if played else {}
    gross_rank = _ranks(snap.gross, False) if played else {}
    means = {"gross": {}, "net": {}}
    rows = []
    for pl in state.players:
        for m, col, src in (("gross", "mean", "gross"), ("net", "mean_net", "net")):
            v = by[src].loc[pl, col]
            means[m][pl] = None if pd.isna(v) else float(v)
        trophy, jacket = by["net"].loc[pl, "win_prob"], by["gross"].loc[pl, "win_prob"]
        rows.append({
            "Player": snap.names.get(pl, names.get(pl, pl)), "Pl": pl,
            "Handicap": snap.handicaps[pl], "Thru": snap.thru[pl],
            "HolesPlayed": snap.holes_played[pl],
            "NetSoFar": snap.net[pl], "GrossVsParSoFar": snap.gross[pl],
            "NetPosition": net_rank.get(pl), "GrossPosition": gross_rank.get(pl),
            "TrophyChancePct": round(float(trophy) * 100, 1),
            "JacketChancePct": round(float(jacket) * 100, 1),
            "SpoonChancePct": round(float(by["spoon"].loc[pl, "win_prob"]) * 100, 1),
            "TrophyChangePp": round((float(trophy) - prev["net"][pl]) * 100, 1) + 0.0,
            "JacketChangePp": round((float(jacket) - prev["gross"][pl]) * 100, 1) + 0.0,
            "ExpectedGrossVsParPer18": (None if means["gross"][pl] is None
                                        else round(means["gross"][pl], 1)),
        })
    rows.sort(key=lambda r: -r["TrophyChancePct"])
    result = {
        "teg_num": int(teg), "rounds_done": done, "rounds_total": snap.n_rounds,
        "live_round": snap.live_round, "simulations": sim.DEFAULT_SIMS,
        "measure_label": "Stableford" if snap.stableford else "net vs par",
        "players": rows,
    }
    if key is not None and gen == _LIVE_GEN[0]:
        for k in [k for k in _LIVE_NOW if k[0] == key[0]]:
            _LIVE_NOW.pop(k, None)
        _LIVE_NOW[key] = (result, means)
    return result, means


def live_prediction(seed: int = 1) -> dict:
    """Win chances now for the TEG in progress, as plain data (TEGBot and the Live tab).

    Completed rounds and the live round's entered holes are banked; the rest is
    simulated. Changes are versus the last finalised round. Raises ValueError when
    no TEG is in progress."""
    return _live_now(seed)[0]


def what_it_takes(player: str | None, competition: str = "trophy",
                  rivals: str = "same_pace") -> dict | list:
    """What a player (name or code; None/"all" for everyone) needs to win from here."""
    from teg_analysis.analysis import live_scenarios

    state, snap, _ = live_snapshot()
    _, means = _live_now()
    expected = {pl: m for pl, m in means["gross"].items() if m is not None}
    expected_net = {pl: m for pl, m in means["net"].items() if m is not None}
    history = _history()
    if player is None or str(player).strip().lower() in ("", "all"):
        return live_scenarios.what_it_takes_all(snap, competition, rivals, expected, history, expected_net)
    text = str(player).strip()
    by_code = {c.lower(): c for c in snap.names}
    code = by_code.get(text.lower())
    if code is None:
        hits = [c for c, n in snap.names.items() if n.lower() == text.lower()]
        if not hits:
            hits = [c for c, n in snap.names.items() if text.lower() in n.lower().split()]
        if len(hits) != 1:
            raise ValueError(f"No single player matches '{text}'.")
        code = hits[0]
    return live_scenarios.what_it_takes(snap, code, competition, rivals, expected, history, expected_net)


# --- routes (sync def: FastAPI threadpools them) -----------------------------

@router.get("/simulation")
def simulation_page(request: Request):
    if request.query_params.get("tab") == "live":
        return templates.TemplateResponse("simulation.html", {
            "request": request, "active_page": "simulation", "wide": True, "tab": "live",
            "live_query": str(request.query_params)})
    ctx = _distributions_context(request.query_params)
    s = ctx.get("s")
    ctx["teg_num"] = s["target"] if s else None
    if s:
        ctx["notes"] = _status_notes(s["tgt"])
        ctx["shares"] = _weight_shares(s["weights"])
        ctx["fmt"] = _fmt_num
    return templates.TemplateResponse("simulation.html", {
        "request": request, "active_page": "simulation", "wide": True, "tab": "predict", **ctx})


@router.get("/simulation/distributions")
def simulation_distributions(request: Request):
    ctx = _distributions_context(request.query_params)
    return templates.TemplateResponse("partials/simulation_distributions.html", {
        "request": request, **ctx})


@router.get("/simulation/run")
def simulation_run(request: Request):
    ctx = _run_context(request.query_params)
    return templates.TemplateResponse("partials/simulation_results.html", {
        "request": request, **ctx})


@router.get("/simulation/live")
def simulation_live(request: Request):
    ctx = _live_context(request.query_params)
    return templates.TemplateResponse("partials/simulation_live.html", {
        "request": request, **ctx})


@router.get("/simulation/live/point")
def simulation_live_point(teg: int, round: int, hole: int, replay: int = 0):
    """Win chances at one hole checkpoint, as JSON for the Live tab's chart."""
    from fastapi.responses import JSONResponse

    replay_b = bool(replay)
    if replay_b and teg not in _completed_tegs():
        return JSONResponse({"error": "Not a finished TEG"}, status_code=400)
    if not replay_b and teg != wp.in_progress_teg():
        return JSONResponse({"error": "Not the TEG in progress"}, status_code=400)
    try:
        pt = _live_point(teg, replay_b, round, hole)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except Exception:
        logger.exception("live point failed")
        return JSONResponse({"error": "Calculation failed"}, status_code=500)
    return {"round": round, "hole": hole, **{m: pt[m] for m in MEASURE_KEYS}}
