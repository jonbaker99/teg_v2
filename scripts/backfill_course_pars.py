#!/usr/bin/env python3
"""Backfill data/course_pars.csv (hole-level Par/SI) from history.

Joins all-scores.parquet to round_info.csv on TEGNum+Round to get Course,
then checks each Course+Hole for consistent Par/SI across every historical
play. Clean (course, hole) pairs go into data/course_pars.csv. Courses with
conflicting historical values are left out and reported instead -- they need
a human decision (see DATA_STORAGE_INGESTION_PLAN.md Phase 2) before they
can be added.

Run from the repo root:
    python scripts/backfill_course_pars.py
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ALL_SCORES = ROOT / "data" / "all-scores.parquet"
ROUND_INFO = ROOT / "data" / "round_info.csv"
OUTPUT = ROOT / "data" / "course_pars.csv"


def build_course_pars() -> tuple[pd.DataFrame, dict]:
    """Return (clean_df, conflicts).

    conflicts maps {course: {hole: {'par': [...], 'si': [...]}}} for courses
    whose historical Par/SI aren't consistent and can't be backfilled
    automatically.
    """
    scores = pd.read_parquet(ALL_SCORES)
    round_info = pd.read_csv(ROUND_INFO)

    merged = scores.merge(
        round_info[["TEGNum", "Round", "Course"]], on=["TEGNum", "Round"], how="left"
    )
    if merged["Course"].isna().any():
        missing = merged[merged["Course"].isna()][["TEGNum", "Round"]].drop_duplicates()
        raise SystemExit(
            f"Rows with no matching round_info -- resolve before backfilling:\n{missing}"
        )

    grouped = (
        merged.groupby(["Course", "Hole"])
        .agg(
            par_values=("PAR", lambda s: sorted(set(s.dropna().astype(int)))),
            si_values=("SI", lambda s: sorted(set(s.dropna().astype(int)))),
        )
        .reset_index()
    )

    clean_rows = []
    conflicts: dict = {}
    for _, row in grouped.iterrows():
        if len(row["par_values"]) > 1 or len(row["si_values"]) > 1:
            conflicts.setdefault(row["Course"], {})[int(row["Hole"])] = {
                "par": row["par_values"],
                "si": row["si_values"],
            }
        else:
            clean_rows.append(
                {
                    "Course": row["Course"],
                    "Hole": int(row["Hole"]),
                    "Par": row["par_values"][0],
                    "SI": row["si_values"][0],
                }
            )

    clean_df = (
        pd.DataFrame(clean_rows, columns=["Course", "Hole", "Par", "SI"])
        .sort_values(["Course", "Hole"])
        .reset_index(drop=True)
    )
    return clean_df, conflicts


def main() -> None:
    clean_df, conflicts = build_course_pars()
    clean_df.to_csv(OUTPUT, index=False)
    print(f"Wrote {len(clean_df)} rows ({clean_df['Course'].nunique()} courses) to {OUTPUT}")

    if conflicts:
        print(
            f"\n{len(conflicts)} course(s) skipped -- historical Par/SI conflicts "
            "need manual resolution:"
        )
        for course, holes in conflicts.items():
            print(f"\n  {course}:")
            for hole, vals in sorted(holes.items()):
                print(f"    Hole {hole}: PAR={vals['par']} SI={vals['si']}")
        print(
            "\nThese courses are NOT in course_pars.csv yet. Resolve via "
            "DATA_STORAGE_INGESTION_PLAN.md Phase 2's decision, then add them "
            "via /admin/edit-data once course_pars is registered there."
        )


if __name__ == "__main__":
    main()
