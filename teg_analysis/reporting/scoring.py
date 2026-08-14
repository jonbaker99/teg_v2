"""Stage 2 scoring: combine the three axes into a single rankable total.

Every NotableEvent (see events.py) carries three 0-10 sub-scores set by the
detectors:

- importance   : contribution to the result, scored at top AND bottom of the board
- rarity       : how noteworthy the thing is in TEG history
- entertainment: colour independent of the result (the non-contender's brilliant
                 or disastrous spell, volatility, surprise-given-standing)

Weights are a dial per mode: the fast post-round write-up leans on importance;
the archive edition cranks rarity + entertainment for richer colour.
"""

from __future__ import annotations

# (importance, rarity, entertainment).
#
# `balanced` is the default every call site uses, so this tuple decides what the
# editor is shown for effectively every report.
#
# It was (1.0, 1.0, 1.0) until 2026-08-11 — never tuned, and not actually
# balanced in effect: the axes don't share a range (importance spans 2-10,
# rarity rarely passes 7), so equal weights quietly favoured the two axes a
# blow-up scores highest on. The measured result was that `big_blowup` took
# **53% of the top-20 slots** across TEGs 9-18 and the cut ran 60% disaster-toned.
#
# Now (1.5, 0.8, 0.7) — the setting previously called `fast`, adopted on the
# evidence in EXPERIMENTS.md -> H10(a): blow-up share 53% -> 40%, tone 60% -> 48%
# disaster, while keeping an 85% top-20 overlap with the long-validated baseline.
# `importance-led` (2.0, 0.5, 0.5) rebalances harder (23% blow-ups, achievement-
# majority) and is the setting to try next if 40% still reads as too much carnage.
#
# Re-measure any change with `python scripts/weight_profiler.py`.
# RE-PROFILED 2026-08-14, after `importance` became counterfactual (impact.py).
# The old tuning was fitted against the hand-tuned axis and was void.
#
# The headline result is that the weights now barely matter. Under the old axis
# the spread between settings was ~30 points of blow-up share; re-swept over
# TEGs 2-18 against the new axis, every reasonable setting lands within 34-43%
# negative. The weights were doing so much work before precisely BECAUSE
# importance was a poor proxy that correlated with badness. Measuring actual
# result-impact dissolved the tuning problem rather than re-solving it.
#
# (2.0, 1.0, 0.5) was marginally best (34% negative / 33% positive, lowest churn
# at 15%) and is principled: lean on the axis that now means what it says, keep
# rarity high enough to surface records and PBs (which serve celebration), and
# damp entertainment, the one axis a blow-up dominates. The margin over the old
# setting is ~2 points and within noise — do not read precision into it.
MODE_WEIGHTS = {
    "balanced": (2.0, 1.0, 0.5),
    # Retained as an alias so `mode="fast"` callers keep working; identical to
    # `balanced` since the fast weights became the default.
    "fast": (2.0, 1.0, 0.5),
    # NOTE: measured as the *opposite* lever to what its name suggests. Cranking
    # rarity + entertainment entrenches the blow-up bias rather than adding
    # colour (53.0% -> 53.5% blow-ups), because those are precisely the two axes
    # a blow-up already dominates. Kept for comparison; not recommended.
    "archive": (1.0, 1.3, 1.3),
}


def cap(x: float, lo: float = 0.0, hi: float = 10.0) -> float:
    """Clamp a raw score into the 0-10 band (or a custom band)."""
    return max(lo, min(hi, x))


def total_score(event, weights=(1.0, 1.0, 1.0)) -> float:
    wi, wr, we = weights
    return wi * event.importance + wr * event.rarity + we * event.entertainment


def finalise(events, mode: str = "balanced"):
    """Set .total on each event for the chosen mode and return them ranked desc."""
    weights = MODE_WEIGHTS.get(mode, MODE_WEIGHTS["balanced"])
    for e in events:
        e.total = round(total_score(e, weights), 2)
    return sorted(events, key=lambda e: e.total, reverse=True)
