"""Per-player per-course history for report bundle enrichment.

`build_player_course_history(teg_num)` returns, for each player in the current
TEG and each course they played, factual history relative to their prior visits
to that course: visit count, personal best, strokes vs last visit, whether
this TEG produced a new course PB. Surfaced in the bundle as
`player_course_history[player][course] = {...}`.

`detect_course_records(teg_num)` returns NEW course gross records (good or bad)
set during this TEG, restricted to courses with >= min_prior_visits prior
appearances across all TEGs. These should be wired into the bundle's beats
list with `mandatory=True` so the writer cannot skip them.

Both functions are parametric over `teg_num`: when TEG 19 data lands, they
produce TEG 19 history automatically. No hardcoding.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd


def _proper(name: str) -> str:
    """'Alex BAKER' -> 'Alex Baker'."""
    return " ".join(w.capitalize() for w in name.split())


def _round_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate hole-level rows to per (TEG, Round, Player, Course) totals."""
    return df.groupby(["TEGNum", "Round", "Player", "Course"], dropna=False).agg(
        Gross=("Sc", "sum"),
        GrossVP=("GrossVP", "sum"),
        Stableford=("Stableford", "sum"),
    ).reset_index()


def build_player_course_history(teg_num: int, df: Optional[pd.DataFrame] = None) -> dict:
    """Per-player per-course history relative to prior TEGs.

    Returns a dict keyed by proper-case player name; each value is a dict keyed
    by course name; each entry is a fact dict suitable for the bundle.

    For each (player, course) in this TEG:
        - `visit_count_through_this_teg`: total visits to this course including
          rounds in this TEG (1 = first ever)
        - `n_prior_visits`: rounds on this course strictly before this TEG
        - `prior_best_gross` / `prior_best_teg`: PB on this course before this TEG
        - `this_teg_best_gross` / `this_teg_best_round`: best round on this course
          in this TEG (lowest gross across the player's rounds on this course)
        - `strokes_vs_last_visit`: gross delta of this TEG's best vs the player's
          most recent prior visit (negative = better)
        - `is_course_pb_this_teg`: True if this TEG's best beats prior_best_gross
        - `summary_facts`: list of factual phrases the editor/writer can use
          verbatim as anchors — neutral, factual, no flourish
    """
    if df is None:
        from teg_analysis.core.data_loader import load_all_data
        df = load_all_data()

    rounds = _round_aggregates(df)
    current = rounds[rounds["TEGNum"] == teg_num]
    if current.empty:
        return {}

    out: dict = {}

    # Iterate over unique (player, course) pairs in the current TEG
    for (player, course), group in current.groupby(["Player", "Course"]):
        # Player's best round on this course IN this TEG
        best_row = group.loc[group["Gross"].idxmin()]
        this_teg_best_gross = int(best_row["Gross"])
        this_teg_best_round = int(best_row["Round"])

        # Player's prior visits to this course (across all prior TEGs)
        prior = rounds[
            (rounds["Player"] == player)
            & (rounds["Course"] == course)
            & (rounds["TEGNum"] < teg_num)
        ].sort_values(["TEGNum", "Round"])

        n_prior = len(prior)
        visit_count_through = n_prior + len(group)

        prior_best_gross: Optional[int] = None
        prior_best_teg: Optional[int] = None
        strokes_vs_last_visit: Optional[int] = None
        is_pb = False

        if n_prior > 0:
            best_prior_idx = prior["Gross"].idxmin()
            prior_best_gross = int(prior.loc[best_prior_idx, "Gross"])
            prior_best_teg = int(prior.loc[best_prior_idx, "TEGNum"])
            last_visit_gross = int(prior.iloc[-1]["Gross"])
            strokes_vs_last_visit = this_teg_best_gross - last_visit_gross
            is_pb = this_teg_best_gross < prior_best_gross

        facts: list[str] = []
        player_proper = _proper(player)

        if n_prior == 0:
            facts.append(f"{player_proper}'s first visit to {course}")
        else:
            # Visit ordinal — only foreground when the venue is well-established
            if n_prior >= 2:
                facts.append(
                    f"{player_proper}'s {_ordinal(n_prior + 1)} visit to {course}"
                )

            if prior_best_gross is not None:
                facts.append(
                    f"{player_proper}'s prior best at {course}: {prior_best_gross} gross "
                    f"(TEG {prior_best_teg})"
                )

            if is_pb:
                facts.append(
                    f"{player_proper}'s new personal best at {course} in R{this_teg_best_round}: "
                    f"{this_teg_best_gross} gross — improved by "
                    f"{prior_best_gross - this_teg_best_gross}"
                )

            if strokes_vs_last_visit is not None and abs(strokes_vs_last_visit) >= 5:
                # Only flag meaningful deltas (>= 5 shots)
                direction = "better" if strokes_vs_last_visit < 0 else "worse"
                facts.append(
                    f"{player_proper} was {abs(strokes_vs_last_visit)} shots {direction} "
                    f"than his last visit to {course}"
                )

        entry = {
            "course": course,
            "visit_count_through_this_teg": visit_count_through,
            "n_prior_visits": n_prior,
            "prior_best_gross": prior_best_gross,
            "prior_best_teg": prior_best_teg,
            "this_teg_best_gross": this_teg_best_gross,
            "this_teg_best_round": this_teg_best_round,
            "strokes_vs_last_visit": strokes_vs_last_visit,
            "is_course_pb_this_teg": is_pb,
            "summary_facts": facts,
        }

        out.setdefault(player_proper, {})[course] = entry

    return out


