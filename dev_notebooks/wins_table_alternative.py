
# SNIPPETS HERE GO INTO THE HISTORY PAGE IF REQUIRED

# NEW: Combine wins and TEGs with CSS classes
summary_table['Wins'] = (
    '<span class="wins-number">' + summary_table['Wins'].astype(str) + '</span>' + 
    ' <span class="wins-tegs">(' + summary_table['TEGs'] + ')</span>'
)

# Keep only Player and Wins columns
display_table = summary_table[['Player', 'Wins']]

st.write(display_table.to_html(
    index=False, 
    justify='left', 
    classes='datawrapper-table wins-table-combined', 
    escape=False
), unsafe_allow_html=True)