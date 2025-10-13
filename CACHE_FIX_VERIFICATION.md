# Cache Fix Verification Plan

## Problem Fixed
Commentary and streaks caches were being regenerated from stale cached data during data updates because `st.cache_data.clear()` was called AFTER cache regeneration instead of BEFORE.

## Fix Applied
Moved `st.cache_data.clear()` to line 274 in `data_update_processing.py` - right after `all-data.parquet` is updated but BEFORE dependent caches are regenerated.

## How to Verify the Fix Works

### Next Data Update Process

When you next update data (add a new round), follow these steps to verify the fix:

#### 1. Before Data Update
```bash
# Check current state of commentary caches
python -c "import pandas as pd; df = pd.read_parquet('data/commentary_round_summary.parquet'); print('Current max TEG/Round:', df.groupby('TEGNum')['Round'].max().tail(3))"
```

#### 2. During Data Update (in Streamlit UI)
Watch for these log messages in order:
1. ✅ "Updated data saved to all-scores.parquet"
2. ✅ "All-data updated and CSV created"
3. 🔑 **"Clearing Streamlit caches before cache regeneration..."** ← NEW MESSAGE
4. 🔑 **"Caches cleared - dependent caches will now use fresh data"** ← NEW MESSAGE
5. ✅ "Streaks cache updated"
6. ✅ "Commentary caches updated"

**CRITICAL**: If you see ❌ error messages at steps 5 or 6, the error handling improvements will now show you exactly what failed.

#### 3. Immediately After Data Update
```bash
# Verify new round is in commentary caches
python -c "import pandas as pd; df = pd.read_parquet('data/commentary_round_summary.parquet'); teg = <TEG_NUM>; print(f'TEG {teg} rounds:', sorted(df[df['TEGNum'] == teg]['Round'].unique()))"
```

Replace `<TEG_NUM>` with the TEG number you just updated.

**Expected Result**: You should see the new round number in the list immediately.

#### 4. Test Round Report Generation
```bash
python streamlit/commentary/generate_round_report.py <TEG_NUM> <ROUND_NUM> --dry-run
```

**Expected Result**: Should work without errors. No "ValueError: No data found for TEG X, Round Y" errors.

## What Changed

### Files Modified
1. **streamlit/helpers/data_update_processing.py**
   - Lines 268-276: Added cache clear BEFORE cache regeneration with detailed comments
   - Lines 277-321: Added comprehensive error handling for cache updates
   - Lines 356-357: Removed duplicate cache clear, added explanatory comment

2. **streamlit/utils.py**
   - Lines 1090-1145: Enhanced `update_streaks_cache()` with granular error handling
   - Lines 1200-1300: Enhanced `update_commentary_caches()` with granular error handling

### Key Changes
- **Cache timing fix**: Caches cleared BEFORE regeneration (root cause fix)
- **Error visibility**: Failed cache updates now show clear error messages in UI
- **Detailed logging**: Each step logs progress and data counts
- **Graceful degradation**: One cache failure doesn't stop other caches from updating

## Success Criteria

✅ **Primary Goal**: Commentary caches include new round data immediately after data update
✅ **Secondary Goal**: No manual `regenerate_caches.py` needed after data updates
✅ **Error Handling**: Clear error messages if anything goes wrong
✅ **Logging**: Detailed logs show exactly which step completed and how much data was processed

## If It Still Fails

If commentary caches still don't include new data after this fix:

1. Check the Streamlit logs for the two new messages about cache clearing
2. Look for any ❌ error messages during cache regeneration
3. Check if there are any OTHER cached functions being called (unlikely, but possible)
4. Verify that `load_all_data()` is being called (should see "Loaded X rows of data" in logs)

The improved error handling means you'll now see EXACTLY where it fails if it does.

## Date of Fix
2025-10-13

## Tested By
- [Pending first data update after fix]
