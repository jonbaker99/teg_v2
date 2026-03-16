"""API Coverage Test — verifies teg_analysis can generate every major data table.

Run from the project root:
    python examples/api_coverage_test.py

Each check prints PASS/FAIL plus basic stats (row/col count).
A summary at the end shows overall coverage.
"""

import sys
import traceback
from pathlib import Path

# Allow running from the examples/ directory or the project root
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── helpers ──────────────────────────────────────────────────────────────────

results = []

def check(label, fn, *, min_rows=1):
    """Run fn(), report PASS/FAIL.  Returns the result on success, None on failure."""
    try:
        result = fn()
        if hasattr(result, '__len__'):
            n = len(result)
            shape = getattr(result, 'shape', None)
            detail = f"shape={shape}" if shape is not None else f"len={n}"
        elif isinstance(result, tuple):
            detail = f"tuple len={len(result)}"
            n = 1
        elif result is None:
            detail = "None"
            n = 0
        else:
            detail = str(result)[:60]
            n = 1

        if n < min_rows:
            print(f"  WARN  {label}  ({detail}, expected >= {min_rows} rows)")
            results.append(("WARN", label))
        else:
            print(f"  PASS  {label}  ({detail})")
            results.append(("PASS", label))
        return result
    except Exception as e:
        print(f"  FAIL  {label}")
        print(f"        {type(e).__name__}: {e}")
        results.append(("FAIL", label))
        return None


def section(title):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


# ── imports ───────────────────────────────────────────────────────────────────

section("Imports")

try:
    from teg_analysis.core.data_loader import load_all_data, get_player_name
    from teg_analysis.core.metadata import get_teg_metadata, load_course_info
    from teg_analysis.constants import ROUND_INFO_CSV
    from teg_analysis.io.file_operations import read_file
    from teg_analysis.analysis.aggregation import (
        aggregate_data,
        get_complete_teg_data,
        get_teg_data_inc_in_progress,
        get_round_data,
        get_9_data,
        get_Pl_data,
        get_current_in_progress_teg_fast,
        get_last_completed_teg_fast,
        has_incomplete_teg_fast,
        calculate_final_round_differentials,
        calculate_biggest_leads_lost_after_r3,
        calculate_biggest_leads_lost_in_r4,
        calculate_biggest_comebacks,
        get_latest_round_defaults,
        prepare_scorecard_selection_options,
    )
    from teg_analysis.analysis.rankings import (
        add_ranks,
        get_best,
        get_worst,
        get_ranked_teg_data,
        get_ranked_round_data,
        get_ranked_frontback_data,
    )
    from teg_analysis.analysis.history import (
        get_teg_winners,
        prepare_complete_history_table,
        prepare_complete_history_table_fast,
        load_cached_winners,
        calculate_trophy_jacket_doubles,
        get_eagles_data,
        get_holes_in_one_data,
    )
    from teg_analysis.analysis.records import (
        identify_aggregate_records_and_pbs,
        identify_9hole_records_and_pbs,
        identify_streak_records,
        identify_all_time_worsts,
        identify_score_count_records,
    )
    from teg_analysis.analysis.streaks import (
        build_streaks,
        prepare_good_streaks_data,
        prepare_bad_streaks_data,
        prepare_current_good_streaks_data,
        prepare_current_bad_streaks_data,
        prepare_record_best_streaks_data,
        prepare_record_worst_streaks_data,
    )
    from teg_analysis.analysis.bestball import (
        prepare_bestball_data,
        calculate_bestball_scores,
        calculate_worstball_scores,
    )
    from teg_analysis.analysis.performance import (
        get_filtered_teg_data,
        prepare_round_data_with_identifiers,
    )
    from teg_analysis.display.tables import (
        score_type_stats,
        max_scoretype_per_round,
        max_scoretype_per_teg,
        datawrapper_table,
    )
    from teg_analysis.analysis.leaderboards import filter_data_by_teg
    from teg_analysis.analysis.scoring import get_net_competition_measure
    print("  PASS  All imports")
    results.append(("PASS", "All imports"))
except Exception as e:
    print(f"  FAIL  Imports — {e}")
    traceback.print_exc()
    sys.exit(1)


# ── 1. Core data loading ──────────────────────────────────────────────────────

section("1. Core Data Loading")

all_data = check("load_all_data()", lambda: load_all_data(exclude_teg_50=True))
course_info = check("load_course_info()", load_course_info)
check("get_teg_metadata(teg=2)", lambda: get_teg_metadata(2))
check("get_player_name('JB')", lambda: get_player_name('JB'), min_rows=0)


