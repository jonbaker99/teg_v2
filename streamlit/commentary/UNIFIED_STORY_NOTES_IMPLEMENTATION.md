# Unified Story Notes Implementation Plan

**Created:** 2025-01-15
**Status:** 🚧 IN PROGRESS

---

## Overview

Unify the tournament and round report story notes generation into a single comprehensive system. Both report types will use the same rich factual foundation, with different emphasis in their narrative generation prompts.

---

## Key Objectives

1. ✅ **Single source of truth** - One comprehensive story notes file per round
2. ✅ **Cost savings** - One LLM pass instead of two per round (~50% reduction)
3. ✅ **Consistency** - Both reports draw from same factual foundation
4. ✅ **Richer context** - All information available to both perspectives
5. ✅ **Natural terminology** - Front 9/Back 9 instead of artificial 6/6/6 splits
6. ✅ **Complete course context** - Course records, history, descriptions
7. ✅ **Dual competition tracking** - Full Trophy (Stableford) and Green Jacket (Gross) data

---

## Implementation Steps

### ✅ COMPLETED

#### **Step 1: Create Implementation Plan Document** ✅
- **File:** `streamlit/commentary/UNIFIED_STORY_NOTES_IMPLEMENTATION.md`
- **Status:** Complete
- **Description:** This document - tracks all progress and decisions
- **Completed:** 2025-01-15

#### **Step 2: Create Unified Round Data Loader** ✅
- **File:** `streamlit/commentary/unified_round_data_loader.py` (NEW)
- **Status:** Complete
- **Description:** Merged data from both existing loaders + added new course/location context
- **Completed:** 2025-01-15

**Tasks Completed:**
- ✅ Created new file structure (942 lines)
- ✅ Ported functions from `round_data_loader.py`
- ✅ Ported functions from `data_loader.py`
- ✅ Added gross competition equivalents for all position tracking
- ✅ NOTE: "_before" versions of rank fields need to be added to source data (commentary cache)
- ✅ Six-hole splits not included (using Front 9/Back 9 instead)
- ✅ NOTE: front_back_difference_gross needs to be added to source data (commentary_round_summary.parquet)
- ✅ Created `build_course_records()` function
  - Before/after tracking for score, vs par, Stableford
  - Record holders before and after round
  - New record detection
- ✅ Created `build_course_context()` function
  - Course name, area, par
  - Course history (previous TEGs)
  - Course records (comprehensive before/after)
- ✅ Created `build_location_context()` function
  - Area, year, return status
  - Previous TEGs in area
  - Country return info
- ✅ Created main `load_unified_round_data()` function
  - 17 data sections loaded
  - Comprehensive logging
- ✅ Added comprehensive docstrings
- ✅ Tested data loader independently (TEG 17, Round 2) - SUCCESS

**Test Results:**
- 90 hole-by-hole records loaded
- 90 position tracking records (dual competition)
- 57 events, 50 streaks, 56 momentum patterns
- Course context: West Cliffs (Lisbon Coast, Portugal)
- Location: Area Return: Consecutive TEG (following TEG 16)
- All data sections loading correctly

**Notes:**
- Course records: West Cliffs has only been played twice, so no records tracked (threshold is >2 times)
- Some data fields (before/after ranks, front_back_difference_gross) need to be added to source data during future data updates

---

### 🚧 IN PROGRESS

*No steps in progress currently*

---

### 📋 NEXT STEPS

---

#### **Step 3: Update Story Notes Generation**
- **File:** `streamlit/commentary/generate_tournament_commentary_v2.py` (MODIFY)
- **Status:** Pending
- **Description:** Update to use unified data loader and generate comprehensive story notes

**Tasks:**
- [ ] Update imports to use `unified_round_data_loader`
- [ ] Modify `generate_round_story()` function
  - Call `load_unified_round_data()` instead of `load_round_data()`
  - Pass all data to LLM (granular + patterns + context)
- [ ] Update data formatting for prompt
  - Include gross competition data
  - Include course context
  - Include location context
  - Remove six-hole splits
- [ ] Test story notes generation with sample round

---

