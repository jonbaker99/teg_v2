import streamlit as st
import pandas as pd
import numpy as np
import os
from utils import get_base_directory, load_datawrapper_css, HANDICAPS_CSV, get_current_handicaps_formatted
from utils import read_file, get_hc, get_next_teg_and_check_if_in_progress_fast, get_current_in_progress_teg_fast, write_file, get_player_name, clear_all_caches



st.set_page_config(page_title="Handicaps")
load_datawrapper_css()


def format_change(val):
    if val > 0:
        return f"+{val}"
    elif val < 0:
        return str(val)
    else:
        return "-"

def format_value(val):
    if pd.isna(val) or val == 0:
        return "-"
    return str(int(val))


st.title("Handicaps")

last_completed, next_tegnum, in_progress = get_next_teg_and_check_if_in_progress_fast()

###====== MANUAL OVERWRITE FOR TESTING -> comment out section to revert to normal
# next_tegnum = 19
# st.write("IN TESTING MODE")
###====== END OF MANUAL OVERWRITE FOR TESTING

next_teg = f'TEG {next_tegnum}'

last_completed_teg = next_tegnum - 1
current_handicaps, handicaps_were_calculated = get_current_handicaps_formatted(last_completed_teg, next_tegnum)

current_handicaps = current_handicaps.sort_values(by = next_teg, ascending=True)

# Format the "Change" column
current_handicaps_formatted = current_handicaps.copy()
current_handicaps_formatted['Change'] = current_handicaps_formatted['Change'].apply(format_change)

# tab1, tab2 = st.tabs(["TEG 17 Handicaps", "Handicap History"])

# with tab1:
        
def format_name(name):
    return '  \n'.join(name.split(' '))  # Double space + newline for Markdown line break

current_handicaps['Handicap_formatted'] = current_handicaps['Handicap'].apply(format_name)


# Title
if not handicaps_were_calculated:
    st.markdown(f"#### {next_teg} Handicaps")
else:
    st.markdown(f"#### {next_teg} Handicaps (Draft)")
    st.info("ℹ️ Draft handicaps subject to final review")

# Create a container for custom metrics
custom_metric_container = st.container()

with custom_metric_container:
    # Create six columns
    cols = st.columns(6)
    
    # Iterate through the columns and DataFrame rows simultaneously
    for col, (_, row) in zip(cols, current_handicaps.iterrows()):
        with col:
            # Display the Handicap name with a line break using Markdown
            #st.markdown(f"**{format_name(row['Handicap'])}**")
            
            # Display the TEG 17 value and Change using st.metric
            st.metric(
                #label="TEG 17",
                label = row['Handicap_formatted'],
                value=row[next_teg],
                delta=row['Change'],
                delta_color='inverse'
            )


# Optional: Add some spacing or additional information
if not handicaps_were_calculated:
    st.caption("Change shows difference in HC vs previous TEG")
else:
    st.caption("Change shows difference in HC vs previous TEG")

# Add interface for writing calculated handicaps to CSV
if handicaps_were_calculated:
    st.markdown("Save Calculated Handicaps?")
   
    st.write("Press button below to save these calculated handicaps to the handicaps file")

    if st.button("💾 Save to File", type="primary"):
        try:
            # Re-calculate handicaps to get the raw data for saving
            calculated_handicaps_for_save = get_hc(next_tegnum)

            # Transform calculated handicaps to CSV format
            def transform_handicaps_to_csv_format(calc_hc_df, teg_num):
                # Read existing handicaps file
                existing_handicaps = read_file(HANDICAPS_CSV)

                # Create new row for this TEG
                teg_name = f"TEG {teg_num}"
                new_row = {"TEG": teg_name}

                # Add handicap for each player (using their initials as column names)
                for _, row in calc_hc_df.iterrows():
                    player_initial = row['Pl']
                    handicap = row['hc']
                    new_row[player_initial] = handicap

                # Fill missing players with 0 (in case some players didn't get calculated handicaps)
                for col in existing_handicaps.columns[1:]:  # Skip 'TEG' column
                    if col not in new_row:
                        new_row[col] = 0

                # Add new row to existing data
                new_row_df = pd.DataFrame([new_row])
                updated_handicaps = pd.concat([existing_handicaps, new_row_df], ignore_index=True)

                return updated_handicaps

            # Transform and save
            updated_handicaps = transform_handicaps_to_csv_format(calculated_handicaps_for_save, next_tegnum)
            write_file(HANDICAPS_CSV, updated_handicaps, f"Add calculated handicaps for {next_teg}")

            # Clear caches to ensure fresh data
            clear_all_caches()

            st.success(f"✅ Handicaps saved successfully to {HANDICAPS_CSV}!")
            st.info("🔄 Page will refresh to show the saved handicaps...")
            st.rerun()

        except Exception as e:
            st.error(f"❌ Error saving handicaps: {str(e)}")




with st.expander("Handicap history"):
    try:
        # historic_handicaps = pd.read_csv(HANDICAPS_CSV)
        historic_handicaps = read_file(HANDICAPS_CSV)
        historic_handicaps = historic_handicaps[historic_handicaps['TEG']!='TEG 50']
        # Apply formatting to all columns except the first one (assuming the first column is names or dates)
        for col in historic_handicaps.columns[1:]:
            historic_handicaps[col] = historic_handicaps[col].apply(format_value)
        
        # Display historic handicaps without index, non-sortable, and left-aligned headers
        st.write(historic_handicaps.to_html(index=False, justify='left', classes = 'datawrapper-table full-width'), unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"File not found: {HANDICAPS_CSV}")
        historic_handicaps = pd.DataFrame()  # Return an empty DataFrame if file is missing
    except pd.errors.EmptyDataError:
        st.warning("The file '/data/handicaps.csv' is empty.")
    except Exception as e:
        st.error(f"An error occurred while reading the CSV file: {str(e)}")

# in_progress = True

if in_progress:

    next_next_tegnum = next_tegnum + 1

    # Get current in-progress TEG information for more descriptive title
    in_progress_teg, rounds_played = get_current_in_progress_teg_fast()

    with st.expander(f"Draft handicaps for TEG {next_next_tegnum} (after {rounds_played} rounds of TEG {in_progress_teg})"):
        # next_hc = get_hc(next_next_tegnum)
        next_hc = get_hc(next_next_tegnum).sort_values("hc_raw", ascending=True, na_position="last").reset_index(drop=True)
        st.write(next_hc.to_html(index=False, justify='left', classes = 'datawrapper-table'), unsafe_allow_html=True)

# === NAVIGATION LINKS ===
from utils import add_navigation_links
add_navigation_links(__file__)