# ── 2. TEG status ─────────────────────────────────────────────────────────────

section("2. TEG Status")

last_teg_result = check("get_last_completed_teg_fast()", get_last_completed_teg_fast)
current_teg_result = check("get_current_in_progress_teg_fast()", get_current_in_progress_teg_fast)
check("has_incomplete_teg_fast()", has_incomplete_teg_fast, min_rows=0)

last_teg = last_teg_result[0] if last_teg_result else None
last_round = last_teg_result[1] if last_teg_result else 4


# ── 3. History / Winners ──────────────────────────────────────────────────────

section("3. History / Winners")

if all_data is not None:
    winners = check("get_teg_winners(df)", lambda: get_teg_winners(all_data))
    if winners is not None:
        check("prepare_complete_history_table(winners)", lambda: prepare_complete_history_table(winners))
        check("calculate_trophy_jacket_doubles(winners)", lambda: calculate_trophy_jacket_doubles(winners), min_rows=0)
    cached_df, _ = load_cached_winners()
    check("prepare_complete_history_table_fast(cached_df)", lambda: prepare_complete_history_table_fast(cached_df))
    check("get_eagles_data(df)", lambda: get_eagles_data(all_data), min_rows=0)
    check("get_holes_in_one_data(df)", lambda: get_holes_in_one_data(all_data), min_rows=0)


# ── 4. Aggregation ────────────────────────────────────────────────────────────

section("4. Aggregation")

teg_data = check("get_complete_teg_data()", get_complete_teg_data)
teg_data_inc = check("get_teg_data_inc_in_progress()", get_teg_data_inc_in_progress)
round_data = check("get_round_data()", get_round_data)
nine_data = check("get_9_data()", get_9_data)
player_data = check("get_Pl_data()", get_Pl_data)

if all_data is not None:
    check("aggregate_data(df, 'TEG')", lambda: aggregate_data(all_data, 'TEG'))
    check("aggregate_data(df, 'Round')", lambda: aggregate_data(all_data, 'Round'))
    check("aggregate_data(df, 'Player')", lambda: aggregate_data(all_data, 'Player'))
    check("filter_data_by_teg(df, teg=2)", lambda: filter_data_by_teg(all_data, 2))


# ── 5. Rankings & Performance ─────────────────────────────────────────────────

section("5. Rankings & Performance")

ranked_teg = check("get_ranked_teg_data()", get_ranked_teg_data)
ranked_round = check("get_ranked_round_data()", get_ranked_round_data)
ranked_fb = check("get_ranked_frontback_data()", get_ranked_frontback_data)

if teg_data is not None:
    check("get_best(ranked_teg, 'GrossVP', top_n=10)", lambda: get_best(ranked_teg, 'GrossVP', top_n=10))
    check("get_worst(ranked_teg, 'GrossVP', top_n=10)", lambda: get_worst(ranked_teg, 'GrossVP', top_n=10))
    check("add_ranks(teg_data)", lambda: add_ranks(teg_data.copy()))

check("get_filtered_teg_data()", get_filtered_teg_data)

if ranked_round is not None:
    check("prepare_round_data_with_identifiers(ranked_round)", lambda: prepare_round_data_with_identifiers(ranked_round))
    check("get_latest_round_defaults(round_data)", lambda: get_latest_round_defaults(ranked_round), min_rows=0)

if all_data is not None:
    check("prepare_scorecard_selection_options(df)", lambda: prepare_scorecard_selection_options(all_data), min_rows=0)


# ── 6. Records ────────────────────────────────────────────────────────────────

section("6. Records")

if ranked_teg is not None and last_teg is not None:
    last_teg_str = f"TEG {last_teg}"
    check(
        "identify_aggregate_records_and_pbs(teg_data, last_teg)",
        lambda: identify_aggregate_records_and_pbs(ranked_teg, last_teg_str),
        min_rows=0,
    )
    check(
        "identify_all_time_worsts(teg_data, last_teg)",
        lambda: identify_all_time_worsts(ranked_teg, last_teg_str),
        min_rows=0,
    )

if ranked_round is not None and last_teg is not None:
    check(
        "identify_aggregate_records_and_pbs(round_data, last_teg, last_round)",
        lambda: identify_aggregate_records_and_pbs(ranked_round, last_teg_str, last_round),
        min_rows=0,
    )

if nine_data is not None and last_teg is not None:
    check(
        "identify_9hole_records_and_pbs(last_teg, last_round, nine_data)",
        lambda: identify_9hole_records_and_pbs(last_teg_str, last_round, nine_data),
        min_rows=0,
    )

