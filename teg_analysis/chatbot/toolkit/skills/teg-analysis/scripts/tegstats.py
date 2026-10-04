"""Tested helpers that encode the site's definitions, for ad-hoc TEG analysis.

    import sys; sys.path.insert(0, "/tmp/teg/skills/teg-analysis/scripts")
    import tegstats as ts
    f = ts.load_frames()        # f.holes, f.rounds, f.tegs, f.winners
    ts.describe_data(f)

Definitions match the site and ``reference/rules.md``: net competition is NetVP up to
TEG 7 and Stableford from TEG 8; ranks use ``method="min"`` so ties share a position.
Works on pandas 2 and 3.
"""
from __future__ import annotations

import dataclasses
import os
import sys
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
import pandas as pd


def _find_root() -> Path:
    cands = [os.environ.get("TEG_ROOT"), "/tmp/teg", *map(str, Path(__file__).resolve().parents)]
    for c in cands:
        if c and (Path(c) / "teg_analysis").is_dir() and (Path(c) / "data").is_dir():
            return Path(c)
    raise RuntimeError("TEG toolkit not set up. Run the setup command first "
                       "(extract teg_toolkit.zip and teg_data.zip into /tmp/teg).")


ROOT = _find_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from teg_analysis.analysis.aggregation import STABLEFORD_ERA_TEG  # noqa: E402
from teg_analysis.analysis.scoring import get_net_competition_measure  # noqa: E402
from teg_analysis.analysis.standings import build_rounds, build_tegs, trophy_rank  # noqa: E402,F401

SMALL_N = 30  # below this, say the sample is small
_HOLE_COLS = ["Player", "Pl", "TEGNum", "Year", "Area", "Course", "Date", "Round", "Hole",
              "FrontBack", "PAR", "SI", "HC", "HCStrokes", "Sc", "GrossVP", "NetVP", "Stableford"]


# ------------------------------------------------------------------ loading

@dataclasses.dataclass
class Frames:
    holes: pd.DataFrame    # one row per player per hole
    rounds: pd.DataFrame   # one row per player per round
    tegs: pd.DataFrame     # one row per player per TEG
    winners: pd.DataFrame  # official winners per completed TEG (incl. manual overrides)
    complete: set


def load_frames() -> Frames:
    """Holes, rounds, tegs and winners from the attached data, as the site defines them.

    Excludes TEG 50 (test data). Includes in-progress TEGs; ``tegs.Complete`` flags them.
    """
    from teg_analysis.analysis.history import get_teg_winners
    from teg_analysis.core.data_loader import load_all_data
    from teg_analysis.io.file_operations import read_file

    raw = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
    if raw.empty:
        raise RuntimeError("No data loaded. Is /tmp/teg/data/all-data.parquet present?")
    complete = {int(t) for t in read_file("data/completed_tegs.csv")["TEGNum"]}
    holes = raw[[c for c in _HOLE_COLS if c in raw.columns]].copy()
    if "Date" in holes.columns:
        holes["Date"] = pd.to_datetime(holes["Date"], format="%d/%m/%Y", errors="coerce").dt.date
    holes = holes.sort_values(["TEGNum", "Round", "Player", "Hole"]).reset_index(drop=True)
    winners = get_teg_winners(raw)
    done = winners["TEG"].astype(str).str.extract(r"(\d+)")[0].astype(int).isin(complete)
    return Frames(holes, build_rounds(raw), build_tegs(raw, complete),
                  winners[done].reset_index(drop=True), complete)


def load_precomputed(name: str | None = None) -> pd.DataFrame | list[str]:
    """One of the site's already-calculated tables (see reference/precomputed.md).

    ``load_precomputed()`` lists the names that are available.
    """
    folder = ROOT / "data"
    avail = sorted(p.stem for p in folder.glob("*.parquet")
                   if p.stem not in ("all-data", "all-scores"))
    if name is None:
        return avail
    key = str(name).removeprefix("data/").removesuffix(".parquet")
    if key not in avail:
        raise ValueError(f"No precomputed table '{name}'. Available: {', '.join(avail) or 'none'}")
    return pd.read_parquet(folder / f"{key}.parquet")


