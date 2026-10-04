"""Round-by-round win probabilities for a TEG, updated after each completed round.

Built on the hole-level simulator (``simulation.py``). Completed rounds are
banked at their actual scores. The remaining rounds are simulated hole by hole
on their actual scorecards (random courses for rounds without one) with
``run_simulation``: gross vs par from each player's par x SI distributions,
Stableford from that gross and the player's strokes on each hole.

Prior form is ``build_distributions`` on the TEGs held before this one, weights
``prior_weights`` (most recent first) renormalised over the TEGs each player
played; a player with none of them gets the field distribution. Current form is
how far this TEG's completed rounds beat or missed what the prior distributions
expected on those holes. With w = k*n / (k*n + P) (n = holes played / 18), every
hole distribution is exponentially tilted so the expected round moves by
w x the residual per round.

Independent holes have no good or bad days, so on their own they make rounds too
predictable (model round SD ~5.0 vs ~6.9 actual). Two correlated offsets are
added to the simulated holes: a TEG form offset per player (variance
``form_var`` x (1 - w), shared by every remaining round) and a day offset per
round (``day_var``). Defaults are a quarter of the variances estimated from
TEGs 3-18, the dose that made the live chances move as much as a calibrated
forecast should with no loss of accuracy (backtest TEGs 5-18).

The net measure is Stableford points from TEG ``STABLEFORD_ERA_TEG`` and net vs
par before it. Ties for the lead are shared wins, in simulations and in the
actual outcome.

UI-agnostic: returns DataFrames/arrays only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

from teg_analysis.analysis import simulation as sim
from teg_analysis.analysis.aggregation import STABLEFORD_ERA_TEG

DEFAULT_K = 3.0
DEFAULT_P = 6.0
DEFAULT_PRIOR_WEIGHTS = sim.DEFAULT_RECENT_WEIGHTS  # 50/35/15, same as the Prediction tab
DEFAULT_FORM_VAR = 3.9  # strokes² per round: TEG form uncertainty (estimated 15.6, quartered)
DEFAULT_DAY_VAR = 1.6   # strokes² per round: day-to-day effect (estimated 6.3, quartered)
MEASURES = ("net", "gross")  # net leads: Stableford (TEG 8+), else NetVP
BACKTEST_KS = (1.0, 2.0, 3.0, 4.0, 6.0)
BACKTEST_PS = (2.0, 4.0, 6.0, 9.0, 12.0)
DEFAULT_BACKTEST_SIMS = 4_000
_HOLES = 18


# ---------------------------------------------------------------- weights

def prior_teg_weights(
    prior_tegs_desc: Sequence[int], played: Iterable[int],
    weights: Sequence[float] = DEFAULT_PRIOR_WEIGHTS,
) -> dict[int, float]:
    """Weights on the TEGs held before this one, renormalised over those played.

    ``prior_tegs_desc`` lists TEGs held before the current one, most recent first;
    only the first ``len(weights)`` count. Returns {TEGNum: weight} summing to 1,
    or {} if the player played none of them.
    """
    played = {int(t) for t in played}
    raw = {int(t): float(w) for t, w in zip(prior_tegs_desc, weights) if int(t) in played and w > 0}
    total = sum(raw.values())
    return {t: w / total for t, w in raw.items()} if total > 0 else {}


def blend_weight(n: float, k: float = DEFAULT_K, P: float = DEFAULT_P) -> float:
    """Current-form weight w = k*n / (k*n + P) after ``n`` completed rounds."""
    if k < 0 or P <= 0:
        raise ValueError("k must be >= 0 and P > 0")
    return float(k * n / (k * n + P)) if n > 0 else 0.0


def form_shift(residual: float, holes_played: int, k: float = DEFAULT_K,
               P: float = DEFAULT_P) -> tuple[float, float]:
    """(expected change per round, w) from this TEG's form so far.

    ``residual`` is actual GrossVP minus what the prior expected on the
    ``holes_played`` holes. n = holes_played / 18, so w grows hole by hole; the
    expected round moves by w x the residual per round.
    """
    n = holes_played / _HOLES
    if n <= 0:
        return 0.0, 0.0
    w = blend_weight(n, k, P)
    return float(w * residual / n), w


def win_shares(totals: np.ndarray, higher_better: bool) -> np.ndarray:
    """Mean win share per column of (sims, players) totals; ties for the lead share the win."""
    best = totals.max(axis=1) if higher_better else totals.min(axis=1)
    lead = totals == best[:, None]
    return (lead / lead.sum(axis=1, keepdims=True)).mean(axis=0)


# ---------------------------------------------------------------- distributions

def prior_distributions(
    history: pd.DataFrame, teg_num: int, players: Sequence[str],
    prior_weights: Sequence[float] = DEFAULT_PRIOR_WEIGHTS, **build_kwargs,
) -> sim.ScoreDistributions:
    """``build_distributions`` on the TEGs held before ``teg_num``.

    Each player's own holes use ``prior_teg_weights`` over the TEGs they played.
    Players who played none of them have their history removed, so they get the
    field distribution. Other ``build_distributions`` options pass through.
    """
    history = history[history["TEGNum"] < int(teg_num)]
    held = sorted({int(t) for t in history["TEGNum"]}, reverse=True)
    prior_tegs = held[:len(prior_weights)]
    if not prior_tegs:
        raise ValueError(f"No TEGs before TEG {teg_num} to build prior form from")
    played = history.groupby("Pl")["TEGNum"].unique()
    pw = {pl: prior_teg_weights(prior_tegs, played.get(pl, []), prior_weights) for pl in players}
    no_prior = [pl for pl, w in pw.items() if not w]
    history = history[~history["Pl"].isin(no_prior)]
    return sim.build_distributions(
        history, players, prior_teg_weights(prior_tegs, prior_tegs, prior_weights),
        player_weights={pl: w for pl, w in pw.items() if w}, **build_kwargs)


def _cell_arrays(dists: sim.ScoreDistributions) -> tuple[np.ndarray, dict]:
    """(support, {Pl: (keys [(par, band)], probs (cells, support))}) from ``dists.probs``."""
    support = np.arange(int(dists.probs["GrossVP"].min()), int(dists.probs["GrossVP"].max()) + 1)
    out: dict[str, tuple[list, np.ndarray]] = {}
    for pl, g in dists.probs.groupby("Pl", sort=False):
        keys = sorted({(int(p), int(b)) for p, b in zip(g["Par"], g["Band"])})
        idx = {key: i for i, key in enumerate(keys)}
        arr = np.zeros((len(keys), len(support)))
        rows = [idx[(int(p), int(b))] for p, b in zip(g["Par"], g["Band"])]
        arr[rows, g["GrossVP"].to_numpy(int) - support[0]] = g["Prob"].to_numpy(float)
        out[pl] = (keys, arr)
    return support, out


def _tilt_rows(p: np.ndarray, support: np.ndarray, targets: np.ndarray) -> np.ndarray:
    """Exponential tilt of each row of ``p`` to its target mean (``sim._tilt_dist``, vectorised, no folding)."""
    x = support.astype(float) - support.mean()
    nz = p > 0
    logp = np.where(nz, np.log(np.where(nz, p, 1.0)), -np.inf)
    xmin = np.where(nz, x, np.inf).min(axis=1)
    xmax = np.where(nz, x, -np.inf).max(axis=1)
    t = np.clip(targets - support.mean(), xmin + 1e-6, xmax - 1e-6)
    lo, hi = np.full(len(p), -20.0), np.full(len(p), 20.0)

    def tilted(theta):
        z = logp + theta[:, None] * x
        e = np.exp(z - z.max(axis=1, keepdims=True))
        return e / e.sum(axis=1, keepdims=True)

    for _ in range(60):  # mean is increasing in theta: bisect
        mid = (lo + hi) / 2
        below = (tilted(mid) * x).sum(axis=1) < t
        lo, hi = np.where(below, mid, lo), np.where(below, hi, mid)
    return tilted((lo + hi) / 2)


def _card_cells(keys: list, card: pd.DataFrame, boundaries) -> np.ndarray:
    """Cell index of each hole of a scorecard (columns Par, SI)."""
    idx = {key: i for i, key in enumerate(keys)}
    band = sim.assign_si_band(card["SI"].to_numpy(int), boundaries)
    return np.array([idx[(int(p), int(b))] for p, b in zip(card["Par"], band)], dtype=int)


def _moments(p: np.ndarray, support: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    m = (p * support).sum(axis=1)
    return m, (p * support ** 2).sum(axis=1) - m ** 2


def shift_cells(p: np.ndarray, support: np.ndarray, shift_per_hole: float) -> np.ndarray:
    """Tilt every cell so its mean moves by ``shift_per_hole`` (zero-probability outcomes stay zero)."""
    return _tilt_rows(p, support, (p * support).sum(axis=1) + shift_per_hole)


def newcomers(dists: sim.ScoreDistributions) -> list[str]:
    """Players with no history at all: every cell came from the field."""
    src = dists.cells.groupby("Pl", sort=False)["Source"].agg(lambda x: set(x) == {"field fallback"})
    return [str(pl) for pl, is_new in src.items() if is_new]


def anchor_newcomers(dists: sim.ScoreDistributions, history: pd.DataFrame,
                     handicaps: dict[str, int]) -> sim.ScoreDistributions:
    """Centre players with no history (field-fallback cells) on their handicap.

    The field distribution is the whole group's scoring, which ignores handicap:
    a 36-handicap debutant would get a ~24-handicap player's scores and win the
    Stableford nearly every time. Their cells are tilted so a typical round
    (4 par 3s, 10 par 4s, 4 par 5s) averages handicap + the group's usual gap
    between gross vs par and handicap in ``history`` (about +1.5 a round).
    """
    new = [pl for pl in newcomers(dists) if pl in handicaps]
    if not new or history.empty:
        return dists
    rounds = history.groupby(["TEGNum", "Round", "Pl"]).agg(G=("GrossVP", "sum"), HC=("HC", "first"))
    gap = float((rounds["G"] - rounds["HC"]).mean())
    support, cells = _cell_arrays(dists)
    for pl in new:
        keys, p = cells[pl]
        means = (p * support).sum(axis=1)
        by_par = {par: means[[i for i, (pp, _) in enumerate(keys) if pp == par]].mean()
                  for par in (3, 4, 5) if any(pp == par for pp, _ in keys)}
        mix = {par: n for par, n in ((3, 4), (4, 10), (5, 4)) if par in by_par}
        typical = _HOLES * sum(n * by_par[par] for par, n in mix.items()) / sum(mix.values())
        target = handicaps[pl] + gap
        cells[pl] = (keys, shift_cells(p, support, (target - typical) / _HOLES))
        dists.warnings.append(f"{pl}: first TEG, no past scores. Uses the group's scoring, "
                              f"centred on handicap {handicaps[pl]} ({target:+.1f} gross a round)")
    out = _dists_from_cells(dists, support, cells)
    return sim.ScoreDistributions(out.boundaries, out.probs, dists.cells, out.warnings)


def _dists_from_cells(base: sim.ScoreDistributions, support: np.ndarray,
                      cells: dict[str, tuple[list, np.ndarray]]) -> sim.ScoreDistributions:
    rows = []
    for pl, (keys, arr) in cells.items():
        for (par, band), p in zip(keys, arr):
            nz = np.flatnonzero(p > 0)
            rows.append(pd.DataFrame({"Pl": pl, "Par": par, "Band": band,
                                      "GrossVP": support[nz].astype(int), "Prob": p[nz]}))
    return sim.ScoreDistributions(base.boundaries, pd.concat(rows, ignore_index=True),
                                  base.cells, list(base.warnings))


# ---------------------------------------------------------------- the TEG

def in_progress_teg() -> int | None:
    """The TEG in progress (in_progress_tegs.csv, not also completed), else None."""
    def nums(path: str) -> list[int]:
        try:
            return sim._tegnums(sim._read_csv(path))
        except (FileNotFoundError, pd.errors.EmptyDataError):
            return []

    done = set(nums(sim.COMPLETED_TEGS_CSV))
    live = [t for t in nums(sim.IN_PROGRESS_TEGS_CSV) if t not in done]
    return min(live) if live else None


@dataclass
class TegState:
    """Everything about one TEG that doesn't depend on k and P."""
    teg_num: int
    players: list[str]
    names: dict[str, str]
    handicaps: dict[str, int]
    n_rounds: int
    cards: dict[int, pd.DataFrame]   # Round -> Hole, Par, SI for rounds with a scorecard
    course_pool: list = field(default_factory=list)
    done: list[int] = field(default_factory=list)        # completed rounds 1..n
    holes: pd.DataFrame | None = None  # completed rounds: Round, Hole, Pl, GrossVP, Net
    prior: sim.ScoreDistributions | None = None   # (Net = Stableford from TEG 8, else NetVP)
    _cells: tuple | None = field(default=None, repr=False)

    def cells(self) -> tuple:
        """(support, per-player prior cell arrays), computed once."""
        if self._cells is None:
            self._cells = _cell_arrays(self.prior)
        return self._cells

    @property
    def stableford(self) -> bool:
        return self.teg_num >= STABLEFORD_ERA_TEG


