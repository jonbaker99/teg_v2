"""Monte Carlo simulation of an upcoming TEG from per-player score distributions.

Each player's hole score (strokes vs par) is sampled from an empirical
distribution built from their history, split by hole par and stroke index (SI)
and recency-weighted by TEG. By default a rolling SI window widens around the
target SI pair until it holds enough holes; fixed SI bands shrunk towards the
par-level distribution are also available. Totals, Stableford points and
finishing positions are then derived for the target tournament's actual
scorecard and handicaps.

UI-agnostic: returns DataFrames/arrays only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

from teg_analysis.constants import (ALL_SCORES_PARQUET, COURSE_PARS_CSV,
                                    ROUND_INFO_CSV)

DEFAULT_SI_BOUNDARIES = (4, 9, 14)
SI_BAND_PRESETS: dict[str, tuple[int, ...]] = {
    "4 bands": (4, 9, 14),
    "3 bands": (6, 12),
    "2 bands": (9,),
    "Par only": (),
}
METHODS = {"window": "Rolling SI window", "bands": "Fixed SI bands"}
DEFAULT_METHOD = "window"
DEFAULT_MIN_HOLES = 20
_WINDOW_BOUNDARIES = (2, 4, 6, 8, 10, 12, 14, 16)  # SI pairs 1-2 ... 17-18
DEFAULT_RECENT_WEIGHTS = (50.0, 35.0, 15.0)
DEFAULT_SHRINKAGE = 10.0
DEFAULT_SIMS = 10_000
MAX_SIMS = 100_000
_PARS = (3, 4, 5)
DEFAULT_FIELD_ALPHA = 5.0  # backtest TEGs 8-18: removes impossible outcomes (most of the log-lik gain) while birdies stay within ~8% of actual; higher alpha over-predicts birdies
FIELD_VP_MIN, FIELD_VP_MAX = -3, 8  # GrossVP clamp for the (shifted) field component


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

COMPLETED_TEGS_CSV = "data/completed_tegs.csv"
IN_PROGRESS_TEGS_CSV = "data/in_progress_tegs.csv"
DEFAULT_ROUNDS = 4
_REQUIRED_PAR_TOTAL = 72


@dataclass
class TargetTournament:
    """Upcoming TEG: fixed-scorecard holes plus ``random_rounds`` of random courses."""
    teg_num: int
    holes: pd.DataFrame            # Round, Hole, Par, SI of rounds with a real scorecard (may be empty)
    players: list[str]
    handicaps: dict[str, int]
    names: dict[str, str]
    random_rounds: int = 0         # rounds with no scorecard yet: a random course per sim
    course_pool: list = field(default_factory=list)  # [(course name, par[18], si[18])]
    handicaps_draft: bool = False  # some handicap came from the draft calc, not handicaps.csv
    candidates: list[str] = field(default_factory=list)  # codes with a handicap available
    n_rounds: int = 0


# Thin readers (module-level so tests can monkeypatch them).

def _read_csv(path: str) -> pd.DataFrame:
    from teg_analysis.io.file_operations import read_file

    return read_file(path)


def _read_round_pars() -> pd.DataFrame:
    from teg_analysis.analysis.round_setup import _read_round_pars as f

    return f()


def _read_rosters_raw() -> pd.DataFrame:
    from teg_analysis.analysis.teg_setup import _read_rosters_raw as f

    return f()


def _read_handicaps_raw() -> pd.DataFrame:
    from teg_analysis.analysis.teg_setup import _read_handicaps_raw as f

    return f()


def _playing_codes(teg_num: int):
    from teg_analysis.analysis.teg_setup import playing_codes

    return playing_codes(teg_num)


def _draft_handicaps(teg_num: int) -> dict[str, int]:
    """Calculated (unsaved) handicaps for ``teg_num``; {} if they can't be calculated."""
    from teg_analysis.analysis.handicaps import get_hc

    try:
        df = get_hc(teg_num)
    except Exception:  # noqa: BLE001 - a draft is a convenience, never fatal
        return {}
    return {str(r.Pl): int(r.hc) for r in df.itertuples()} if len(df) else {}


def _players_of_teg(teg_num: int) -> list[str]:
    df = _read_csv(ALL_SCORES_PARQUET)
    df = df[df["Sc"].notna() & (df["TEGNum"].astype(int) == int(teg_num))]
    return sorted(str(p) for p in df["Pl"].unique())


def _player_dict() -> dict[str, str]:
    from teg_analysis.core.players import get_player_dict

    return get_player_dict()


def _tegnums(df: pd.DataFrame) -> list[int]:
    if df is None or df.empty or "TEGNum" not in df.columns:
        return []
    return [int(t) for t in pd.to_numeric(df["TEGNum"], errors="coerce").dropna().unique()]


def default_target_teg() -> int:
    """TEG in progress (in_progress_tegs.csv), else the one after the last completed TEG."""
    def nums(path: str) -> list[int]:
        try:
            return _tegnums(_read_csv(path))
        except (FileNotFoundError, pd.errors.EmptyDataError):
            return []

    done = nums(COMPLETED_TEGS_CSV)
    inp = [t for t in nums(IN_PROGRESS_TEGS_CSV) if t not in done]  # stale rows ignored
    if inp:
        return min(inp)
    return (max(done) if done else 0) + 1


