import streamlit as st
import pandas as pd
import numpy as np
import os
from utils import get_base_directory, load_datawrapper_css, HANDICAPS_CSV, get_current_handicaps_formatted
from utils import read_file, get_hc, get_next_teg_and_check_if_in_progress



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

last_completed, next_tegnum, in_progress = get_next_teg_and_check_if_in_progress()
next_teg = f'TEG {next_tegnum}'

last_completed_teg = next_tegnum - 1
current_handicaps = get_current_handicaps_formatted(last_completed_teg, next_tegnum)

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
st.header(f"{next_teg} Handicaps")

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
st.caption("Change shows difference in HC vs previous TEG")




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


if in_progress:

    next_next_tegnum = next_tegnum + 1

    with st.expander(f"Draft handicaps for TEG {next_next_tegnum}"):
        next_hc = get_hc(next_next_tegnum)
        st.write(next_hc.to_html(index=False, justify='left', classes = 'datawrapper-table'), unsafe_allow_html=True)