def describe_data(frames: Frames | None = None) -> None:
    """Print each frame's shape and columns, the TEGs covered, and the players."""
    f = frames or load_frames()
    for name in ("holes", "rounds", "tegs", "winners"):
        df = getattr(f, name)
        print(f"{name}: {len(df):,} rows\n  columns: {', '.join(map(str, df.columns))}")
    t = f.tegs
    inprog = sorted(set(t["TEGNum"]) - set(f.complete))
    print(f"TEGs {int(t['TEGNum'].min())}-{int(t['TEGNum'].max())}; "
          f"complete: {len(f.complete)}; in progress: {inprog or 'none'}")
    print("players: " + ", ".join(f"{p} ({n})" for p, n in
                                  t.groupby("Pl")["Player"].first().items()))
    print(f"net competition: NetVP up to TEG {STABLEFORD_ERA_TEG - 1}, "
          f"Stableford from TEG {STABLEFORD_ERA_TEG}")


# ------------------------------------------------------------------ definitions

def net_measure(teg_num: int) -> str:
    """'NetVP' (lowest wins) up to TEG 7, 'Stableford' (highest wins) from TEG 8."""
    return get_net_competition_measure(int(teg_num))


def net_score(df: pd.DataFrame) -> pd.Series:
    """Per-row net-competition value: NetVP in the early era, Stableford from TEG 8."""
    era_stab = df["TEGNum"].astype(int) >= STABLEFORD_ERA_TEG
    return df["Stableford"].where(era_stab, df["NetVP"])


def rank_min(df: pd.DataFrame, value: str, by: list[str] | None = None,
             ascending: bool = True) -> pd.Series:
    """Tie-aware rank (method="min"): equal values share the best position. Missing values get <NA>."""
    r = df.groupby(by)[value].rank(method="min", ascending=ascending) if by \
        else df[value].rank(method="min", ascending=ascending)
    return r.astype("Int64")  # NaN values stay <NA>


def top_n(df: pd.DataFrame, value: str, n: int = 5, ascending: bool = False,
          by: list[str] | None = None) -> pd.DataFrame:
    """Top ``n`` rows by ``value``, tie-complete: every row tied at rank <= n is kept.

    Adds a ``Rank`` column. ``ascending=True`` for lowest-is-best measures (GrossVP, NetVP).
    """
    out = df.copy()
    out["Rank"] = rank_min(out, value, by, ascending)
    sort_cols = (by or []) + ["Rank"]
    return out[(out["Rank"] <= n).fillna(False).astype(bool)].sort_values(sort_cols, kind="stable")


# ------------------------------------------------------------------ uncertainty

def bootstrap_ci(x, stat: Callable = np.mean, n_boot: int = 5000, ci: float = 0.95,
                 seed: int = 0) -> dict:
    """Percentile bootstrap CI for ``stat(x)``. Returns est, lo, hi, n, small_n."""
    a = np.asarray(x, dtype=float)
    a = a[~np.isnan(a)]
    n = len(a)
    if n == 0:
        return {"est": np.nan, "lo": np.nan, "hi": np.nan, "n": 0, "small_n": True}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    boots = np.apply_along_axis(stat, 1, a[idx]) if stat is not np.mean else a[idx].mean(axis=1)
    lo, hi = np.percentile(boots, [(1 - ci) / 2 * 100, (1 + ci) / 2 * 100])
    return {"est": float(stat(a)), "lo": float(lo), "hi": float(hi), "n": n, "small_n": n < SMALL_N}


def bootstrap_diff_ci(a, b, n_boot: int = 5000, ci: float = 0.95, seed: int = 0) -> dict:
    """Bootstrap CI for mean(a) - mean(b), resampling each group separately."""
    a = np.asarray(a, dtype=float); a = a[~np.isnan(a)]
    b = np.asarray(b, dtype=float); b = b[~np.isnan(b)]
    if len(a) == 0 or len(b) == 0:
        return {"diff": np.nan, "lo": np.nan, "hi": np.nan, "n_a": len(a), "n_b": len(b),
                "small_n": True}
    rng = np.random.default_rng(seed)
    ma = a[rng.integers(0, len(a), size=(n_boot, len(a)))].mean(axis=1)
    mb = b[rng.integers(0, len(b), size=(n_boot, len(b)))].mean(axis=1)
    lo, hi = np.percentile(ma - mb, [(1 - ci) / 2 * 100, (1 + ci) / 2 * 100])
    return {"diff": float(a.mean() - b.mean()), "lo": float(lo), "hi": float(hi),
            "n_a": len(a), "n_b": len(b), "small_n": min(len(a), len(b)) < SMALL_N,
            "excludes_zero": bool(lo > 0 or hi < 0)}


def small_sample(n: int, threshold: int = SMALL_N) -> bool:
    """True when ``n`` is too small to lean on."""
    return int(n) < threshold


# ------------------------------------------------------------------ own-baseline comparison

