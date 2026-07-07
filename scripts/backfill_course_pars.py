#!/usr/bin/env python3
"""Backfill data/course_pars.csv (hole-level Par/SI) from history.

Joins all-scores.parquet to round_info.csv on TEGNum+Round to get Course, then
checks each Course+Hole for consistent Par/SI across every historical round
played there. Outcomes per (course, hole):

  - Clean: every round agrees -> written straight to course_pars.csv.
  - Majority: most rounds agree and a small number of rounds disagree on
    every hole (a strong signal of one mis-recorded round, not a genuine
    course re-rating) -> the majority value is written, and the
    disagreeing round(s) are reported so the underlying all-scores.parquet
    records can be reviewed separately (NOT auto-corrected here -- that's a
    bigger, separate decision).
  - No majority (a genuine tie): left out of course_pars.csv and reported --
    needs a human decision (see DATA_STORAGE_INGESTION_PLAN.md Phase 2).
  - Known variable routing (see KNOWN_VARIABLE_ROUTING below): the course is
    sometimes played with the front/back 9 swapped, so there is no single
    correct Par/SI-per-hole-number to backfill. Deliberately excluded, not
    "unresolved" -- do not try to reconcile these via majority vote or any
    other automatic method. Confirmed with Jon, not a data-entry error.

Run from the repo root:
    python scripts/backfill_course_pars.py
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ALL_SCORES = ROOT / "data" / "all-scores.parquet"
ROUND_INFO = ROOT / "data" / "round_info.csv"
OUTPUT = ROOT / "data" / "course_pars.csv"

# Courses confirmed (not guessed) to sometimes be played with the front/back 9
# swapped -- so a per-hole-number Par/SI conflict here is real variation, not
# an error, and must never be "resolved" to one canonical set. Confirmed by
# Jon, 2026-07-07, re: Praia D'El Rey specifically (see
# DATA_STORAGE_INGESTION_PLAN.md "Decisions needed for Jon" -> resolved).
KNOWN_VARIABLE_ROUTING = {
    "Praia D'El Rey": (
        "Sometimes played back-9-first. The apparent 18-hole Par/SI conflict "
        "(TEG 7 Round 1 vs every other round there) is real variation, not a "
        "data-entry error -- do not attempt to resolve it, and do not "
        "'correct' all-scores.parquet for that round."
    ),
}


def build_course_pars() -> tuple[pd.DataFrame, dict, dict]:
    """Return (clean_df, overrides, unresolved).

    overrides maps {course: {hole: {'used': (par, si), 'outliers': [(teg, round, par, si), ...]}}}
    for holes resolved by majority vote.
    unresolved maps {course: {hole: {'par': [...], 'si': [...]}}} for holes with
    no clear majority. Courses in KNOWN_VARIABLE_ROUTING are skipped entirely
    (never appear in clean_rows, overrides, or unresolved).
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
    merged = merged[~merged["Course"].isin(KNOWN_VARIABLE_ROUTING)]

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

    if KNOWN_VARIABLE_ROUTING:
        print(
            f"\n{len(KNOWN_VARIABLE_ROUTING)} course(s) deliberately excluded -- known to be "
            "played with variable routing, not a data error, do not attempt to resolve:"
        )
        for course, note in KNOWN_VARIABLE_ROUTING.items():
            print(f"\n  {course}: {note}")

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
