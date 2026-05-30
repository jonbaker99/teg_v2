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

MODE_WEIGHTS = {
    "balanced": (1.0, 1.0, 1.0),
    "fast": (1.5, 0.8, 0.7),
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
