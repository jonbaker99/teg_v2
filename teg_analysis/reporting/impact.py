"""Counterfactual `importance`: what the result would have been without the event.

The old `importance` axis was a hand-tuned function of shot-cost, round number
and standing weight. Its docstring called it "contribution to the result", but
it never consulted the result — so a champion's gross 11 that cost him 2.3
Stableford points against an 8-point winning margin scored as highly as a
blow-up that actually decided a competition. Measured on TEG 18 (2026-08-14):
none of Alex Baker's eight worst holes could have cost him the Trophy, yet they
generated 10 negative beats and half the champion-negative material in the cut.

This module answers the question the axis claimed to answer:

    if this player had scored their OWN AVERAGE over these holes instead of
    what they actually scored, would the competition have finished differently?

Two properties fall out of that definition, both wanted:

- **The gross/net mismatch dissolves.** Impact is measured in each
  competition's own metric — Stableford or net-vs-par for the Trophy and
  Wooden Spoon, gross-vs-par for the Green Jacket. A gross catastrophe that
  costs nothing in net terms scores low for the Trophy but can still score
  high for the Jacket, which is exactly right.
- **A winner's collapse that didn't cost them the win scores low by
  construction**, rather than by a prompt rule fighting the inputs.

The baseline is the player's own mean for THIS TEG (Jon's call, 2026-08-14):
self-calibrating to handicap and form, and needs no cross-TEG data.

RECOVERABILITY. Raw counterfactual cost is time-blind: a point dropped at R1 H1
is arithmetically identical to one dropped at R4 H18. Narratively they are not
— with 71 holes still to play, calling the first one a cause of the result is a
leap, while the last one is as close to causation as golf gets. So the raw cost
is scaled by how little opportunity remained to recover (Jon, 2026-08-14). The
floor is deliberately high (`_RECOVERY_FLOOR`): an early disaster that a player
never made up is still a genuine cost, so it is discounted, not erased.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

# (column, higher_is_better) per competition. The Jacket is gross by
# definition; the Trophy and Spoon follow the era metric.
_JACKET_COL = ("GrossVP", False)


def _trophy_col(metric: str) -> tuple:
    return ("NetVP", False) if metric == "net_vs_par" else ("Stableford", True)


# An event with maximum time to recover keeps this share of its raw cost; one on
# the final hole keeps all of it. Not zero — an early collapse the player never
# made up genuinely cost them, it just cannot claim to have *caused* the result.
_RECOVERY_FLOOR = 0.45
# >1 keeps the middle of the tournament closer to the floor, so the premium is
# concentrated in the closing stretch where the causal claim is strongest.
_RECOVERY_CURVE = 1.6


class ImpactModel:
    """Per-TEG counterfactual engine. Build once, query per event.

    Cheap: one groupby per competition up front, then arithmetic per query.
    A whole TEG's sweep runs in well under a second.
    """

    def __init__(self, teg_df: pd.DataFrame, metric: str = "stableford"):
        self.metric = metric
        self.df = teg_df
        self.comps = {"trophy": _trophy_col(metric), "jacket": _JACKET_COL}
        # The Spoon is the Trophy metric read from the wrong end, so it shares
        # the Trophy's totals — only the direction of "nearest rival" differs.
        self.totals = {}
        self.means = {}
        for name, (col, _) in self.comps.items():
            self.totals[name] = teg_df.groupby("Player")[col].sum()
            self.means[name] = teg_df.groupby("Player")[col].mean()
        # Absolute hole position across the whole TEG, for recoverability.
        self.total_holes = float(
            (teg_df["Round"].max() - 1) * 18 + teg_df["Hole"].max()) or 1.0

    def _recoverability(self, rows: pd.DataFrame) -> float:
        """How much of an event's raw cost survives, given time left to recover.

        Keyed on the event's LAST hole — what matters is how much golf remained
        after it, not when it started.
        """
        last = float(((rows["Round"] - 1) * 18 + rows["Hole"]).max())
        progress = min(max(last / self.total_holes, 0.0), 1.0)
        return _RECOVERY_FLOOR + (1.0 - _RECOVERY_FLOOR) * progress ** _RECOVERY_CURVE

    def _standings(self, name: str, override: Optional[tuple] = None) -> pd.Series:
        """Totals sorted best-first, optionally with one player's total replaced."""
        col, higher = self.comps[name]
        totals = self.totals[name]
        if override is not None:
            player, value = override
            totals = totals.copy()
            totals[player] = value
        return totals.sort_values(ascending=not higher)

    def _gap_to_rival(self, standings: pd.Series, player: str, higher: bool,
                      from_bottom: bool = False) -> float:
        """Distance to the rival that matters.

        Leading a competition, that is the cushion over second. Anywhere else it
        is the deficit to the place above. For the Spoon it is the cushion over
        (or deficit to) the player adjacent from the bottom.
        """
        order = list(standings.index)
        if player not in order:
            return 1.0
        i = order.index(player)
        if from_bottom:
            j = len(order) - 2 if i == len(order) - 1 else i + 1
        else:
            j = 1 if i == 0 else i - 1
        if not 0 <= j < len(order) or j == i:
            return 1.0
        return abs(float(standings.iloc[i]) - float(standings.iloc[j])) or 1.0

    def event_impact(self, players: list, holes: list,
                     round_num: Optional[int] = None) -> float:
        """0-10 importance for one event, as the max across competitions.

        `holes` is the beat's hole evidence. When a beat is round-scoped and
        carries no hole evidence, pass `round_num` and the whole round is
        neutralised instead.
        """
        best = 0.0
        for player in players or []:
            rows = self._rows_for(player, holes, round_num)
            if rows is None or rows.empty:
                continue
            for name, (col, higher) in self.comps.items():
                actual = float(rows[col].sum())
                expected = float(self.means[name].get(player, 0.0)) * len(rows)
                # SYMMETRIC. "What would the result have been without this
                # event" is sign-agnostic: a birdie run that sealed the win is
                # as important as a collapse that lost it. Scoring only the
                # damage zeroed every good beat and shoved the cut 41% -> 58%
                # negative (measured 2026-08-14) — the opposite of the goal.
                magnitude = abs(actual - expected)
                if magnitude == 0:
                    continue
                # Neutralising is the same operation either way: swap what they
                # actually scored for what they average.
                neutral = float(self.totals[name][player]) - actual + expected
                recover = self._recoverability(rows)

                for from_bottom in (False, True):   # competition proper, then the Spoon
                    before = self._standings(name)
                    after = self._standings(name, override=(player, neutral))
                    moved = list(before.index).index(player) != list(after.index).index(player)
                    if moved:
                        # Even a result-changing event is discounted if it
                        # happened early enough to be recovered from.
                        best = max(best, 10.0 * recover)
                        continue
                    gap = self._gap_to_rival(before, player, higher, from_bottom)
                    best = max(best, 10.0 * min(1.0, magnitude / gap) * recover)
                    if name == "jacket":
                        break                     # no Spoon on the gross competition
        return round(min(best, 10.0), 2)

    def _rows_for(self, player: str, holes: list,
                  round_num: Optional[int]) -> Optional[pd.DataFrame]:
        d = self.df[self.df["Player"] == player]
        if holes:
            keys = {(h.get("hole"), h.get("round", round_num)) for h in holes}
            bare = {h.get("hole") for h in holes}
            if round_num is not None:
                d = d[(d["Round"] == round_num) & (d["Hole"].isin(bare))]
            else:
                d = d[d.apply(lambda r: (r["Hole"], r["Round"]) in keys
                              or r["Hole"] in bare, axis=1)]
        elif round_num is not None:
            d = d[d["Round"] == round_num]
        else:
            return None
        return d


def apply_counterfactual_importance(events: list, teg_df: pd.DataFrame,
                                    metric: str = "stableford") -> list:
    """Overwrite `importance` on every event whose impact can be computed.

    Applied as a post-processing pass rather than by editing each detector, so
    the detectors stay responsible for FINDING things and this stays the single
    place that decides how much any of them MATTERED.

    Events with no hole evidence and no round (the competition-spine beats:
    trophy_win, jacket_win, wooden_spoon) keep their hand-set importance — they
    are the result, so asking what they cost the result is meaningless. The
    prior value is kept in `context["importance_legacy"]` for comparison.
    """
    model = ImpactModel(teg_df, metric)
    for e in events:
        if not e.players:
            continue
        if not e.holes and e.round is None:
            continue
        imp = model.event_impact(e.players, e.holes, e.round)
        e.context["importance_legacy"] = round(e.importance, 2)
        e.context["impact_metric"] = metric
        e.importance = imp
    return events