def completed_rounds(scores: pd.DataFrame, teg_num: int, players: Sequence[str]) -> list[int]:
    """Leading rounds 1, 2, ... where every player has all 18 holes."""
    t = scores[scores["TEGNum"] == teg_num]
    holes = t.groupby(["Round", "Pl"])["Hole"].nunique()
    full = {r for r in t["Round"].unique()
            if all(holes.get((r, p), 0) == _HOLES for p in players)}
    done = []
    while len(done) + 1 in full:
        done.append(len(done) + 1)
    return done


def _cards_from_scores(t: pd.DataFrame) -> dict[int, pd.DataFrame]:
    """Scorecards of rounds with all 18 holes scored (a round in progress has only part of one)."""
    out = {}
    for r, g in t.groupby("Round"):
        c = g.drop_duplicates("Hole").sort_values("Hole")
        if len(c) != _HOLES:
            continue
        out[int(r)] = pd.DataFrame({"Hole": c["Hole"].astype(int).to_numpy(),
                                    "Par": c["PAR"].astype(int).to_numpy(),
                                    "SI": c["SI"].astype(int).to_numpy()})
    return out


def load_teg_state(
    teg_num: int, history: pd.DataFrame | None = None,
    prior_weights: Sequence[float] = DEFAULT_PRIOR_WEIGHTS, *,
    from_scores: bool = False, **build_kwargs,
) -> TegState:
    """Roster, handicaps, scorecards, banked rounds and prior distributions for a TEG.

    ``history`` is hole-level scores (``sim.load_history`` format, default: all TEGs
    except test TEG 50). By default the roster, handicaps, scorecards and round
    count come from ``sim.load_target_tournament`` (in-progress or upcoming TEG);
    ``from_scores=True`` takes them all from the TEG's own scores (completed TEGs,
    backtests).
    """
    teg_num = int(teg_num)
    history = sim.load_history(teg_nums=[50]) if history is None else history
    t = history[history["TEGNum"] == teg_num]
    played = set(t["Pl"])
    if from_scores:
        if t.empty:
            raise ValueError(f"No scores for TEG {teg_num}")
        hcs = t.groupby("Pl")["HC"].first()
        players = sorted(hcs.index)
        handicaps = {p: int(round(h)) for p, h in hcs.items()}
        names = {p: p for p in players}
        cards, n_rounds, pool = _cards_from_scores(t), int(t["Round"].nunique()), []
    else:
        target = sim.load_target_tournament(teg_num)
        extra = played - set(target.players)
        if extra:
            raise ValueError(f"TEG {teg_num} has scores for players not on the roster: "
                             f"{', '.join(sorted(extra))}")
        players, names = list(target.players), dict(target.names)
        handicaps = dict(target.handicaps)
        for p, h in t.groupby("Pl")["HC"].first().items():
            handicaps[p] = int(round(h))
        cards = {int(r): g[["Hole", "Par", "SI"]].reset_index(drop=True)
                 for r, g in target.holes.groupby("Round")}
        cards.update(_cards_from_scores(t))
        n_rounds = max(int(target.n_rounds), int(t["Round"].nunique()) if len(t) else 0)
        pool = list(target.course_pool)
    done = completed_rounds(t, teg_num, players)
    if len(done) < n_rounds and not pool and any(r not in cards for r in range(len(done) + 1, n_rounds + 1)):
        raise ValueError(f"TEG {teg_num}: a remaining round has no scorecard and no course pool")
    net_col = "Stableford" if teg_num >= STABLEFORD_ERA_TEG else "NetVP"
    holes = t.loc[t["Round"].isin(done), ["Round", "Hole", "Pl", "GrossVP", net_col]].rename(
        columns={net_col: "Net"}).astype({"Round": int, "Hole": int, "GrossVP": int, "Net": int})
    prior = prior_distributions(history, teg_num, players, prior_weights, **build_kwargs)
    prior = anchor_newcomers(prior, history[history["TEGNum"] < teg_num], handicaps)
    return TegState(teg_num, players, names, handicaps, n_rounds, cards, pool, done,
                    holes.reset_index(drop=True), prior)


