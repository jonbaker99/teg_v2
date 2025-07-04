import streamlit as st
import pandas as pd
import numpy as np
from utils import load_all_data, format_vs_par, get_scorecard_data, get_teg_metadata, format_date_for_scorecard
from pathlib import Path

def load_scorecard_css():
    """Load the scorecard CSS file and inject it into Streamlit"""
    css_file = Path(__file__).parent / "scorecard_styles.css"
    
    try:
        with open(css_file, 'r') as f:
            css_content = f.read()
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
        return True
    except FileNotFoundError:
        st.error(f"CSS file not found: {css_file}")
        return False

def generate_single_round_html(player_code, teg_num, round_num, title=None, subheader=None):
    """Generate HTML for single player, single round scorecard"""
    
    # Load data using new function
    df = get_scorecard_data(teg_num, round_num, player_code)
    
    if len(df) != 18:
        return f"<div class='scorecard-container'><p>Error: Expected 18 holes, found {len(df)} holes.</p></div>"
    
    # Generate default title if not provided
    if title is None:
        player_name = df['Player'].iloc[0]
        title = f"TEG {teg_num} Round {round_num} | {player_name}"
    
    # Generate default subheader if not provided
    if subheader is None:
        metadata = get_teg_metadata(teg_num, round_num)
        course = metadata.get('Course')
        date_str = metadata.get('Date')
        formatted_date = format_date_for_scorecard(date_str)
        
        if course and formatted_date:
            subheader = f"{course} | {formatted_date}"
        elif course:
            subheader = course
        elif formatted_date:
            subheader = formatted_date
        # If neither available, subheader remains None
    
    # Calculate totals
    front_9 = df[df['Hole'] <= 9]
    back_9 = df[df['Hole'] > 9]
    
    front_totals = {
        'PAR': int(front_9['PAR'].sum()),
        'Sc': int(front_9['Sc'].sum()),
        'Stableford': int(front_9['Stableford'].sum())
    }
    
    back_totals = {
        'PAR': int(back_9['PAR'].sum()),
        'Sc': int(back_9['Sc'].sum()), 
        'Stableford': int(back_9['Stableford'].sum())
    }
    
    total_totals = {
        'PAR': int(df['PAR'].sum()),
        'Sc': int(df['Sc'].sum()),
        'Stableford': int(df['Stableford'].sum())
    }
    
    # Build HTML
    html_parts = []
    
    html_parts.append('<div class="scorecard-container layout-single-round">')

    # Header with title and optional subheader
    html_parts.append('<div class="scorecard-header">')
    html_parts.append(f'<h2>{title}</h2>')
    if subheader:
        html_parts.append(f'<p class="scorecard-subheader">{subheader}</p>')
    html_parts.append('</div>')

    html_parts.append('<table class="scorecard-table">')
    
    # Header section
    html_parts.append('<thead>')
    
    # Hole numbers row
    html_parts.append('<tr>')
    html_parts.append('<th class="label-column hole-header">Hole</th>')
    for hole in range(1, 10):
        html_parts.append(f'<th class="hole-header">{hole}</th>')
    html_parts.append('<th class="hole-header totals front-back-divider">OUT</th>')
    for hole in range(10, 19):
        html_parts.append(f'<th class="hole-header">{hole}</th>')
    html_parts.append('<th class="hole-header totals">IN</th>')
    html_parts.append('<th class="hole-header totals">TOTAL</th>')
    html_parts.append('</tr>')
    
    # PAR row
    html_parts.append('<tr>')
    html_parts.append('<th class="label-column par-header">PAR</th>')
    for hole in range(1, 10):
        par_val = int(df[df['Hole'] == hole]['PAR'].iloc[0])
        html_parts.append(f'<th class="par-header">{par_val}</th>')
    html_parts.append(f'<th class="totals front-back-divider par-header">{front_totals["PAR"]}</th>')
    for hole in range(10, 19):
        par_val = int(df[df['Hole'] == hole]['PAR'].iloc[0])
        html_parts.append(f'<th class="par-header">{par_val}</th>')
    html_parts.append(f'<th class="totals par-header">{back_totals["PAR"]}</th>')
    html_parts.append(f'<th class="totals par-header">{total_totals["PAR"]}</th>')
    html_parts.append('</tr>')
    
    html_parts.append('</thead>')
    
    # Body section
    html_parts.append('<tbody>')
    
    # Score row
    html_parts.append('<tr>')
    html_parts.append('<td class="label-column">Score</td>')
    for hole in range(1, 10):
        hole_data = df[df['Hole'] == hole].iloc[0]
        vs_par = int(hole_data['GrossVP'])
        score = int(hole_data['Sc'])
        html_parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')
    html_parts.append(f'<td class="totals front-back-divider">{front_totals["Sc"]}</td>')
    for hole in range(10, 19):
        hole_data = df[df['Hole'] == hole].iloc[0]
        vs_par = int(hole_data['GrossVP'])
        score = int(hole_data['Sc'])
        html_parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')
    html_parts.append(f'<td class="totals">{back_totals["Sc"]}</td>')
    html_parts.append(f'<td class="totals">{total_totals["Sc"]}</td>')
    html_parts.append('</tr>')
    
    # Stableford row
    html_parts.append('<tr>')
    html_parts.append('<td class="label-column">Stableford</td>')
    for hole in range(1, 10):
        hole_data = df[df['Hole'] == hole].iloc[0]
        stableford = int(hole_data['Stableford'])
        html_parts.append(f'<td class="score-cell" data-stableford="{stableford}"><span>{stableford}</span></td>')
    html_parts.append(f'<td class="totals front-back-divider">{front_totals["Stableford"]}</td>')
    for hole in range(10, 19):
        hole_data = df[df['Hole'] == hole].iloc[0]
        stableford = int(hole_data['Stableford'])
        html_parts.append(f'<td class="score-cell" data-stableford="{stableford}"><span>{stableford}</span></td>')
    html_parts.append(f'<td class="totals">{back_totals["Stableford"]}</td>')
    html_parts.append(f'<td class="totals">{total_totals["Stableford"]}</td>')
    html_parts.append('</tr>')
    
    html_parts.append('</tbody>')
    html_parts.append('</table>')
    html_parts.append('</div>')
    
    return ''.join(html_parts)

