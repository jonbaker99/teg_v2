#!/usr/bin/env python3
"""Backfill data/course_pars.csv (hole-level Par/SI) from history.

For each course, uses the *most recent* round played there (by Date) as the
Par/SI for every hole. Recency, not majority vote, is the source of truth:
a course can be legitimately re-rated over time (Boavista's SI once was),
so "what actually happened most recently" is a better default than "what
most historical rounds agree on" -- and it naturally resolves courses with
too little history to have a majority (Estoril: only 2 rounds ever).

This file is a *default*, not a guarantee -- it's what pre-round setup
(the round_pars.csv workflow, see round_setup.py / DATA_STORAGE_INGESTION_PLAN.md
Phase "pre-round setup") prefills from before an admin confirms/edits the
actual Par/SI for an upcoming round. Courses in KNOWN_VARIABLE_ROUTING still
get a value here (the most recent round's), but are flagged so the pre-round
setup UI can prompt a human to double-check rather than silently trust it.

Run from the repo root:
    python scripts/backfill_course_pars.py
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from teg_analysis.constants import KNOWN_VARIABLE_ROUTING  # noqa: E402

ALL_SCORES = ROOT / "data" / "all-scores.parquet"
ROUND_INFO = ROOT / "data" / "round_info.csv"
OUTPUT = ROOT / "data" / "course_pars.csv"


def build_course_pars() -> tuple[pd.DataFrame, dict]:
    """Return (course_pars_df, sources).

    sources maps {course: (teg_num, round_num, date)} recording which round's
    Par/SI was used for each course, for transparency/debugging.
    """
    scores = pd.read_parquet(ALL_SCORES)
    round_info = pd.read_csv(ROUND_INFO)

    # One row per TEG+Round+Hole (Par/SI don't vary by player within a round).
    rounds_holes = scores[["TEGNum", "Round", "Hole", "PAR", "SI"]].drop_duplicates()
    merged = rounds_holes.merge(
        round_info[["TEGNum", "Round", "Course", "Date"]], on=["TEGNum", "Round"], how="left"
    )
    if merged["Course"].isna().any():
        missing = merged[merged["Course"].isna()][["TEGNum", "Round"]].drop_duplicates()
        raise SystemExit(
            f"Rows with no matching round_info -- resolve before backfilling:\n{missing}"
        )
    merged["Date"] = pd.to_datetime(merged["Date"], dayfirst=True)

    course_pars_rows = []
    sources: dict = {}

    for course, grp in merged.groupby("Course"):
        latest_date = grp["Date"].max()
        # Tiebreak on TEGNum/Round in the rare case two rounds share a Date.
        latest = grp[grp["Date"] == latest_date].sort_values(["TEGNum", "Round"])
        teg_num, round_num = int(latest.iloc[-1]["TEGNum"]), int(latest.iloc[-1]["Round"])
        latest_round = grp[(grp["TEGNum"] == teg_num) & (grp["Round"] == round_num)]

        for _, row in latest_round.sort_values("Hole").iterrows():
            course_pars_rows.append(
                {"Course": course, "Hole": int(row["Hole"]), "Par": int(row["PAR"]), "SI": int(row["SI"])}
            )
        sources[course] = (teg_num, round_num, latest_date.date().isoformat())

    course_pars_df = (
        pd.DataFrame(course_pars_rows, columns=["Course", "Hole", "Par", "SI"])
        .sort_values(["Course", "Hole"])
        .reset_index(drop=True)
    )
    return course_pars_df, sources


def main() -> None:
    course_pars_df, sources = build_course_pars()
    course_pars_df.to_csv(OUTPUT, index=False)
    print(f"Wrote {len(course_pars_df)} rows ({course_pars_df['Course'].nunique()} courses) to {OUTPUT}")

    print("\nSource round used per course (most recent by Date):")
    for course, (teg, rnd, date) in sorted(sources.items()):
        flag = "  <-- variable routing, double-check" if course in KNOWN_VARIABLE_ROUTING else ""
        print(f"  {course}: TEG {teg} Round {rnd} ({date}){flag}")

    if KNOWN_VARIABLE_ROUTING:
        print(f"\n{len(KNOWN_VARIABLE_ROUTING)} course(s) flagged for a manual double-check before use:")
        for course, note in KNOWN_VARIABLE_ROUTING.items():
            print(f"\n  {course}: {note}")


if __name__ == "__main__":
    main()