def available_target_tegs() -> list[int]:
    """The default target TEG plus any later TEG with a scorecard, newest first.

    A finished TEG is no longer offered.
    """
    d = default_target_teg()
    rp = _read_round_pars()
    return sorted({d} | {t for t in _tegnums(rp) if t >= d}, reverse=True)


def _course_pool() -> list:
    """Courses from course_pars.csv with a valid 18-hole, par-72, SI 1..18 card."""
    df = _read_csv(COURSE_PARS_CSV)
    pool = []
    for name, g in df.groupby("Course", sort=True):
        g = g.sort_values("Hole")
        if len(g) != 18 or sorted(g["Hole"].astype(int)) != list(range(1, 19)):
            continue
        par = g["Par"].to_numpy(dtype=int)
        si = g["SI"].to_numpy(dtype=int)
        if int(par.sum()) != _REQUIRED_PAR_TOTAL or sorted(si.tolist()) != list(range(1, 19)):
            continue
        pool.append((str(name), par, si))
    return pool


def load_target_tournament(teg_num: int | None = None,
                           players: Sequence[str] | None = None) -> TargetTournament:
    """Roster, handicaps and course(s) for a future TEG (default: ``default_target_teg()``).

    Rounds with a scorecard in round_pars.csv use it; the rest (up to the TEG's
    round count from round_info.csv, else 4) become ``random_rounds``, each
    sampled from ``course_pool`` per sim. ``players`` (codes) overrides the roster.
    Handicaps come from handicaps.csv ("TEG n"), else the draft calculation
    (``handicaps_draft``); ``candidates`` lists everyone with a handicap available.
    """
    teg_num = default_target_teg() if teg_num is None else int(teg_num)

    # --- rounds
    rp = _read_round_pars()
    rp = rp[pd.to_numeric(rp["TEGNum"], errors="coerce") == teg_num] if not rp.empty else rp
    if rp.empty:
        holes = pd.DataFrame(columns=["Round", "Hole", "Par", "SI"], dtype=int)
    else:
        holes = rp[["Round", "Hole", "Par", "SI"]].astype(int).sort_values(
            ["Round", "Hole"]).reset_index(drop=True)
    n_fixed = int(holes["Round"].nunique()) if len(holes) else 0
    try:
        ri = _read_csv(ROUND_INFO_CSV)
        ri = ri[pd.to_numeric(ri["TEGNum"], errors="coerce") == teg_num]
        n_listed = int(ri["Round"].nunique()) if len(ri) else 0
    except FileNotFoundError:
        n_listed = 0
    n_rounds = max(n_listed or DEFAULT_ROUNDS, n_fixed)
    random_rounds = n_rounds - n_fixed
    pool: list = []
    if random_rounds > 0:
        pool = _course_pool()
        if not pool:
            raise ValueError("No usable courses in course_pars.csv (need 18 holes, par 72, "
                             "SI 1-18) to simulate rounds without a scorecard")

    # --- handicaps
    hc_raw = _read_handicaps_raw()
    row = hc_raw[hc_raw["TEG"].astype(str).str.strip() == f"TEG {teg_num}"]
    saved: dict[str, int] = {}
    if not row.empty:
        for c in hc_raw.columns:
            if c == "TEG":
                continue
            val = row[c].iloc[0]
            if not (pd.isna(val) or str(val).strip() == ""):
                saved[str(c)] = int(round(float(val)))
    draft = _draft_handicaps(teg_num)
    candidates = sorted(set(saved) | set(draft))

    # --- roster
    pdict = _player_dict()
    if players is not None:
        chosen = [str(p) for p in players]
        unknown = [p for p in chosen if p not in pdict]
        if unknown:
            raise ValueError(f"Unknown player(s): {', '.join(unknown)}")
    else:
        codes = _playing_codes(teg_num)
        if codes is not None:
            chosen = sorted(codes)
        else:
            done = [t for t in _tegnums(_read_csv(COMPLETED_TEGS_CSV)) if t < teg_num]
            chosen = _players_of_teg(max(done)) if done else []
    if not chosen:
        raise ValueError(f"No players on the roster for TEG {teg_num}")

    handicaps: dict[str, int] = {}
    used_draft = False
    missing = []
    for p in chosen:
        if p in saved:
            handicaps[p] = saved[p]
        elif p in draft:
            handicaps[p] = draft[p]
            used_draft = True
        else:
            missing.append(p)
    if missing:
        raise ValueError(f"No handicap for TEG {teg_num} player(s): {', '.join(missing)}")

    return TargetTournament(
        teg_num, holes, chosen, handicaps, {p: pdict.get(p, p) for p in chosen},
        random_rounds=random_rounds, course_pool=pool, handicaps_draft=used_draft,
        candidates=candidates, n_rounds=n_rounds)


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


