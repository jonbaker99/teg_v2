# Next Session: Phase 5 — Dead code audit

**Branch:** `cleanup-teg-analysis` (pushed to remote)
**Model:** Sonnet (single-file edits, removing dead code)

## What's done

- **Phase 1**: All streamlit imports removed from `teg_analysis/`
- **Phase 2**: aggregation.py split complete (2,931 → 1,012 lines)
- **Phase 3**: streaks.py refactored (1,152 → 423 lines)
- **Phase 4**: scoring.py, records.py, commentary.py cleaned up (-810 lines net):
  - `scoring.py`: 963 → 516 lines — deleted 11 UI/chart functions (all duplicated in streamlit/helpers/)
  - `records.py`: 655 → 479 lines — deleted course analysis section + format_record_value
  - `commentary.py`: 1155 → 1023 lines — removed section header, extracted shared streak helpers
  - Note: commentary.py target of ~600 was miscalibrated; all 5 public functions are externally called

## Phase 5 changes (Sonnet) — FOR OPUS REVIEW

Commit: `6bea02c` on branch `claude/cleanup-teg-analysis-Ncy3y`

### Files modified/deleted

| File | Before | After | Change |
|---|---|---|---|
| `teg_analysis/analysis/rankings.py` | 363 lines | 219 lines | -144 |
| `teg_analysis/analysis/performance.py` | 262 lines | 92 lines | -170 |
| `teg_analysis/analysis/leaderboards.py` | 80 lines | 13 lines | -67 |
| `teg_analysis/display/formatters.py` | 547 lines | 522 lines | -25 |
| `teg_analysis/display/html_tables.py` | 255 lines | DELETED | -255 |

### Functions removed

- `rankings.py`: `convert_pivot_scores_to_ranks`, `calculate_average_rank_from_ranked_df`
- `performance.py`: `prepare_performance_table`, `_select_personal`, `_select_top_n`, `_format_display`, `_SUMMARY_MEASURES`, `prepare_pb_summary_table`, `_format_when`
- `leaderboards.py`: `get_teg_leaderboard`, `get_round_leaderboard`
- `formatters.py`: `format_crosstab_columns`
- `html_tables.py` (entire file): `generate_ranking_table_html`, `dataframe_to_html_table`, `create_round_leaderboard_html`

### What was NOT changed
`aggregation.py`, `pipeline.py`, `history.py`, `bestball.py`, `tables.py`, `navigation.py` — all have active callers or need separate analysis (see PROJECT_PLAN.md Phase 6+).

### Uncertainties / things for Opus to verify
- `performance.py` still exports `get_measure_name_mappings`, `prepare_round_data_with_identifiers`, `get_performance_measure_titles`, `format_performance_value`, `prepare_worst_performance_dataframe`, `load_worst_performance_custom_css`, `create_worst_performance_section`, `get_filtered_teg_data` — confirm these all have callers
- `html_tables.py` imported `aggregate_data` from `aggregation.py`; confirm that import is now gone and nothing depended on `html_tables` being importable
- Tests pass (`pytest tests/test_independence.py tests/test_core_functions.py -v`) but are lightweight — Opus should do a grep sweep for any remaining references to deleted names

## What to do next

See `PROJECT_PLAN.md` for Phase 6+.
