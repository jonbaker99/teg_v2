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
expected on those scorecards. With w = k*n / (k*n + P) (n = completed rounds):

- mean: every hole distribution is exponentially tilted so the expected round
  moves by w x the average residual;
- SD: the distributions are sharpened or flattened (p**a, then re-tilted to the
  same means) so the round SD on the played scorecards is
  (1 - w/2) x prior SD + w/2 x SD of the residuals (prior SD if n < 2).

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
DEFAULT_PRIOR_WEIGHTS = (50.0, 30.0, 20.0)
MEASURES = ("net", "gross")  # net leads: Stableford (TEG 8+), else NetVP
BACKTEST_KS = (1.0, 2.0, 3.0, 4.0, 6.0)
BACKTEST_PS = (2.0, 4.0, 6.0, 9.0, 12.0)
DEFAULT_BACKTEST_SIMS = 4_000
_HOLES = 18
_SPREAD_RANGE = (0.2, 5.0)  # bounds on the p**a exponent


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


def blend_weight(n: int, k: float = DEFAULT_K, P: float = DEFAULT_P) -> float:
    """Current-form weight w = k*n / (k*n + P) after ``n`` completed rounds."""
    if k < 0 or P <= 0:
        raise ValueError("k must be >= 0 and P > 0")
    return float(k * n / (k * n + P)) if n > 0 else 0.0


def blend_form(
    prior_sd: float, residuals: Sequence[float],
    k: float = DEFAULT_K, P: float = DEFAULT_P,
) -> tuple[float, float, float]:
    """(mean shift per round, target round SD, w) from this TEG's round residuals.

    Residual = actual round GrossVP - the prior expectation on that scorecard.
    The blended mean is prior + w x mean residual. The SD uses w/2, since 1-3
    rounds give a poor variance estimate; with fewer than 2 rounds the prior SD
    is kept.
    """
    res = np.asarray(residuals, dtype=float)
    n = len(res)
    w = blend_weight(n, k, P)
    if n == 0:
        return 0.0, float(prior_sd), 0.0
    cur_sd = float(res.std(ddof=1)) if n >= 2 else prior_sd
    return float(w * res.mean()), float((w / 2) * cur_sd + (1 - w / 2) * prior_sd), w


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


def _round_moments(p, support, holes_per_card: list[np.ndarray]) -> tuple[float, float]:
    """Average round mean and SD over scorecards (holes independent within a round)."""
    m, v = _moments(p, support)
    means = [m[h].sum() for h in holes_per_card]
    vars_ = [v[h].sum() for h in holes_per_card]
    return float(np.mean(means)), float(np.sqrt(np.mean(vars_)))


def adjust_cells(
    p: np.ndarray, support: np.ndarray, shift_per_hole: float,
    target_sd: float | None, ref_holes: list[np.ndarray],
) -> np.ndarray:
    """Move every cell's mean by ``shift_per_hole`` and set the round SD on ``ref_holes``.

    The spread is changed by p**a (a > 1 sharpens, a < 1 flattens; outcomes with
    zero probability stay at zero), each cell then tilted back to its shifted
    mean. ``target_sd=None`` keeps a = 1 (mean shift only).
    """
    targets = (p * support).sum(axis=1) + shift_per_hole

    def make(a: float) -> np.ndarray:
        q = np.where(p > 0, p, 0.0) ** a
        return _tilt_rows(q / q.sum(axis=1, keepdims=True), support, targets)

    if target_sd is None or not ref_holes:
        return make(1.0)
    lo, hi = np.log(_SPREAD_RANGE[0]), np.log(_SPREAD_RANGE[1])
    for _ in range(30):  # round SD falls as a rises: bisect on log a
        mid = (lo + hi) / 2
        if _round_moments(make(np.exp(mid)), support, ref_holes)[1] > target_sd:
            lo = mid
        else:
            hi = mid
    return make(np.exp((lo + hi) / 2))


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
    gross: pd.DataFrame | None = None  # Round x Pl actual GrossVP (completed rounds)
    net: pd.DataFrame | None = None    # Round x Pl Stableford (TEG 8+) or NetVP
    prior: sim.ScoreDistributions | None = None

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
    cur = t[t["Round"].isin(done)]
    gross = cur.pivot_table(index="Round", columns="Pl", values="GrossVP", aggfunc="sum")
    net = cur.pivot_table(index="Round", columns="Pl", values=net_col, aggfunc="sum")
    prior = prior_distributions(history, teg_num, players, prior_weights, **build_kwargs)
    return TegState(teg_num, players, names, handicaps, n_rounds, cards, pool, done,
                    gross, net, prior)


