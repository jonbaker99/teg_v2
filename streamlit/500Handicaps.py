import streamlit as st
import pandas as pd
import numpy as np
import os
from utils import get_base_directory, datawrapper_table_css
from utils import read_file_from_storage



st.set_page_config(page_title="Handicaps")
datawrapper_table_css()

# Define the base directory dynamically
BASE_DIR = get_base_directory()
HANDICAPS_FILE_PATH = BASE_DIR / 'data' / 'handicaps.csv'


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

# Current handicaps data
current_handicaps = pd.DataFrame({
    'Handicap': ['Gregg WILLIAMS', 'Dave MULLIN', 'Jon BAKER', 'John PATTERSON', 'Stuart NEUMANN', 'Alex BAKER'],
    #'TEG 16': [16, 20, 19, 26, 29, 30],
    #'TEG 17': [16, 21, 22, 26, 27, 34],
    'TEG 18': [20, 20, 18, 28, 27, 36],
    'Change': [4, -1, -4, 2, 0, 2]
})

next_teg = 'TEG 18'
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
        # historic_handicaps = pd.read_csv(HANDICAPS_FILE_PATH)
        historic_handicaps = read_file_from_storage(HANDICAPS_FILE_PATH, 'csv')
        historic_handicaps = historic_handicaps[historic_handicaps['TEG']!='TEG 50']
        # Apply formatting to all columns except the first one (assuming the first column is names or dates)
        for col in historic_handicaps.columns[1:]:
            historic_handicaps[col] = historic_handicaps[col].apply(format_value)
        
        # Display historic handicaps without index, non-sortable, and left-aligned headers
        st.write(historic_handicaps.to_html(index=False, justify='left', classes = 'datawrapper-table'), unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"File not found: {HANDICAPS_FILE_PATH}")
        historic_handicaps = pd.DataFrame()  # Return an empty DataFrame if file is missing
    except pd.errors.EmptyDataError:
        st.warning("The file '/data/handicaps.csv' is empty.")
    except Exception as e:
        st.error(f"An error occurred while reading the CSV file: {str(e)}")