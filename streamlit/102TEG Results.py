import streamlit as st
import pandas as pd
from typing import List, Dict, Any
import logging
from utils import get_teg_rounds, get_round_data, load_all_data
from make_charts import create_cumulative_graph, adjusted_grossvp, adjusted_stableford

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
PAGE_TITLE = "Golf Scores"
PAGE_ICON = "⛳"
MEASURES = ['Sc', 'GrossVP', 'NetVP', 'Stableford']
PLAYER_COLUMN = 'Player'

# Custom CSS
CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');

    .datawrapper-table {
        font-family: Roboto, Arial, sans-serif !important;
        border-collapse: separate !important;
        border-spacing: 0 !important;
        font-size: 14px !important;
        width: 100%;
        max-width: 600px;
        margin-bottom: 40px !important;
    }
    .datawrapper-table th, .datawrapper-table td {
        text-align: center !important;
        padding: 12px 8px !important;
        border: none !important;
        border-bottom: 1px solid #e0e0e0 !important;
        word-wrap: break-word;
    }
    .datawrapper-table th {
        font-weight: bold !important;
        border-bottom: 2px solid #000 !important;
    }
    .datawrapper-table th.rank-header {
        padding: 12px 8px !important;
    }
    .datawrapper-table tr:hover {
        background-color: #f5f5f5 !important;
    }
    .datawrapper-table .total {
        font-weight: bold !important;
    }
    .datawrapper-table td:nth-child(2),
    .datawrapper-table th:nth-child(2) {
        text-align: left !important;
    }
    .datawrapper-table td:first-child,
    .datawrapper-table th:first-child {
        font-size: 12px !important;
        width: 30px !important;
        max-width: 30px !important;
    }
    .datawrapper-table .top-rank {
        background-color: #f7f7f7 !important;
    }
    .leaderboard-header {
        font-size: 18px !important;
        margin-top: 30px !important;
        margin-bottom: 0px !important;
        padding: 0px;
    }
    .divider {
        border-top: 1px solid #e0e0e0;
        margin: 40px 0;
    }

    @media (max-width: 300px) {
        .datawrapper-table th:not(:first-child):not(:nth-child(2)):not(:last-child),
        .datawrapper-table td:not(:first-child):not(:nth-child(2)):not(:last-child) {
            display: none;
        }
    }