def checkpoints(state: TegState) -> list[tuple[int, int]]:
    """Every (round, hole) checkpoint so far: (0, 0) before the TEG, then each hole of each completed round."""
    return [(0, 0)] + [(r, h) for r in state.done for h in range(1, _HOLES + 1)]


def _remaining_target(state: TegState, rnd: int, hole: int) -> sim.TargetTournament:
    """Holes after hole ``hole`` of round ``rnd``, then the later rounds."""
    later = range(rnd + 1, state.n_rounds + 1)
    fixed = []
    if rnd and hole < _HOLES:
        c = state.cards[rnd]
        fixed.append(c[c["Hole"] > hole].assign(Round=rnd))
    fixed += [state.cards[r].assign(Round=r) for r in later if r in state.cards]
    holes = (pd.concat(fixed, ignore_index=True)[["Round", "Hole", "Par", "SI"]] if fixed
             else pd.DataFrame(columns=["Round", "Hole", "Par", "SI"], dtype=int))
    return sim.TargetTournament(
        state.teg_num, holes, list(state.players), dict(state.handicaps), dict(state.names),
        random_rounds=sum(r not in state.cards for r in later),
        course_pool=state.course_pool, n_rounds=len(later) + int(bool(rnd) and hole < _HOLES))


def _pool_card(course) -> pd.DataFrame:
    return pd.DataFrame({"Par": np.asarray(course[1], dtype=int), "SI": np.asarray(course[2], dtype=int)})


