"""Run the site's Predictatron (Monte Carlo) engine, with what-if overrides.

Python API (``import sim`` after ``sys.path.insert(0, "<skill>/scripts")``):

    baseline(**common)            -> dict   the site's default run for the next TEG
    whatif(**common, **settings)  -> dict   a changed run next to the baseline, with deltas
    handicap_impact(...)          -> dict   Shapley split of handicap changes vs the previous TEG
    equalising(...)               -> dict   handicap that gives each player ~36 pts/round

Common keyword args: ``target`` (TEG number), ``players`` (codes or names),
``n_sims`` (default: the site's), ``seed`` (default 0).
Settings: ``handicaps`` {player: hc}, ``exclude_tegs`` [n], ``only_tegs`` [n],
``weights`` [w1, w2, ...] (recency weights, newest TEG first), ``teg_weights`` {teg: w},
``method``, ``min_holes``, ``shrinkage``, ``field_alpha``.

CLI: ``python sim.py <baseline|whatif|handicap-impact|equalising> [--json] ...``
Run ``python sim.py <command> -h`` for the options.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
import os
import sys
from pathlib import Path


def _find_root() -> Path:
    """Folder holding ``teg_analysis/`` and ``data/``: $TEG_ROOT, /tmp/teg, or a parent of this file."""
    cands = [os.environ.get("TEG_ROOT"), "/tmp/teg", *map(str, Path(__file__).resolve().parents)]
    for c in cands:
        if c and (Path(c) / "teg_analysis").is_dir() and (Path(c) / "data").is_dir():
            return Path(c)
    raise SystemExit("error: TEG toolkit not set up. Run the setup command first "
                     "(extract teg_toolkit.zip and teg_data.zip into /tmp/teg).")


ROOT = _find_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from teg_analysis.analysis import simulation as sim  # noqa: E402
from teg_analysis.core.players import get_player_dict  # noqa: E402

DEFAULT_N_SIMS = sim.DEFAULT_SIMS  # as the site and get_predictions
DEFAULT_SEED = 1  # as webapp default_prediction, so baseline repeats get_predictions
EXCLUDED_TEGS = [50]  # TEG 50 is test data (as on the site)


class SimError(ValueError):
    """A problem the caller can fix; the message says how."""


# ------------------------------------------------------------------ players

def resolve_player(token: str, pool: dict[str, str] | None = None) -> str:
    """Player code from a code, full name, or unique name fragment (case-insensitive)."""
    pool = pool or get_player_dict()
    t = str(token).strip()
    if not t:
        raise SimError("Empty player name.")
    up = t.upper()
    if up in pool:
        return up
    low = t.lower()
    exact = [c for c, n in pool.items() if n.lower() == low]
    if len(exact) == 1:
        return exact[0]
    part = [c for c, n in pool.items() if low in n.lower()]
    if len(part) == 1:
        return part[0]
    options = ", ".join(f"{c} ({n})" for c, n in pool.items())
    why = "matches several players" if part else "is not a known player"
    raise SimError(f"'{token}' {why}. Use a code or full name. Known: {options}")


def _check_number(label: str, value, lo: float, hi: float) -> None:
    """Same limits as the site's settings form: finite and within lo..hi."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise SimError(f"{label} must be a number, got '{value}'.")
    if not math.isfinite(v) or not lo <= v <= hi:
        raise SimError(f"{label} must be between {lo:g} and {hi:g}.")


# ------------------------------------------------------------------ the run

@dataclasses.dataclass
class Run:
    result: "sim.SimulationResult"
    target: "sim.TargetTournament"
    settings: dict


def _settings_text(s: dict) -> list[str]:
    return [f"{k}={v}" for k, v in s.items() if v not in (None, [], {}, ())]