def _remaining_target(state: TegState, after: int) -> sim.TargetTournament:
    rounds = range(after + 1, state.n_rounds + 1)
    fixed = [state.cards[r].assign(Round=r) for r in rounds if r in state.cards]
    holes = (pd.concat(fixed, ignore_index=True)[["Round", "Hole", "Par", "SI"]] if fixed
             else pd.DataFrame(columns=["Round", "Hole", "Par", "SI"], dtype=int))
    return sim.TargetTournament(
        state.teg_num, holes, list(state.players), dict(state.handicaps), dict(state.names),
        random_rounds=sum(r not in state.cards for r in rounds),
        course_pool=state.course_pool, n_rounds=len(rounds))


def _pool_card(course) -> pd.DataFrame:
    return pd.DataFrame({"Par": np.asarray(course[1], dtype=int), "SI": np.asarray(course[2], dtype=int)})


def _after_round(state: TegState, after: int, k: float, P: float,
                 n_sims: int, seed: int | None) -> pd.DataFrame:
    """Tidy rows for one after_round (both measures)."""
    played = state.done[:after]
    support, cells = _cell_arrays(state.prior)
    bnd = state.prior.boundaries
    remaining = state.n_rounds - after
    rem_cards = [state.cards[r] for r in range(after + 1, state.n_rounds + 1) if r in state.cards]
    n_random = remaining - len(rem_cards)

    adjusted, means, sds, ws = {}, [], [], []
    for pl in state.players:
        keys, p = cells[pl]
        ref = [_card_cells(keys, state.cards[r], bnd) for r in played]
        prior_mean = (p * support).sum(axis=1)
        res = [float(state.gross.loc[r, pl]) - float(prior_mean[h].sum())
               for r, h in zip(played, ref)]
        prior_sd = _round_moments(p, support, ref)[1] if ref else float("nan")
        shift, target_sd, w = blend_form(prior_sd, res, k, P)
        q = adjust_cells(p, support, shift / _HOLES,
                         target_sd if len(res) >= 2 else None, ref) if played else p
        adjusted[pl] = (keys, q)
        ws.append(w)
        rem = [_card_cells(keys, c, bnd) for c in rem_cards]
        if n_random:
            pool = [_card_cells(keys, _pool_card(c), bnd) for c in state.course_pool]
            pm, pv = _moments(q, support)
            avg_m = np.mean([pm[h].sum() for h in pool])
            avg_v = np.mean([pv[h].sum() for h in pool])
        if remaining:
            qm, qv = _moments(q, support)
            m_all = [qm[h].sum() for h in rem] + ([avg_m] * n_random if n_random else [])
            v_all = [qv[h].sum() for h in rem] + ([avg_v] * n_random if n_random else [])
            means.append(float(np.mean(m_all)))
            sds.append(float(np.sqrt(np.mean(v_all))))
        else:
            means.append(float("nan"))
            sds.append(float("nan"))

    gross_b = np.array([int(state.gross.loc[played, pl].sum()) if played else 0
                        for pl in state.players], dtype=np.int64)
    net_b = np.array([int(state.net.loc[played, pl].sum()) if played else 0
                      for pl in state.players], dtype=np.int64)
    if remaining:
        dists = _dists_from_cells(state.prior, support, adjusted)
        res = sim.run_simulation(dists, _remaining_target(state, after), n_sims, seed)
        vp = res.gross.astype(np.int64) - res.par_total
        gross_t = gross_b + vp
        if state.stableford:
            net_t = net_b + res.stableford
        else:
            net_t = net_b + vp - remaining * np.array([state.handicaps[p] for p in state.players])
    else:
        gross_t, net_t = gross_b[None, :], net_b[None, :]
    probs = {"net": win_shares(net_t, higher_better=state.stableford),
             "gross": win_shares(gross_t, higher_better=False)}
    return pd.concat([pd.DataFrame({
        "teg": state.teg_num, "after_round": after, "measure": m, "player": state.players,
        "win_prob": probs[m], "mean": means, "sd": sds, "w": ws,
        "banked": net_b if m == "net" else gross_b}) for m in MEASURES], ignore_index=True)


def win_probs_by_round(
    teg_num: int | TegState,
    history: pd.DataFrame | None = None,
    k: float = DEFAULT_K,
    P: float = DEFAULT_P,
    prior_weights: Sequence[float] = DEFAULT_PRIOR_WEIGHTS,
    n_sims: int = sim.DEFAULT_SIMS,
    seed: int | None = None,
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
    return pd.concat([_after_round(state, r, k, P, n_sims, seed)
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
