
### ==============================
### DEBUGGING DATA (TEMPORARY)


# TEG 18 Diagnostic Tool
# Add this to any Streamlit page temporarily

import streamlit as st
from utils import load_all_data, get_round_data, get_tegnum_rounds
from utils import read_file

st.title("🔍 TEG 18 Diagnostic")

# Cache control
col1, col2 = st.columns(2)
with col1:
    if st.button("Clear Cache"):
        st.cache_data.clear()
        st.success("Cache cleared!")
with col2:
    if st.button("Refresh Page"):
        st.rerun()

st.write("---")

# 1. CHECK IF TEG 18 IS SEEN AS INCOMPLETE
st.subheader("1. TEG 18 Completeness Check")

try:
    # Load raw data without filtering
    all_data_raw = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
    
    if 18 in all_data_raw['TEGNum'].unique():
        st.success("✅ TEG 18 found in raw data")
        
        # Check rounds for TEG 18
        teg18_data = all_data_raw[all_data_raw['TEGNum'] == 18]
        observed_rounds = sorted(teg18_data['Round'].unique())
        observed_count = len(observed_rounds)
        
        # Check expected rounds
        expected_count = get_tegnum_rounds(18)
        
        st.write(f"**Observed rounds:** {observed_rounds} (Count: {observed_count})")
        st.write(f"**Expected rounds:** {expected_count}")
        
        if observed_count == expected_count:
            st.success("✅ TEG 18 is COMPLETE")
        else:
            st.error(f"❌ TEG 18 is INCOMPLETE ({observed_count}/{expected_count} rounds)")
            
        # Check what happens with incomplete filter
        all_data_complete_only = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=True)
        if 18 in all_data_complete_only['TEGNum'].unique():
            st.success("✅ TEG 18 survives the incomplete filter")
        else:
            st.error("❌ TEG 18 is filtered out by incomplete filter")
            
    else:
        st.error("❌ TEG 18 NOT found in raw data")
        st.write(f"Available TEGs: {sorted(all_data_raw['TEGNum'].unique())}")
        
except Exception as e:
    st.error(f"Error loading raw data: {e}")

st.write("---")

# 2. CHECK CACHING ISSUES
st.subheader("2. Caching Check")

try:
    # Test get_round_data (used by problematic pages)
    round_data = get_round_data()
    
    if 18 in round_data['TEGNum'].unique():
        st.success("✅ TEG 18 found in get_round_data()")
        teg18_round_data = round_data[round_data['TEGNum'] == 18]
        st.write(f"TEG 18 rounds in get_round_data: {sorted(teg18_round_data['Round'].unique())}")
    else:
        st.error("❌ TEG 18 NOT found in get_round_data()")
        st.write(f"Available TEGs in get_round_data: {sorted(round_data['TEGNum'].unique())}")
        
    # Test with different parameters
    round_data_inc_incomplete = get_round_data(ex_50=True, ex_incomplete=False)
    
    if 18 in round_data_inc_incomplete['TEGNum'].unique():
        st.success("✅ TEG 18 found in get_round_data(ex_incomplete=False)")
    else:
        st.error("❌ TEG 18 NOT found in get_round_data(ex_incomplete=False)")
        
except Exception as e:
    st.error(f"Error with get_round_data: {e}")

st.write("---")

# 3. DETAILED FUNCTION CHECK
st.subheader("3. Function-by-Function Check")

functions_to_test = [
    ("load_all_data(default)", lambda: load_all_data()),
    ("load_all_data(exclude_incomplete=False)", lambda: load_all_data(exclude_incomplete_tegs=False)),
    ("load_all_data(exclude_incomplete=True)", lambda: load_all_data(exclude_incomplete_tegs=True)),
    ("get_round_data()", lambda: get_round_data()),
    ("get_round_data(ex_incomplete=False)", lambda: get_round_data(ex_incomplete=False)),
]

for func_name, func in functions_to_test:
    try:
        data = func()
        has_teg18 = 18 in data['TEGNum'].unique()
        status = "✅" if has_teg18 else "❌"
        st.write(f"{status} **{func_name}**: TEG 18 {'found' if has_teg18 else 'NOT found'}")
        
        if has_teg18:
            teg18_subset = data[data['TEGNum'] == 18]
            rounds = sorted(teg18_subset['Round'].unique())
            st.write(f"   └─ Rounds: {rounds}")
            
    except Exception as e:
        st.write(f"❌ **{func_name}**: Error - {e}")