def detect_course_records(
    teg_num: int,
    df: Optional[pd.DataFrame] = None,
    min_prior_visits: int = 3,
) -> list[dict]:
    """Detect new gross course records (good or bad) set during this TEG.

    A new record only "counts" if the course has been played at least
    `min_prior_visits` times across all TEGs before this one — otherwise
    the sample is too small for a "record" to be meaningful.

    Returns a list of beat-shaped dicts the bundle assembler can merge
    into the events list with mandatory=True:
        {
            "type": "course_record_low" | "course_record_high",
            "player": str (proper case),
            "course": str,
            "round": int,
            "gross": int,
            "prior_record": int,
            "n_prior_visits": int,
            "summary_fact": str,
        }
    """
    if df is None:
        from teg_analysis.core.data_loader import load_all_data
        df = load_all_data()

    rounds = _round_aggregates(df)
    events: list[dict] = []

    for course, group in rounds.groupby("Course"):
        prior = group[group["TEGNum"] < teg_num]
        current = group[group["TEGNum"] == teg_num]
        if len(prior) < min_prior_visits or current.empty:
            continue

        prior_min = int(prior["Gross"].min())
        prior_max = int(prior["Gross"].max())

        # Emit ONE event per direction per course: the lowest gross in this TEG
        # (if it beats prior_min) and the highest (if it exceeds prior_max).
        # Intermediate rounds that "beat" the static prior record but are not
        # the final standing record are not separately notable.
        new_lows = current[current["Gross"] < prior_min]
        if not new_lows.empty:
            row = new_lows.loc[new_lows["Gross"].idxmin()]
            improvement = prior_min - int(row["Gross"])
            events.append({
                "type": "course_record_low",
                "player": _proper(row["Player"]),
                "course": course,
                "round": int(row["Round"]),
                "gross": int(row["Gross"]),
                "prior_record": prior_min,
                "improvement": improvement,
                "n_prior_visits": len(prior),
                "summary_fact": (
                    f"new {course} course record: {int(row['Gross'])} gross by "
                    f"{_proper(row['Player'])} in R{int(row['Round'])}, beating the "
                    f"prior record of {prior_min} (across {len(prior)} prior visits)"
                ),
            })

        new_highs = current[current["Gross"] > prior_max]
        if not new_highs.empty:
            row = new_highs.loc[new_highs["Gross"].idxmax()]
            events.append({
                "type": "course_record_high",
                "player": _proper(row["Player"]),
                "course": course,
                "round": int(row["Round"]),
                "gross": int(row["Gross"]),
                "prior_record": prior_max,
                "n_prior_visits": len(prior),
                "summary_fact": (
                    f"new {course} course-worst: {int(row['Gross'])} gross by "
                    f"{_proper(row['Player'])} in R{int(row['Round'])}, exceeding the "
                    f"prior worst of {prior_max} (across {len(prior)} prior visits)"
                ),
            })

    return events


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"