def generate_tournament_html(player_code, teg_num, title=None, subheader=None):
    """Generate HTML for single player tournament view (all rounds)"""
    
    # Load data using new function
    player_data = get_scorecard_data(teg_num, player_code=player_code)
    
    if player_data.empty:
        return f"<div class='scorecard-container'><p>Error: No data found for player {player_code} in TEG {teg_num}.</p></div>"
    
    # Generate default title if not provided
    if title is None:
        player_name = player_data['Player'].iloc[0]
        title = f"TEG {teg_num} Tournament | {player_name}"
    
    # Generate default subheader if not provided
    if subheader is None:
        metadata = get_teg_metadata(teg_num)
        area = metadata.get('Area')
        year = metadata.get('Year')
        
        if area and year:
            subheader = f"{area} | {year}"
        elif area:
            subheader = area
        elif year:
            subheader = str(year)
        # If neither available, subheader remains None
    
    rounds = sorted(player_data['Round'].unique())
    
    html_parts = []
    html_parts.append('<div class="scorecard-container layout-multi-round">')

    # Header with title and optional subheader
    html_parts.append('<div class="scorecard-header">')
    html_parts.append(f'<h2>{title}</h2>')
    if subheader:
        html_parts.append(f'<p class="scorecard-subheader">{subheader}</p>')
    html_parts.append('</div>')
    
    # Gross Scores Section
    html_parts.append('<div class="section-header">Gross Scores</div>')
    html_parts.append('<table class="scorecard-table">')
    
    # Header
    html_parts.append('<thead>')
    html_parts.append('<tr>')
    html_parts.append('<th class="round-label">Round</th>')
    for hole in range(1, 10):
        html_parts.append(f'<th>{hole}</th>')
    html_parts.append('<th class="totals front-back-divider">OUT</th>')
    for hole in range(10, 19):
        html_parts.append(f'<th>{hole}</th>')
    html_parts.append('<th class="totals">IN</th>')
    html_parts.append('<th class="totals">TOTAL</th>')
    html_parts.append('</tr>')
    html_parts.append('</thead>')
    
    # Body - one row per round
    html_parts.append('<tbody>')
    for round_num in rounds:
        round_data = player_data[player_data['Round'] == round_num].sort_values('Hole')
        
        # Calculate totals
        front_total = int(round_data[round_data['Hole'] <= 9]['Sc'].sum())
        back_total = int(round_data[round_data['Hole'] > 9]['Sc'].sum())
        total_score = int(round_data['Sc'].sum())
        
        html_parts.append('<tr>')
        html_parts.append(f'<td class="round-label">Round {round_num}</td>')
        
        # Front 9
        for hole in range(1, 10):
            hole_data = round_data[round_data['Hole'] == hole].iloc[0]
            vs_par = int(hole_data['GrossVP'])
            score = int(hole_data['Sc'])
            html_parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')
        
        html_parts.append(f'<td class="totals front-back-divider">{front_total}</td>')
        
        # Back 9
        for hole in range(10, 19):
            hole_data = round_data[round_data['Hole'] == hole].iloc[0]
            vs_par = int(hole_data['GrossVP'])
            score = int(hole_data['Sc'])
            html_parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')
        
        html_parts.append(f'<td class="totals">{back_total}</td>')
        html_parts.append(f'<td class="totals">{total_score}</td>')
        html_parts.append('</tr>')
    
    html_parts.append('</tbody>')
    html_parts.append('</table>')
    
    # Stableford Section
    html_parts.append('<div class="section-header">Stableford Points</div>')
    html_parts.append('<table class="scorecard-table">')
    
    # Header
    html_parts.append('<thead>')
    html_parts.append('<tr>')
    html_parts.append('<th class="round-label">Round</th>')
    for hole in range(1, 10):
        html_parts.append(f'<th>{hole}</th>')
    html_parts.append('<th class="totals front-back-divider">OUT</th>')
    for hole in range(10, 19):
        html_parts.append(f'<th>{hole}</th>')
    html_parts.append('<th class="totals">IN</th>')
    html_parts.append('<th class="totals">TOTAL</th>')
    html_parts.append('</tr>')
    html_parts.append('</thead>')
    
    # Body - Stableford scores
    html_parts.append('<tbody>')
    for round_num in rounds:
        round_data = player_data[player_data['Round'] == round_num].sort_values('Hole')
        
        # Calculate totals
        front_total = int(round_data[round_data['Hole'] <= 9]['Stableford'].sum())
        back_total = int(round_data[round_data['Hole'] > 9]['Stableford'].sum())
        total_stableford = int(round_data['Stableford'].sum())
        
        html_parts.append('<tr>')
        html_parts.append(f'<td class="round-label">Round {round_num}</td>')
        
        # Front 9
        for hole in range(1, 10):
            hole_data = round_data[round_data['Hole'] == hole].iloc[0]
            stableford = int(hole_data['Stableford'])
            html_parts.append(f'<td class="score-cell" data-stableford="{stableford}"><span>{stableford}</span></td>')
        
        html_parts.append(f'<td class="totals front-back-divider">{front_total}</td>')
        
        # Back 9
        for hole in range(10, 19):
            hole_data = round_data[round_data['Hole'] == hole].iloc[0]
            stableford = int(hole_data['Stableford'])
            html_parts.append(f'<td class="score-cell" data-stableford="{stableford}"><span>{stableford}</span></td>')
        
        html_parts.append(f'<td class="totals">{back_total}</td>')
        html_parts.append(f'<td class="totals">{total_stableford}</td>')
        html_parts.append('</tr>')
    
    html_parts.append('</tbody>')
    html_parts.append('</table>')
    html_parts.append('</div>')
    
    return ''.join(html_parts)