def run_scenario(
    *, target: int | None = None, players=None, n_sims: int = DEFAULT_N_SIMS,
    seed: int = DEFAULT_SEED, handicaps: dict | None = None,
    exclude_tegs=None, only_tegs=None, weights=None, teg_weights: dict | None = None,
    method: str = sim.DEFAULT_METHOD, min_holes: int = sim.DEFAULT_MIN_HOLES,
    shrinkage: float = sim.DEFAULT_SHRINKAGE, field_alpha: float = sim.DEFAULT_FIELD_ALPHA,
) -> Run:
    """One simulation of the target TEG. With no overrides it equals the site's default run."""
    pool = get_player_dict()
    codes = [resolve_player(p, pool) for p in players] if players else None
    target = sim.default_target_teg() if target is None else int(target)
    if method not in sim.METHODS:
        raise SimError(f"method must be one of {list(sim.METHODS)}")
    if not 1 <= int(n_sims) <= sim.MAX_SIMS:
        raise SimError(f"n_sims must be 1..{sim.MAX_SIMS:,}")
    _check_number("shrinkage", shrinkage, 0, 1e6)
    _check_number("field_alpha", field_alpha, 0, 200)
    if not 1 <= int(min_holes) <= 500:
        raise SimError("min_holes must be a whole number between 1 and 500.")
    for i, v in enumerate(weights or []):
        _check_number(f"weights[{i}]", v, 0, 1e6)
    for t, v in (teg_weights or {}).items():
        _check_number(f"weight for TEG {t}", v, 0, 1e6)
    try:
        tgt = sim.load_target_tournament(target, codes)
    except ValueError as exc:
        raise SimError(str(exc)) from exc

    if handicaps:
        hc = dict(tgt.handicaps)
        for who, val in handicaps.items():
            code = resolve_player(who, pool)
            if code not in hc:
                raise SimError(f"{pool.get(code, code)} is not in TEG {target}'s field "
                               f"({', '.join(tgt.players)}); add them with players=[...].")
            hc[code] = int(round(float(val)))
        tgt = dataclasses.replace(tgt, handicaps=hc)

    history = sim.load_history(teg_nums=EXCLUDED_TEGS)
    earlier = history[history["TEGNum"] < target]  # no peeking at the answer
    hist = earlier if not earlier.empty else history
    if only_tegs:
        keep = {int(t) for t in only_tegs}
        hist = hist[hist["TEGNum"].isin(keep)]
        if hist.empty:
            raise SimError(f"No history left after only_tegs={sorted(keep)}.")
    if exclude_tegs:
        hist = hist[~hist["TEGNum"].isin({int(t) for t in exclude_tegs})]
        if hist.empty:
            raise SimError("No history left after excluding those TEGs.")
    completed = sim.completed_teg_numbers(hist)
    w = sim.default_teg_weights(completed, tuple(weights) if weights else sim.DEFAULT_RECENT_WEIGHTS)
    for t, val in (teg_weights or {}).items():
        if int(t) not in w:
            raise SimError(f"TEG {t} is not in the history used (have {sorted(w)}).")
        w[int(t)] = float(val)
    if sum(w.values()) <= 0:
        raise SimError("All TEG weights are zero; give at least one TEG a weight above 0.")

    dists = sim.build_distributions(
        hist, tgt.players, w, sim.DEFAULT_SI_BOUNDARIES, float(shrinkage),
        method=method, min_holes=int(min_holes), player_weights=None, field_alpha=float(field_alpha))
    res = sim.run_simulation(dists, tgt, int(n_sims), int(seed), keep_scores=True)
    settings = {"target": target, "n_sims": int(n_sims), "seed": int(seed), "method": method,
                "min_holes": int(min_holes), "shrinkage": float(shrinkage),
                "field_alpha": float(field_alpha),
                "teg_weights": {int(t): float(v) for t, v in sorted(w.items(), reverse=True) if v > 0},
                "handicaps": dict(tgt.handicaps)}
    return Run(res, tgt, settings)


# ------------------------------------------------------------------ tables

def _se_pp(p: float, n: int) -> float:
    return 100.0 * math.sqrt(max(p * (1 - p), 0.0) / n)


