# Next Session Plan

**Working branch:** `cleanup-teg-analysis` — all cleanup work happens here. Do NOT merge to `main` until the full cleanup is complete and reviewed.

## What's done (Phases 1–5)

- **Phase 1**: All streamlit imports removed from `teg_analysis/`
- **Phase 2**: aggregation.py split complete (2,931 → 1,012 lines)
- **Phase 3**: streaks.py refactored (1,152 → 423 lines)
- **Phase 4**: scoring.py, records.py, commentary.py cleaned up (-810 lines net)
- **Phase 5**: Dead code audit (-667 lines) — Opus reviewed and approved
  - Deleted: `convert_pivot_scores_to_ranks`, `calculate_average_rank_from_ranked_df`, `prepare_performance_table` + helpers, `prepare_pb_summary_table` + helpers, `get_teg_leaderboard`, `get_round_leaderboard`, `format_crosstab_columns`, entire `html_tables.py`

### Opus review note from Phase 5
Some retained functions in `performance.py` (`get_performance_measure_titles`, `load_worst_performance_custom_css`, `create_worst_performance_section`, `get_filtered_teg_data`) have no external callers yet — they're migration targets for when streamlit switches to `teg_analysis/`.

## What to do next

**Phase 6 DONE** — Documentation updated to reflect cleanup phases 1-5.

**Phase 7 (next)** — Opus review of all changes. See `PROJECT_PLAN.md` for review checklist.
