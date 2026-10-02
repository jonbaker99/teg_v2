"""Monte Carlo simulation of an upcoming TEG from per-player score distributions.

Each player's hole score (strokes vs par) is sampled from an empirical
distribution built from their history, split by hole par and stroke-index (SI)
band, recency-weighted by TEG and shrunk towards their par-level distribution
when a cell has little data. Totals, Stableford points and finishing positions
are then derived for the target tournament's actual scorecard and handicaps.

UI-agnostic: returns DataFrames/arrays only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

from teg_analysis.constants import ALL_SCORES_PARQUET

DEFAULT_SI_BOUNDARIES = (4, 9, 14)
SI_BAND_PRESETS: dict[str, tuple[int, ...]] = {
    "4 bands": (4, 9, 14),
    "3 bands": (6, 12),
    "2 bands": (9,),
    "Par only": (),
}
DEFAULT_RECENT_WEIGHTS = (50.0, 35.0, 15.0)
DEFAULT_SHRINKAGE = 10.0
DEFAULT_SIMS = 10_000
MAX_SIMS = 100_000
_PARS = (3, 4, 5)


# ---------------------------------------------------------------- SI bands

def parse_si_boundaries(text: str | Sequence[int]) -> tuple[int, ...]:
    """Parse "4,9,14" (or a sequence) into strictly ascending ints in 1..17."""
    if isinstance(text, str):
        parts = [p.strip() for p in text.replace(";", ",").split(",") if p.strip()]
    else:
        parts = list(text)
    out: list[int] = []
    for p in parts:
        try:
            f = float(p)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid SI boundary: {p!r}") from None
        if f != int(f):
            raise ValueError(f"SI boundary must be a whole number: {p!r}")
        out.append(int(f))
    if any(not 1 <= b <= 17 for b in out):
        raise ValueError("SI boundaries must be between 1 and 17")
    if any(b2 <= b1 for b1, b2 in zip(out, out[1:])):
        raise ValueError("SI boundaries must be strictly ascending")
    return tuple(out)


def si_band_labels(boundaries: Sequence[int]) -> list[str]:
    """Band labels, e.g. (4, 9, 14) -> SI 1-4, SI 5-9, SI 10-14, SI 15-18."""
    if not boundaries:
        return ["All SI"]
    edges = [0, *boundaries, 18]
    labels = []
    for lo, hi in zip(edges, edges[1:]):
        lo += 1
        labels.append(f"SI {lo}" if lo == hi else f"SI {lo}-{hi}")
    return labels


def assign_si_band(si, boundaries: Sequence[int]) -> np.ndarray:
    """Band index 0..len(boundaries) per SI (SI equal to a boundary is in the lower band)."""
    return np.searchsorted(np.asarray(boundaries, dtype=int), np.asarray(si), side="left")


# ---------------------------------------------------------------- history

def load_history(teg_nums: Iterable[int] | None = None) -> pd.DataFrame:
    """Played holes from all-scores.parquet. ``teg_nums`` are TEGs to *exclude*."""
    from teg_analysis.io.file_operations import read_file

    df = read_file(ALL_SCORES_PARQUET)
    df = df[df["Sc"].notna()].copy()
    if teg_nums is not None:
        df = df[~df["TEGNum"].isin(list(teg_nums))]
    df["TEGNum"] = df["TEGNum"].astype(int)
    df["PAR"] = df["PAR"].astype(int)
    df["SI"] = df["SI"].astype(int)
    df["GrossVP"] = (df["Sc"] - df["PAR"]).round().astype(int)
    return df.reset_index(drop=True)


def completed_teg_numbers(history: pd.DataFrame) -> list[int]:
    """Distinct TEG numbers in history, most recent first."""
    return sorted((int(t) for t in history["TEGNum"].unique()), reverse=True)


def default_teg_weights(
    teg_nums_desc: list[int], weights: Sequence[float] = DEFAULT_RECENT_WEIGHTS
) -> dict[int, float]:
    """Weights for the most recent TEGs (first in ``teg_nums_desc``); all others 0."""
    return {int(t): (float(weights[i]) if i < len(weights) else 0.0)
            for i, t in enumerate(teg_nums_desc)}


# ---------------------------------------------------------------- target

@dataclass
class TargetTournament:
    teg_num: int
    holes: pd.DataFrame
    players: list[str]
    handicaps: dict[str, int]
    names: dict[str, str]


def available_target_tegs() -> list[int]:
    """TEG numbers with a scorecard in round_pars.csv, newest first."""
    from teg_analysis.analysis.round_setup import _read_round_pars

    rp = _read_round_pars()
    if rp.empty:
        return []
    return sorted((int(t) for t in rp["TEGNum"].dropna().unique()), reverse=True)


def load_target_tournament(teg_num: int | None = None) -> TargetTournament:
    """Scorecard, roster and handicaps for a future TEG (default: latest in round_pars)."""
    from teg_analysis.analysis.round_setup import _read_round_pars
    from teg_analysis.analysis.teg_setup import _read_handicaps_raw, _read_rosters_raw
    from teg_analysis.core.players import get_player_dict

    rp = _read_round_pars()
    if rp.empty:
        raise ValueError("No round pars set up (data/round_pars.csv is empty or missing)")
    if teg_num is None:
        teg_num = max(int(t) for t in rp["TEGNum"].unique())
    teg_num = int(teg_num)
    holes = rp[rp["TEGNum"].astype(int) == teg_num]
    if holes.empty:
        raise ValueError(f"No round pars for TEG {teg_num}")
    holes = holes[["Round", "Hole", "Par", "SI"]].astype(int).sort_values(
        ["Round", "Hole"]).reset_index(drop=True)

    ros = _read_rosters_raw()
    if not ros.empty:
        ros = ros[ros["TEGNum"].astype(int) == teg_num]
        playing = ros["Playing"].astype(str).str.lower().isin(["true", "1", "yes"])
        players = [str(p) for p in ros.loc[playing, "Pl"]]
    else:
        players = []
    if not players:
        raise ValueError(f"No players on the roster for TEG {teg_num}")

    hc = _read_handicaps_raw()
    row = hc[hc["TEG"].astype(str).str.strip() == f"TEG {teg_num}"]
    handicaps: dict[str, int] = {}
    missing = []
    for p in players:
        val = row[p].iloc[0] if (not row.empty and p in row.columns) else np.nan
        if pd.isna(val) or str(val).strip() == "":
            missing.append(p)
        else:
            handicaps[p] = int(round(float(val)))
    if missing:
        raise ValueError(f"No handicap for TEG {teg_num} player(s): {', '.join(missing)}")

    pdict = get_player_dict()
    return TargetTournament(teg_num, holes, players, handicaps,
                            {p: pdict.get(p, p) for p in players})


# ---------------------------------------------------------------- distributions

@dataclass
class ScoreDistributions:
    boundaries: tuple[int, ...]
    probs: pd.DataFrame
    cells: pd.DataFrame
    warnings: list[str] = field(default_factory=list)


def _weighted_hist(vp: np.ndarray, w: np.ndarray, vmin: int, size: int) -> np.ndarray:
    """Normalised weighted histogram of ``vp`` over support vmin..vmin+size-1 (zeros if empty)."""
    h = np.bincount(vp - vmin, weights=w, minlength=size).astype(float)
    s = h.sum()
    return h / s if s > 0 else h


def build_distributions(
    history: pd.DataFrame,
    players: Sequence[str],
    teg_weights: dict[int, float],
    boundaries: Sequence[int] = DEFAULT_SI_BOUNDARIES,
    shrinkage: float = DEFAULT_SHRINKAGE,
    pars: Sequence[int] = _PARS,
) -> ScoreDistributions:
    """Per player/par/SI-band GrossVP distributions, recency-weighted and shrunk to par level."""
    boundaries = tuple(boundaries)
    labels = si_band_labels(boundaries)
    n_bands = len(labels)
    k = float(shrinkage)
    warnings: list[str] = []

    h = history[["TEGNum", "Pl", "PAR", "SI", "GrossVP"]].copy()
    vmin, vmax = int(h["GrossVP"].min()), int(h["GrossVP"].max())
    size = vmax - vmin + 1
    support = np.arange(vmin, vmax + 1)
    h["w"] = h["TEGNum"].map(lambda t: float(teg_weights.get(int(t), 0.0))).astype(float)
    h["band"] = assign_si_band(h["SI"].to_numpy(), boundaries)
    vp_all = h["GrossVP"].to_numpy().astype(int)
    w_all = h["w"].to_numpy()
    pl_all = h["Pl"].to_numpy()
    par_all = h["PAR"].to_numpy()
    band_all = h["band"].to_numpy()

    def kish(w: np.ndarray) -> float:
        return float(w.sum() ** 2 / (w ** 2).sum()) if len(w) and (w ** 2).sum() > 0 else 0.0

    prob_rows: list[pd.DataFrame] = []
    cell_rows: list[dict] = []

    for pl in players:
        pmask = pl_all == pl
        for par in pars:
            m = pmask & (par_all == par) & (w_all > 0)
            fallback: str | None = None
            if m.any():
                p_par = _weighted_hist(vp_all[m], w_all[m], vmin, size)
            else:
                m_hist = pmask & (par_all == par)
                if m_hist.any():
                    fallback = "history fallback"
                    p_par = _weighted_hist(vp_all[m_hist], np.ones(m_hist.sum()), vmin, size)
                    warnings.append(f"{pl} par {par}: no data in weighted TEGs, "
                                    "used the player's full history")
                else:
                    fm = (par_all == par) & (w_all > 0)
                    if fm.any():
                        p_par = _weighted_hist(vp_all[fm], w_all[fm], vmin, size)
                    else:
                        fm = par_all == par
                        p_par = _weighted_hist(vp_all[fm], np.ones(fm.sum()), vmin, size)
                    fallback = "field fallback"
                    warnings.append(f"{pl} par {par}: no history at all, used the field distribution")
            for b in range(n_bands):
                mc = m & (band_all == b)
                n = int(mc.sum())
                eff = kish(w_all[mc]) if n else 0.0
                if fallback:
                    final, src, n, eff = p_par, fallback, 0, 0.0
                elif n == 0:
                    final, src = p_par, "par fallback"
                else:
                    p_cell = _weighted_hist(vp_all[mc], w_all[mc], vmin, size)
                    final = (eff * p_cell + k * p_par) / (eff + k) if eff + k > 0 else p_cell
                    src = "cell"
                nz = np.flatnonzero(final > 0)
                prob_rows.append(pd.DataFrame({
                    "Pl": pl, "Par": par, "Band": b,
                    "GrossVP": support[nz].astype(int), "Prob": final[nz]}))
                cell_rows.append({
                    "Pl": pl, "Par": par, "Band": b, "BandLabel": labels[b], "N": n,
                    "EffN": eff, "MeanVP": float((final * support).sum()), "Source": src})

    probs = (pd.concat(prob_rows, ignore_index=True) if prob_rows else
             pd.DataFrame(columns=["Pl", "Par", "Band", "GrossVP", "Prob"]))
    cells = pd.DataFrame(cell_rows)
    return ScoreDistributions(boundaries, probs, cells, warnings)


# ---------------------------------------------------------------- simulation

@dataclass
class SimulationResult:
    players: list[str]
    names: dict[str, str]
    n_sims: int
    teg_num: int
    par_total: int
    gross: np.ndarray
    stableford: np.ndarray
    gross_pos: np.ndarray
    stableford_pos: np.ndarray
    handicaps: dict[str, int] = field(default_factory=dict)


def _positions(totals: np.ndarray, rng: np.random.Generator, higher_better: bool) -> np.ndarray:
    """Finishing position 1..n per row; ties broken uniformly at random."""
    key = totals.astype(np.float64)
    if higher_better:
        key = -key
    key = key + rng.random(key.shape) * 0.5
    return (np.argsort(np.argsort(key, axis=1), axis=1) + 1).astype(np.int8)


def run_simulation(
    dists: ScoreDistributions,
    target: TargetTournament,
    n_sims: int = DEFAULT_SIMS,
    seed: int | None = None,
) -> SimulationResult:
    """Simulate the target tournament ``n_sims`` times (clamped to 1..MAX_SIMS)."""
    n_sims = int(min(max(int(n_sims), 1), MAX_SIMS))
    holes = target.holes
    par = holes["Par"].to_numpy(dtype=int)
    si = holes["SI"].to_numpy(dtype=int)
    bad = sorted(set(par.tolist()) - set(_PARS))
    if bad:
        raise ValueError(f"Unsupported par value(s) in target scorecard: {bad}")
    band = assign_si_band(si, dists.boundaries)
    n_holes = len(par)
    rng = np.random.default_rng(seed)

    # (Pl, Par, Band) -> (support values, cdf)
    groups = {key: g for key, g in dists.probs.groupby(["Pl", "Par", "Band"])}

    n_pl = len(target.players)
    gross = np.empty((n_sims, n_pl), dtype=np.int32)
    stab = np.empty((n_sims, n_pl), dtype=np.int32)
    keys = np.unique(par * 100 + band)
    for j, pl in enumerate(target.players):
        hc = int(target.handicaps[pl])
        strokes = hc // 18 + ((hc % 18) >= si).astype(int)
        u = rng.random((n_sims, n_holes))
        vp = np.empty((n_sims, n_holes), dtype=np.int8)
        for key in keys:
            p, b = int(key // 100), int(key % 100)
            g = groups.get((pl, p, b))
            if g is None:
                raise ValueError(f"No distribution for player {pl}, par {p}, band {b}")
            vals = g["GrossVP"].to_numpy()
            cdf = np.cumsum(g["Prob"].to_numpy())
            cdf /= cdf[-1]
            cols = np.flatnonzero((par == p) & (band == b))
            idx = np.minimum(np.searchsorted(cdf, u[:, cols], side="right"), len(vals) - 1)
            vp[:, cols] = vals[idx]
        gross[:, j] = vp.sum(axis=1, dtype=np.int32) + int(par.sum())
        net_vp = vp.astype(np.int16) - strokes.astype(np.int16)
        stab[:, j] = np.maximum(0, 2 - net_vp).sum(axis=1, dtype=np.int32)

    return SimulationResult(
        players=list(target.players), names=dict(target.names), n_sims=n_sims,
        teg_num=target.teg_num, par_total=int(par.sum()), gross=gross, stableford=stab,
        gross_pos=_positions(gross, rng, higher_better=False),
        stableford_pos=_positions(stab, rng, higher_better=True),
        handicaps=dict(target.handicaps))


# ---------------------------------------------------------------- summaries

def summary_table(result: SimulationResult) -> pd.DataFrame:
    """One row per player (sorted by mean gross) with totals, percentiles, win odds, expected position."""
    rows = []
    for j, pl in enumerate(result.players):
        g, s = result.gross[:, j], result.stableford[:, j]
        rows.append({
            "Pl": pl, "Player": result.names.get(pl, pl),
            "Handicap": result.handicaps.get(pl),
            "MeanGross": float(g.mean()), "MeanGrossVP": float(g.mean() - result.par_total),
            "MeanStableford": float(s.mean()),
            "P10Gross": float(np.percentile(g, 10)), "P90Gross": float(np.percentile(g, 90)),
            "P10Stableford": float(np.percentile(s, 10)),
            "P90Stableford": float(np.percentile(s, 90)),
            "WinGross": float((result.gross_pos[:, j] == 1).mean()),
            "WinStableford": float((result.stableford_pos[:, j] == 1).mean()),
            "ExpPosGross": float(result.gross_pos[:, j].mean()),
            "ExpPosStableford": float(result.stableford_pos[:, j].mean()),
        })
    return pd.DataFrame(rows).sort_values("MeanGross").reset_index(drop=True)


def _measure(result: SimulationResult, measure: str) -> tuple[np.ndarray, np.ndarray]:
    if measure == "gross":
        return result.gross, result.gross_pos
    if measure == "stableford":
        return result.stableford, result.stableford_pos
    raise ValueError("measure must be 'gross' or 'stableford'")


def position_grid(result: SimulationResult, measure: str) -> pd.DataFrame:
    """Fraction of sims each player finishes in each position (rows sum to 1)."""
    _, pos = _measure(result, measure)
    n = len(result.players)
    grid = np.stack([(pos == p).mean(axis=0) for p in range(1, n + 1)], axis=1)
    df = pd.DataFrame(grid, index=[result.names.get(p, p) for p in result.players],
                      columns=list(range(1, n + 1)))
    order = pos.mean(axis=0).argsort(kind="stable")
    return df.iloc[order]


def total_distribution(result: SimulationResult, measure: str) -> pd.DataFrame:
    """Histogram of simulated totals per player: Pl, Player, Total, Fraction."""
    tot, _ = _measure(result, measure)
    frames = []
    for j, pl in enumerate(result.players):
        vals, counts = np.unique(tot[:, j], return_counts=True)
        frames.append(pd.DataFrame({
            "Pl": pl, "Player": result.names.get(pl, pl),
            "Total": vals.astype(int), "Fraction": counts / tot.shape[0]}))
    return pd.concat(frames, ignore_index=True)
