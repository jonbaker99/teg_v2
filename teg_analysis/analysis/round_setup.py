"""Pre-round setup: confirming a specific round's Par/SI before anyone plays it.

``course_pars.csv`` holds a *default* Par/SI per course (the most recently
played round there — see ``scripts/backfill_course_pars.py``). This module
manages ``round_pars.csv``, the *confirmed* Par/SI for one specific TEG+Round,
set up by an admin ahead of play.

Round entry (whoever is scoring, on a phone) reads Par/SI from round_pars —
it's shown on the entry screen like it would be on a paper scorecard, but
never edited there. Editing only happens here, in pre-round setup, so a
player is never responsible for course/Par/SI data.

    round_info.csv (TEG+Round -> Course, Date)
        -> get_rounds_status()       list every round + whether it's set up
        -> get_round_setup_form()    build the 18-hole form (existing
                                      round_pars, else course_pars default,
                                      else blank), flagging known-variable
                                      routing courses
        -> save_round_setup()        upsert the confirmed 18 holes
"""

import pandas as pd

from teg_analysis.constants import (
    ROUND_INFO_CSV,
    COURSE_PARS_CSV,
    ROUND_PARS_CSV,
    KNOWN_VARIABLE_ROUTING,
)

_ROUND_PARS_COLUMNS = ["TEGNum", "Round", "Hole", "Par", "SI"]


def _read_round_pars() -> pd.DataFrame:
    from teg_analysis.io import read_file

    try:
        return read_file(ROUND_PARS_CSV)
    except FileNotFoundError:
        return pd.DataFrame(columns=_ROUND_PARS_COLUMNS)


def get_rounds_status() -> list[dict]:
    """Upcoming TEG+Rounds that need (or have) pre-round setup.

    Scoped to rounds with metadata in round_info.csv but **no scores yet in
    all-scores.parquet** — i.e. not-yet-played rounds. Once a round is
    actually played, its real Par/SI is already locked into all-scores.parquet
    directly, so it has nothing left to "set up"; only the historical
    ``ALL_SCORES_PARQUET`` reads for those rounds. Cross-referencing here
    keeps this page short and actionable instead of listing 18 TEGs of
    already-played history.

    Returns rows newest-first: ``{teg_num, round_num, course, date, is_set_up}``.
    """
    from teg_analysis.io import read_file
    from teg_analysis.constants import ALL_SCORES_PARQUET

    round_info = read_file(ROUND_INFO_CSV)
    round_pars = _read_round_pars()
    all_scores = read_file(ALL_SCORES_PARQUET)

    played_keys = set(
        zip(all_scores["TEGNum"].astype(int), all_scores["Round"].astype(int))
    )
    set_up_keys = set()
    if not round_pars.empty:
        set_up_keys = set(
            zip(round_pars["TEGNum"].astype(int), round_pars["Round"].astype(int))
        )

    rows = []
    for _, r in round_info.sort_values(
        ["TEGNum", "Round"], ascending=[False, False]
    ).iterrows():
        teg_num, round_num = int(r["TEGNum"]), int(r["Round"])
        if (teg_num, round_num) in played_keys:
            continue  # already played -- nothing to set up
        rows.append(
            {
                "teg_num": teg_num,
                "round_num": round_num,
                "course": r["Course"],
                "date": r["Date"],
                "is_set_up": (teg_num, round_num) in set_up_keys,
            }
        )
    return rows


def get_round_setup_form(teg_num: int, round_num: int) -> dict:
    """Build the 18-hole Par/SI form for a TEG+Round.

    Prefers, in order: an existing round_pars.csv entry (already confirmed),
    then the course_pars.csv default for that round's course, then blank.

    Returns ``{teg_num, round_num, course, source, flagged, flag_note, holes}``
    where ``source`` is one of ``'confirmed' | 'course_default' | 'blank'`` and
    ``holes`` is a list of ``{hole, par, si}`` dicts, holes 1-18.
    """
    from teg_analysis.io import read_file

    round_info = read_file(ROUND_INFO_CSV)
    match = round_info[
        (round_info["TEGNum"] == teg_num) & (round_info["Round"] == round_num)
    ]
    if match.empty:
        raise ValueError(f"TEG {teg_num} Round {round_num} not found in round_info.csv")
    course = match.iloc[0]["Course"]

    round_pars = _read_round_pars()
    existing = round_pars[
        (round_pars["TEGNum"] == teg_num) & (round_pars["Round"] == round_num)
    ]
    if not existing.empty:
        holes = [
            {"hole": int(r["Hole"]), "par": int(r["Par"]), "si": int(r["SI"])}
            for _, r in existing.sort_values("Hole").iterrows()
        ]
        source = "confirmed"
    else:
        course_pars = read_file(COURSE_PARS_CSV)
        course_rows = course_pars[course_pars["Course"] == course].sort_values("Hole")
        if not course_rows.empty:
            holes = [
                {"hole": int(r["Hole"]), "par": int(r["Par"]), "si": int(r["SI"])}
                for _, r in course_rows.iterrows()
            ]
            source = "course_default"
        else:
            holes = [{"hole": h, "par": "", "si": ""} for h in range(1, 19)]
            source = "blank"

    return {
        "teg_num": teg_num,
        "round_num": round_num,
        "course": course,
        "source": source,
        "flagged": course in KNOWN_VARIABLE_ROUTING,
        "flag_note": KNOWN_VARIABLE_ROUTING.get(course),
        "holes": holes,
    }


def save_round_setup(teg_num: int, round_num: int, holes: list[dict]) -> dict:
    """Upsert the confirmed 18-hole Par/SI for a TEG+Round into round_pars.csv.

    Args:
        teg_num, round_num: which round.
        holes: list of ``{hole, par, si}`` dicts (or matching keys 'Hole'/'Par'/'SI').

    Returns:
        ``{teg_num, round_num, holes_saved}``.
    """
    from teg_analysis.io import write_file

    round_pars = _read_round_pars()
    round_pars = round_pars[
        ~((round_pars["TEGNum"] == teg_num) & (round_pars["Round"] == round_num))
    ]

    new_rows = pd.DataFrame(
        [
            {
                "TEGNum": teg_num,
                "Round": round_num,
                "Hole": int(h.get("hole", h.get("Hole"))),
                "Par": int(h.get("par", h.get("Par"))),
                "SI": int(h.get("si", h.get("SI"))),
            }
            for h in holes
        ]
    )
    round_pars = pd.concat([round_pars, new_rows], ignore_index=True)
    for col in ("TEGNum", "Round", "Hole", "Par", "SI"):
        round_pars[col] = round_pars[col].astype(int)
    round_pars = round_pars.sort_values(["TEGNum", "Round", "Hole"]).reset_index(drop=True)

    write_file(
        ROUND_PARS_CSV, round_pars, f"Set up Par/SI for TEG {teg_num} Round {round_num}"
    )
    return {"teg_num": teg_num, "round_num": round_num, "holes_saved": len(new_rows)}
