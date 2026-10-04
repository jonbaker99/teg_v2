"""Round-by-round win probabilities for a TEG, updated after each completed round.

Each player's remaining rounds are simulated as gross rounds: a round's GrossVP
total is drawn from Normal(mean, sd) and spread over 18 holes using one of the
player's past rounds as a template (holes ordered by stroke index). Stableford
points are then scored from those gross holes with the player's handicap for
this TEG, so Stableford is never simulated directly and past handicaps don't
matter. Completed rounds are banked at their actual scores.

The mean and SD blend prior form with current form. Prior form is the player's
rounds in the TEGs held before this one (weights ``prior_weights``, most recent
first, renormalised over the TEGs they played; field average if none). Current
form is this TEG's completed rounds, with weight w = k*n / (k*n + P) on the mean
and w/2 on the SD. Only the ratio P/k changes w (w = n / (n + P/k)).

The net measure is Stableford points from TEG ``STABLEFORD_ERA_TEG`` and net vs
par before it. Ties for the lead are shared wins, in simulations and in the
actual outcome.

UI-agnostic: returns DataFrames/arrays only.
"""

from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np
import pandas as pd

from teg_analysis.analysis.aggregation import STABLEFORD_ERA_TEG
from teg_analysis.analysis.simulation import (COMPLETED_TEGS_CSV, DEFAULT_SIMS, MAX_SIMS,
                                              _read_csv, _tegnums)
from teg_analysis.constants import ALL_DATA_PARQUET

DEFAULT_K = 3.0
DEFAULT_P = 6.0
DEFAULT_PRIOR_WEIGHTS = (50.0, 30.0, 20.0)
MEASURES = ("net", "gross")  # net leads: Stableford (TEG 8+), else NetVP
BACKTEST_KS = (1.0, 2.0, 3.0, 4.0, 6.0)
BACKTEST_PS = (2.0, 4.0, 6.0, 9.0, 12.0)
DEFAULT_BACKTEST_SIMS = 4_000
_HOLES = 18
_SI_COLS = [f"SI{s}" for s in range(1, _HOLES + 1)]


# ---------------------------------------------------------------- data