def _strokes(si: np.ndarray, hc: int) -> int:
    """Handicap strokes received over holes with these stroke indexes."""
    return int((hc // _HOLES + ((hc % _HOLES) >= np.asarray(si, dtype=int))).sum())


def _add_round_offsets(out: sim.SimulationResult, tgt: sim.TargetTournament, form_sd: float,
                       day_sd: float, rng: np.random.Generator) -> np.ndarray:
    """Add correlated form to kept hole draws in place; returns (sims, players, holes) GrossVP.

    Per sim and player, a TEG form offset ~ N(0, form_sd) (strokes per round, shared by
    every remaining round) plus a fresh day offset ~ N(0, day_sd) per round. Each
    round's offset is rounded and spread one stroke at a time over random holes of
    that round (a whole stroke on every hole when it exceeds the hole count), so the
    hole scores, and the Stableford scored from them, carry it exactly.
    """
    hv = out.hole_vp.astype(np.int16)
    n_s, n_p, _ = hv.shape
    round_of = np.concatenate([tgt.holes["Round"].to_numpy(int),
                               np.repeat(np.arange(tgt.random_rounds) + 10_000, _HOLES)])
    theta = rng.normal(0.0, form_sd, (n_s, n_p)) if form_sd > 0 else np.zeros((n_s, n_p))
    for rid in np.unique(round_of):
        cols = np.flatnonzero(round_of == rid)
        m = len(cols)
        day = rng.normal(0.0, day_sd, (n_s, n_p)) if day_sd > 0 else 0.0
        x = np.rint((theta + day) * m / _HOLES).astype(np.int64)
        base, rem = np.divmod(x, m)
        rank = np.argsort(np.argsort(rng.random((n_s, n_p, m)), axis=2), axis=2)
        hv[:, :, cols] += (base[..., None] + (rank < rem[..., None])).astype(np.int16)
    hv = np.clip(hv, -9, 20)
    out.hole_vp = hv.astype(np.int8)
    return hv


def win_probs_at(state: TegState, rnd: int, hole: int, k: float = DEFAULT_K,
                 P: float = DEFAULT_P, n_sims: int = sim.DEFAULT_SIMS,
                 seed: int | None = None, *, form_var: float = DEFAULT_FORM_VAR,
                 day_var: float = DEFAULT_DAY_VAR) -> pd.DataFrame:
    """Win chances after hole ``hole`` of completed round ``rnd`` ((0, 0) = before the TEG).

    Rounds before ``rnd`` and holes 1..``hole`` of it are banked; the rest of the
    round and the later rounds are simulated. Current form counts played holes as
    a fraction of a round (``form_shift``). Returns a tidy frame: teg, round, hole,
    measure, player, win_prob, mean and sd (expected GrossVP per 18 remaining holes
    and its SD including the form and day offsets, NaN when none remain), w, banked.

    ``form_var`` and ``day_var`` (strokes² per round; 0 turns them off) add the
    correlated spread independent holes lack: an uncertain TEG form offset per
    player (variance form_var x (1 - w)) and a fresh day offset per round, spread
    over the simulated holes (``_add_round_offsets``).
    """
    rnd, hole = int(rnd), int(hole)
    if rnd == 0:
        hole = 0
    elif rnd not in state.done or not 1 <= hole <= _HOLES:
        raise ValueError(f"No completed round {rnd} hole {hole} in TEG {state.teg_num}")
    support, cells = state.cells()
    bnd = state.prior.boundaries
    full = [r for r in state.done if r < rnd] + ([rnd] if hole == _HOLES else [])
    segments = [(r, _HOLES) for r in full] + ([(rnd, hole)] if rnd and hole < _HOLES else [])
    holes_played = sum(h for _, h in segments)
    played = state.holes.merge(pd.DataFrame(segments, columns=["Round", "Upto"]), on="Round")
    played = played[played["Hole"] <= played["Upto"]]
    tot = played.groupby("Pl")[["GrossVP", "Net"]].sum()
    gross_b = np.array([int(tot["GrossVP"].get(p, 0)) for p in state.players], dtype=np.int64)
    net_b = np.array([int(tot["Net"].get(p, 0)) for p in state.players], dtype=np.int64)
    by_round = played.groupby(["Pl", "Round"])["GrossVP"].sum()

    tgt = _remaining_target(state, rnd, hole)
    rem_cards = [c for _, c in tgt.holes.groupby("Round")] if len(tgt.holes) else []
    w = form_shift(0.0, holes_played, k, P)[1]
    adjusted, means, sds = {}, [], []
    for pl in state.players:
        keys, p = cells[pl]
        prior_mean = (p * support).sum(axis=1)
        residual = sum(float(by_round.get((pl, r), 0)) - float(prior_mean[
            _card_cells(keys, state.cards[r][state.cards[r]["Hole"] <= h], bnd)].sum())
            for r, h in segments)
        shift, _ = form_shift(residual, holes_played, k, P)
        q = shift_cells(p, support, shift / _HOLES) if segments else p
        adjusted[pl] = (keys, q)
        qm, qv = _moments(q, support)
        hm = [qm[_card_cells(keys, c, bnd)] for c in rem_cards]
        hv = [qv[_card_cells(keys, c, bnd)] for c in rem_cards]
        if tgt.random_rounds:
            pool = [_card_cells(keys, _pool_card(c), bnd) for c in state.course_pool]
            hm += [np.concatenate([qm[h] for h in pool]).reshape(-1, _HOLES).mean(axis=0)] * tgt.random_rounds
            hv += [np.concatenate([qv[h] for h in pool]).reshape(-1, _HOLES).mean(axis=0)] * tgt.random_rounds
        if hm:
            means.append(float(np.concatenate(hm).mean() * _HOLES))
            sds.append(float(np.sqrt(np.concatenate(hv).mean() * _HOLES
                                     + max(form_var, 0.0) * (1 - w) + max(day_var, 0.0))))
        else:
            means.append(float("nan"))
            sds.append(float("nan"))

    if len(tgt.holes) or tgt.random_rounds:
        dists = _dists_from_cells(state.prior, support, adjusted)
        extra = form_var > 0 or day_var > 0
        out = sim.run_simulation(dists, tgt, n_sims, seed, keep_scores=extra)
        if extra:
            rng = np.random.default_rng(None if seed is None else [int(seed), 104729])
            hv = _add_round_offsets(out, tgt, float(np.sqrt(form_var * (1 - w))),
                                    float(np.sqrt(day_var)), rng)
            vp = hv.sum(axis=2, dtype=np.int64)
            stab = sim.stableford_totals(out, state.handicaps)
        else:
            vp = out.gross.astype(np.int64) - out.par_total
            stab = out.stableford
        gross_t = gross_b + vp
        if state.stableford:
            net_t = net_b + stab
        else:
            fixed_si = tgt.holes["SI"].to_numpy(int)
            strokes = np.array([_strokes(fixed_si, state.handicaps[p]) + tgt.random_rounds * state.handicaps[p]
                                for p in state.players])
            net_t = net_b + vp - strokes
    else:
        gross_t, net_t = gross_b[None, :], net_b[None, :]
    probs = {"net": win_shares(net_t, higher_better=state.stableford),
             "gross": win_shares(gross_t, higher_better=False)}
    return pd.concat([pd.DataFrame({
        "teg": state.teg_num, "round": rnd, "hole": hole, "measure": m, "player": state.players,
        "win_prob": probs[m], "mean": means, "sd": sds, "w": w,
        "banked": net_b if m == "net" else gross_b}) for m in MEASURES], ignore_index=True)


def _after_round(state: TegState, after: int, k: float, P: float,
                 n_sims: int, seed: int | None, **var_kwargs) -> pd.DataFrame:
    """Tidy rows for one after_round (both measures)."""
    df = win_probs_at(state, after, _HOLES if after else 0, k, P, n_sims, seed, **var_kwargs)
    return df.rename(columns={"round": "after_round"}).drop(columns="hole")


def win_probs_by_round(
    teg_num: int | TegState,
    history: pd.DataFrame | None = None,
    k: float = DEFAULT_K,
    P: float = DEFAULT_P,
    prior_weights: Sequence[float] = DEFAULT_PRIOR_WEIGHTS,
    n_sims: int = sim.DEFAULT_SIMS,
    seed: int | None = None,
    *,
    form_var: float = DEFAULT_FORM_VAR,
    day_var: float = DEFAULT_DAY_VAR,
    **state_kwargs,
) -> pd.DataFrame:
    """Win probabilities after round 0 (pre-tournament), 1, 2, ... of a TEG.

    Covers every completed round so far; once all rounds are done the last row
    set is the actual result. Returns a tidy frame: teg, after_round, measure
    ("net" first, then "gross"), player, win_prob, mean and sd (expected GrossVP
    per remaining round and its SD, NaN when none remain), w (current-form
    weight) and banked (measure total so far). Pass a ``TegState`` to reuse one
    (e.g. across k/P); otherwise ``load_teg_state(teg_num, history, prior_weights,
    **state_kwargs)``. The same ``seed`` gives the same random draws across k/P.
    """
    state = teg_num if isinstance(teg_num, TegState) else load_teg_state(
        teg_num, history, prior_weights, **state_kwargs)
    return pd.concat([_after_round(state, r, k, P, n_sims, seed, form_var=form_var, day_var=day_var)
                      for r in range(len(state.done) + 1)], ignore_index=True)


# ---------------------------------------------------------------- backtest

def backtest_blend(
    ks: Sequence[float] = BACKTEST_KS,
    Ps: Sequence[float] = BACKTEST_PS,
    target_tegs: Sequence[int] | None = None,
    history: pd.DataFrame | None = None,
    prior_weights: Sequence[float] = DEFAULT_PRIOR_WEIGHTS,
    n_sims: int = DEFAULT_BACKTEST_SIMS,
    seed: int = 0,
) -> pd.DataFrame:
    """Brier score of each (k, P) on completed TEGs replayed round by round.

    For each target TEG (default: every TEG in completed_tegs.csv with
    ``len(prior_weights)`` TEGs before it in ``history``; every target must have
    all its rounds complete) win probabilities after rounds 1..n-1 are scored
    against the actual winner(s) (ties shared): Brier = sum over players of
    (p - outcome)^2. Round 0 is left out because k and P don't change it. Only
    P/k changes w, so each ratio is simulated once. Returns k, P, measure,
    after_round, brier, tegs (mean over TEGs).
    """
    history = sim.load_history(teg_nums=[50]) if history is None else history
    tegs = sorted(int(t) for t in history["TEGNum"].unique())
    if target_tegs is None:
        done = set(sim._tegnums(sim._read_csv(sim.COMPLETED_TEGS_CSV)))
        target_tegs = [t for t in tegs
                       if t in done and sum(e < t for e in tegs) >= len(prior_weights)]
    states = []
    for t in target_tegs:
        st = load_teg_state(t, history, prior_weights, from_scores=True)
        if len(st.done) != st.n_rounds:
            raise ValueError(f"TEG {t} is not complete, so it can't be backtested")
        states.append(st)
    rows, cache = [], {}
    for k in ks:
        for P in Ps:
            ratio = round(float(P) / float(k), 9) if k > 0 else float("inf")
            if ratio not in cache:
                part = []
                for st in states:
                    df = win_probs_by_round(st, k=k, P=P, n_sims=n_sims, seed=seed)
                    final = df[df["after_round"] == st.n_rounds].set_index(["measure", "player"])["win_prob"]
                    live = df[(df["after_round"] >= 1) & (df["after_round"] < st.n_rounds)]
                    outcome = final.reindex(pd.MultiIndex.from_frame(live[["measure", "player"]]))
                    sq = (live["win_prob"].to_numpy() - outcome.to_numpy()) ** 2
                    b = live.assign(sq=sq).groupby(["measure", "after_round"])["sq"].sum()
                    part += [(m, int(r), st.teg_num, float(v)) for (m, r), v in b.items()]
                cache[ratio] = part
            rows += [{"k": float(k), "P": float(P), "measure": m, "after_round": r,
                      "teg": t, "brier": v} for m, r, t, v in cache[ratio]]
    out = pd.DataFrame(rows)
    return (out.groupby(["k", "P", "measure", "after_round"])
            .agg(brier=("brier", "mean"), tegs=("teg", "nunique")).reset_index())