def generate_round_comparison_html(teg_num, round_num, title=None, subheader=None):
    """Generate HTML for multi-player round comparison"""
    
    # Load data using new function
    round_data = get_scorecard_data(teg_num, round_num)
    
    if round_data.empty:
        return f"<div class='scorecard-container'><p>Error: No data found for TEG {teg_num} Round {round_num}.</p></div>"
    
    # Generate default title if not provided
    if title is None:
        title = f"TEG {teg_num} Round {round_num} | Player Comparison"
    
    # Generate default subheader if not provided
    if subheader is None:
        metadata = get_teg_metadata(teg_num, round_num)
        course = metadata.get('Course')
        date_str = metadata.get('Date')
        formatted_date = format_date_for_scorecard(date_str)
        
        if course and formatted_date:
            subheader = f"{course} | {formatted_date}"
        elif course:
            subheader = course
        elif formatted_date:
            subheader = formatted_date
        # If neither available, subheader remains None
    
    players = round_data['Pl'].unique()
    
    # Sort players by total score (ascending)
    player_totals = []
    for player in players:
        player_data = round_data[round_data['Pl'] == player]
        total_score = int(player_data['Sc'].sum())
        player_name = player_data['Player'].iloc[0]
        player_totals.append((total_score, player, player_name))
    
    player_totals.sort(key=lambda x: x[0])  # Sort by score
    sorted_players = [(player, name) for _, player, name in player_totals]
    
    html_parts = []
    html_parts.append('<div class="scorecard-container layout-multi-player">')

    # Header with title and optional subheader
    html_parts.append('<div class="scorecard-header">')
    html_parts.append(f'<h2>{title}</h2>')
    if subheader:
        html_parts.append(f'<p class="scorecard-subheader">{subheader}</p>')
    html_parts.append('</div>')
    
    # Gross Scores Section
    html_parts.append('<div class="section-header">Gross Scores</div>')
    html_parts.append('<table class="scorecard-table">')
    
    # Header
    html_parts.append('<thead>')
    html_parts.append('<tr>')
    html_parts.append('<th class="player-label">Player</th>')
    for hole in range(1, 10):
        html_parts.append(f'<th>{hole}</th>')
    html_parts.append('<th class="totals front-back-divider">OUT</th>')
    for hole in range(10, 19):
        html_parts.append(f'<th>{hole}</th>')
    html_parts.append('<th class="totals">IN</th>')
    html_parts.append('<th class="totals">TOTAL</th>')
    html_parts.append('</tr>')
    html_parts.append('</thead>')
    
    # Body - one row per player
    html_parts.append('<tbody>')
    for player_code, player_name in sorted_players:
        player_data = round_data[round_data['Pl'] == player_code].sort_values('Hole')
        
        # Calculate totals
        front_total = int(player_data[player_data['Hole'] <= 9]['Sc'].sum())
        back_total = int(player_data[player_data['Hole'] > 9]['Sc'].sum())
        total_score = int(player_data['Sc'].sum())
        
        html_parts.append('<tr>')
        html_parts.append(f'<td class="player-label">{player_name}</td>')
        
        # Front 9
        for hole in range(1, 10):
            hole_data = player_data[player_data['Hole'] == hole].iloc[0]
            vs_par = int(hole_data['GrossVP'])
            score = int(hole_data['Sc'])
            html_parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')
        
        html_parts.append(f'<td class="totals front-back-divider">{front_total}</td>')
        
        # Back 9
        for hole in range(10, 19):
            hole_data = player_data[player_data['Hole'] == hole].iloc[0]
            vs_par = int(hole_data['GrossVP'])
            score = int(hole_data['Sc'])
            html_parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')
        
        html_parts.append(f'<td class="totals">{back_total}</td>')
        html_parts.append(f'<td class="totals">{total_score}</td>')
        html_parts.append('</tr>')
    
    html_parts.append('</tbody>')
    html_parts.append('</table>')
    
    # Stableford Section
    html_parts.append('<div class="section-header">Stableford Points</div>')
    html_parts.append('<table class="scorecard-table">')
    
    # Header
    html_parts.append('<thead>')
    html_parts.append('<tr>')
    html_parts.append('<th class="player-label">Player</th>')
    for hole in range(1, 10):
        html_parts.append(f'<th>{hole}</th>')
    html_parts.append('<th class="totals front-back-divider">OUT</th>')
    for hole in range(10, 19):
        html_parts.append(f'<th>{hole}</th>')
    html_parts.append('<th class="totals">IN</th>')
    html_parts.append('<th class="totals">TOTAL</th>')
    html_parts.append('</tr>')
    html_parts.append('</thead>')
    
    # Body - Stableford scores  
    html_parts.append('<tbody>')
    for player_code, player_name in sorted_players:
        player_data = round_data[round_data['Pl'] == player_code].sort_values('Hole')
        
        # Calculate totals
        front_total = int(player_data[player_data['Hole'] <= 9]['Stableford'].sum())
        back_total = int(player_data[player_data['Hole'] > 9]['Stableford'].sum())
        total_stableford = int(player_data['Stableford'].sum())
        
        html_parts.append('<tr>')
        html_parts.append(f'<td class="player-label">{player_name}</td>')
        
        # Front 9
        for hole in range(1, 10):
            hole_data = player_data[player_data['Hole'] == hole].iloc[0]
            stableford = int(hole_data['Stableford'])
            html_parts.append(f'<td class="score-cell" data-stableford="{stableford}"><span>{stableford}</span></td>')
        
        html_parts.append(f'<td class="totals front-back-divider">{front_total}</td>')
        
        # Back 9
        for hole in range(10, 19):
            hole_data = player_data[player_data['Hole'] == hole].iloc[0]
            stableford = int(hole_data['Stableford'])
            html_parts.append(f'<td class="score-cell" data-stableford="{stableford}"><span>{stableford}</span></td>')
        
        html_parts.append(f'<td class="totals">{back_total}</td>')
        html_parts.append(f'<td class="totals">{total_stableford}</td>')
        html_parts.append('</tr>')
    
    html_parts.append('</tbody>')
    html_parts.append('</table>')
    html_parts.append('</div>')
    
    return ''.join(html_parts)