def round_scores(all_data: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per TEG/round/player from all-data.parquet.

    Columns: TEGNum, Round, Pl, GrossVP, NetVP, Stableford, HC, Holes, and
    SI1..SI18 (hole GrossVP by stroke index; NaN where the round lacks that SI).
    """
    if all_data is None:
        from teg_analysis.io.file_operations import read_file

        all_data = read_file(ALL_DATA_PARQUET)
    df = all_data[all_data["Sc"].notna()].copy()
    df["TEGNum"] = df["TEGNum"].astype(int)
    df["Round"] = df["Round"].astype(int)
    df["SI"] = df["SI"].astype(int)
    keys = ["TEGNum", "Round", "Pl"]
    out = df.groupby(keys).agg(
        GrossVP=("GrossVP", "sum"), NetVP=("NetVP", "sum"), Stableford=("Stableford", "sum"),
        HC=("HC", "first"), Holes=("Sc", "count")).reset_index()
    by_si = df.pivot_table(index=keys, columns="SI", values="GrossVP", aggfunc="first")
    by_si = by_si.reindex(columns=range(1, _HOLES + 1))
    by_si.columns = _SI_COLS
    out = out.merge(by_si.reset_index(), on=keys, how="left")
    for c in ("GrossVP", "NetVP", "Stableford", "HC"):
        out[c] = out[c].astype(float)
    return out.sort_values(keys).reset_index(drop=True)


# ---------------------------------------------------------------- form

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


def _weighted_mean_sd(x: np.ndarray, w: np.ndarray) -> tuple[float, float]:
    """Weighted mean and SD (reliability weights, so equal weights give the sample SD)."""
    v1 = w.sum()
    mean = float((w * x).sum() / v1)
    denom = v1 - (w ** 2).sum() / v1
    sd = float(np.sqrt((w * (x - mean) ** 2).sum() / denom)) if denom > 0 else float("nan")
    return mean, sd


def _form_stats(rounds: pd.DataFrame, teg_w: dict[int, float]) -> tuple[float, float]:
    """Mean/SD of round GrossVP; each TEG's weight is split equally over its rounds."""
    r = rounds[rounds["TEGNum"].isin(list(teg_w))]
    n_per_teg = r.groupby("TEGNum")["GrossVP"].transform("count")
    w = r["TEGNum"].map(teg_w).to_numpy(float) / n_per_teg.to_numpy(float)
    return _weighted_mean_sd(r["GrossVP"].to_numpy(float), w)


def prior_form(
    rounds: pd.DataFrame, teg_num: int, players: Sequence[str],
    prior_weights: Sequence[float] = DEFAULT_PRIOR_WEIGHTS,
) -> pd.DataFrame:
    """Per-player prior GrossVP per round from the TEGs held before ``teg_num``.

    Returns Pl, PriorMean, PriorSD, PriorSource ("player" or "field"), PriorTEGs.
    Players with no rounds in those TEGs get the field's mean and SD; a player SD
    that can't be estimated also falls back to the field's.
    """
    held = sorted({int(t) for t in rounds["TEGNum"] if int(t) < int(teg_num)}, reverse=True)
    prior_tegs = held[:len(prior_weights)]
    if not prior_tegs:
        raise ValueError(f"No TEGs before TEG {teg_num} to build prior form from")
    prior = rounds[rounds["TEGNum"].isin(prior_tegs)]
    field_mean, field_sd = _form_stats(prior, prior_teg_weights(prior_tegs, prior_tegs, prior_weights))
    rows = []
    for pl in players:
        own = prior[prior["Pl"] == pl]
        w = prior_teg_weights(prior_tegs, own["TEGNum"].unique(), prior_weights)
        if w:
            mean, sd = _form_stats(own, w)
            src = "player"
            if not np.isfinite(sd) or sd <= 0:
                sd = field_sd
        else:
            mean, sd, src = field_mean, field_sd, "field"
        rows.append({"Pl": pl, "PriorMean": mean, "PriorSD": sd, "PriorSource": src,
                     "PriorTEGs": ",".join(str(t) for t in sorted(w, reverse=True))})
    return pd.DataFrame(rows)


def blend_weight(n: int, k: float = DEFAULT_K, P: float = DEFAULT_P) -> float:
    """Current-form weight w = k*n / (k*n + P) after ``n`` completed rounds."""
    if k < 0 or P <= 0:
        raise ValueError("k must be >= 0 and P > 0")
    return float(k * n / (k * n + P)) if n > 0 else 0.0


def blend_form(
    prior_mean: float, prior_sd: float, current: Sequence[float],
    k: float = DEFAULT_K, P: float = DEFAULT_P,
) -> tuple[float, float, float]:
    """Blend prior and current form: (mean, sd, w).

    The mean uses w = ``blend_weight(n)``; the SD uses w/2, since 1-3 rounds give
    a poor variance estimate. With fewer than 2 current rounds the current SD is
    unknown, so the prior SD is used.
    """
    cur = np.asarray(current, dtype=float)
    n = len(cur)
    w = blend_weight(n, k, P)
    if n == 0:
        return float(prior_mean), float(prior_sd), 0.0
    mean = w * cur.mean() + (1 - w) * prior_mean
    cur_sd = float(cur.std(ddof=1)) if n >= 2 else prior_sd
    sd = (w / 2) * cur_sd + (1 - w / 2) * prior_sd
    return float(mean), float(sd), w


# ---------------------------------------------------------------- simulation

def hole_strokes(handicap: int) -> np.ndarray:
    """Handicap strokes on SI 1..18 (plus handicaps give strokes back on the easiest holes)."""
    hc = int(handicap)
    return hc // _HOLES + ((hc % _HOLES) >= np.arange(1, _HOLES + 1))


def spread_to_total(templates: np.ndarray, totals: np.ndarray) -> np.ndarray:
    """Shift SI-ordered template rounds (rows, 18) so each row sums to ``totals``.

    The difference is spread evenly; any remainder goes one stroke each to the
    lowest SIs (hardest holes).
    """
    d = np.asarray(totals, dtype=np.int64) - templates.sum(axis=1)
    base, rem = np.divmod(d, _HOLES)
    return templates + base[:, None] + (np.arange(_HOLES) < rem[:, None])


def win_shares(totals: np.ndarray, higher_better: bool) -> np.ndarray:
    """Mean win share per column of (sims, players) totals; ties for the lead share the win."""
    best = totals.max(axis=1) if higher_better else totals.min(axis=1)
    lead = totals == best[:, None]
    return (lead / lead.sum(axis=1, keepdims=True)).mean(axis=0)


def simulate_win_probs(
    banked_gross: np.ndarray, banked_net: np.ndarray,
    means: np.ndarray, sds: np.ndarray,
    templates: Sequence[np.ndarray], handicaps: Sequence[int],
    remaining: int, stableford: bool,
    n_sims: int = DEFAULT_SIMS, rng: np.random.Generator | None = None,
) -> dict[str, np.ndarray]:
    """Win probability per player for each measure in ``MEASURES``.

    Each remaining round: GrossVP total ~ round(Normal(mean, sd)), spread over a
    random template round of that player (SI-ordered GrossVP, ``templates[j]`` of
    shape (m, 18)). Net is Stableford points from those holes and the handicap
    when ``stableford``, else net vs par (gross - handicap). Totals add to the
    banked ones. With ``remaining == 0`` this is the actual outcome.
    """
    rng = rng or np.random.default_rng()
    n_sims = int(min(max(int(n_sims), 1), MAX_SIMS)) if remaining > 0 else 1
    n_pl = len(means)
    gross = np.tile(np.asarray(banked_gross, dtype=np.int64), (n_sims, 1))
    net = np.tile(np.asarray(banked_net, dtype=np.int64), (n_sims, 1))
    for j in range(n_pl):
        strokes = hole_strokes(handicaps[j])
        tmpl = np.asarray(templates[j], dtype=np.int64)
        for _ in range(remaining):
            z = rng.standard_normal(n_sims)
            pick = rng.integers(0, len(tmpl), size=n_sims)
            tot = np.rint(means[j] + sds[j] * z).astype(np.int64)
            gross[:, j] += tot
            if stableford:
                holes = spread_to_total(tmpl[pick], tot)
                net[:, j] += np.maximum(0, 2 + strokes - holes).sum(axis=1)
            else:
                net[:, j] += tot - int(handicaps[j])
    return {"net": win_shares(net, higher_better=stableford),
            "gross": win_shares(gross, higher_better=False)}


# ---------------------------------------------------------------- orchestration

def _teg_setup(teg_num: int, rounds: pd.DataFrame) -> tuple[list[str], dict[str, int], int]:
    """Players, handicaps and round count: from data for completed TEGs, else the target loader."""
    t = rounds[rounds["TEGNum"] == teg_num]
    if teg_num in _tegnums(_read_csv(COMPLETED_TEGS_CSV)) and not t.empty:
        hcs = t.groupby("Pl")["HC"].first()
        return sorted(hcs.index), {p: int(round(h)) for p, h in hcs.items()}, int(t["Round"].nunique())
    from teg_analysis.analysis.simulation import load_target_tournament

    target = load_target_tournament(teg_num)
    played = set(t["Pl"])
    if played - set(target.players):
        raise ValueError(f"TEG {teg_num} has scores for players not on the roster: "
                         f"{', '.join(sorted(played - set(target.players)))}")
    hcs = dict(target.handicaps)
    for p, h in t.groupby("Pl")["HC"].first().items():
        hcs[p] = int(round(h))
    return list(target.players), hcs, max(int(target.n_rounds), int(t["Round"].nunique()))


def completed_rounds(rounds: pd.DataFrame, teg_num: int, players: Sequence[str]) -> list[int]:
    """Leading rounds 1, 2, ... where every player has all 18 holes."""
    t = rounds[(rounds["TEGNum"] == teg_num) & (rounds["Holes"] == _HOLES)]
    full = {r for r, g in t.groupby("Round") if set(players) <= set(g["Pl"])}
    done = []
    while len(done) + 1 in full:
        done.append(len(done) + 1)
    return done


def _templates(rounds: pd.DataFrame, teg_num: int, players: Sequence[str],
               n_prior: int) -> list[np.ndarray]:
    """SI-ordered GrossVP rounds per player from the prior TEGs; field rounds if none."""
    held = sorted({int(t) for t in rounds["TEGNum"] if int(t) < teg_num}, reverse=True)
    prior = rounds[rounds["TEGNum"].isin(held[:n_prior])].dropna(subset=_SI_COLS)
    field = prior[_SI_COLS].to_numpy(dtype=np.int64)
    if not len(field):
        raise ValueError(f"No complete prior rounds before TEG {teg_num}")
    out = []
    for pl in players:
        own = prior.loc[prior["Pl"] == pl, _SI_COLS].to_numpy(dtype=np.int64)
        out.append(own if len(own) else field)
    return out


def win_probs_by_round(
    teg_num: int,
    rounds: pd.DataFrame | None = None,
    k: float = DEFAULT_K,
    P: float = DEFAULT_P,
    prior_weights: Sequence[float] = DEFAULT_PRIOR_WEIGHTS,
    n_sims: int = DEFAULT_SIMS,
    seed: int | None = None,
    *,
    players: Sequence[str] | None = None,
    handicaps: dict[str, int] | None = None,
    n_rounds: int | None = None,
) -> pd.DataFrame:
    """Win probabilities after round 0 (pre-tournament), 1, 2, ... of ``teg_num``.

    Covers every completed round so far; once all rounds are done the last row
    set is the actual result. Returns a tidy frame with columns teg, after_round,
    measure ("net" first, then "gross"), player, win_prob, mean, sd (simulated
    GrossVP per round), w (current-form weight on the mean) and banked (measure
    total so far). ``players``/``handicaps``/``n_rounds`` override the TEG's own.
    With ``seed`` each after_round uses its own reproducible stream, so runs with
    different k/P share random numbers.
    """
    teg_num = int(teg_num)
    rounds = round_scores() if rounds is None else rounds
    if players is None or handicaps is None or n_rounds is None:
        pl0, hc0, nr0 = _teg_setup(teg_num, rounds)
        players = pl0 if players is None else list(players)
        handicaps = hc0 if handicaps is None else handicaps
        n_rounds = nr0 if n_rounds is None else int(n_rounds)
    players = list(players)
    stableford = teg_num >= STABLEFORD_ERA_TEG
    net_col = "Stableford" if stableford else "NetVP"

    prior = prior_form(rounds, teg_num, players, prior_weights).set_index("Pl")
    templates = _templates(rounds, teg_num, players, len(prior_weights))
    hcs = [int(handicaps[p]) for p in players]
    done = completed_rounds(rounds, teg_num, players)
    cur = rounds[(rounds["TEGNum"] == teg_num) & rounds["Round"].isin(done)]
    cur = cur.set_index(["Pl", "Round"])

    frames = []
    for r in range(len(done) + 1):
        played = list(range(1, r + 1))
        means, sds, ws, gross_b, net_b = [], [], [], [], []
        for pl in players:
            g = [cur.loc[(pl, rr), "GrossVP"] for rr in played]
            m, s, w = blend_form(prior.loc[pl, "PriorMean"], prior.loc[pl, "PriorSD"], g, k, P)
            means.append(m)
            sds.append(s)
            ws.append(w)
            gross_b.append(int(sum(g)))
            net_b.append(int(sum(cur.loc[(pl, rr), net_col] for rr in played)))
        rng = np.random.default_rng(None if seed is None else [int(seed), teg_num, r])
        probs = simulate_win_probs(np.array(gross_b), np.array(net_b), np.array(means),
                                   np.array(sds), templates, hcs, n_rounds - r,
                                   stableford, n_sims, rng)
        for measure in MEASURES:
            frames.append(pd.DataFrame({
                "teg": teg_num, "after_round": r, "measure": measure, "player": players,
                "win_prob": probs[measure], "mean": means, "sd": sds, "w": ws,
                "banked": net_b if measure == "net" else gross_b}))
    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------- backtest

def backtest_blend(
    ks: Sequence[float] = BACKTEST_KS,
    Ps: Sequence[float] = BACKTEST_PS,
    target_tegs: Sequence[int] | None = None,
    rounds: pd.DataFrame | None = None,
    prior_weights: Sequence[float] = DEFAULT_PRIOR_WEIGHTS,
    n_sims: int = DEFAULT_BACKTEST_SIMS,
    seed: int = 0,
) -> pd.DataFrame:
    """Brier score of each (k, P) on completed TEGs replayed round by round.

    For each target TEG (default: every TEG in completed_tegs.csv with
    ``len(prior_weights)`` TEGs before it in ``rounds``; every target must have all
    its rounds complete) win probabilities after rounds 1..n-1 are scored against the
    actual winner(s) (ties shared): Brier = sum over players of (p - outcome)^2.
    Round 0 is left out because k and P don't change it. Random numbers are shared
    across (k, P). Returns k, P, measure, after_round, brier, tegs (mean over TEGs).
    """
    rounds = round_scores() if rounds is None else rounds
    tegs = sorted(int(t) for t in rounds["TEGNum"].unique())
    if target_tegs is None:
        done = set(_tegnums(_read_csv(COMPLETED_TEGS_CSV)))
        target_tegs = [t for t in tegs
                       if t in done and sum(e < t for e in tegs) >= len(prior_weights)]
    setups = {}
    for t in target_tegs:
        g = rounds[rounds["TEGNum"] == t]
        hcs = g.groupby("Pl")["HC"].first()
        players, nr = sorted(hcs.index), int(g["Round"].nunique())
        if nr == 0 or len(completed_rounds(rounds, t, players)) != nr:
            raise ValueError(f"TEG {t} is not complete, so it can't be backtested")
        setups[t] = (players, {p: int(round(h)) for p, h in hcs.items()}, nr)
    rows = []
    for k in ks:
        for P in Ps:
            for t, (players, hcs, nr) in setups.items():
                df = win_probs_by_round(t, rounds, k, P, prior_weights, n_sims, seed,
                                        players=players, handicaps=hcs, n_rounds=nr)
                final = df[df["after_round"] == nr].set_index(["measure", "player"])["win_prob"]
                live = df[(df["after_round"] >= 1) & (df["after_round"] < nr)]
                outcome = final.reindex(pd.MultiIndex.from_frame(live[["measure", "player"]]))
                sq = (live["win_prob"].to_numpy() - outcome.to_numpy()) ** 2
                b = live.assign(sq=sq).groupby(["measure", "after_round"])["sq"].sum()
                for (measure, r), v in b.items():
                    rows.append({"k": float(k), "P": float(P), "measure": measure,
                                 "after_round": int(r), "teg": t, "brier": float(v)})
    out = pd.DataFrame(rows)
    return (out.groupby(["k", "P", "measure", "after_round"])
            .agg(brier=("brier", "mean"), tegs=("teg", "nunique")).reset_index())