# 4. CACHE INFO
st.write("---")
st.subheader("4. Cache Information")
st.write("If you see inconsistent results above, it's likely a caching issue.")
st.write("**Try:** Clear Cache → Refresh Page → Run diagnostic again")

# Show current cache status
try:
    import streamlit as st
    # This is a rough way to check if caches exist
    st.write("Note: Streamlit caches are internal - clearing and re-running is the best approach")
except:
    pass

st.write("---")
st.subheader("🕵️ Quick Pipeline Test")

try:
    # Test the exact same flow as get_round_data()
    st.write("**Testing get_round_data() pipeline step by step:**")
    
    # Step 1: Same as get_round_data() calls
    all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
    st.write(f"Step 1 - load_all_data: TEG 18 present = {18 in all_data['TEGNum'].unique()}")
    
    # Step 2: Same aggregation as get_round_data() calls
    from utils import aggregate_data
    aggregated = aggregate_data(all_data, 'Round')
    st.write(f"Step 2 - aggregate_data: TEG 18 present = {18 in aggregated['TEGNum'].unique()}")
    
    if 18 not in aggregated['TEGNum'].unique():
        st.error("🎯 FOUND THE PROBLEM: TEG 18 is lost in aggregate_data()")
        
        # Show what happened to TEG 18
        teg18_before = all_data[all_data['TEGNum'] == 18]
        st.write(f"TEG 18 before aggregation: {len(teg18_before)} rows")
        st.write("Sample TEG 18 data:")
        st.dataframe(teg18_before[['Player', 'TEG', 'Round', 'Sc', 'GrossVP']].head())
        
except Exception as e:
    st.error(f"Error: {e}")

st.write("---")
st.subheader("🔍 Debugging aggregate_data()")

try:
    from utils import list_fields_by_aggregation_level
    
    # Test the field detection
    all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
    fields_by_level = list_fields_by_aggregation_level(all_data)
    
    st.write("**Fields detected by aggregation level:**")
    for level, fields in fields_by_level.items():
        st.write(f"- {level}: {fields}")
    
    # Test just the grouping part
    st.write("**Testing Round-level grouping:**")
    
    # Get the group columns that aggregate_data uses for 'Round'
    aggregation_hierarchy = ['Player', 'TEG', 'Round', 'FrontBack', 'Hole']
    round_idx = aggregation_hierarchy.index('Round')
    group_columns = []
    
    for level in aggregation_hierarchy[:round_idx + 1]:
        group_columns.extend(fields_by_level[level])
    
    group_columns = list(set(group_columns))
    st.write(f"Group columns for Round aggregation: {group_columns}")
    
    # Check if required columns exist for TEG 18
    teg18_data = all_data[all_data['TEGNum'] == 18]
    missing_cols = [col for col in group_columns if col not in teg18_data.columns]
    
    if missing_cols:
        st.error(f"❌ TEG 18 is missing these required columns: {missing_cols}")
    else:
        st.success("✅ TEG 18 has all required columns")
        
        # Try the actual groupby operation
        measures = ['Sc', 'GrossVP', 'NetVP', 'Stableford']
        st.write("**Testing groupby operation on TEG 18:**")
        
        try:
            teg18_grouped = teg18_data.groupby(group_columns, as_index=False)[measures].sum()
            st.write(f"TEG 18 after groupby: {len(teg18_grouped)} rows")
            if len(teg18_grouped) > 0:
                st.dataframe(teg18_grouped.head())
            else:
                st.error("❌ Groupby resulted in empty dataframe")
                
        except Exception as e:
            st.error(f"❌ Groupby failed: {e}")

except Exception as e:
    st.error(f"Debug error: {e}")


st.write("**Checking TEG 18 data for missing fields:**")
teg18_data = all_data[all_data['TEGNum'] == 18]

critical_fields = ['Date', 'Course', 'Year']
for field in critical_fields:
    if field in teg18_data.columns:
        missing_count = teg18_data[field].isna().sum()
        unique_values = teg18_data[field].dropna().unique()
        st.write(f"- {field}: {missing_count} missing values, unique values: {unique_values}")
    else:
        st.write(f"- {field}: **COLUMN MISSING**")