def player_table(run: Run) -> pd.DataFrame:
    """One row per player: handicap, win % (Trophy = Stableford, Jacket = gross, Spoon), means."""
    res = run.result
    summ = sim.summary_table(res).set_index("Pl")
    odds = sim.odds_table(res).set_index("Pl")
    n = res.n_sims
    rows = []
    for pl in odds.index:
        rows.append({
            "Pl": pl, "Player": res.names.get(pl, pl), "Handicap": int(summ.loc[pl, "Handicap"]),
            "TrophyPct": round(odds.loc[pl, "Trophy"] * 100, 6),
            "TrophySEpp": round(_se_pp(odds.loc[pl, "Trophy"], n), 2),
            "JacketPct": round(odds.loc[pl, "Jacket"] * 100, 6),
            "SpoonPct": round(odds.loc[pl, "Spoon"] * 100, 6),
            "MeanStableford": round(float(summ.loc[pl, "MeanStableford"]), 6),
            "MeanGrossVP": round(float(summ.loc[pl, "MeanGrossVP"]), 6),
            "ExpPosStableford": round(float(summ.loc[pl, "ExpPosStableford"]), 2),
        })
    return pd.DataFrame(rows)


def _head(run: Run) -> dict:
    t = run.target
    notes = []
    if t.handicaps_draft:
        notes.append("Handicaps include a draft calculation (not yet saved for this TEG).")
    if t.random_rounds:
        notes.append(f"{t.random_rounds} round(s) have no scorecard yet: each sim draws a random "
                     f"par-72 course from {len(t.course_pool)} on file.")
    return {"teg": run.result.teg_num, "n_sims": run.result.n_sims, "seed": run.settings["seed"],
            "players": list(run.result.players), "notes": notes}


def _records(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.to_json(orient="records"))


# ------------------------------------------------------------------ commands

def baseline(**common) -> dict:
    """The site's default run (same defaults as the Predictatron page / get_predictions)."""
    allowed = {"target", "players", "n_sims", "seed"}
    bad = set(common) - allowed
    if bad:
        raise SimError(f"baseline takes only {sorted(allowed)}; use whatif for {sorted(bad)}.")
    run = run_scenario(**common)
    out = _head(run)
    out["settings"] = run.settings
    out["table"] = _records(player_table(run))
    grid = sim.position_grid(run.result, "stableford")
    out["position_pct_stableford"] = {
        run.result.names.get(pl, pl): [round(float(x) * 100, 1) for x in grid.loc[run.result.names.get(pl, pl)]]
        for pl in run.result.players}
    return out


def whatif(**kw) -> dict:
    """A changed run next to the baseline (same roster, seed, sims). Deltas are scenario minus baseline."""
    common = {k: kw[k] for k in ("target", "players", "n_sims", "seed") if k in kw}
    base = run_scenario(**common)
    scen = run_scenario(**kw)
    b, s = player_table(base).set_index("Pl"), player_table(scen).set_index("Pl")
    rows = []
    for pl in s.index:
        rows.append({
            "Pl": pl, "Player": s.loc[pl, "Player"],
            "BaseHandicap": int(b.loc[pl, "Handicap"]), "Handicap": int(s.loc[pl, "Handicap"]),
            "BaseTrophyPct": b.loc[pl, "TrophyPct"], "TrophyPct": s.loc[pl, "TrophyPct"],
            "TrophyDeltaPP": round(s.loc[pl, "TrophyPct"] - b.loc[pl, "TrophyPct"], 2),
            "BaseJacketPct": b.loc[pl, "JacketPct"], "JacketPct": s.loc[pl, "JacketPct"],
            "JacketDeltaPP": round(s.loc[pl, "JacketPct"] - b.loc[pl, "JacketPct"], 2),
            "BaseMeanStableford": b.loc[pl, "MeanStableford"], "MeanStableford": s.loc[pl, "MeanStableford"],
            "MeanStablefordDelta": round(s.loc[pl, "MeanStableford"] - b.loc[pl, "MeanStableford"], 2),
        })
    out = _head(scen)
    out["baseline_settings"] = base.settings
    out["scenario_settings"] = scen.settings
    out["table"] = _records(pd.DataFrame(rows).sort_values("TrophyPct", ascending=False))
    out["notes"].append("Deltas use the same seed (paired draws), so they are steadier than the "
                        "win % themselves, but still carry noise of a few tenths of a point.")
    return out