def _tilt_dist(p: np.ndarray, support: np.ndarray, target_mean: float,
               lo: int = FIELD_VP_MIN, hi: int = FIELD_VP_MAX) -> np.ndarray:
    """Exponentially tilt ``p`` (p(x) * exp(theta * x)) so its mean is ``target_mean``.

    Unlike shifting the whole distribution sideways, tilting keeps the field's
    shape: a better player gets more birdies and fewer doubles, but eagles stay
    rare in proportion to how rare they are for the field. Outcomes the field has
    never had stay at zero. Mass outside ``lo..hi`` is folded into the edges.
    """
    p = np.where((support < lo) | (support > hi), 0.0, p) + np.bincount(
        np.clip(support, lo, hi) - support[0], weights=np.where((support < lo) | (support > hi), p, 0.0),
        minlength=len(p))[:len(p)]
    nz = p > 0
    if not nz.any():
        return p
    x = support[nz].astype(float)
    base = p[nz]
    target = float(np.clip(target_mean, x.min() + 1e-6, x.max() - 1e-6)) if x.min() < x.max() else x.min()

    def tilted(theta: float) -> np.ndarray:
        z = np.log(base) + theta * (x - x.mean())
        e = np.exp(z - z.max())
        return e / e.sum()

    a, b = -20.0, 20.0  # mean is increasing in theta: bisect
    for _ in range(80):
        mid = (a + b) / 2
        if (tilted(mid) * x).sum() < target:
            a = mid
        else:
            b = mid
    out = np.zeros_like(p, dtype=float)
    out[nz] = tilted((a + b) / 2)
    return out


def _pair_label(lo: int, hi: int) -> str:
    """SI range label for SI pairs lo..hi (0-based), e.g. (1, 3) -> "SI 3-8"."""
    return f"SI {2 * lo + 1}-{2 * hi + 2}"


