# TEG Status Tracking Implementation Plan

## Context and Problem

The TEG History page currently faces a speed vs completeness trade-off:
- **Fast path**: Uses cached `teg_winners.csv` but may miss recently completed TEGs
- **Slow path**: Calculates winners from `all-scores.parquet` (~hundreds of MB) which is too slow for page loads
- **Gap**: No efficient way to detect when a TEG has been completed but not yet cached

## Solution: TEG Status Files

Create lightweight status tracking files that are updated during data operations and used for fast completeness checks.

### New Data Files

#### 1. `data/completed_tegs.csv`
```csv
TEGNum,TEG,Year,Status,Rounds
18,TEG 18,2025,complete,4
17,TEG 17,2024,complete,4
```

#### 2. `data/in_progress_tegs.csv`
```csv
TEGNum,TEG,Year,Status,Rounds
19,TEG 19,2026,in_progress,2
```

**Field Definitions:**
- `TEGNum`: Integer TEG number for sorting
- `TEG`: Display name (e.g., "TEG 18")
- `Year`: Tournament year
- `Status`: "complete" or "in_progress"
- `Rounds`: Number of completed rounds (1-4)

## Implementation Requirements

### 1. Data Update Process (`streamlit/1000Data update.py`)

**Current Flow Enhancement:**
1. After new data is loaded and processed
2. **NEW**: Analyze completion status of all TEGs in the data
3. **NEW**: Update status files with current TEG states
4. **NEW**: Identify newly completed TEGs and update cached winners
5. Clear caches as currently done

**Specific Implementation:**
```python
def update_teg_status_files():
    """Update TEG status files after data changes."""
    # Load all data to determine TEG completion status
    all_data = load_all_data(exclude_incomplete_tegs=False)

    # Analyze completion by TEG
    teg_completion = analyze_teg_completion(all_data)

    # Split into completed and in-progress
    completed_tegs = teg_completion[teg_completion['Status'] == 'complete']
    in_progress_tegs = teg_completion[teg_completion['Status'] == 'in_progress']

    # Save status files
    save_teg_status_file(completed_tegs, 'completed_tegs.csv')
    save_teg_status_file(in_progress_tegs, 'in_progress_tegs.csv')

    # Note: Winner updates now handled via user interaction on history page
    # No automatic winner calculation during data updates

def analyze_teg_completion(all_data):
    """Determine completion status and round count for each TEG."""
    # Group by TEG and count unique rounds per player
    # TEG is complete when all players have 4 rounds
    # Implementation details to be determined based on data structure
    pass

def calculate_and_save_missing_winners(missing_teg_nums):
    """Calculate and save winners for specific missing TEGs."""
    # Load all data (expensive operation)
    all_data = load_all_data()

    # Calculate winners only for missing TEGs
    for teg_num in missing_teg_nums:
        winners = get_teg_winners(all_data, teg_num)
        append_to_cached_winners(winners)

    # Clear relevant caches after update
    st.cache_data.clear()
```

**Integration Point:**
- Add status update call after data processing, before cache clearing
- Ensure this runs for both manual uploads and automated data updates

### 2. Data Delete Process (`streamlit/delete_data.py`)

**Current Flow Enhancement:**
1. After data deletion is processed
2. **NEW**: Re-analyze remaining data for TEG completion status
3. **NEW**: Update status files to reflect changes
4. **NEW**: Remove deleted TEGs from cached winners if applicable
5. Clear caches as currently done

**Specific Implementation:**
```python
def update_status_after_deletion():
    """Update TEG status files after data deletion."""
    # Similar to update process but handles TEG removal
    # May need to remove TEGs entirely from status files
    # Update cached winners to remove deleted TEGs
    update_teg_status_files()  # Reuse same logic
```

**Integration Point:**
- Add status update call after deletion confirmation, before cache clearing

### 3. TEG History Page (`streamlit/101TEG History.py`)

**Enhanced Logic:**
1. Load cached winners (fast)
2. **NEW**: Load TEG status files (very fast - few KB)
3. **NEW**: Compare completed TEGs against cached winners
4. **NEW**: If mismatches found, show notification and/or trigger update
5. Display complete history as currently done

**Specific Implementation:**
```python
def check_winner_completeness():
    """Check if cached winners match completed TEGs status."""
    # Load status files
    completed_tegs = read_file('data/completed_tegs.csv')
    cached_winners = load_cached_winners()

    # Extract TEG numbers from both sources
    completed_teg_nums = set(completed_tegs['TEGNum'])
    cached_teg_nums = extract_teg_nums_from_winners(cached_winners)

    # Identify missing winners
    missing_winners = completed_teg_nums - cached_teg_nums

    return missing_winners

def display_completeness_status():
    """Show status if winners are missing for completed TEGs."""
    missing = check_winner_completeness()
    if missing:
        st.warning(f"Winners missing for completed TEGs: {sorted(missing)}")

        # Offer to calculate and save winners for missing TEGs
        if st.button("Calculate and Save Winners for Missing TEGs"):
            with st.spinner("Calculating winners for completed TEGs..."):
                calculate_and_save_missing_winners(missing)
            st.success("Winners updated! Refreshing page...")
            st.rerun()

        st.info("Or run the data update process to refresh all winner information.")
```

**Integration Point:**
- Add completeness check after loading cached data
- Display status before main history table

### 4. Data Edit Page Integration

**New Functionality:**
- Display current TEG status files as editable tables
- Allow manual status adjustments for edge cases
- Provide refresh button to regenerate status from raw data