def handicap_impact(**kw) -> dict:
    """Shapley split: how each handicap change since the previous TEG moved every player's Trophy chance."""
    run = run_scenario(**kw)
    res = run.result
    old = sim.previous_handicaps(res.teg_num)
    if not old:
        raise SimError(f"No saved handicaps for TEG {res.teg_num - 1} to compare against.")
    imp = sim.handicap_change_impact(res, old)
    names = res.names
    out = _head(run)
    out["movers"] = [{"Pl": p, "Player": names.get(p, p), "old": imp.old_handicaps[p],
                      "new": imp.new_handicaps[p]} for p in imp.movers]
    out["no_previous_handicap"] = [names.get(p, p) for p in imp.no_previous]
    rows = []
    for j, pl in enumerate(imp.players):
        row = {"Pl": pl, "Player": names.get(pl, pl),
               "OldTrophyPct": round(float(imp.win_old[j]) * 100, 2),
               "NewTrophyPct": round(float(imp.win_new[j]) * 100, 2),
               "TotalChangePP": round(float(imp.total_change[j]), 2)}
        if imp.shapley is not None:
            for i, m in enumerate(imp.movers):
                row[f"from_{m}_PP"] = round(float(imp.shapley[i, j]), 2)
        rows.append(row)
    out["table"] = rows
    out["notes"].append("from_<code>_PP = Shapley share of the total change due to that player's "
                        "handicap change. Shares add up to TotalChangePP. Positive = better for that row's player.")
    if imp.skipped_reason:
        out["notes"].append(imp.skipped_reason)
    return out


def equalising(**kw) -> dict:
    """Handicap that gives each player about 36 Stableford points per round."""
    run = run_scenario(**kw)
    df = sim.equalising_handicaps(run.result)
    out = _head(run)
    out["target_points_per_round"] = sim.EQUALISING_TARGET
    out["table"] = _records(df.round(3))
    out["notes"].append("EqualisingHC = integer handicap whose mean Stableford per round is closest to "
                        "the target. WinStableford = Trophy share if everyone played those handicaps.")
    return out


# ------------------------------------------------------------------ text output

def _fmt_table(rows: list[dict]) -> str:
    return pd.DataFrame(rows).round(2).to_string(index=False)


def render_text(cmd: str, out: dict) -> str:
    lines = [f"TEG {out['teg']}, {out['n_sims']:,} sims, seed {out['seed']}"]
    if cmd == "handicap-impact":
        lines.append("Handicap changes: " + (", ".join(
            f"{m['Player']} {m['old']}->{m['new']}" for m in out["movers"]) or "none"))
    lines.append(_fmt_table(out["table"]))
    if cmd == "baseline":
        lines.append("Settings: " + ", ".join(_settings_text(
            {k: v for k, v in out["settings"].items() if k != "handicaps"})))
    for n in out["notes"]:
        lines.append("Note: " + n)
    return "\n".join(lines)


# ------------------------------------------------------------------ CLI

def _csv_ints(text: str) -> list[int]:
    try:
        return [int(x) for x in text.split(",") if x.strip()]
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{text}' is not a comma list of whole numbers")


def _csv_floats(text: str) -> list[float]:
    try:
        return [float(x) for x in text.split(",") if x.strip()]
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{text}' is not a comma list of numbers")


