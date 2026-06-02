"""Era helpers: which Trophy metric applies to a given TEG.

The Trophy was decided by total net-vs-par (lower is better) for TEGs 1–7,
and by total Stableford points (higher is better) from TEG 8 onwards.
"""

from typing import Literal

TrophyMetric = Literal["stableford", "net_vs_par"]

STABLEFORD_FROM_TEG = 8


def trophy_metric(teg_num: int) -> TrophyMetric:
    """Return the Trophy metric for the given TEG number."""
    return "stableford" if teg_num >= STABLEFORD_FROM_TEG else "net_vs_par"