def vs_own_baseline(df: pd.DataFrame, metric: str, situation: pd.Series,
                    player_col: str = "Pl", n_boot: int = 2000, seed: int = 0) -> pd.DataFrame:
    """Each player's ``metric`` in a situation vs their own other rows.

    ``situation`` is a boolean Series aligned to ``df`` (e.g. ``df.Hole == 18``).
    Returns one row per player (n_in, mean_in, n_out, mean_out, diff, CI, small_n) plus an
    ``ALL`` row: the n_in-weighted mean of the player diffs, with a bootstrap CI that
    resamples within each player. Players with no rows in either group are dropped.
    A player is only ever compared with themselves, which removes who is simply better.
    """
    mask = situation.reindex(df.index).fillna(False).astype(bool)
    rng = np.random.default_rng(seed)
    rows, groups = [], []
    for pl, g in df.groupby(player_col):
        a = g.loc[mask.loc[g.index], metric].dropna().to_numpy(dtype=float)
        b = g.loc[~mask.loc[g.index], metric].dropna().to_numpy(dtype=float)
        if len(a) == 0 or len(b) == 0:
            continue
        ci = bootstrap_diff_ci(a, b, n_boot=n_boot, seed=int(rng.integers(1 << 31)))
        rows.append({player_col: pl, "n_in": len(a), "mean_in": a.mean(), "n_out": len(b),
                     "mean_out": b.mean(), "diff": ci["diff"], "lo": ci["lo"], "hi": ci["hi"],
                     "small_n": ci["small_n"]})
        groups.append((a, b))
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    w = out["n_in"].to_numpy(dtype=float)
    est = float((out["diff"] * w).sum() / w.sum())
    boots = np.empty(n_boot)
    for k in range(n_boot):
        d = [a[rng.integers(0, len(a), len(a))].mean() - b[rng.integers(0, len(b), len(b))].mean()
             for a, b in groups]
        boots[k] = np.dot(d, w) / w.sum()
    lo, hi = np.percentile(boots, [2.5, 97.5])
    allrow = {player_col: "ALL", "n_in": int(w.sum()), "mean_in": np.nan,
              "n_out": int(out["n_out"].sum()), "mean_out": np.nan, "diff": est,
              "lo": float(lo), "hi": float(hi), "small_n": bool(w.sum() < SMALL_N)}
    return pd.concat([out, pd.DataFrame([allrow])], ignore_index=True)


# ------------------------------------------------------------------ counterfactual re-scoring

def strokes_received(hc, si):
    """Strokes a player on handicap ``hc`` gets at stroke index ``si``: hc//18 + (hc%18 >= si)."""
    hc = np.asarray(hc)
    si = np.asarray(si)
    return hc // 18 + ((hc % 18) >= si).astype(int)


def rescore(holes: pd.DataFrame, handicaps: dict | None = None, delta: dict | None = None,
            teg: int | None = None) -> pd.DataFrame:
    """Copy of ``holes`` re-scored on other handicaps (same stroke allocation as the site).

    ``handicaps`` {player code or full name: new HC}; ``delta`` {player: change to add};
    ``teg`` limits the change to one TEG (default all). Updates HC, HCStrokes, NetVP and
    Stableford (``Stableford = max(0, 2 - NetVP)``); the originals are kept as ``*_orig``.
    Gross scores do not change. Feed the result to ``build_rounds`` / ``build_tegs`` to see
    totals and positions under the new handicaps.
    """
    out = holes.copy()
    for c in ("HC", "HCStrokes", "NetVP", "Stableford"):
        out[c + "_orig"] = out[c]
    who = out["Pl"].astype(str)
    name = out["Player"].astype(str)
    in_teg = np.ones(len(out), dtype=bool) if teg is None else (out["TEGNum"] == int(teg)).to_numpy()
    new_hc = out["HC"].to_numpy(dtype=float).copy()
    for spec, add in ((handicaps or {}, False), (delta or {}, True)):
        for p, val in spec.items():
            m = ((who == str(p).upper()) | (name.str.lower() == str(p).lower())).to_numpy() & in_teg
            if not m.any():
                raise ValueError(f"No holes for player '{p}' (teg={teg}).")
            new_hc[m] = new_hc[m] + val if add else val
    new_hc = np.rint(new_hc)
    out["HC"] = new_hc.astype(out["HC"].dtype) if pd.api.types.is_integer_dtype(out["HC"]) else new_hc
    hc = new_hc.astype(int)
    out["HCStrokes"] = strokes_received(hc, out["SI"].to_numpy(dtype=int)).astype(float)
    out["NetVP"] = out["GrossVP"] - out["HCStrokes"]
    out["Stableford"] = (2 - out["NetVP"]).clip(lower=0)
    return out
