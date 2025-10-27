# Prompt for Starting Phase 5 Wave 2

Copy and paste this into a new Claude Code conversation:

---

I'm continuing Phase 5 of the TEG analysis system refactor. **Wave 1 is complete** and I need to execute **Wave 2: Consolidation**.

## Context

**Project:** TEG golf tournament analysis system (Python/Streamlit)
**Location:** `c:\Users\jonba\Documents\Projects - not on onedrive\teg_v2`
**Branch:** refactor
**Phase 5 Goal:** Make teg_analysis package UI-independent (works with any framework)

## Wave 1 Completion Status ✅

**Accomplished:**
- teg_analysis package now imports without Streamlit ✅
- 5 analysis files cleaned of UI dependencies
- 2 new modules created:
  - `teg_analysis/core/metadata.py` (3 functions)
  - `teg_analysis/display/navigation.py` (4 functions)
- 9 functions migrated from streamlit/utils.py to teg_analysis
- All validation tests pass
- 2 commits created and pushed

**Current Validation:**
```bash
python -c "import teg_analysis"  # ✅ WORKS
grep -c "^def " streamlit/utils.py  # Returns: 100
```

**Key Pattern Established:**
```python
# Pure function in teg_analysis (no UI)
def calculate_something(data: pd.DataFrame) -> dict:
    result = do_calculation(data)
    return {'value': result, 'status': 'success'}

# UI wrapper in streamlit/utils.py
@st.cache_data
def calculate_something_cached():
    from teg_analysis.analysis import calculate_something
    return calculate_something(load_data())
```

## Wave 2 Objectives

**Two agents to execute:**

### Agent E: Deduplicate Functions (~2 hours)
**Goal:** Remove 20+ duplicate functions between streamlit/utils.py and teg_analysis

**Process:**
1. Identify duplicates by searching for function names in both locations
2. Compare implementations - keep the better one (usually teg_analysis version)
3. Replace in utils.py with thin import wrapper
4. Test that pages still work

**Expected Duplicates:**
- Data aggregation functions
- Ranking functions
- Format functions
- Any function that exists in both places

**Wrapper Pattern for utils.py:**
```python
# MIGRATED to teg_analysis.analysis.aggregation.function_name
def function_name(*args, **kwargs):
    """Deprecated: Use teg_analysis.analysis.aggregation.function_name

    Kept as wrapper for backward compatibility.
    """
    from teg_analysis.analysis.aggregation import function_name as _func
    return _func(*args, **kwargs)
```

### Agent F: Create Wrapper Layer (~2-3 hours)
**Goal:** Transform streamlit/utils.py into thin Streamlit wrapper

**Current:** ~100 functions
**Target:** ~50 functions (50% reduction)

**Keep in utils.py:**
- I/O with Streamlit caching (@st.cache_data wrappers)
- Streamlit-specific UI (st.markdown, st.columns, CSS)
- Cache management (clear_all_caches, etc.)
- Session state wrappers
- GitHub operations for Railway

**Remove from utils.py (delegate to teg_analysis):**
- Pure calculations → use teg_analysis.analysis
- Data loading → use teg_analysis.core.data_loader
- Data transforms → use teg_analysis.core.data_transforms
- Metadata lookups → use teg_analysis.core.metadata

## Success Criteria for Wave 2

- [ ] utils.py reduced to ~50 functions (from 100)
- [ ] No duplicates between utils.py and teg_analysis (or properly wrapped)
- [ ] Sample pages still work: `streamlit run streamlit/101TEG\ History.py`
- [ ] All imports still work
- [ ] Changes committed with good messages

## Key Reference Documents

**Complete execution guide:**
- Read: `docs/PHASE_5_WAVES_2_4_CONTEXT.md` - Full details for Waves 2-4

**Prior work:**
- `docs/PHASE_5_WAVE_1_COMPLETION.md` - What was done in Wave 1
- `docs/PHASE_5_MASTER_PLAN.md` - Overall Phase 5 strategy

## Instructions

1. **Start with Agent E** (deduplication):
   - Search for duplicate function names
   - Compare implementations
   - Keep teg_analysis version, wrap in utils.py
   - Test incrementally

2. **Then Agent F** (wrapper layer):
   - Review all functions in utils.py
   - Categorize: keep vs migrate
   - Create thin wrappers with @st.cache_data
   - Validate function count reduction

3. **Commit frequently:**
   - After Agent E completion
   - After Agent F completion
   - Use good commit messages with Co-Authored-By: Claude <noreply@anthropic.com>

4. **Test after each agent:**
   - Verify package imports: `python -c "import teg_analysis"`
   - Test a sample page: `streamlit run streamlit/101TEG\ History.py`
   - Count functions: `grep -c "^def " streamlit/utils.py`

5. **Update documentation:**
   - Keep track of progress in `docs/PHASE_5_WAVE_2_PROGRESS.md`
   - Note any issues or decisions

## Expected Timeline

- Agent E: ~2 hours
- Agent F: ~2-3 hours
- **Total Wave 2:** 4-5 hours

After Wave 2, we'll proceed to Wave 3 (update 57 pages) and Wave 4 (validation & docs).

## Questions?

Ask if you need clarification on:
- Which functions to deduplicate
- How to identify duplicates
- Wrapper patterns
- Testing approach
- Anything else

**Ready to start Wave 2!** 🚀