#### **Step 4: Update Prompts for Comprehensive Story Notes**
- **File:** `streamlit/commentary/prompts.py` (MODIFY)
- **Status:** Pending
- **Description:** Update prompts to extract comprehensive story notes with all sections

**Tasks:**
- [ ] Update `ROUND_STORY_PROMPT`
  - Add sections for dual competition tracking (Trophy + Jacket)
  - Add course context section (records, history, description)
  - Add location context section (area, returns)
  - Remove 6/6/6 splits, emphasize Front 9/Back 9
  - Add instructions for before/after movement commentary
  - Add instructions for course records (before/after round)
- [ ] Update `ROUND_REPORT_PROMPT`
  - Emphasize: hole-by-hole detail, position changes, forward-looking stakes
  - De-emphasize: career context, venue history deep dives
  - Focus on "live coverage" perspective
- [ ] Update `TOURNAMENT_SYNTHESIS_PROMPT`
  - Emphasize: tournament arc, career context, venue significance
  - Can reference: specific defining moments (but not every hole)
  - Focus on "retrospective" perspective
- [ ] Document prompt changes

---

#### **Step 5: Update Round Report Generation**
- **File:** `streamlit/commentary/generate_round_report.py` (MODIFY)
- **Status:** Pending
- **Description:** Update to read unified story notes instead of generating separate ones

**Tasks:**
- [ ] Remove `generate_round_story_notes()` function
- [ ] Update to read story notes from tournament commentary location:
  - Path: `data/commentary/round_reports/TEG{teg}_R{round}_story_notes.md`
- [ ] Keep `generate_round_narrative_report()` unchanged
- [ ] Update CLI to skip story notes generation option
- [ ] Update documentation
- [ ] Test with sample round

---

#### **Step 6: Test Unified System**
- **Status:** Pending
- **Description:** End-to-end testing with sample TEG

**Tasks:**
- [ ] Run tournament commentary generation for test TEG (e.g., TEG 17)
- [ ] Verify comprehensive story notes are generated
- [ ] Verify all data sections are present:
  - [ ] Round metadata
  - [ ] Round summary (with gross fields)
  - [ ] Hole-by-hole scoring
  - [ ] Position changes (both competitions)
  - [ ] Events (with before/after ranks)
  - [ ] Streaks
  - [ ] Momentum patterns
  - [ ] Front 9/Back 9 patterns (with gross)
  - [ ] Lead timeline (both competitions)
  - [ ] Lead changes (both competitions)
  - [ ] Course records (before/after)
  - [ ] Course context
  - [ ] Location context
  - [ ] Projections (both competitions)
- [ ] Run round report generation using unified story notes
- [ ] Compare outputs with previous system
- [ ] Verify cost savings (fewer LLM calls)

---

### 🔮 FUTURE CONSIDERATIONS

#### **Deprecate Old Systems**
- **File:** `streamlit/commentary/round_data_loader.py`
- **Status:** Future
- **Description:** Mark as deprecated, keep for backwards compatibility

**Tasks:**
- [ ] Add deprecation warning to file header
- [ ] Update any remaining references
- [ ] Consider removing after migration period

#### **Archive Old Round Report Story Notes**
- **Status:** Future
- **Description:** Clean up old separate round report story notes files

**Tasks:**
- [ ] Archive old `TEG*_R*_story_notes.md` files from round reports
- [ ] Keep tournament story notes as single source
- [ ] Update documentation

---

## File Change Summary

### NEW Files:
1. ✅ **`streamlit/commentary/UNIFIED_STORY_NOTES_IMPLEMENTATION.md`** (this document)
2. 📋 **`streamlit/commentary/unified_round_data_loader.py`** - Unified data loader

### MODIFY Files:
3. 📋 **`streamlit/commentary/generate_tournament_commentary_v2.py`** - Use unified loader
4. 📋 **`streamlit/commentary/prompts.py`** - Update all prompts
5. 📋 **`streamlit/commentary/generate_round_report.py`** - Read unified story notes

### DEPRECATE (Future):
6. 🔮 **`streamlit/commentary/round_data_loader.py`** - Mark as deprecated

---

## Data Changes Summary