# Add this to the end of your existing diagnostic file

st.write("---")
st.title("📁 File Source & Content Debug")

st.write("---")
st.subheader("1. Environment & File Path Check")

# Check environment
from utils import (
    ROUND_INFO_FILE, 
    ROUND_INFO_FILE_PATH,
    is_running_on_railway,
    get_base_directory
)
import os
from pathlib import Path

st.write(f"**Running on Railway:** {is_running_on_railway()}")
st.write(f"**Base Directory:** {get_base_directory()}")

# Show the file paths being used
st.write("**File paths in use:**")
st.write(f"- ROUND_INFO_FILE (for GitHub): `{ROUND_INFO_FILE}`")
st.write(f"- ROUND_INFO_FILE_PATH (for local): `{ROUND_INFO_FILE_PATH}`")

# Check which file actually exists locally
local_file = ROUND_INFO_FILE_PATH
if local_file.exists():
    st.success(f"✅ Local file exists: {local_file}")
    st.write(f"   File size: {local_file.stat().st_size} bytes")
    import datetime
    st.write(f"   Last modified: {datetime.datetime.fromtimestamp(local_file.stat().st_mtime)}")
else:
    st.error(f"❌ Local file NOT found: {local_file}")

st.write("---")
st.subheader("2. What the App is Actually Reading")

# Test what read_file actually returns
try:
    st.write("**Using read_file():**")
    round_info = read_file(ROUND_INFO_FILE)
    
    st.success("✅ Successfully read round_info data via read_file()")
    st.write(f"Shape: {round_info.shape}")
    st.write(f"Columns: {list(round_info.columns)}")
    
    # Show all the data
    st.write("**Complete round_info.csv contents:**")
    st.dataframe(round_info)
    
    # Check specifically for TEG 18
    st.write("**TEG 18 check:**")
    st.write(f"Available TEGNums: {sorted(round_info['TEGNum'].unique())}")
    
    # Check data types
    st.write(f"TEGNum column type: {round_info['TEGNum'].dtype}")
    
    # Try different ways to find TEG 18
    teg18_exact = round_info[round_info['TEGNum'] == 18]
    teg18_string = round_info[round_info['TEGNum'] == '18']
    teg18_contains = round_info[round_info['TEGNum'].astype(str).str.contains('18')]
    
    st.write(f"TEG 18 found (as int): {len(teg18_exact)} rows")
    st.write(f"TEG 18 found (as string): {len(teg18_string)} rows")
    st.write(f"TEG 18 found (contains '18'): {len(teg18_contains)} rows")
    
    if len(teg18_exact) > 0:
        st.success("✅ TEG 18 found in round_info!")
        st.dataframe(teg18_exact)
    elif len(teg18_string) > 0:
        st.warning("⚠️ TEG 18 found but stored as string")
        st.dataframe(teg18_string)
    else:
        st.error("❌ TEG 18 NOT found in round_info")

except Exception as e:
    st.error(f"Error reading via read_file(): {e}")
    import traceback
    st.code(traceback.format_exc())

st.write("---")
st.subheader("3. Direct File Reading Test")

# Also try reading the local file directly
if local_file.exists():
    try:
        st.write("**Reading local file directly with pandas:**")
        import pandas as pd
        direct_read = pd.read_csv(local_file)
        
        st.success("✅ Direct read successful")
        st.write(f"Shape: {direct_read.shape}")
        st.dataframe(direct_read)
        
        # Check for TEG 18 in direct read
        direct_teg18 = direct_read[direct_read['TEGNum'] == 18]
        if len(direct_teg18) > 0:
            st.success("✅ TEG 18 found in direct read!")
        else:
            st.error("❌ TEG 18 NOT found in direct read")
            
    except Exception as e:
        st.error(f"Error in direct read: {e}")

st.write("---")
st.subheader("4. File Content Comparison")

# Show first few lines of actual file content
if local_file.exists():
    try:
        with open(local_file, 'r') as f:
            content = f.read()
        
        st.write("**Raw file content (first 1000 characters):**")
        st.code(content[:1000])
        
    except Exception as e:
        st.error(f"Error reading raw content: {e}")

