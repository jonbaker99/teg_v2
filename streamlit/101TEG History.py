import streamlit as st
import pandas as pd
import altair as alt
from utils import load_all_data, get_teg_winners, get_teg_rounds, datawrapper_table_css

# === LOAD DATA === #
all_data = load_all_data(exclude_incomplete_tegs=True, exclude_teg_50=True)
filtered_data = all_data.copy()
datawrapper_table_css()
# CREATE WINNERS TABLE

winners = get_teg_winners(filtered_data).drop(columns=['Year'])
winner_df = winners.replace(r'\*', '', regex=True)

# === GENERATE DATA FOR CHARTS AND DOUBLES === #
# Melt the DataFrame for players and competitions in long format
melted_winners = pd.melt(winner_df, id_vars=['TEG'], value_vars=['TEG Trophy', 'Green Jacket', 'HMM Wooden Spoon'],
                         var_name='Competition', value_name='Player')

# Group by player and competition, then count the occurrences
player_wins = melted_winners.groupby(['Player', 'Competition']).size().unstack(fill_value=0).sort_values(by='TEG Trophy', ascending=False)
player_wins = player_wins[['TEG Trophy', 'Green Jacket', 'HMM Wooden Spoon']]
player_wins.columns = ['Trophy', 'Jacket', 'Spoon']

# Sort data for each competition
trophy_sorted = player_wins.sort_values(by='Trophy', ascending=False).reset_index()
jacket_sorted = player_wins.sort_values(by='Jacket', ascending=False).reset_index()
spoon_sorted = player_wins.sort_values(by='Spoon', ascending=False).reset_index()

# Find players who won both the Trophy and Jacket in the same TEG
same_player_both = winner_df[winner_df['TEG Trophy'] == winner_df['Green Jacket']]
player_doubles = same_player_both['TEG Trophy'].value_counts().reset_index()
player_doubles.columns = ['Player', 'Doubles']
player_doubles = player_doubles.sort_values(by='Doubles', ascending=False)

# Find the maximum number of wins across all competitions to set the x-axis range
max_wins = max(trophy_sorted['Trophy'].max(), jacket_sorted['Jacket'].max(), spoon_sorted['Spoon'].max())

# === FUNCTION TO CREATE A HORIZONTAL BAR CHART === #
def create_bar_chart(df, x_col, y_col, title):
    chart = alt.Chart(df).mark_bar().encode(
        #x=alt.X(x_col, title=None, axis=alt.Axis(grid=False, labels=False, domain=False), scale=alt.Scale(domain=(0, max_wins+2))),
        x=alt.X(x_col, title=None, axis=alt.Axis(grid=False, labels=False, domain=False)),
        y=alt.Y(y_col, sort='-x', title=None),
        #color=alt.value('steelblue')
    ).properties(
        title=title,
        # width=350,
        height=320
    )
    
    text = chart.mark_text(align='left', baseline='middle', dx=3).encode(text=x_col)
    
    return chart + text

# === DISPLAY CONTENT === #

st.title("TEG History")

'---'
st.markdown("### Contents")
st.markdown('1. Number of wins by player')
st.markdown('2. TEG winners by year')
st.markdown('3. Doubles')
'---'

# Show the 3 bar charts from the 'winners' page
st.subheader("Competition wins")

col1, col2, col3 = st.columns(3,gap = 'medium')

with col1:
    trophy_chart = create_bar_chart(trophy_sorted, 'Trophy', 'Player', 'TEG Trophy Wins')
    st.altair_chart(trophy_chart, use_container_width=True)

with col2:
    jacket_chart = create_bar_chart(jacket_sorted, 'Jacket', 'Player', 'Green Jacket Wins')
    st.altair_chart(jacket_chart, use_container_width=True)
    st.caption('*Green Jacket awarded in TEG 5 to SN for best stableford round; DM had best gross score')

with col3:
    spoon_chart = create_bar_chart(spoon_sorted, 'Spoon', 'Player', 'Wooden Spoon Wins')
    st.altair_chart(spoon_chart, use_container_width=True)

st.divider()

# Show the table and footnote from the 'history' page
st.subheader("TEG History")
st.write(winners.to_html(index=False, justify='left', classes='datawrapper-table'), unsafe_allow_html=True)
st.caption('*Green Jacket awarded in TEG 5 for best stableford round; DM had best gross score')

st.divider()


# Show the 'Doubles' section from the 'winners' page
st.subheader("Doubles")
st.caption(f"There have been {same_player_both.shape[0]} trophy / jacket doubles")
st.write(player_doubles.to_html(index=False, justify='left', classes='datawrapper-table'), unsafe_allow_html=True)