</style>
"""

@st.cache_data
def create_leaderboard(leaderboard_df: pd.DataFrame, value_column: str, ascending: bool = True) -> pd.DataFrame:
    """
    Create a leaderboard from the given dataframe.

    Args:
        leaderboard_df (pd.DataFrame): Input dataframe.
        value_column (str): Column to use for ranking.
        ascending (bool): Whether to sort in ascending order.

    Returns:
        pd.DataFrame: Leaderboard dataframe.
    """
    pivot_df = leaderboard_df.pivot_table(
        index=PLAYER_COLUMN, 
        columns='Round', 
        values=value_column, 
        aggfunc='sum', 
        fill_value=0
    ).assign(Total=lambda x: x.sum(axis=1)).sort_values('Total', ascending=ascending)

    pivot_df.columns = [f'R{col}' if isinstance(col, int) else col for col in pivot_df.columns]
    pivot_df = pivot_df.reset_index()
    pivot_df['Rank'] = pivot_df['Total'].rank(method='min', ascending=ascending).astype(int)

    duplicated_scores = pivot_df['Total'].duplicated(keep=False)
    pivot_df.loc[duplicated_scores, 'Rank'] = pivot_df.loc[duplicated_scores, 'Rank'].astype(str) + '='

    columns = ['Rank', PLAYER_COLUMN] + [col for col in pivot_df.columns if col not in ['Rank', PLAYER_COLUMN]]
    leaderboard = pivot_df[columns]
    logger.info(f"Leaderboard created for {value_column}.")
    return leaderboard

def generate_table_html(df: pd.DataFrame) -> str:
    """
    Generate HTML table from dataframe.

    Args:
        df (pd.DataFrame): Input dataframe.

    Returns:
        str: HTML table string.
    """
    html = ["<table class='datawrapper-table'>"]
    html.append("<thead><tr><th class='rank-header'></th>" + "".join(f"<th>{col}</th>" for col in df.columns[1:]) + "</tr></thead><tbody>")

    for _, row in df.iterrows():
        row_class = ' class="top-rank"' if str(row['Rank']).startswith('1') else ''
        html.append(f"<tr{row_class}>")
        for col in df.columns:
            cell_class = ' class="total"' if col == 'Total' else ''
            html.append(f'<td{cell_class}>{row[col]}</td>')
        html.append("</tr>")

    html.append("</tbody></table>")
    return "".join(html)

def format_value(value: Any, value_type: str) -> str:
    """
    Format values based on their type.

    Args:
        value (Any): The value to format.
        value_type (str): The type of value ('GrossVP' or 'Stableford').

    Returns:
        str: Formatted value string.
    """
    try:
        num = float(value)
        if value_type == 'GrossVP':
            if num > 0:
                return f"+{int(num)}" if num.is_integer() else f"+{num}"
            elif num < 0:
                return f"{int(num)}" if num.is_integer() else f"{num}"
            else:
                return "="
        elif value_type == 'Stableford':
            return f"{int(round(num))}"
        else:
            return str(value)
    except (ValueError, TypeError):
        return str(value)

def get_champions(df: pd.DataFrame) -> str:
    """
    Get champions from dataframe.

    Args:
        df (pd.DataFrame): Input dataframe.

    Returns:
        str: Comma-separated list of champions.
    """
    champions = df[df['Rank'] == 1][PLAYER_COLUMN].astype(str).tolist()
    return ', '.join(champions)

def display_leaderboard(leaderboard_df: pd.DataFrame, value_column: str, title: str, leader_label: str, ascending: bool) -> None:
    """
    Display a leaderboard.

    Args:
        leaderboard_df (pd.DataFrame): Input dataframe.
        value_column (str): Column to use for ranking.
        title (str): Title of the leaderboard.
        leader_label (str): Label for the leader/champion.
        ascending (bool): Whether to sort in ascending order.
    """
    leaderboard = create_leaderboard(leaderboard_df, value_column, ascending)
    champions = get_champions(leaderboard)

    columns_to_format = [col for col in leaderboard.columns if col not in ['Rank', PLAYER_COLUMN]]

    for col in columns_to_format:
        leaderboard[col] = leaderboard[col].apply(lambda x: format_value(x, value_column))

    st.markdown(f"""
        <h3 class='leaderboard-header'>{title}</h3>
        <p>{leader_label}: {champions}</p>
        """, unsafe_allow_html=True)

    table_html = generate_table_html(leaderboard)
    st.markdown(table_html, unsafe_allow_html=True)


# =========== CODE TO MAKE PAGE

#st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

if st.sidebar.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()

try:
    with st.spinner("Loading data..."):
        round_df = get_round_data()
        all_data = load_all_data()

    required_columns = [PLAYER_COLUMN, 'TEGNum', 'TEG', 'Round'] + MEASURES
    missing_columns = [col for col in required_columns if col not in round_df.columns]
    if missing_columns:
        st.error(f"Missing columns in data: {', '.join(missing_columns)}")
        logger.error(f"Missing columns in data: {', '.join(missing_columns)}")
        st.stop()

    teg_order = round_df[['TEG', 'TEGNum']].drop_duplicates().sort_values('TEGNum')
    tegs = teg_order['TEG'].tolist()

    if not tegs:
        st.warning("No TEGs available in the data.")
        st.stop()

    chosen_teg = st.radio('Select TEG', tegs, horizontal=True)

    leaderboard_df = round_df[round_df['TEG'] == chosen_teg]

    if leaderboard_df.empty:
        st.warning(f"No data available for {chosen_teg}.")
        st.stop()

    current_rounds = leaderboard_df['Round'].nunique()
    total_rounds = get_teg_rounds(chosen_teg)
    is_complete = current_rounds >= total_rounds

    page_header = f"{chosen_teg} Results" if is_complete else f"{chosen_teg} Scoreboard"
    leader_label = "Champion" if is_complete else "Leader"

    st.subheader(page_header)

    tab1, tab2 = st.tabs(["TEG Trophy & Spoon", "Green Jacket"])

    with tab1:

        display_leaderboard(
            leaderboard_df, 
            'Stableford', 
            "TEG Trophy Leaderboard (Best Stableford)",
            leader_label, 
            ascending=False
        )

        stableford_chart_type = st.radio(
                "Choose Stableford chart type:",
                ('Standard', 'Adjusted scale'),
                key='stableford_chart_type'
            )
        st.caption("Adjusted view 'zooms in' by showing performance vs. net par to more clearly show gaps between players")

        # fig_stableford = create_cumulative_graph(all_data, chosen_teg,  'Stableford Cum TEG', f'Trophy race: {chosen_teg}')
        # st.plotly_chart(fig_stableford, use_container_width=True)

        # Create and display Stableford chart
        if stableford_chart_type == 'Standard':
            fig_stableford = create_cumulative_graph(all_data, chosen_teg, 'Stableford Cum TEG', 
                                                    f'Trophy race: {chosen_teg}',
                                                    y_axis_label='Cumulative Stableford Points',
                                                    chart_type='stableford')
        else:
            fig_stableford = create_cumulative_graph(all_data, chosen_teg, 'Adjusted Stableford', 
                                                    f'Trophy race (Adjusted scale): {chosen_teg}', 
                                                    y_calculation=adjusted_stableford,
                                                    y_axis_label='Cumulative Stableford Points vs. net par',
                                                    chart_type='stableford')

        st.plotly_chart(fig_stableford, use_container_width=True)
        st.caption('Higher = better')

    with tab2: 
        display_leaderboard(
            leaderboard_df, 
            'GrossVP', 
            "Green Jacket Leaderboard (Best Gross)",
            leader_label, 
            ascending=True
        )

        # with st.expander("The race for the jacket..."):
        #     fig_grossvp = create_cumulative_graph(all_data, chosen_teg, 'GrossVP Cum TEG', f'Cumulative gross for {chosen_teg}')
        #     st.plotly_chart(fig_grossvp, use_container_width=True)


        grossvp_chart_type = st.radio(
            "Choose Green Jacket chart type:",
            ('Standard', 'Adjusted scale'),
            key='grossvp_chart_type'
        )
        st.caption("Adjusted view 'zooms in' by showing performance vs. bogey golf to more clearly show gaps between players")

        # Create and display Green Jacket chart
        if grossvp_chart_type == 'Standard':
            fig_grossvp = create_cumulative_graph(all_data, chosen_teg, 'GrossVP Cum TEG', 
                                                f'Green Jacket race: {chosen_teg}',
                                                y_axis_label='Cumulative gross vs par',
                                                chart_type='gross')
        else:
            fig_grossvp = create_cumulative_graph(all_data, chosen_teg, 'Adjusted GrossVP', 
                                                f'Green Jacket race (Adjusted scale): {chosen_teg}', 
                                                y_calculation=adjusted_grossvp,
                                                y_axis_label='Cumulative gross vs. bogey golf (par+1)',
                                                chart_type='gross')

        st.plotly_chart(fig_grossvp, use_container_width=True)
        st.caption('Lower = better')


except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    logger.error(f"An error occurred: {str(e)}", exc_info=True)