# Load CSS
css_loaded = load_scorecard_css()

st.title('Scorecard v2 - Enhanced Visual Design')

if not css_loaded:
    st.warning("CSS not loaded - scorecard may not display correctly")


# Create tabs
tab1, tab2, tab3 = st.tabs(["Single Round", "Tournament View", "Round Comparison"])

# Tab 1: Single Round (existing functionality)
with tab1:
    st.markdown('**Select round to view enhanced scorecard**')
    
    # Create dropdowns
    pl_options = sorted(all_data['Pl'].unique())
    default_pl = pl_options[0] if pl_options else None
    
    tegnum_options = sorted(all_data['TEGNum'].unique())
    default_tegnum = max(tegnum_options) if tegnum_options else None
    
    def get_max_round(tegnum):
        return all_data[all_data['TEGNum'] == tegnum]['Round'].max()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_pl = st.selectbox('Select Player', pl_options, index=pl_options.index(default_pl), key='tab1_player')
    
    with col2:    
        selected_tegnum = st.selectbox('Select TEGNum', tegnum_options, index=tegnum_options.index(default_tegnum), key='tab1_teg')
    
    with col3:
        max_round = get_max_round(selected_tegnum)
        round_options = sorted(all_data[all_data['TEGNum'] == selected_tegnum]['Round'].unique())
        selected_round = st.selectbox('Select Round', round_options, index=round_options.index(max_round) if max_round in round_options else 0, key='tab1_round')
    
    # Filter data
    rd_data = get_scorecard_data(selected_tegnum, selected_round, selected_pl)

    
    if len(rd_data) == 0:
        st.error("No data found for the selected criteria.")
    else:
        # Prepare data
        output_cols = ['Hole', 'PAR', 'SI', 'HCStrokes', 'Sc', 'GrossVP', 'NetVP', 'Stableford']
        output_data = rd_data[output_cols].copy()
        
        def to_int_or_zero(x):
            if pd.isna(x):
                return 0
            return int(x)
        
        numeric_columns = output_data.select_dtypes(include=['float64', 'int64']).columns
        for col in numeric_columns:
            output_data[col] = output_data[col].map(to_int_or_zero)
        
        if len(output_data) == 18:
            scorecard_html = generate_single_round_html(selected_pl, selected_tegnum, selected_round)
            st.markdown(scorecard_html, unsafe_allow_html=True)
        else:
            st.error(f"Expected 18 holes, found {len(output_data)} holes for this round.")

