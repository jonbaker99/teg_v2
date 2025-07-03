# Caching Strategy for TEG Golf Tournament App

## Overview

This document outlines the caching strategy for a Streamlit golf tournament analysis app hosted on Railway. The app analyzes scores from an annual golf tournament, reading data from GitHub via API calls and serving multiple users viewing tournament results.

## Current Architecture Context

### **Data Storage**
- **GitHub storage**: All data files stored in GitHub repository
- **Railway deployment**: Streamlit app reads files via GitHub API
- **Key datasets**: 
  - `all-scores.parquet` (primary analysis dataset)
  - `handicaps.csv` (reference data)
  - `round_info.csv` (course/tournament metadata)

### **File Reading Pattern**
```python
def read_file(file_path: str) -> pd.DataFrame:
    if os.getenv('RAILWAY_ENVIRONMENT'):
        return read_from_github(file_path)  # GitHub API call
    else:
        return pd.read_csv(local_path)      # Local development
```

### **Current Caching Issues**
- **Inconsistent caching** across functions
- **No caching on file reads** (GitHub API bottleneck)
- **Short TTLs** causing unnecessary API calls
- **Manual cache management** needed after data updates

## Key Caching Principles

### **1. Railway Shared Cache**
- Cache is **shared across all users and devices** accessing the same Railway instance
- First user populates cache, subsequent users get fast loads
- Perfect for golf tournament scenario (one admin, many viewers)

### **2. Data Change Patterns**
Golf tournament data has distinct update frequencies:
- **Reference data** (handicaps, course info): Changes rarely (monthly/yearly)
- **Tournament scores**: Only changes during data updates or deletions
- **Derived data** (rankings, statistics): Recalculated from core datasets

### **3. Cache Invalidation Trigger**
**Key insight**: Cache should persist until `all-scores.parquet` is modified (either data added or deleted). This file is the source of truth for all tournament analysis.

## Recommended Caching Strategy

### **Tier 1: File Reading (Critical Bottleneck)**
```python
@st.cache_data  # No TTL - persist until manual clear
def read_file(file_path: str) -> pd.DataFrame:
```
**Rationale**: Eliminates repeated GitHub API calls, the primary performance bottleneck

### **Tier 2: Reference Data (Rarely Changes)**
```python
@st.cache_data  # No TTL - persist until manual clear
def load_and_prepare_handicap_data(file_path: str) -> pd.DataFrame:

@st.cache_data  # No TTL - persist until manual clear  
def read_round_info() -> pd.DataFrame:
```
**Rationale**: Handicaps and course info change very infrequently

### **Tier 3: Core Datasets (Tournament Data)**
```python
@st.cache_data  # No TTL - persist until manual clear
def load_all_data(exclude_teg_50: bool = True, exclude_incomplete_tegs: bool = False) -> pd.DataFrame:

@st.cache_data  # No TTL - persist until manual clear
def get_round_data(ex_50=True, ex_incomplete=False):
```
**Rationale**: Only changes when all-scores.parquet is modified

### **Tier 4: Derived/Aggregated Data**
```python
@st.cache_data  # No TTL - persist until manual clear
def get_ranked_teg_data():

@st.cache_data  # No TTL - persist until manual clear
def get_ranked_round_data():

@st.cache_data  # No TTL - persist until manual clear
def score_type_stats():
```
**Rationale**: Expensive calculations that only need refresh when underlying tournament data changes

## Cache Management Implementation

### **Automatic Cache Clearing**
Clear caches immediately after any data modification:

```python
# In data update process (1000Data update.py)
def run_update_process():
    # ... data update logic ...
    write_file(ALL_SCORES_PARQUET, final_df, "Updated with new data")
    
    # Clear all caches after successful update
    st.cache_data.clear()
    st.success("Data updated and caches cleared")

# In data deletion process (delete_data.py)  
def perform_deletion():
    # ... deletion logic ...
    write_file(ALL_SCORES_PARQUET, updated_df, "Deleted selected data")
    
    # Clear all caches after successful deletion
    st.cache_data.clear()
    st.success("Data deleted and caches cleared")
```

### **Manual Cache Controls**
Provide user controls for cache management:

```python
# Add to data management pages
col1, col2 = st.columns(2)

with col1:
    if st.button("🔄 Clear All Caches"):
        st.cache_data.clear()
        st.success("All caches cleared!")

with col2:
    if st.button("📊 Cache Status"):
        # Show cache information if available
        st.info("Cache cleared after every data update")
```

### **Selective Cache Clearing (Optional)**
For more granular control:

```python
def clear_tournament_caches():
    """Clear only tournament-related caches, preserve reference data"""
    load_all_data.clear()
    get_round_data.clear()
    get_ranked_teg_data.clear()
    get_ranked_round_data.clear()
    score_type_stats.clear()
```

## Implementation Steps

### **Step 1: Update Function Decorators**
Remove TTL from all caching decorators:
```python
# Change from:
@st.cache_data(ttl=300)

# To:
@st.cache_data
```

### **Step 2: Add Cache Clearing to Data Operations**
Modify data update and deletion functions to clear caches after successful operations.

### **Step 3: Add Manual Cache Controls**
Include cache management buttons on administrative pages.

### **Step 4: Test Cache Behavior**
- Verify first load is slow (GitHub API calls)
- Verify subsequent loads are fast (cached data)
- Verify cache clears after data updates/deletions

## Performance Impact

### **Expected Results**
- **First user/page load**: Slow (GitHub API calls, cache population)
- **Subsequent loads**: Fast (cached data)
- **After data updates**: One slow load (cache rebuild), then fast again
- **Multi-user benefit**: Admin's initial load benefits all viewers

### **Memory Considerations**
- Golf tournament data is small (<10MB total)
- Railway memory limits easily accommodate full dataset caching
- Aggressive caching strategy is safe for this use case

## Key Benefits

1. **Eliminates GitHub API bottleneck** during normal usage
2. **Provides fast experience** for tournament participants viewing results
3. **Maintains data freshness** by clearing cache when data actually changes
4. **Shared cache benefit** across all users
5. **Simple cache management** tied to actual data modification events

## Trade-offs

| Approach | Pros | Cons |
|----------|------|------|
| **No TTL + Manual Clear** | Always fresh after updates, maximum performance | Requires explicit cache management |
| **Long TTL (24h)** | Automatic refresh, simpler | May serve stale data, unnecessary API calls |
| **Short TTL (1h)** | Regular refresh | Frequent API calls, reduced performance |

**Recommendation**: No TTL with manual clearing tied to data changes. This matches the infrequent, event-driven nature of golf tournament data updates while maximizing performance for all users.
