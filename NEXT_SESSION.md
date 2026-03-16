# Next Session Plan

**Working branch:** `cleanup-teg-analysis` — all cleanup work happens here. Do NOT merge to `main` until the full cleanup is complete and reviewed.

## What's done (Phases 1–7)

- **Phase 1**: All streamlit imports removed from `teg_analysis/`
- **Phase 2**: aggregation.py split complete (2,931 → 1,012 lines)
- **Phase 3**: streaks.py refactored (1,152 → 423 lines)
- **Phase 4**: scoring.py, records.py, commentary.py cleaned up (-810 lines net)
- **Phase 5**: Dead code audit (-667 lines) — Opus reviewed and approved
- **Phase 6**: Documentation updated to reflect cleanup phases 1-5
- **Phase 7**: Opus review complete — all checks passed, minor fixes applied

### Phase 7 review summary
- No streamlit imports in `teg_analysis/` ✅
- All deleted functions have zero remaining callers ✅
- Backward-compatible aliases in streaks.py verified ✅
- `__init__.py` exports verified ✅
- No circular dependencies ✅
- Minor fixes: removed unused `import numpy` from streaks.py, updated PROJECT_PLAN.md status

### Opus review note from Phase 5
Some retained functions in `performance.py` (`get_performance_measure_titles`, `load_worst_performance_custom_css`, `create_worst_performance_section`, `get_filtered_teg_data`) have no external callers yet — they're migration targets for when streamlit switches to `teg_analysis/`.

## What to do next

**Ready to merge to `main`.** The cleanup branch is reviewed and approved. Next steps:

1. Merge `cleanup-teg-analysis` → `main`
2. Plan next phase of work (API, streamlit migration, or new features)
