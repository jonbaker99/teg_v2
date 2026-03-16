# Next Session: Finish aggregation.py Split

**Branch:** `cleanup-teg-analysis` (pushed to remote)
**Model:** Opus (this is multi-file refactor work)

## What's done

- 4 new files created with code extracted from aggregation.py:
  - `analysis/history.py` — winners, history tables, eagles, caching
  - `analysis/performance.py` — one `prepare_performance_table()` replacing 11 functions
  - `analysis/leaderboards.py` — TEG/round leaderboards
  - `analysis/bestball.py` — bestball/worstball
- aggregation.py still has ALL the old code (2,930 lines) — the new files are additions, not replacements yet

## What to do now

### 1. Gut aggregation.py (~15 min)

Delete everything from aggregation.py EXCEPT:
- Lines 1-14: imports and logger
- Lines 17-44: `get_teg_rounds`, `get_tegnum_rounds`
- Lines 130-214: `list_fields_by_aggregation_level`, `aggregate_data`
- Lines 217-290: cached accessors (`get_complete_teg_data`, `get_teg_data_inc_in_progress`, `get_round_data`, `get_9_data`, `get_Pl_data`)
- Lines 2697-2774: TEG status functions (`get_last_completed_teg_fast`, `get_current_in_progress_teg_fast`, `has_incomplete_teg_fast`)

The remaining ~1,750-2,414 block (round/TEG selection helpers + comeback analysis) needs a decision: keep in aggregation.py or create `analysis/latest.py`. Suggest keeping in aggregation for now to limit scope.

### 2. Update __init__.py

Add new module imports and re-exports:
```python
from . import history, performance, leaderboards, bestball
from .history import get_teg_winners
from .leaderboards import filter_data_by_teg
```

### 3. Update internal callers

- `pipeline.py` line 135: change `from teg_analysis.analysis.aggregation import prepare_bestball_data, calculate_bestball_scores, calculate_worstball_scores` → `from teg_analysis.analysis.bestball import ...`
- `examples/example_fastapi.py`: update `filter_data_by_teg` import
- `tests/test_core_functions.py`: status functions stay in aggregation, no change needed

### 4. Test

```bash
grep -r "import streamlit" teg_analysis/ --include="*.py"  # should be empty
python -c "from teg_analysis.analysis import history, performance, leaderboards, bestball"
pytest tests/ -v
```

### 5. Commit, then move to Phase 3 (streaks.py refactor)

## Full plan

See `PROJECT_PLAN.md` for Phases 3-7.
