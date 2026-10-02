"""Bounce-back rate: how often a player recovers on the hole after a bad one.

Definition (stated with every result, so callers can show it):

- A **trigger** is a hole scored at bogey or worse (or double bogey or worse,
  with ``trigger="double_or_worse"``) against par.
- The **response** is the next hole in the *same round*. Hole 18 never
  triggers, because there is no next hole in that round.
- A **bounce-back** is a response hole at par or better.
- **Bounce-back rate** = bounce-backs / triggers.

Gross uses ``GrossVP``. Net uses ``NetVP`` (handicap strokes applied), which
is closer to "playing to handicap" than gross for high handicappers.

For context each row also carries the player's ordinary par-or-better rate on
every hole that *could* be a response (holes 2–18). A bounce-back rate above
that baseline means the player recovers better than their normal standard.
"""

from __future__ import annotations

import pandas as pd

BASIS_COLUMNS = {"gross": "GrossVP", "net": "NetVP"}
TRIGGER_THRESHOLDS = {"bogey_or_worse": 1, "double_or_worse": 2}
GROUPINGS = {
    "player": ["Player"],
    "player_teg": ["Player", "TEGNum"],
    "player_year": ["Player", "Year"],
}


def _paired_holes(all_data: pd.DataFrame, vp_col: str) -> pd.DataFrame:
    """Each hole joined to the next hole in the same round, same player."""
    cols = ["Player", "TEGNum", "Round", "Hole", "Year", vp_col]
    df = all_data[cols].sort_values(["Player", "TEGNum", "Round", "Hole"])
    nxt = df.groupby(["Player", "TEGNum", "Round"])[["Hole", vp_col]].shift(-1)
    df = df.assign(next_hole=nxt["Hole"], next_vp=nxt[vp_col])
    # Only consecutive holes count, so a gap in the data never pairs hole 7 with 9.
    return df[df["next_hole"] == df["Hole"] + 1]


def bounce_back_stats(
    all_data: pd.DataFrame,
    basis: str = "gross",
    trigger: str = "bogey_or_worse",
    group_by: str = "player",
) -> pd.DataFrame:
    """Bounce-back rate per group, best first.

    Returns columns: the grouping columns, ``Triggers``, ``BounceBacks``,
    ``BounceBackRate``, ``BaselineParOrBetterRate`` and ``Difference``
    (rate minus baseline, in percentage points). Rates are percentages.
    """
    if basis not in BASIS_COLUMNS:
        raise ValueError(f"basis must be one of {sorted(BASIS_COLUMNS)}")
    if trigger not in TRIGGER_THRESHOLDS:
        raise ValueError(f"trigger must be one of {sorted(TRIGGER_THRESHOLDS)}")
    if group_by not in GROUPINGS:
        raise ValueError(f"group_by must be one of {sorted(GROUPINGS)}")

    vp_col = BASIS_COLUMNS[basis]
    keys = GROUPINGS[group_by]
    pairs = _paired_holes(all_data, vp_col)
    pairs = pairs.assign(
        is_trigger=pairs[vp_col] >= TRIGGER_THRESHOLDS[trigger],
        next_good=pairs["next_vp"] <= 0,
    )

    triggered = pairs[pairs["is_trigger"]]
    out = triggered.groupby(keys).agg(
        Triggers=("is_trigger", "size"),
        BounceBacks=("next_good", "sum"),
    )
    baseline = pairs.groupby(keys)["next_good"].mean().rename("BaselineParOrBetterRate")
    out = out.join(baseline).reset_index()
    out["BounceBacks"] = out["BounceBacks"].astype(int)
    out["BounceBackRate"] = (100 * out["BounceBacks"] / out["Triggers"]).round(1)
    out["BaselineParOrBetterRate"] = (100 * out["BaselineParOrBetterRate"]).round(1)
    out["Difference"] = (out["BounceBackRate"] - out["BaselineParOrBetterRate"]).round(1)
    return out.sort_values("BounceBackRate", ascending=False, kind="stable").reset_index(drop=True)
