#!/usr/bin/env python3
"""Backfill data/course_pars.csv (hole-level Par/SI) from history.

Joins all-scores.parquet to round_info.csv on TEGNum+Round to get Course, then
checks each Course+Hole for consistent Par/SI across every historical round
played there. Three outcomes per (course, hole):

  - Clean: every round agrees -> written straight to course_pars.csv.
  - Majority: most rounds agree and a small number of rounds disagree on
    every hole (a strong signal of one mis-recorded round, not a genuine
    course re-rating) -> the majority value is written, and the
    disagreeing round(s) are reported so the underlying all-scores.parquet
    records can be reviewed separately (NOT auto-corrected here -- that's a
    bigger, separate decision).
  - No majority (a genuine tie): left out of course_pars.csv and reported --
    needs a human decision (see DATA_STORAGE_INGESTION_PLAN.md Phase 2).

Run from the repo root:
    python scripts/backfill_course_pars.py
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ALL_SCORES = ROOT / "data" / "all-scores.parquet"
ROUND_INFO = ROOT / "data" / "round_info.csv"
OUTPUT = ROOT / "data" / "course_pars.csv"


def build_course_pars() -> tuple[pd.DataFrame, dict, dict]:
    """Return (clean_df, overrides, unresolved).

    overrides maps {course: {hole: {'used': (par, si), 'outliers': [(teg, round, par, si), ...]}}}
    for holes resolved by majority vote.
    unresolved maps {course: {hole: {'par': [...], 'si': [...]}}} for holes with
    no clear majority.
    """
    scores = pd.read_parquet(ALL_SCORES)
    round_info = pd.read_csv(ROUND_INFO)

    # One row per TEG+Round+Hole (Par/SI don't vary by player within a round).
    rounds_holes = scores[["TEGNum", "Round", "Hole", "PAR", "SI"]].drop_duplicates()
    merged = rounds_holes.merge(
        round_info[["TEGNum", "Round", "Course"]], on=["TEGNum", "Round"], how="left"
    )
    if merged["Course"].isna().any():
        missing = merged[merged["Course"].isna()][["TEGNum", "Round"]].drop_duplicates()
        raise SystemExit(
            f"Rows with no matching round_info -- resolve before backfilling:\n{missing}"
        )

    clean_rows = []
    overrides: dict = {}
    unresolved: dict = {}

    for (course, hole), grp in merged.groupby(["Course", "Hole"]):
        counts = grp.groupby(["PAR", "SI"]).size().sort_values(ascending=False)
        if len(counts) == 1:
            par, si = counts.index[0]
            clean_rows.append({"Course": course, "Hole": int(hole), "Par": int(par), "SI": int(si)})
            continue

        top_n = int(counts.iloc[0])
        rest_n = int(counts.iloc[1:].sum())
        if top_n > rest_n:
            par, si = counts.index[0]
            clean_rows.append({"Course": course, "Hole": int(hole), "Par": int(par), "SI": int(si)})
            outlier_rows = grp[(grp["PAR"] != par) | (grp["SI"] != si)]
            outliers = [
                (int(r.TEGNum), int(r.Round), int(r.PAR), int(r.SI))
                for r in outlier_rows.itertuples()
            ]
            overrides.setdefault(course, {})[int(hole)] = {"used": (int(par), int(si)), "outliers": outliers}
        else:
            unresolved.setdefault(course, {})[int(hole)] = {
                "par": sorted(set(int(p) for p, _ in counts.index)),
                "si": sorted(set(int(s) for _, s in counts.index)),
            }

    clean_df = (
        pd.DataFrame(clean_rows, columns=["Course", "Hole", "Par", "SI"])
        .sort_values(["Course", "Hole"])
        .reset_index(drop=True)
    )
    return clean_df, overrides, unresolved


def main() -> None:
    clean_df, overrides, unresolved = build_course_pars()
    clean_df.to_csv(OUTPUT, index=False)
    print(f"Wrote {len(clean_df)} rows ({clean_df['Course'].nunique()} courses) to {OUTPUT}")

    if overrides:
        print(
            f"\n{len(overrides)} course(s) resolved by majority vote -- a small number of "
            "rounds disagreed with every other round and were treated as the likely error:"
        )
        outlier_round_tally: dict = {}
        for course, holes in overrides.items():
            print(f"\n  {course}:")
            for hole, info in sorted(holes.items()):
                par, si = info["used"]
                print(f"    Hole {hole}: using PAR={par} SI={si} (majority)")
            for hole, info in sorted(holes.items()):
                for teg, rnd, par, si in info["outliers"]:
                    outlier_round_tally[(teg, rnd)] = outlier_round_tally.get((teg, rnd), 0) + 1
        print("\n  Rounds that disagreed with the majority (worth a separate look at the raw")
        print("  all-scores.parquet records for these rounds -- NOT changed by this script):")
        for (teg, rnd), n in sorted(outlier_round_tally.items(), key=lambda x: -x[1]):
            print(f"    TEG {teg} Round {rnd}: disagreed on {n} hole(s)")

    if unresolved:
        print(f"\n{len(unresolved)} course(s) have no clear majority -- need a manual decision:")
        for course, holes in unresolved.items():
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