# Clear cache button for this section
if st.button("Clear All Caches (File Debug)", key="clear_file_debug_cache"):
    st.cache_data.clear()
    st.success("All caches cleared!")
    st.rerun()

st.write("**🔍 Testing round info merge:**")
try:
    import pandas as pd
    
    # Read round info directly 
    round_info = pd.read_csv(ROUND_INFO_FILE_PATH)
    st.write(f"Round info shape: {round_info.shape}")
    
    # Check TEG 18 specifically
    teg18_info = round_info[round_info['TEGNum'] == 18]
    st.write(f"TEG 18 in round_info: {len(teg18_info)} rows")
    if len(teg18_info) > 0:
        st.dataframe(teg18_info)
    
except Exception as e:
    st.error(f"Round info test error: {e}")


# Deep Aggregation Debug - add this to your diagnostic

st.write("---")
st.title("🔬 Deep Aggregation Function Debug")

try:
    # Get the data that goes into aggregate_data
    all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
    
    st.write("## Step 1: Input Data Analysis")
    teg18_input = all_data[all_data['TEGNum'] == 18]
    
    st.write(f"**TEG 18 input rows:** {len(teg18_input)}")
    st.write(f"**TEG 18 columns:** {list(teg18_input.columns)}")
    
    # Check critical columns
    critical_cols = ['Player', 'TEG', 'Round', 'Date', 'Course', 'Year', 'Sc', 'GrossVP', 'NetVP', 'Stableford']
    st.write("**Critical column check:**")
    for col in critical_cols:
        if col in teg18_input.columns:
            null_count = teg18_input[col].isna().sum()
            unique_count = teg18_input[col].nunique()
            st.write(f"- {col}: {null_count} nulls, {unique_count} unique values")
            if null_count > 0:
                st.error(f"  ❌ {col} has {null_count} null values!")
        else:
            st.error(f"- {col}: MISSING COLUMN")
    
    st.write("## Step 2: Reproducing aggregate_data() Logic")
    
    # Import the actual functions
    from utils import list_fields_by_aggregation_level
    
    # Get field detection
    fields_by_level = list_fields_by_aggregation_level(all_data)
    st.write("**Fields by level:**")
    for level, fields in fields_by_level.items():
        st.write(f"- {level}: {fields}")
    
    # Reproduce the grouping logic for 'Round' level
    aggregation_hierarchy = ['Player', 'TEG', 'Round', 'FrontBack', 'Hole']
    round_idx = aggregation_hierarchy.index('Round')
    group_columns = []
    
    for level in aggregation_hierarchy[:round_idx + 1]:
        group_columns.extend(fields_by_level[level])
    
    group_columns = list(set(group_columns))
    st.write(f"**Group columns:** {group_columns}")
    
    # Check if TEG 18 has all group columns
    missing_cols = [col for col in group_columns if col not in teg18_input.columns]
    if missing_cols:
        st.error(f"❌ TEG 18 missing columns: {missing_cols}")
    else:
        st.success("✅ TEG 18 has all group columns")
    
    st.write("## Step 3: Testing Groupby Step by Step")
    
    # Test 1: Simple groupby without measures
    st.write("**Test 1: Simple groupby (no aggregation)**")
    try:
        simple_groups = teg18_input.groupby(group_columns).size()
        st.write(f"Simple groupby result: {len(simple_groups)} groups")
        st.write("First few groups:")
        st.write(simple_groups.head())
        
        if len(simple_groups) == 0:
            st.error("❌ Even simple groupby returned 0 groups!")
        else:
            st.success(f"✅ Simple groupby found {len(simple_groups)} groups")
            
    except Exception as e:
        st.error(f"❌ Simple groupby failed: {e}")
        import traceback
        st.code(traceback.format_exc())
    
    # Test 2: Check for problematic values in group columns
    st.write("**Test 2: Checking for problematic values in group columns**")
    for col in group_columns:
        if col in teg18_input.columns:
            col_data = teg18_input[col]
            null_count = col_data.isna().sum()
            inf_count = 0
            if col_data.dtype in ['float64', 'float32']:
                inf_count = col_data.isin([float('inf'), float('-inf')]).sum()
            
            st.write(f"- {col}: {null_count} nulls, {inf_count} infinites")
            
            if null_count > 0 or inf_count > 0:
                st.error(f"  ❌ {col} has problematic values!")
                # Show the problematic rows
                problem_mask = col_data.isna()
                if inf_count > 0:
                    problem_mask = problem_mask | col_data.isin([float('inf'), float('-inf')])
                
                problem_rows = teg18_input[problem_mask]
                st.write(f"  Problematic rows ({len(problem_rows)}):")
                st.dataframe(problem_rows[['Player', 'Round', 'Hole', col]].head())
    
    # Test 3: Full aggregation with measures
    st.write("**Test 3: Full aggregation with measures**")
    measures = ['Sc', 'GrossVP', 'NetVP', 'Stableford']
    
    # Check if TEG 18 has the measure columns
    missing_measures = [m for m in measures if m not in teg18_input.columns]
    if missing_measures:
        st.error(f"❌ TEG 18 missing measure columns: {missing_measures}")
    else:
        try:
            # Try the full aggregation
            aggregated = teg18_input.groupby(group_columns, as_index=False)[measures].sum()
            st.write(f"Full aggregation result: {len(aggregated)} rows")
            
            if len(aggregated) == 0:
                st.error("❌ Full aggregation returned 0 rows!")
            else:
                st.success(f"✅ Full aggregation worked! {len(aggregated)} rows")
                st.write("First few aggregated rows:")
                st.dataframe(aggregated.head())
                
        except Exception as e:
            st.error(f"❌ Full aggregation failed: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    st.write("## Step 4: Compare with Working TEG")
    
    # Compare with TEG 17 to see what's different
    if 17 in all_data['TEGNum'].unique():
        teg17_input = all_data[all_data['TEGNum'] == 17]
        st.write(f"**TEG 17 input rows:** {len(teg17_input)}")
        
        # Test TEG 17 aggregation
        try:
            teg17_aggregated = teg17_input.groupby(group_columns, as_index=False)[measures].sum()
            st.write(f"TEG 17 aggregation result: {len(teg17_aggregated)} rows")
            
            if len(teg17_aggregated) > 0:
                st.success("✅ TEG 17 aggregation works!")
                
                # Compare data quality
                st.write("**Data quality comparison:**")
                for col in group_columns:
                    if col in teg17_input.columns and col in teg18_input.columns:
                        teg17_nulls = teg17_input[col].isna().sum()
                        teg18_nulls = teg18_input[col].isna().sum()
                        
                        if teg17_nulls != teg18_nulls:
                            st.write(f"- {col}: TEG17={teg17_nulls} nulls, TEG18={teg18_nulls} nulls")
                        
            else:
                st.error("❌ TEG 17 aggregation also fails!")
                
        except Exception as e:
            st.error(f"TEG 17 aggregation error: {e}")
    
except Exception as e:
    st.error(f"Debug error: {e}")
    import traceback
    st.code(traceback.format_exc())


st.write("---")
st.title("📍 File Path Tracing")

try:
    from utils import read_file, ROUND_INFO_FILE, ROUND_INFO_FILE_PATH, get_base_directory
    import os
    
    st.write("## 1. File Path Constants")
    st.write(f"**ROUND_INFO_FILE (for read_file):** `{ROUND_INFO_FILE}`")
    st.write(f"**ROUND_INFO_FILE_PATH (local path):** `{ROUND_INFO_FILE_PATH}`")
    st.write(f"**Base directory:** `{get_base_directory()}`")
    
    # Construct what the actual path should be
    expected_local_path = get_base_directory() / "data" / "round_info.csv"
    st.write(f"**Expected local path:** `{expected_local_path}`")
    
    st.write("## 2. File Existence Check")
    st.write(f"**ROUND_INFO_FILE_PATH exists:** {ROUND_INFO_FILE_PATH.exists()}")
    st.write(f"**Expected local path exists:** {expected_local_path.exists()}")
    
    if ROUND_INFO_FILE_PATH.exists():
        st.write(f"**ROUND_INFO_FILE_PATH size:** {ROUND_INFO_FILE_PATH.stat().st_size} bytes")
    if expected_local_path.exists():
        st.write(f"**Expected path size:** {expected_local_path.stat().st_size} bytes")
    
    st.write("## 3. Testing read_file")
    
    # Monkey patch to see what file it's actually reading
    original_read_csv = __import__('pandas').read_csv
    
    def debug_read_csv(*args, **kwargs):
        st.write(f"🔍 **pandas.read_csv called with:** `{args[0]}`")
        return original_read_csv(*args, **kwargs)
    
    # Temporarily replace pandas.read_csv
    import pandas as pd
    pd.read_csv = debug_read_csv
    
    try:
        st.write("**Calling read_file(ROUND_INFO_FILE):**")
        round_info_via_function = read_file(ROUND_INFO_FILE)
        st.write(f"Result shape: {round_info_via_function.shape}")
        
        teg18_via_function = round_info_via_function[round_info_via_function['TEGNum'] == 18]
        st.write(f"TEG 18 rows via function: {len(teg18_via_function)}")
        
    except Exception as e:
        st.error(f"read_file error: {e}")
    finally:
        # Restore original function
        pd.read_csv = original_read_csv
    
    st.write("## 4. Testing direct file read")
    st.write(f"**Reading directly from ROUND_INFO_FILE_PATH:** `{ROUND_INFO_FILE_PATH}`")
    
    try:
        round_info_direct = pd.read_csv(ROUND_INFO_FILE_PATH)
        st.write(f"Direct read shape: {round_info_direct.shape}")
        
        teg18_direct = round_info_direct[round_info_direct['TEGNum'] == 18]
        st.write(f"TEG 18 rows direct: {len(teg18_direct)}")
        
        # Compare the two results
        if len(teg18_via_function) != len(teg18_direct):
            st.error("❌ DIFFERENT RESULTS! The function is reading a different file!")
            
            st.write("**Via function TEG 18 data:**")
            if len(teg18_via_function) > 0:
                st.dataframe(teg18_via_function)
            else:
                st.write("No TEG 18 data found")
                
            st.write("**Direct read TEG 18 data:**")
            if len(teg18_direct) > 0:
                st.dataframe(teg18_direct)
            else:
                st.write("No TEG 18 data found")
        else:
            st.success("✅ Both methods return the same data")
            
    except Exception as e:
        st.error(f"Direct read error: {e}")
    
    st.write("## 5. Check if add_round_info uses the same path")
    
    # Let's also trace what add_round_info is doing
    st.write("**Tracing add_round_info function:**")
    
    # Get a small sample of data to test with
    all_data_sample = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
    teg18_sample = all_data_sample[all_data_sample['TEGNum'] == 18].head(5)  # Just 5 rows for testing
    
    st.write(f"Testing with {len(teg18_sample)} TEG 18 rows")
    
    # Monkey patch again to see what add_round_info reads
    pd.read_csv = debug_read_csv
    
    try:
        from utils import add_round_info
        st.write("**Calling add_round_info:**")
        result = add_round_info(teg18_sample)
        
        missing_date = result['Date'].isna().sum()
        missing_course = result['Course'].isna().sum()
        
        st.write(f"After add_round_info - missing Date: {missing_date}")
        st.write(f"After add_round_info - missing Course: {missing_course}")
        
    except Exception as e:
        st.error(f"add_round_info error: {e}")
    finally:
        # Restore original function
        pd.read_csv = original_read_csv
        
except Exception as e:
    st.error(f"File path tracing error: {e}")
    import traceback
    st.code(traceback.format_exc())



st.write("## 6. Column Name Debug")
try:
    round_info = read_file(ROUND_INFO_FILE)
    
    st.write("**Actual columns in round_info:**")
    st.write(list(round_info.columns))
    
    # Check for exact column names
    st.write("**Column existence check:**")
    st.write(f"'Date' in columns: {'Date' in round_info.columns}")
    st.write(f"'Course' in columns: {'Course' in round_info.columns}")
    
    # Show a sample of the data
    st.write("**Sample round_info data:**")
    st.dataframe(round_info.head())
    
    # Try the problematic selection
    try:
        test_selection = round_info[['TEGNum', 'Round', 'Date', 'Course']]
        st.success("✅ Column selection works")
        st.write(f"Selection shape: {test_selection.shape}")
    except KeyError as e:
        st.error(f"❌ Column selection failed: {e}")
        
except Exception as e:
    st.error(f"Column debug error: {e}")
