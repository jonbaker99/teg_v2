"""Simulation dashboard: /simulation (TEG simulator driven by analysis.simulation)."""

import logging
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from teg_analysis.analysis import simulation as sim
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


def _clear_caches() -> None:
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
    return sim.build_distributions(
        _history_before(history, s["target"]), tgt.players, s["weights"],
        s["boundaries"], s["k"], method=s["method"], min_holes=s["min_holes"],
        player_weights=s["player_weights"] or None, field_alpha=s["field_alpha"])


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
        res = sim.run_simulation(dists, tgt, s["n_sims"], s["seed"])
        measures = []
        for key, label in (("gross", "Gross"), ("stableford", "Stableford")):
            cols, grid = _grid_rows(res, key)
            measures.append({
                "key": key, "label": label, "summary": _summary_rows(res, key),
                "grid_cols": cols, "grid": grid, "chart_json": _chart_json(res, key)})
        return {
            "measures": measures,
            "caption": _caption(res, s, len(tgt.holes) + 18 * tgt.random_rounds),
            "courses": _courses_drawn(res, tgt),
            "clamp_note": s["clamp_note"], "warnings": dists.warnings,
            "teg_num": res.teg_num,
        }
    except ValueError as exc:  # setup problems (missing handicap, no scorecard pool)
        logger.warning("Simulation setup: %s", exc)
        return {"fatal": f"Can't simulate yet: {exc}. Check the TEG setup (roster and handicaps)."}
    except Exception:
        logger.exception("simulation run failed")
        return {"fatal": "Couldn't run the simulation."}


# --- routes (sync def: FastAPI threadpools them) -----------------------------

@router.get("/simulation")
def simulation_page(request: Request):
    ctx = _distributions_context(request.query_params)
    s = ctx.get("s")
    ctx["teg_num"] = s["target"] if s else None
    if s:
        ctx["notes"] = _status_notes(s["tgt"])
        ctx["shares"] = _weight_shares(s["weights"])
        ctx["fmt"] = _fmt_num
    return templates.TemplateResponse("simulation.html", {
        "request": request, "active_page": "simulation", "wide": True, **ctx})


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
