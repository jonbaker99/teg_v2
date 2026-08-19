"""All-time streak and score-count record detection, wired into the beat/
bundle system as mandatory beats — the TEG-level analogue of
`course_history.py`'s per-course records.

Two gaps this closes (found while auditing what the storyline pipeline can
surface, 2026-08-19): `teg_analysis/analysis/streaks.py` and
`teg_analysis/analysis/records.py` already compute all-time streak records
and score-count records (most Eagles/Birdies/Pars-or-better in a TEG, most
TBPs) for the webapp Records page, but nothing wired them into `events.py` /
`story_plan.assemble_bundle`, so an LLM writing a report had no beat to hang
"this ties the all-time record" on — it could only reach that fact by
inference from raw context, which the pipeline explicitly forbids.

`detect_streak_records(teg_num)` flags when a player's longest streak within
this TEG (Eagles, Birdies, Pars-or-better, TBPs, +2s-or-worse, Over-par) ties
or breaks the all-time record for that streak type. The "No X" streaks
(No Eagles, No Birdies, No +2s, No TBPs) are excluded — they are the inverse
of a positive/negative streak and rarely a compelling record in their own
right.

`detect_score_count_records(teg_num)` flags when a player's TEG-total count
of a scoring category (Eagles, Birdies-or-better, Pars-or-better, TBPs) ties
or breaks the all-time record for a single TEG.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

_INTERESTING_STREAK_TYPES = {
    "Eagles", "Birdies", "Pars or Better", "TBPs", "+2s or Worse", "Over Par",
}


def _proper(name: str) -> str:
    return " ".join(w.capitalize() for w in str(name).split())


def detect_streak_records(teg_num: int, df: Optional[pd.DataFrame] = None) -> list[dict]:
    """Detect all-time-record-tying/breaking streaks set during this TEG.

    Returns a list of beat-shaped dicts:
        {
            "type": "streak_record",
            "streak_type": str,
            "player": str,
            "value": int,
            "prior_record": int,
            "round": Optional[int],
            "location": str,
            "summary_fact": str,
        }
    """
    from teg_analysis.core.data_loader import load_all_data
    from teg_analysis.analysis.streaks import (
        build_streaks, prepare_record_streaks_data, get_player_window_streaks,
    )

    if df is None:
        df = load_all_data()

    selected_teg = f"TEG {teg_num}"
    teg_rows = df[df["TEGNum"] == teg_num]
    if teg_rows.empty:
        return []
    last_round = int(teg_rows["Round"].max())

    streaks_df = build_streaks(df)
    teg_streaks = get_player_window_streaks(df, streaks_df, teg=selected_teg, round_num=last_round)
    if teg_streaks.empty:
        return []

    record_lookup: dict[str, int] = {}
    for direction in ("good", "bad"):
        records = prepare_record_streaks_data(df, direction)
        for _, r in records.iterrows():
            record_lookup[r["Streak Type"]] = int(str(r["Record"]).rstrip("*"))

    events: list[dict] = []
    for _, row in teg_streaks.iterrows():
        stype = row["Streak Type"]
        if stype not in _INTERESTING_STREAK_TYPES:
            continue
        value = int(row["Max Streak"])
        record_value = record_lookup.get(stype)
        if not record_value or value == 0 or value < record_value:
            continue

        loc = row["Location"]
        round_num = None
        if isinstance(loc, str) and " R" in loc:
            try:
                round_num = int(loc.split(" R", 1)[1].split(" ", 1)[0])
            except (IndexError, ValueError):
                round_num = None

        verb = "ties" if value == record_value else "breaks"
        player = _proper(row["Player"])
        events.append({
            "type": "streak_record",
            "streak_type": stype,
            "player": player,
            "value": value,
            "prior_record": record_value,
            "round": round_num,
            "location": loc,
            "summary_fact": (
                f"{player}'s {value}-hole \"{stype}\" streak {verb} the "
                f"all-time TEG record ({record_value}), at {loc}"
            ),
        })
    return events


def detect_score_count_records(teg_num: int, df: Optional[pd.DataFrame] = None) -> list[dict]:
    """Detect all-time-record-tying/breaking scoring-category counts (most
    Eagles/Birdies-or-better/Pars-or-better, or most TBPs) for this TEG.

    Returns a list of beat-shaped dicts:
        {
            "type": "score_count_record",
            "score_type": str,
            "player": str,
            "count": int,
            "summary_fact": str,
        }
    """
    from teg_analysis.core.data_loader import load_all_data
    from teg_analysis.analysis.records import identify_score_count_records

    if df is None:
        df = load_all_data()

    selected_teg = f"TEG {teg_num}"
    result = identify_score_count_records(df, selected_teg)
    # identify_score_count_records reports player CODES ('Pl'), not names.
    code_to_name = df[["Pl", "Player"]].drop_duplicates().set_index("Pl")["Player"].to_dict()

    events: list[dict] = []
    for rec in result["best_score_counts"] + result["worst_score_counts"]:
        player = _proper(code_to_name.get(rec["player"], rec["player"]))
        label = "Eagle" if rec["score_type"] == "Eagles" and rec["count"] == 1 else rec["score_type"]
        events.append({
            "type": "score_count_record",
            "score_type": rec["score_type"],
            "player": player,
            "count": rec["count"],
            "summary_fact": (
                f"{player} recorded {rec['count']} {label} in "
                f"TEG {teg_num} — an all-time TEG record"
            ),
        })
    return events