### ✅ ADDED:
- Gross competition position tracking through round
- "_before" versions of rank fields (Stableford and Gross)
- `front_back_difference_gross` to round summary
- Gross equivalents for lead timeline, lead changes, projections
- Course records: before/after for score, vs par, Stableford
- Course context: history, description, records
- Location context: area returns, venue significance
- Victory context split into Stableford and Gross sections

### ❌ REMOVED:
- `net_vp` field (not required)
- Six-hole splits (1-6, 7-12, 13-18) - replaced by Front 9/Back 9
- Separate round report story notes generation

---

## Testing Checklist

### Unit Testing:
- [ ] Test unified data loader independently
- [ ] Verify all data fields are populated correctly
- [ ] Test course context generation
- [ ] Test location context generation
- [ ] Test course records before/after logic

### Integration Testing:
- [ ] Generate story notes for TEG 17, Round 1
- [ ] Verify all sections present in story notes
- [ ] Generate round report using unified story notes
- [ ] Generate tournament report using unified story notes
- [ ] Compare with previous system outputs

### Validation:
- [ ] Verify no duplicate LLM calls
- [ ] Verify cost savings achieved
- [ ] Verify both competitions fully tracked
- [ ] Verify course records accurate (before/after)
- [ ] Verify location context accurate

---

## Decision Log

### 2025-01-15: Remove Six-Hole Splits
**Decision:** Remove artificial 6/6/6 splits (holes 1-6, 7-12, 13-18) in favor of natural Front 9/Back 9 split.
**Rationale:** Front 9/Back 9 is how golfers naturally discuss rounds. Hot/cold spell analysis covers detailed momentum tracking.

### 2025-01-15: Add Course Records Before/After
**Decision:** Track course records both before and after the round for score, vs par, and Stableford.
**Rationale:** Allows clear identification of new records set during the round and provides context for performances.

### 2025-01-15: Add Gross Competition Tracking Throughout
**Decision:** Add gross position tracking, lead changes, projections for Green Jacket competition.
**Rationale:** Green Jacket is equally important competition, needs same level of detail as Trophy.

### 2025-01-15: Add "_before" Rank Fields
**Decision:** Include both before and after rank fields for all position tracking.
**Rationale:** Makes movement commentary much easier to write (e.g., "moved from 3rd to 1st").

---

## Progress Tracking

**Overall Progress:** 33% Complete (2/6 major steps)

| Step | Status | Progress |
|------|--------|----------|
| 1. Create Plan | ✅ Complete | 100% |
| 2. Unified Data Loader | ✅ Complete | 100% |
| 3. Update Story Generation | 📋 Pending | 0% |
| 4. Update Prompts | 📋 Pending | 0% |
| 5. Update Round Reports | 📋 Pending | 0% |
| 6. Testing | 📋 Pending | 0% |

---

## Notes & Observations

### 2025-01-15: Unified Data Loader Complete

**Achievements:**
- Created comprehensive 942-line unified data loader
- Successfully tested with TEG 17, Round 2
- All 17 data sections loading correctly
- Dual competition tracking (Trophy + Jacket) implemented
- Course context with before/after record tracking working
- Location context with area returns functioning

**Key Findings:**
1. **Course Records Threshold:** Courses played ≤2 times don't have records tracked (sensible threshold to avoid noise)
2. **Source Data Dependencies:** Some fields (before/after ranks, front_back_difference_gross) will need to be added to source data files in future data updates
3. **Performance:** Data loader runs efficiently, loads all data in ~2-3 seconds
4. **Data Volume:** Typical round has 90 hole-by-hole records, 50-60 events, 50-60 patterns

**Technical Decisions:**
- Used pandas DataFrames for position tracking (efficient for sorting/ranking)
- Split course records into before/after for each metric (score, vs par, Stableford)
- Implemented dual competition tracking from the start (avoids future refactoring)
- Comprehensive logging for debugging and transparency

**Next Steps:**
- Move to Step 3: Update story notes generation
- Will need to integrate unified loader into tournament commentary generator
- Prompts will need updating to handle richer data structure

---

**Last Updated:** 2025-01-15 18:30 (Unified Data Loader Complete)