def build_distributions(
    history: pd.DataFrame,
    players: Sequence[str],
    teg_weights: dict[int, float],
    boundaries: Sequence[int] = DEFAULT_SI_BOUNDARIES,
    shrinkage: float = DEFAULT_SHRINKAGE,
    pars: Sequence[int] = _PARS,
    *,
    method: str = DEFAULT_METHOD,
    min_holes: int = DEFAULT_MIN_HOLES,
    player_weights: dict[str, dict[int, float]] | None = None,
    field_alpha: float = DEFAULT_FIELD_ALPHA,
) -> ScoreDistributions:
    """Per player/par GrossVP distributions by SI, recency-weighted by TEG.

    ``method="window"`` (default): SIs are paired (1-2 ... 17-18). For each target
    pair the player's holes of that par are gathered from that pair, widening to
    neighbouring pairs until at least ``min_holes`` raw holes; an observation's
    weight is TEG weight x 1/(1+pair distance). No shrinkage. ``boundaries`` and
    ``shrinkage`` are ignored.

    ``method="bands"``: fixed SI ``boundaries``, cells shrunk to the par-level
    distribution with strength ``shrinkage``.

    ``player_weights[pl]`` replaces ``teg_weights`` for that player's own holes
    (the field fallback keeps the global weights).

    ``field_alpha`` (0 disables) blends each cell towards the field so rare events
    (eagles, blobs) have non-zero probability: the field's GrossVP distribution for
    the same par and the same SI pairs/band as the cell (all players' holes in
    ``history``, equal weight) is exponentially tilted (``_tilt_dist``) so it has the
    player's mean while keeping the field's shape, then mixed as
    (EffN*p_player + alpha*p_field)/(EffN + alpha). The field is clamped to GrossVP
    -3..+8 (tails folded into the edges) so absurd scores cannot appear. Fallback cells (history/field fallback) are not blended; a
    bands-mode par-fallback cell uses the par-level effective N as its EffN.
    """
    if method not in METHODS:
        raise ValueError(f"Unknown method {method!r}")
    window = method == "window"
    if window:
        boundaries = _WINDOW_BOUNDARIES
    boundaries = tuple(boundaries)
    labels = si_band_labels(boundaries)
    n_bands = len(labels)
    k = float(shrinkage)
    min_holes = max(1, int(min_holes))
    warnings: list[str] = []

    h = history[["TEGNum", "Pl", "PAR", "SI", "GrossVP"]].copy()
    vmin, vmax = int(h["GrossVP"].min()), int(h["GrossVP"].max())
    alpha = max(0.0, float(field_alpha))
    if alpha > 0:  # support must hold the clamp range so the shifted field fits
        vmin, vmax = min(vmin, FIELD_VP_MIN), max(vmax, FIELD_VP_MAX)
    size = vmax - vmin + 1
    support = np.arange(vmin, vmax + 1)
    h["w"] = h["TEGNum"].map(lambda t: float(teg_weights.get(int(t), 0.0))).astype(float)
    h["band"] = assign_si_band(h["SI"].to_numpy(), boundaries)
    vp_all = h["GrossVP"].to_numpy().astype(int)
    w_global = h["w"].to_numpy()
    teg_all = h["TEGNum"].to_numpy().astype(int)
    pl_all = h["Pl"].to_numpy()
    par_all = h["PAR"].to_numpy()
    band_all = h["band"].to_numpy()

    def kish(w: np.ndarray) -> float:
        return float(w.sum() ** 2 / (w ** 2).sum()) if len(w) and (w ** 2).sum() > 0 else 0.0

    # field holes per (par, band), equal weight: counts over the support
    field_counts: dict[tuple[int, int], np.ndarray] = {}
    if alpha > 0:
        for par in pars:
            for b in range(n_bands):
                fm = (par_all == par) & (band_all == b)
                field_counts[(par, b)] = np.bincount(vp_all[fm] - vmin, minlength=size).astype(float)

    def blend(final: np.ndarray, par: int, lo: int, hi: int, eff: float) -> np.ndarray:
        fc = sum(field_counts[(par, bb)] for bb in range(lo, hi + 1))
        if eff <= 0 or fc.sum() <= 0:
            return final
        pf = fc / fc.sum()
        full = _tilt_dist(pf, support, float((final * support).sum()))
        return (eff * final + alpha * full) / (eff + alpha)

    prob_rows: list[pd.DataFrame] = []
    cell_rows: list[dict] = []

    for pl in players:
        pmask = pl_all == pl
        w_all = w_global
        if player_weights and pl in player_weights:
            ov = player_weights[pl]
            w_own = np.array([float(ov.get(int(t), 0.0)) for t in teg_all])
            w_all = np.where(pmask, w_own, w_global)
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
                    fm = (par_all == par) & (w_global > 0)
                    if fm.any():
                        p_par = _weighted_hist(vp_all[fm], w_global[fm], vmin, size)
                    else:
                        fm = par_all == par
                        p_par = _weighted_hist(vp_all[fm], np.ones(fm.sum()), vmin, size)
                    fallback = "field fallback"
                    warnings.append(f"{pl} par {par}: no history at all, used the field distribution")
            for b in range(n_bands):
                if fallback:
                    final, src, n, eff, win = p_par, fallback, 0, 0.0, "All SI"
                elif window:
                    dist = np.abs(band_all[m] - b)
                    r = 0
                    while True:
                        lo, hi = max(0, b - r), min(n_bands - 1, b + r)
                        inw = dist <= r
                        n = int(inw.sum())
                        if n >= min_holes or (lo == 0 and hi == n_bands - 1):
                            break
                        r += 1
                    wo = w_all[m][inw] / (1.0 + dist[inw])
                    final = _weighted_hist(vp_all[m][inw], wo, vmin, size)
                    eff, src, win = kish(wo), "window", _pair_label(lo, hi)
                    if alpha > 0:
                        final = blend(final, par, lo, hi, eff)
                else:
                    mc = m & (band_all == b)
                    n = int(mc.sum())
                    eff = kish(w_all[mc]) if n else 0.0
                    win = labels[b]
                    if n == 0:
                        final, src = p_par, "par fallback"
                    else:
                        p_cell = _weighted_hist(vp_all[mc], w_all[mc], vmin, size)
                        final = (eff * p_cell + k * p_par) / (eff + k) if eff + k > 0 else p_cell
                        src = "cell"
                    if alpha > 0:
                        final = blend(final, par, b, b, eff if n else kish(w_all[m]))
                nz = np.flatnonzero(final > 0)
                prob_rows.append(pd.DataFrame({
                    "Pl": pl, "Par": par, "Band": b,
                    "GrossVP": support[nz].astype(int), "Prob": final[nz]}))
                cell_rows.append({
                    "Pl": pl, "Par": par, "Band": b, "BandLabel": labels[b], "Window": win,
                    "N": n, "EffN": eff, "MeanVP": float((final * support).sum()), "Source": src})

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
    eagles: np.ndarray | None = None   # (n_sims, n_pl) int16: holes with GrossVP <= -2
    blobs: np.ndarray | None = None    # (n_sims, n_pl) int16: holes with 0 Stableford points
    random_rounds: int = 0
    courses_used: np.ndarray | None = None  # (n_sims, random_rounds) index into target.course_pool
    hole_vp: np.ndarray | None = None  # (n_sims, n_pl, n_holes) int8 GrossVP draws; only if keep_scores
    hole_si: np.ndarray | None = None  # (n_sims, n_holes) int8 stroke index per sim/hole; only if keep_scores


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
    keep_scores: bool = False,
) -> SimulationResult:
    """Simulate the target tournament ``n_sims`` times (clamped to 1..MAX_SIMS).

    ``keep_scores`` also stores the per-hole draws (``hole_vp``/``hole_si``) so they can be
    re-scored under other handicaps (see ``stableford_totals``). It never changes the draws.

    Fixed-scorecard rounds are identical every sim; each random round draws a course
    uniformly (with replacement) from ``target.course_pool``, the same course for all
    players within a sim. Pool courses are par 72, so the par total is constant.
    """
    n_sims = int(min(max(int(n_sims), 1), MAX_SIMS))
    holes = target.holes
    fpar = holes["Par"].to_numpy(dtype=int)
    fsi = holes["SI"].to_numpy(dtype=int)
    nf = len(fpar)
    rr = int(target.random_rounds)
    rng = np.random.default_rng(seed)

    def key_groups(par: np.ndarray, si: np.ndarray) -> dict[tuple[int, int], np.ndarray]:
        """Hole columns per (par, band) for one scorecard."""
        band = assign_si_band(si, dists.boundaries)
        return {(int(p), int(b)): np.flatnonzero((par == p) & (band == b))
                for p, b in sorted(set(zip(par.tolist(), band.tolist())))}

    fixed_groups = key_groups(fpar, fsi)
    pool_par = pool_si = courses_used = None
    course_groups: list = []
    course_rows: list = []
    if rr > 0:
        if not target.course_pool:
            raise ValueError("Target has random rounds but no course pool")
        pool_par = np.stack([np.asarray(c[1], dtype=int) for c in target.course_pool])
        pool_si = np.stack([np.asarray(c[2], dtype=int) for c in target.course_pool])
        if len(set(pool_par.sum(axis=1).tolist())) != 1:
            raise ValueError("Course pool must share one par total")
        courses_used = rng.integers(0, len(pool_par), size=(n_sims, rr)).astype(np.int16)
        course_groups = [key_groups(pool_par[c], pool_si[c]) for c in range(len(pool_par))]
        # sims (rows) that drew each course, per random round
        course_rows = [[np.flatnonzero(courses_used[:, r] == c) for c in range(len(pool_par))]
                       for r in range(rr)]
    all_pars = set(fpar.tolist()) | (set(np.unique(pool_par).tolist()) if rr else set())
    bad = sorted(all_pars - set(_PARS))
    if bad:
        raise ValueError(f"Unsupported par value(s) in target scorecard: {bad}")
    par_total = int(fpar.sum()) + (int(pool_par[0].sum()) * rr if rr else 0)
    n_holes = nf + 18 * rr

    # (Pl, Par, Band) -> (support values, cdf)
    cdfs = {}
    for key, g in dists.probs.groupby(["Pl", "Par", "Band"]):
        cdf = np.cumsum(g["Prob"].to_numpy())
        cdfs[key] = (g["GrossVP"].to_numpy().astype(np.int8), cdf / cdf[-1])

    def draw(pl: str, key: tuple[int, int], u: np.ndarray) -> np.ndarray:
        got = cdfs.get((pl, key[0], key[1]))
        if got is None:
            raise ValueError(f"No distribution for player {pl}, par {key[0]}, band {key[1]}")
        vals, cdf = got
        return vals[np.minimum(np.searchsorted(cdf, u, side="right"), len(vals) - 1)]

    n_pl = len(target.players)
    gross = np.empty((n_sims, n_pl), dtype=np.int32)
    stab = np.empty((n_sims, n_pl), dtype=np.int32)
    eagles = np.empty((n_sims, n_pl), dtype=np.int16)
    blobs = np.empty((n_sims, n_pl), dtype=np.int16)
    hole_vp = np.empty((n_sims, n_pl, n_holes), dtype=np.int8) if keep_scores else None
    for j, pl in enumerate(target.players):
        hc = int(target.handicaps[pl])
        strokes = np.empty((n_sims, n_holes), dtype=np.int8)
        strokes[:, :nf] = hc // 18 + ((hc % 18) >= fsi)
        u = rng.random((n_sims, n_holes))
        vp = np.empty((n_sims, n_holes), dtype=np.int8)
        for key, cols in fixed_groups.items():
            vp[:, cols] = draw(pl, key, u[:, cols])
        for r in range(rr):
            off = nf + 18 * r
            strokes[:, off:off + 18] = hc // 18 + ((hc % 18) >= pool_si[courses_used[:, r]])
            for c, rows in enumerate(course_rows[r]):
                if not len(rows):
                    continue
                for key, hcols in course_groups[c].items():
                    sel = np.ix_(rows, off + hcols)
                    vp[sel] = draw(pl, key, u[sel])
        del u
        if hole_vp is not None:
            hole_vp[:, j, :] = vp
        gross[:, j] = vp.sum(axis=1, dtype=np.int32) + par_total
        net_vp = vp - strokes  # int8: |vp| <= 9, strokes <= 3
        stab[:, j] = np.maximum(0, 2 - net_vp).sum(axis=1, dtype=np.int32)
        eagles[:, j] = (vp <= -2).sum(axis=1)
        blobs[:, j] = (net_vp >= 2).sum(axis=1)

    hole_si = None
    if keep_scores:
        hole_si = np.empty((n_sims, n_holes), dtype=np.int8)
        hole_si[:, :nf] = fsi
        for r in range(rr):
            hole_si[:, nf + 18 * r:nf + 18 * (r + 1)] = pool_si[courses_used[:, r]]

    return SimulationResult(
        players=list(target.players), names=dict(target.names), n_sims=n_sims,
        teg_num=target.teg_num, par_total=par_total, gross=gross, stableford=stab,
        gross_pos=_positions(gross, rng, higher_better=False),
        stableford_pos=_positions(stab, rng, higher_better=True),
        handicaps=dict(target.handicaps), eagles=eagles, blobs=blobs,
        random_rounds=rr, courses_used=courses_used, hole_vp=hole_vp, hole_si=hole_si)