**Implementation Location:**
Add new section to existing data management page or create dedicated status management tab

```python
def display_teg_status_editor():
    """Allow manual editing of TEG status files."""
    st.subheader("TEG Status Management")

    # Load and display completed TEGs
    completed_tegs = read_file('data/completed_tegs.csv')
    st.write("Completed TEGs")
    edited_completed = st.data_editor(completed_tegs)

    # Load and display in-progress TEGs
    in_progress_tegs = read_file('data/in_progress_tegs.csv')
    st.write("In-Progress TEGs")
    edited_in_progress = st.data_editor(in_progress_tegs)

    # Save changes
    if st.button("Save Status Changes"):
        save_status_files(edited_completed, edited_in_progress)
        st.success("Status files updated")

    # Regenerate from data
    if st.button("Regenerate from Raw Data"):
        update_teg_status_files()
        st.rerun()
```

## Technical Considerations

### File Format Choice
- **CSV**: Human readable, easily editable, consistent with existing files
- **Size**: Each file will be < 1KB (20-30 rows max)
- **Performance**: Sub-millisecond load times

### Error Handling
- Graceful fallback if status files missing (regenerate from data)
- Validation of status file contents (expected columns, data types)
- Recovery from corrupted status files

### Data Consistency
- Status files updated atomically during data operations
- Clear documentation of when files are updated
- Manual override capability for edge cases

### Integration with Existing Caching
- Status files complement existing cache strategy
- Cache clearing includes status file refresh
- Status check runs before cache population

## Implementation Progress Tracking

### ✅ Completed Tasks
- [x] Implementation plan documented
- [x] Implement `analyze_teg_completion()` function
- [x] Implement `save_teg_status_file()` function
- [x] Implement `update_teg_status_files()` function
- [x] Integrate status updates into data update process
- [x] Integrate status updates into data delete process
- [x] Test status file generation with sample data
- [x] Implement `check_winner_completeness()` function
- [x] Enhance existing `load_cached_winners()` function to calculate missing winners
- [x] Add completeness check to TEG History page with save prompt below table
- [x] Test user workflow for updating missing winners
- [x] Add status file display to data edit page
- [x] Implement manual editing interface for status files
- [x] Add "Regenerate from Raw Data" functionality
- [x] Test manual override scenarios
- [x] Add consistent cache clearing to data update process

### 🔄 In Progress
- [ ] None currently

### 📋 To Do - Core Implementation
1. **Phase 1**: Create status file update logic in data operations ✅ COMPLETED

2. **Phase 2**: Integrate completeness checking in history page ✅ COMPLETED

3. **Phase 3**: Add manual editing capability to data management ✅ COMPLETED
   - [x] Add status file display to data edit page
   - [x] Implement manual editing interface
   - [x] Add "Regenerate from Raw Data" functionality
   - [x] Test manual override scenarios

4. **Phase 4**: Fast status functions for other pages
   - [ ] Implement `get_next_teg_and_check_if_in_progress_fast()` function
   - [ ] Replace slow status checks in handicaps page
   - [ ] Update other pages to use fast status checks
   - [ ] Performance testing and validation

### 📋 To Do - Further Implementations
- [ ] Explore additional performance optimizations across the application
- [ ] Implement real-time TEG progress indicators
- [ ] Add automated notifications for TEG completion
- [ ] Create performance monitoring dashboard

## Testing Strategy

- Test with various TEG completion scenarios (0-4 rounds)
- Verify status updates during data add/delete operations
- Confirm fast loading of status files vs full data loading
- Test manual override functionality
- Validate winner cache updating for new completions

## Additional Benefits Across Application

The status CSV files will provide performance improvements in multiple areas:

### 1. Handicaps Page (`500Handicaps.py`)
**Current Implementation:**
- Uses `get_next_teg_and_check_if_in_progress()` which loads full data to determine TEG status
- Calls `get_complete_teg_data()` and `get_teg_data_inc_in_progress()` - expensive operations

**Enhancement:**
```python
def get_next_teg_and_check_if_in_progress_fast():
    """Fast TEG status check using status files."""
    completed_tegs = read_file('data/completed_tegs.csv')
    in_progress_tegs = read_file('data/in_progress_tegs.csv')

    last_completed_teg = completed_tegs['TEGNum'].max() if not completed_tegs.empty else 0
    next_teg = last_completed_teg + 1
    in_progress = (in_progress_tegs['TEGNum'] == next_teg).any() if not in_progress_tegs.empty else False

    return last_completed_teg, next_teg, in_progress
```

### 2. Leaderboard and Latest TEG Pages
- Quick determination of current TEG status without loading full datasets
- Fast validation that leaderboard is showing the correct in-progress TEG

### 3. Data Validation Pages
- Rapid checks for TEG completion status during data entry
- Quick validation that uploaded data is for appropriate TEG

### 4. Navigation and Menu Logic
- Dynamic menu items based on TEG completion status
- Fast checks for which pages should be available

### 5. Records and Analysis Pages
- Quick filtering to show only completed TEGs in analysis
- Fast exclusion of incomplete TEG data from calculations

## Future Enhancements

- Real-time TEG progress indicators using status files
- Email notifications when TEGs complete (triggered by status file updates)
- Automated winner announcement generation
- Integration with leaderboard for live status updates
- Performance monitoring dashboard showing load time improvements

---
*This document provides the foundation for implementing efficient TEG status tracking while maintaining the performance gains of cached data.*