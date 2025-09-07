# TEG Codebase Organization Plan

**Objective**: Organize functions by category to improve maintainability and identify additional duplication  
**Approach**: Restructure utils.py and helper files into logical categories before addressing duplication  
**Priority**: Organization first, then fix direct duplication, defer "similar short function" consolidation

---

## Phase 1: Code Organization by Category

### Suggested Function Categories

Based on the function catalogue analysis, here are the proposed categories for organizing the codebase:

#### **Core Data Operations**
- Primary data loading (`load_all_data`, `read_file`, `write_file`)
- GitHub integration (`read_from_github`, `write_to_github`)
- File I/O and backup operations
- Data validation and integrity checking

#### **Statistical Analysis** 
- Performance calculations (`get_best`, `get_worst`, `chosen_rd_context`, `chosen_teg_context`)
- Score type statistics (`score_type_stats`, `max_scoretype_per_round`)
- Streak analysis and running calculations
- Ranking and comparison functions

#### **Data Processing & Transformation**
- Core scoring calculations (`process_round_for_all_scores`)
- Data aggregation (`aggregate_data` and related functions)
- Data reshaping and format conversion
- Cumulative score calculations

#### **Data Access & Caching**
- Cached data retrieval functions (`get_complete_teg_data`, `get_round_data`, etc.)
- Specialized data loaders (`get_scorecard_data`)
- Data filtering and subset operations

#### **Display & Formatting**
- Value formatting (`format_vs_par`, `format_record_value`, `ordinal`, `safe_ordinal`)
- HTML table generation (`datawrapper_table`, `create_stat_section`)
- Text and number formatting utilities

#### **Chart & Visualization**
- Chart creation (`create_cumulative_graph`, `create_round_graph`)
- Chart formatting and styling
- Visualization data preparation

#### **Scorecard System**
- HTML scorecard generation (all scorecard functions)
- Scorecard data processing and validation
- Mobile vs desktop rendering

#### **UI State Management**
- Session state initialization (`initialize_*_state` functions)
- User interaction workflows
- State reset and management utilities

#### **Helper Utilities**
- Player and trophy name conversions
- Course information loading
- CSS and styling functions
- Range compression and general utilities

---

## Implementation Strategy

### Step 1: Audit Current Organization
- **Target Files**: `utils.py` (~80 functions), `helpers/*.py` (~15 files)
- **Action**: Map each function to proposed categories
- **Output**: Function-to-category mapping document

### Step 2: Identify Direct Duplication (Priority Fix)
- **Critical**: Fix duplicate `get_best` function in `utils.py`
- **Search**: Look for any other duplicate function definitions
- **Verify**: Confirm no other critical duplication exists

### Step 3: Reorganize Code Files
**Option A**: Reorganize within existing files
```
# utils.py structure
# ==========================================
# CORE DATA OPERATIONS
# ==========================================
def load_all_data(...):
    ...

def read_file(...):
    ...

# ==========================================  
# STATISTICAL ANALYSIS
# ==========================================
def get_best(...):
    ...
```

**Option B**: Split into category-specific files
```
utils/
  ├── core_data.py
  ├── statistical_analysis.py  
  ├── data_processing.py
  ├── display_formatting.py
  └── helper_utilities.py
```

### Step 4: Update Imports
- Update all import statements across the codebase
- Ensure no broken dependencies
- Test all pages to verify functionality

### Step 5: Review for Additional Duplication
- With organized code, scan each category for similar patterns
- Document any newly identified duplication
- Update duplication analysis document

---

## Decision Points

### 1. File Organization Approach
**Recommendation**: Start with Option A (reorganize within existing files)
- Less import disruption
- Easier to review and test
- Can migrate to separate files later if beneficial

### 2. utils.py Size Management
- Current: ~80 functions in one file
- With categories: More navigable but still large
- Future consideration: Split into separate files if file becomes unwieldy

### 3. Helper Files Organization
- Some helpers already well-organized by function
- Focus on `utils.py` first, then review helper consistency
- Ensure helper file names align with category structure

---

## Expected Benefits

### Immediate Benefits
1. **Easier Navigation**: Clear sections within files
2. **Duplication Identification**: Related functions grouped together
3. **Code Review**: Easier to spot patterns and inconsistencies
4. **Maintenance**: Logical grouping for future modifications

### Follow-up Benefits  
1. **Targeted Refactoring**: Work on one category at a time
2. **Testing Strategy**: Test category-by-category
3. **Documentation**: Category-based documentation structure
4. **New Development**: Clear guidance on where to add new functions

---

## Success Criteria

- [ ] All functions categorized and documented
- [ ] Direct duplication eliminated (critical bug fixes)
- [ ] Code organized with clear section headers
- [ ] All imports working correctly  
- [ ] All pages functional after reorganization
- [ ] Additional duplication patterns identified and documented

---

## Timeline Estimate

- **Step 1** (Audit): 2-3 hours
- **Step 2** (Fix Critical Issues): 1 hour  
- **Step 3** (Reorganize): 3-4 hours
- **Step 4** (Update Imports): 1-2 hours
- **Step 5** (Review): 1-2 hours

**Total**: 8-12 hours of focused work

---

## Next Actions

1. **Confirm approach**: Option A vs Option B for file organization
2. **Review categories**: Any additions/changes to proposed categories?
3. **Priority confirmation**: Organization → Fix Duplication → Defer Consolidation?
4. **Begin audit**: Start mapping functions to categories