# ---------------------------------------------------------------- summaries

def summary_table(result: SimulationResult) -> pd.DataFrame:
    """One row per player (sorted by mean gross) with totals, percentiles, win odds, expected position."""
    rows = []
    for j, pl in enumerate(result.players):
        g, s = result.gross[:, j], result.stableford[:, j]
        row = {
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
        }
        if result.eagles is not None:
            row["EagleChance"] = float((result.eagles[:, j] >= 1).mean())
        if result.blobs is not None:
            row["ExpBlobs"] = float(result.blobs[:, j].mean())
        rows.append(row)
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


def total_distribution(result: SimulationResult, measure: str, smooth: bool = False,
                       bandwidth: float | None = None) -> pd.DataFrame:
    """Distribution of simulated totals per player: Pl, Player, Total, Fraction.

    ``smooth=False``: the raw histogram. ``smooth=True``: the integer histogram
    convolved with a Gaussian kernel (``bandwidth`` in strokes/points, default
    max(1.5, 1.06*std*n^-0.2) per player) on an integer grid from min-4h to max+4h;
    Fraction is the density per grid step and still sums to 1 per player.
    """
    tot, _ = _measure(result, measure)
    frames = []
    for j, pl in enumerate(result.players):
        col = tot[:, j]
        if not smooth:
            vals, counts = np.unique(col, return_counts=True)
            frac = counts / tot.shape[0]
        else:
            n = len(col)
            h = float(bandwidth) if bandwidth else max(1.5, 1.06 * float(col.std()) * n ** -0.2)
            half = pad = int(np.ceil(4 * h))  # pad >= kernel half-width keeps "same" length
            lo, hi = int(col.min()) - pad, int(col.max()) + pad
            hist = np.bincount(col - lo, minlength=hi - lo + 1).astype(float) / n
            k = np.exp(-0.5 * (np.arange(-half, half + 1) / h) ** 2)
            frac = np.convolve(hist, k / k.sum(), mode="same")
            frac = frac / frac.sum()
            vals = np.arange(lo, hi + 1)
        frames.append(pd.DataFrame({
            "Pl": pl, "Player": result.names.get(pl, pl),
            "Total": vals.astype(int), "Fraction": frac}))
    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------- backtest