if all_data is not None and last_teg is not None:
    check(
        "identify_score_count_records(all_data, last_teg)",
        lambda: identify_score_count_records(all_data, last_teg_str),
        min_rows=0,
    )


# ── 7. Streaks ────────────────────────────────────────────────────────────────

section("7. Streaks")

if all_data is not None:
    streaks_df = check("build_streaks(df)", lambda: build_streaks(all_data))
    check("prepare_good_streaks_data(df)", lambda: prepare_good_streaks_data(all_data))
    check("prepare_bad_streaks_data(df)", lambda: prepare_bad_streaks_data(all_data))
    check("prepare_current_good_streaks_data(df)", lambda: prepare_current_good_streaks_data(all_data))
    check("prepare_current_bad_streaks_data(df)", lambda: prepare_current_bad_streaks_data(all_data))
    check("prepare_record_best_streaks_data(df)", lambda: prepare_record_best_streaks_data(all_data))
    check("prepare_record_worst_streaks_data(df)", lambda: prepare_record_worst_streaks_data(all_data))

    if streaks_df is not None and last_teg is not None:
        check(
            "identify_streak_records(all_data, streaks_df, last_teg)",
            lambda: identify_streak_records(all_data, streaks_df, last_teg_str),
            min_rows=0,
        )


# ── 8. Score types ────────────────────────────────────────────────────────────

section("8. Score Types (Eagles / Birdies / Pars / TBPs)")

check("score_type_stats()", score_type_stats)
check("max_scoretype_per_round()", max_scoretype_per_round)
check("max_scoretype_per_teg()", max_scoretype_per_teg)


# ── 9. Bestball ───────────────────────────────────────────────────────────────

section("9. Bestball / Worstball")

if all_data is not None:
    bestball_data = check("prepare_bestball_data(df)", lambda: prepare_bestball_data(all_data))
    if bestball_data is not None and len(bestball_data) > 0:
        check("calculate_bestball_scores(bestball_data)", lambda: calculate_bestball_scores(bestball_data))
        check("calculate_worstball_scores(bestball_data)", lambda: calculate_worstball_scores(bestball_data))


# ── 10. Final round / comebacks ───────────────────────────────────────────────

section("10. Final Round Drama / Comebacks")

if all_data is not None:
    round_info = read_file(ROUND_INFO_CSV)
    check("calculate_final_round_differentials(df, round_info)", lambda: calculate_final_round_differentials(all_data, round_info), min_rows=0)
    check("calculate_biggest_leads_lost_after_r3(df, round_info)", lambda: calculate_biggest_leads_lost_after_r3(all_data, round_info), min_rows=0)
    check("calculate_biggest_leads_lost_in_r4(df, round_info)", lambda: calculate_biggest_leads_lost_in_r4(all_data, round_info), min_rows=0)
    check("calculate_biggest_comebacks(df, round_info)", lambda: calculate_biggest_comebacks(all_data, round_info), min_rows=0)


# ── 11. Net competition measure ───────────────────────────────────────────────

section("11. Scoring Utilities")

check("get_net_competition_measure(1) == 'NetVP'",
      lambda: "NetVP" if get_net_competition_measure(1) == 'NetVP' else (_ for _ in ()).throw(AssertionError("expected NetVP")),
      min_rows=0)
check("get_net_competition_measure(8) == 'Stableford'",
      lambda: "Stableford" if get_net_competition_measure(8) == 'Stableford' else (_ for _ in ()).throw(AssertionError("expected Stableford")),
      min_rows=0)


# ── 12. Display helpers ───────────────────────────────────────────────────────

section("12. Display Helpers")

if teg_data is not None:
    check("datawrapper_table(df)", lambda: datawrapper_table(teg_data.head(5), return_html=True), min_rows=0)


# ── Summary ───────────────────────────────────────────────────────────────────

print(f"\n{'═' * 60}")
print("  SUMMARY")
print(f"{'═' * 60}")

by_status = {"PASS": [], "WARN": [], "FAIL": []}
for status, label in results:
    by_status[status].append(label)

total = len(results)
print(f"  PASS : {len(by_status['PASS'])}/{total}")
if by_status['WARN']:
    print(f"  WARN : {len(by_status['WARN'])}/{total}  (empty results — may be expected)")
if by_status['FAIL']:
    print(f"  FAIL : {len(by_status['FAIL'])}/{total}")
    print()
    for label in by_status['FAIL']:
        print(f"    ✗  {label}")

print()
if not by_status['FAIL']:
    print("  All checks passed.")
else:
    print("  Some checks FAILED — see above for details.")
    sys.exit(1)
