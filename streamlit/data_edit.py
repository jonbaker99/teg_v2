# === IMPORTS ===
import streamlit as st
import pandas as pd
import logging

# Import data loading and file operations from main utils
from utils import read_file, write_file, clear_all_caches

# === CONFIGURATION ===
st.title("📝 Data Edit")

# Configure logging for debugging and monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === PAGE DESCRIPTION ===
st.markdown("Edit CSV data files directly through the web interface. Changes are automatically synced via GitHub.")

# === FILE SELECTION ===
# Available CSV files for editing with descriptions
AVAILABLE_FILES = {
    # "Test File": {
    #     "path": "data/test_file.csv",
    #     "description": "Sample data file for testing editing functionality"
    # },
    "Round Info": {
        "path": "data/round_info.csv",
        "description": "Tournament metadata: courses, dates, TEG information"
    }, 
    "Future TEGs": {
        "path": "data/future_tegs.csv",
        "description": "Planned future tournaments for history display"
    },
    "Handicaps": {
        "path": "data/handicaps.csv",
        "description": "Player handicap data for net scoring calculations"
    },
    "View Processed Data": {  # Add this entry
        "path": "processed_data_view",
        "description": "Read-only view of fully processed tournament data (all-data.parquet)"
    }
}

st.markdown("### Select File to Edit")

# File selection dropdown
selected_file_name = st.selectbox(
    "Choose a CSV file to edit:",
    options=list(AVAILABLE_FILES.keys()),
    index=0,  # Default to Test File
    help="Select which CSV file you want to edit. Changes will be automatically synced via GitHub."
)

selected_file = AVAILABLE_FILES[selected_file_name]["path"]
selected_description = AVAILABLE_FILES[selected_file_name]["description"]

st.markdown(f"**Selected File:** `{selected_file}`")
st.markdown(f"**Description:** {selected_description}")

# === SPECIAL HANDLING FOR READ-ONLY DATA ===
if selected_file_name == "View Processed Data":
    st.markdown("### 📊 Processed Tournament Data (Read-Only)")
    
    try:
        with st.spinner("Loading processed data..."):
            from utils import load_all_data
            all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
        
        # Display basic info
        st.info(f"**{len(all_data):,} records** across **{all_data['TEGNum'].nunique()} TEGs** and **{all_data['Pl'].nunique()} players**")
        
        # Display the data (read-only)
        st.dataframe(
            all_data,
            use_container_width=True,
            height=600
        )
        
        # Optional: Add download button
        if st.button("📥 Download as CSV"):
            csv = all_data.to_csv(index=False)
            st.download_button(
                label="Download Full Dataset",
                data=csv,
                file_name=f"processed_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        # Stop here - don't show editing interface
        st.stop()
        
    except Exception as e:
        st.error(f"Error loading processed data: {e}")
        st.stop()


# === DATA LOADING ===
try:
    # Try to load the selected file
    df = read_file(selected_file)
    st.success(f"✅ Successfully loaded {selected_file}")
    
    # Display file info
    st.markdown(f"**File Info:** {df.shape[0]} rows, {df.shape[1]} columns")
    
    # Show file-specific warnings/info
    if selected_file == "data/round_info.csv":
        st.warning("⚠️ **Important:** This file contains core tournament metadata. Changes may affect historical data and leaderboards.")
    elif selected_file == "data/handicaps.csv":
        st.info("ℹ️ **Note:** Changes to handicaps will affect net scoring calculations across all tournaments.")
    elif selected_file == "data/future_tegs.csv":
        st.info("ℹ️ **Note:** This file controls future tournament planning and navigation behavior.")
    
except FileNotFoundError:
    # Handle missing files based on file type
    if selected_file == "data/test_file.csv":
        # If test.csv doesn't exist, create a sample one
        st.warning(f"⚠️ {selected_file} not found. Creating sample file...")
        
        # Create sample data
        sample_data = pd.DataFrame({
            'ID': [1, 2, 3],
            'Name': ['Sample A', 'Sample B', 'Sample C'], 
            'Value': [10.5, 20.0, 15.7],
            'Active': [True, False, True]
        })
        
        # Save sample file
        try:
            write_file(selected_file, sample_data, "Create sample test_file.csv file")
            st.success(f"✅ Created sample {selected_file}")
            df = sample_data
        except Exception as e:
            st.error(f"❌ Failed to create sample file: {str(e)}")
            st.stop()
    else:
        # For other files, show error and don't proceed
        st.error(f"❌ {selected_file} not found. This file may need to be created through other means.")
        st.info("💡 Try selecting a different file or contact your administrator to create this file.")
        st.stop()
        
except Exception as e:
    st.error(f"❌ Error loading {selected_file}: {str(e)}")
    logger.error(f"Error loading file: {str(e)}")
    st.stop()

# === DATA EDITING ===
st.markdown("### Edit Data")
st.markdown("Make changes to the data below. Click **Save Changes** when finished.")

# Use st.data_editor for interactive editing
edited_df = st.data_editor(
    df,
    use_container_width=True,
    num_rows="dynamic",  # Allow adding/removing rows
    key="data_editor"
)

# === SAVE FUNCTIONALITY ===
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    if st.button("💾 Save Changes", type="primary", use_container_width=True):
        try:
            # Check if data has changed
            if not df.equals(edited_df):
                # Save the edited data
                commit_message = f"Update {selected_file_name} ({selected_file}) via Data Edit page"
                write_file(selected_file, edited_df, commit_message)
                
                # Clear caches to ensure fresh data
                clear_all_caches()
                
                st.success("✅ Changes saved successfully!")
                st.balloons()  # Celebratory animation
                
                # Show summary of changes
                if df.shape != edited_df.shape:
                    st.info(f"📊 Data shape changed from {df.shape} to {edited_df.shape}")
                
                logger.info(f"Successfully saved changes to {selected_file}")
                
                # Auto-rerun to show updated data
                st.rerun()
                
            else:
                st.info("ℹ️ No changes detected - file not modified")
                
        except Exception as e:
            st.error(f"❌ Failed to save changes: {str(e)}")
            logger.error(f"Error saving file: {str(e)}")

# === HELP SECTION ===
with st.expander("ℹ️ How to Use"):
    st.markdown("""
    **Editing Instructions:**
    - Click on any cell to edit its value
    - Use **+** button to add new rows
    - Use **×** button to delete rows
    - Changes are made in-memory until you click **Save Changes**
    
    **Data Sync:**
    - Changes are automatically committed to GitHub
    - Updates are immediately available on Railway and your laptop
    - All modifications are version controlled with commit messages
    
    **Supported Operations:**
    - Edit cell values
    - Add new rows
    - Delete existing rows  
    - Change column data types (automatically detected)
    """)


# === REFRESH CACHES ===

if st.button("🔄 Clear Cache"):
    st.cache_data.clear()
    st.success("All caches cleared!")
    st.rerun()  # Refresh the page


# === FILE STATUS ===
st.markdown("---")
st.markdown(f"**File:** `{selected_file}`")
st.markdown(f"**Current Shape:** {edited_df.shape[0]} rows × {edited_df.shape[1]} columns")