def backtest_field_alpha(
    history: pd.DataFrame,
    alphas: Sequence[float] = (0, 0.5, 1, 2, 3, 5, 8, 12),
    target_tegs: Sequence[int] | None = None,
    method: str = DEFAULT_METHOD,
    min_holes: int = DEFAULT_MIN_HOLES,
    weights: Sequence[float] = DEFAULT_RECENT_WEIGHTS,
) -> pd.DataFrame:
    """Out-of-sample log-likelihood of each ``field_alpha``.

    For each target TEG t (default: every TEG, except 50, with >= 3 earlier TEGs),
    distributions are built from TEGs before t (recency weights ``weights``) for the
    players who played t; every hole of t is scored by log P(actual GrossVP) (zero
    probabilities floored at 1e-6). Returns Alpha, MeanLogLik, Holes, ZeroProbHoles.
    """
    all_tegs = sorted(int(t) for t in history["TEGNum"].unique())
    if target_tegs is None:
        target_tegs = [t for t in all_tegs if t != 50 and sum(e < t for e in all_tegs) >= 3]
    rows = []
    for a in alphas:
        ll_sum, n, zeros = 0.0, 0, 0
        for t in target_tegs:
            prior = history[history["TEGNum"] < t]
            actual = history[history["TEGNum"] == t]
            if prior.empty or actual.empty:
                continue
            players = sorted(actual["Pl"].unique())
            w = default_teg_weights(completed_teg_numbers(prior), weights)
            d = build_distributions(prior, players, w, method=method, min_holes=min_holes,
                                    field_alpha=a)
            lookup = {(r.Pl, r.Par, r.Band, r.GrossVP): r.Prob for r in d.probs.itertuples()}
            band = assign_si_band(actual["SI"].to_numpy(), d.boundaries)
            for pl, par, b, vp in zip(actual["Pl"], actual["PAR"], band, actual["GrossVP"]):
                pr = lookup.get((pl, int(par), int(b), int(vp)), 0.0)
                if pr <= 0:
                    zeros += 1
                ll_sum += float(np.log(max(pr, 1e-6)))
                n += 1
        rows.append({"Alpha": float(a), "MeanLogLik": ll_sum / n if n else float("nan"),
                     "Holes": n, "ZeroProbHoles": zeros})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- betting odds

# Traditional fractional odds ladder (odds against, as numerator/denominator).
_ODDS_LADDER = [
    (1, 1000), (1, 500), (1, 200), (1, 100), (1, 50), (1, 33), (1, 25), (1, 20), (1, 16),
    (1, 14), (1, 12), (1, 10), (1, 8), (1, 7), (1, 6), (1, 5), (2, 9), (1, 4), (2, 7),
    (1, 3), (4, 11), (2, 5), (4, 9), (1, 2), (8, 15), (4, 7), (8, 13), (4, 6), (8, 11),
    (4, 5), (5, 6), (10, 11), (1, 1), (11, 10), (6, 5), (5, 4), (11, 8), (6, 4), (13, 8),
    (7, 4), (15, 8), (2, 1), (9, 4), (5, 2), (11, 4), (3, 1), (10, 3), (7, 2), (4, 1),
    (9, 2), (5, 1), (11, 2), (6, 1), (13, 2), (7, 1), (15, 2), (8, 1), (9, 1), (10, 1),
    (11, 1), (12, 1), (14, 1), (16, 1), (20, 1), (25, 1), (33, 1), (40, 1), (50, 1),
    (66, 1), (80, 1), (100, 1), (150, 1), (200, 1), (250, 1), (500, 1), (1000, 1),
]