def _parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--target", type=int, help="TEG number (default: the next TEG)")
    common.add_argument("--players", help="comma list of codes or names (default: the TEG roster)")
    common.add_argument("--n-sims", type=int, default=DEFAULT_N_SIMS)
    common.add_argument("--seed", type=int, default=DEFAULT_SEED)
    common.add_argument("--json", action="store_true", help="print JSON")
    sett = argparse.ArgumentParser(add_help=False)
    sett.add_argument("--handicap", action="append", default=[], metavar="PLAYER=HC",
                      help="override a handicap, repeatable (e.g. --handicap GW=18)")
    sett.add_argument("--exclude-tegs", type=_csv_ints, help="drop these TEGs from the form history")
    sett.add_argument("--only-tegs", type=_csv_ints, help="use only these TEGs as form history")
    sett.add_argument("--weights", type=_csv_floats,
                      help="recency weights, newest TEG first (default 50,35,15; others 0)")
    sett.add_argument("--teg-weights", metavar="TEG:W,...",
                      help="explicit weight per TEG, e.g. 18:0,17:50 (others keep the default)")
    sett.add_argument("--method", choices=list(sim.METHODS), default=sim.DEFAULT_METHOD)
    sett.add_argument("--min-holes", type=int, default=sim.DEFAULT_MIN_HOLES)
    sett.add_argument("--shrinkage", type=float, default=sim.DEFAULT_SHRINKAGE,
                      help="only used by --method bands")
    sett.add_argument("--field-alpha", type=float, default=sim.DEFAULT_FIELD_ALPHA,
                      help="blend towards the field's shape, 0 = off")
    p = argparse.ArgumentParser(prog="sim.py", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("baseline", parents=[common], help="the site's default run")
    sub.add_parser("whatif", parents=[common, sett], help="changed run vs baseline")
    sub.add_parser("handicap-impact", parents=[common, sett], help="Shapley split of handicap changes")
    sub.add_parser("equalising", parents=[common, sett], help="handicaps that equalise to 36 pts/round")
    return p


def _kwargs(a: argparse.Namespace) -> dict:
    kw = {"target": a.target, "n_sims": a.n_sims, "seed": a.seed,
          "players": [x.strip() for x in a.players.split(",") if x.strip()] if a.players else None}
    if a.cmd == "baseline":
        return {k: v for k, v in kw.items() if v is not None}
    hc = {}
    for item in a.handicap:
        if "=" not in item:
            raise SimError(f"--handicap needs PLAYER=HC, got '{item}'")
        who, val = item.rsplit("=", 1)
        try:
            hc[who.strip()] = float(val)
        except ValueError:
            raise SimError(f"Handicap for '{who}' must be a number, got '{val}'")
    tw = None
    if a.teg_weights:
        tw = {}
        for item in a.teg_weights.split(","):
            try:
                t, v = item.split(":")
                tw[int(t)] = float(v)
            except ValueError:
                raise SimError(f"--teg-weights needs TEG:W pairs like 18:0,17:50, got '{item}'")
    kw.update(handicaps=hc or None, exclude_tegs=a.exclude_tegs, only_tegs=a.only_tegs,
              weights=a.weights, teg_weights=tw, method=a.method, min_holes=a.min_holes,
              shrinkage=a.shrinkage, field_alpha=a.field_alpha)
    return {k: v for k, v in kw.items() if v is not None}


COMMANDS = {"baseline": baseline, "whatif": whatif,
            "handicap-impact": handicap_impact, "equalising": equalising}


def main(argv: list[str] | None = None) -> int:
    a = _parser().parse_args(argv)
    try:
        out = COMMANDS[a.cmd](**_kwargs(a))
    except (SimError, ValueError, FileNotFoundError, KeyError) as exc:
        msg = f"{type(exc).__name__}: {exc}" if not isinstance(exc, SimError) else str(exc)
        print(json.dumps({"error": msg}) if a.json else f"error: {msg}", file=sys.stderr if not a.json else sys.stdout)
        return 1
    print(json.dumps(out, indent=1) if a.json else render_text(a.cmd, out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