# Tab 2: Tournament View
with tab2:
    st.markdown('**Select player and tournament to view all rounds**')
    
    col1, col2 = st.columns(2)
    
    with col1:
        pl_options_t2 = sorted(all_data['Pl'].unique())
        selected_pl_t2 = st.selectbox('Select Player', pl_options_t2, key='tab2_player')
    
    with col2:
        tegnum_options_t2 = sorted(all_data['TEGNum'].unique())
        selected_tegnum_t2 = st.selectbox('Select Tournament', tegnum_options_t2, index=len(tegnum_options_t2)-1, key='tab2_teg')
    
    # Filter data for selected player and tournament
    tournament_data = get_scorecard_data(selected_tegnum_t2, player_code=selected_pl_t2)

    
    if len(tournament_data) == 0:
        st.error("No data found for the selected player and tournament.")
    else:
        # Get player name and TEG name
        player_name = tournament_data['Player'].iloc[0]
        teg_name = f"TEG {selected_tegnum_t2}"
        
        # Generate tournament view
        tournament_html = generate_tournament_html(selected_pl_t2, selected_tegnum_t2)
        st.markdown(tournament_html, unsafe_allow_html=True)

# Tab 3: Round Comparison
with tab3:
    st.markdown('**Select tournament and round to compare all players**')
    
    col1, col2 = st.columns(2)
    
    with col1:
        tegnum_options_t3 = sorted(all_data['TEGNum'].unique())
        selected_tegnum_t3 = st.selectbox('Select Tournament', tegnum_options_t3, index=len(tegnum_options_t3)-1, key='tab3_teg')
    
    with col2:
        round_options_t3 = sorted(all_data[all_data['TEGNum'] == selected_tegnum_t3]['Round'].unique())
        selected_round_t3 = st.selectbox('Select Round', round_options_t3, index=len(round_options_t3)-1, key='tab3_round')
    
    # Filter data for selected tournament and round
    comparison_data = get_scorecard_data(selected_tegnum_t3, selected_round_t3)
    
    if len(comparison_data) == 0:
        st.error("No data found for the selected tournament and round.")
    else:
        teg_name = f"TEG {selected_tegnum_t3}"
        
        # Generate round comparison view
        comparison_html = generate_round_comparison_html(selected_tegnum_t3, selected_round_t3)
        st.markdown(comparison_html, unsafe_allow_html=True)