def fractional_odds(p: float) -> str:
    """Fair fractional odds for probability ``p``, snapped to the traditional ladder.

    No bookmaker's margin. Uses the nearest ladder price in log-odds; 1/1 is "Evens".
    Never-happened outcomes read "1000/1+" and certainties "1/1000".
    """
    if not np.isfinite(p) or p <= 0:
        return "1000/1+"
    if p >= 1:
        return "1/1000"
    target = np.log((1 - p) / p)
    num, den = min(_ODDS_LADDER, key=lambda nd: abs(np.log(nd[0] / nd[1]) - target))
    return "Evens" if num == den else f"{num}/{den}"


def odds_table(result: SimulationResult) -> pd.DataFrame:
    """Win chances and fair fractional odds for the three prizes.

    Trophy = 1st on Stableford, Green Jacket = 1st on gross, Wooden Spoon = last on
    Stableford (the Trophy order, worst first). Rows ordered by Trophy chance.
    """
    n = len(result.players)
    rows = []
    for j, pl in enumerate(result.players):
        trophy = float((result.stableford_pos[:, j] == 1).mean())
        jacket = float((result.gross_pos[:, j] == 1).mean())
        spoon = float((result.stableford_pos[:, j] == n).mean())
        rows.append({"Pl": pl, "Player": result.names.get(pl, pl),
                     "Trophy": trophy, "TrophyOdds": fractional_odds(trophy),
                     "Jacket": jacket, "JacketOdds": fractional_odds(jacket),
                     "Spoon": spoon, "SpoonOdds": fractional_odds(spoon)})
    return pd.DataFrame(rows).sort_values("Trophy", ascending=False, kind="stable").reset_index(drop=True)


# ---------------------------------------------------------------- handicap what-ifs

MAX_SHAPLEY_MOVERS = 8  # 2**8 subsets
EQUALISING_TARGET = 36.0  # Stableford points per round
_TIEBREAK_SEED = 0
_VP_OFFSET = 20


def _require_scores(result: SimulationResult) -> None:
    if result.hole_vp is None or result.hole_si is None:
        raise ValueError("Re-scoring needs run_simulation(..., keep_scores=True)")


def _player_stableford(result: SimulationResult, j: int, hc: int) -> np.ndarray:
    """Stableford totals (n_sims,) of player index ``j`` on handicap ``hc`` (plus handicaps, i.e. negative, give strokes back)."""
    hc = int(hc)
    si = result.hole_si
    strokes = (hc // 18 + ((hc % 18) >= si)).astype(np.int8)
    return np.maximum(0, 2 - (result.hole_vp[:, j, :] - strokes)).sum(axis=1, dtype=np.int32)


def stableford_totals(result: SimulationResult, handicaps: dict[str, int]) -> np.ndarray:
    """Re-score the kept draws: (n_sims, n_pl) Stableford totals on ``handicaps``."""
    _require_scores(result)
    out = np.empty((result.n_sims, len(result.players)), dtype=np.int32)
    for j, pl in enumerate(result.players):
        out[:, j] = _player_stableford(result, j, handicaps.get(pl, result.handicaps.get(pl, 0)))
    return out


def _tiebreak(result: SimulationResult) -> np.ndarray:
    return np.random.default_rng(_TIEBREAK_SEED).random((result.n_sims, len(result.players)))


def _win_share(totals: np.ndarray, half_noise: np.ndarray) -> np.ndarray:
    """Share of sims each column wins (highest total, ties broken by the fixed ``half_noise``, in [0, 0.5))."""
    winner = np.argmax(totals + half_noise, axis=1)
    return np.bincount(winner, minlength=totals.shape[1]) / totals.shape[0]


def previous_handicaps(teg_num: int) -> dict[str, int]:
    """Handicaps saved for TEG ``teg_num - 1`` (exact row; blank cells skipped)."""
    raw = _read_handicaps_raw()
    playing = _playing_codes(int(teg_num) - 1)  # None: no roster record, so 0 = not playing
    row = raw[raw["TEG"].astype(str).str.strip() == f"TEG {int(teg_num) - 1}"]
    out: dict[str, int] = {}
    if row.empty:
        return out
    for c in raw.columns:
        if c == "TEG":
            continue
        val = row[c].iloc[0]
        if pd.isna(val) or str(val).strip() == "":
            continue
        v = int(round(float(val)))
        if v == 0 and playing is None:
            continue
        out[str(c)] = v
    return out


@dataclass
class HandicapImpact:
    players: list[str]
    old_handicaps: dict[str, int]    # effective "old" handicap (= new for players without one)
    new_handicaps: dict[str, int]
    movers: list[str]                # players whose handicap changed, in roster order
    no_previous: list[str]           # players with no previous handicap (treated as unchanged)
    win_old: np.ndarray              # (n_pl,) Stableford win share, everyone on old handicaps
    win_new: np.ndarray              # (n_pl,) ... everyone on new handicaps
    mean_old: np.ndarray             # (n_pl,) mean Stableford total on old handicaps
    mean_new: np.ndarray
    shapley: np.ndarray | None       # (n_movers, n_pl) pp change; None if too many movers
    single: np.ndarray | None        # (n_movers, n_pl) pp change, only that mover changed
    skipped_reason: str = ""

    @property
    def single_sum(self) -> np.ndarray | None:
        return None if self.single is None else self.single.sum(axis=0)

    @property
    def total_change(self) -> np.ndarray:
        return (self.win_new - self.win_old) * 100.0


def handicap_change_impact(result: SimulationResult, old_handicaps: dict[str, int]) -> HandicapImpact:
    """Exact Shapley split of each mover's handicap change into every player's win chance.

    The same simulated rounds and one fixed tie-break array are used for every
    handicap combination, so differences between combinations are paired.
    """
    _require_scores(result)
    pls = result.players
    n_pl = len(pls)
    new = {p: int(result.handicaps[p]) for p in pls}
    old = {p: int(old_handicaps[p]) if p in old_handicaps else new[p] for p in pls}
    no_prev = [p for p in pls if p not in old_handicaps]
    movers = [p for p in pls if old[p] != new[p]]
    m = len(movers)

    cols = np.stack([np.stack([_player_stableford(result, j, old[p]) for j, p in enumerate(pls)], axis=1),
                     np.stack([_player_stableford(result, j, new[p]) for j, p in enumerate(pls)], axis=1)])
    noise = 0.5 * _tiebreak(result)  # scaled once, shared by every subset
    mover_idx = [pls.index(p) for p in movers]
    base = cols[0].copy()  # non-movers are identical in cols[0] and cols[1]

    def win(mask: int) -> np.ndarray:
        t = base.copy()
        for b, j in enumerate(mover_idx):
            if mask >> b & 1:
                t[:, j] = cols[1][:, j]
        return _win_share(t, noise) * 100.0

    w_old, w_new = win(0) / 100.0, win((1 << m) - 1) / 100.0
    shap = single = None
    reason = ""
    if m > MAX_SHAPLEY_MOVERS:
        reason = f"{m} handicaps changed; the exact split is skipped above {MAX_SHAPLEY_MOVERS}."
        single = np.stack([win(1 << i) - win(0) for i in range(m)])  # cheap: m extra passes
    elif m:
        W = np.stack([win(k) for k in range(1 << m)])  # (2**m, n_pl) in pp
        from math import factorial
        coef = [factorial(k) * factorial(m - k - 1) / factorial(m) for k in range(m)]
        shap = np.zeros((m, n_pl))
        for i in range(m):
            for mask in range(1 << m):
                if mask >> i & 1:
                    continue
                shap[i] += coef[bin(mask).count("1")] * (W[mask | 1 << i] - W[mask])
        single = np.stack([W[1 << i] - W[0] for i in range(m)])
    else:
        shap = single = np.zeros((0, n_pl))
    return HandicapImpact(
        players=list(pls), old_handicaps=old, new_handicaps=new, movers=movers, no_previous=no_prev,
        win_old=w_old, win_new=w_new, mean_old=cols[0].mean(axis=0), mean_new=cols[1].mean(axis=0),
        shapley=shap, single=single, skipped_reason=reason)


def _mean_points_by_handicap(result: SimulationResult, j: int, hcs: np.ndarray) -> np.ndarray:
    """Mean Stableford points per round for player ``j`` at each handicap in ``hcs``.

    Counts holes by (SI, GrossVP) once, so every handicap is then a cheap lookup.
    """
    n_holes = result.hole_si.shape[1]
    width = 64
    idx = (result.hole_si.astype(np.int16) * width
           + (result.hole_vp[:, j, :].astype(np.int16) + _VP_OFFSET))
    counts = np.bincount(idx.ravel(), minlength=19 * width).reshape(19, width)
    vp = np.arange(width) - _VP_OFFSET
    kmax = int(hcs.max()) // 18 + 1
    # A[k, s]: total points at SI s if every such hole gets k strokes
    A = np.stack([(counts * np.maximum(0, 2 - vp + k)).sum(axis=1) for k in range(kmax + 1)])
    sis = np.arange(1, 19)
    out = np.empty(len(hcs))
    for i, hc in enumerate(hcs):
        k = int(hc) // 18 + ((int(hc) % 18) >= sis)
        out[i] = A[k, sis].sum()
    return out / result.n_sims / (n_holes / 18)


def equalising_handicaps(result: SimulationResult, target_per_round: float = EQUALISING_TARGET,
                         hc_range: tuple[int, int] = (0, 54)) -> pd.DataFrame:
    """Per player, the integer handicap whose mean Stableford per round is closest to the target."""
    _require_scores(result)
    lo, hi = int(hc_range[0]), int(hc_range[1])
    hcs = np.arange(lo, hi + 1)
    rows, chosen = [], {}
    for j, pl in enumerate(result.players):
        f = _mean_points_by_handicap(result, j, hcs)
        k = int(np.argmin(np.abs(f - target_per_round)))  # first minimum = lower handicap on ties
        reachable = bool(f.min() <= target_per_round <= f.max())
        unrounded = float(np.interp(target_per_round, np.maximum.accumulate(f), hcs))
        chosen[pl] = int(hcs[k])
        cur = int(result.handicaps.get(pl, 0))
        rows.append({"Pl": pl, "Player": result.names.get(pl, pl), "CurrentHC": cur,
                     "EqualisingHC": int(hcs[k]), "Change": int(hcs[k]) - cur,
                     "Unrounded": unrounded, "PtsPerRound": float(f[k]), "Reachable": reachable})
    win = _win_share(stableford_totals(result, chosen), 0.5 * _tiebreak(result))
    df = pd.DataFrame(rows)
    df["WinStableford"] = win
    return df
