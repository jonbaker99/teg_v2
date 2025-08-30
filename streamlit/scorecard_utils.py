"""
Golf Scorecard Generation Utilities
Converts pandas DataFrames to beautiful HTML golf scorecards
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from utils import get_scorecard_data, get_teg_metadata, format_date_for_scorecard

date_format = '%d %B %Y'

def generate_scorecard_html(df, layout="single-round", title="Scorecard"):
    """
    Convert a pandas DataFrame to a golf scorecard HTML.
    
    Args:
        df: DataFrame with columns: Hole, PAR, SI, HCStrokes, Sc, GrossVP, NetVP, Stableford
        layout: "single-round", "multi-round", or "multi-player" 
        title: Title for the scorecard
    
    Returns:
        HTML string ready for st.write(unsafe_allow_html=True)
    """
    
    # Ensure we have 18 holes
    if len(df) != 18:
        st.error(f"Expected 18 holes, got {len(df)} holes")
        return ""
    
    # Calculate front 9, back 9, and total
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
    
    # Generate hole header row
    hole_header = '<th class="label-column hole-header">Hole</th>'
    for hole in range(1, 19):
        if hole == 10:
            hole_header += f'<th class="hole-header totals front-back-divider">OUT</th>'
        hole_header += f'<th class="hole-header">{hole}</th>'
    hole_header += '<th class="hole-header totals">IN</th><th class="hole-header totals">TOTAL</th>'
    
    # Generate PAR row
    par_row = '<th class="label-column">PAR</th>'
    for hole in range(1, 19):
        if hole == 10:
            par_row += f'<th class="totals front-back-divider">{front_totals["PAR"]}</th>'
        par_value = int(df[df['Hole'] == hole]['PAR'].iloc[0])
        par_row += f'<th>{par_value}</th>'
    par_row += f'<th class="totals">{back_totals["PAR"]}</th><th class="totals">{total_totals["PAR"]}</th>'
    
    # Generate score row with data attributes
    score_row = '<td class="label-column">Score</td>'
    for hole in range(1, 19):
        if hole == 10:
            score_row += f'<td class="totals front-back-divider">{front_totals["Sc"]}</td>'
        
        hole_data = df[df['Hole'] == hole].iloc[0]
        vs_par = int(hole_data['GrossVP'])
        score = int(hole_data['Sc'])
        
        score_row += f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>'
    
    score_row += f'<td class="totals">{back_totals["Sc"]}</td><td class="totals">{total_totals["Sc"]}</td>'
    
    # Generate Stableford row with data attributes  
    stableford_row = '<td class="label-column">Stableford</td>'
    for hole in range(1, 19):
        if hole == 10:
            stableford_row += f'<td class="totals front-back-divider">{front_totals["Stableford"]}</td>'
        
        hole_data = df[df['Hole'] == hole].iloc[0]
        stableford = int(hole_data['Stableford'])
        
        stableford_row += f'<td class="score-cell" data-stableford="{stableford}"><span>{stableford}</span></td>'
    
    stableford_row += f'<td class="totals">{back_totals["Stableford"]}</td><td class="totals">{total_totals["Stableford"]}</td>'
    
    # Combine into full HTML
    html = f'''
    <div class="scorecard-container layout-{layout}">
        <div class="scorecard-header">
            <p class="scorecard-title">{title}</p>
        </div>
        
        <table class="scorecard-table">
            <thead>
                <tr>{hole_header}</tr>
                <tr>{par_row}</tr>
            </thead>
            <tbody>
                <tr>{score_row}</tr>
                <tr>{stableford_row}</tr>
            </tbody>
        </table>
    </div>
    '''
    
    return html

def format_vs_par(value):
    """Format vs par values for display"""
    if pd.isna(value):
        return ""
    value = int(value)
    if value > 0:
        return f"+{value}"
    elif value < 0:
        return f"{value}"
    else:
        return "="

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
        title = f"{player_name} | TEG {teg_num}, Round {round_num}"
    
    # Generate default subheader if not provided
    if subheader is None:
        metadata = get_teg_metadata(teg_num, round_num)
        course = metadata.get('Course')
        date_str = metadata.get('Date')
        formatted_date = format_date_for_scorecard(date_str, output_format=date_format)
        
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
    html_parts.append(f'<p class="scorecard-title">{title}</p>')
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

        # # Debug
        # if vs_par == -2:
        #     st.write(f"DEBUG: Eagle found on hole {hole}, vs_par={vs_par}")

        score = int(hole_data['Sc'])
        html_parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')

        # # Debug - show what HTML is being generated
        # if vs_par == -2:
        #     st.write(f"DEBUG: HTML generated: <td class=\"score-cell\" data-vs-par=\"{vs_par}\"><span>{score}</span></td>")


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
        title = f"{player_name} | TEG {teg_num}"
    
    
    # # Debug - remove this after testing
    # st.write("DEBUG metadata:", get_teg_metadata(teg_num))
    
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
    html_parts.append(f'<p class="scorecard-title">{title}</p>')
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
        title = f"TEG {teg_num}, Round {round_num}"
    
    # Generate default subheader if not provided
    if subheader is None:
        metadata = get_teg_metadata(teg_num, round_num)
        course = metadata.get('Course')
        date_str = metadata.get('Date')
        formatted_date = format_date_for_scorecard(date_str, output_format= date_format)
        
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
    
    # Calculate PAR totals (using first player's data since PAR is same for all)
    first_player_data = round_data[round_data['Pl'] == players[0]].sort_values('Hole')
    front_par_total = int(first_player_data[first_player_data['Hole'] <= 9]['PAR'].sum())
    back_par_total = int(first_player_data[first_player_data['Hole'] > 9]['PAR'].sum())
    total_par = int(first_player_data['PAR'].sum())
    
    html_parts = []
    html_parts.append('<div class="scorecard-container layout-multi-player">')

    # Header with title and optional subheader
    html_parts.append('<div class="scorecard-header">')
    html_parts.append(f'<p class="scorecard-title">{title}</p>')
    if subheader:
        html_parts.append(f'<p class="scorecard-subheader">{subheader}</p>')
    html_parts.append('</div>')
    
    # Gross Scores Section
    html_parts.append('<div class="section-header">Gross Scores</div>')
    html_parts.append('<table class="scorecard-table">')
    
    # Header
    html_parts.append('<thead>')
    
    # Row 1: Hole numbers
    html_parts.append('<tr>')
    html_parts.append('<th class="player-label hole-header">Player</th>')
    for hole in range(1, 10):
        html_parts.append(f'<th class="hole-header">{hole}</th>')
    html_parts.append('<th class="hole-header totals front-back-divider">OUT</th>')
    for hole in range(10, 19):
        html_parts.append(f'<th class="hole-header">{hole}</th>')
    html_parts.append('<th class="hole-header totals">IN</th>')
    html_parts.append('<th class="hole-header totals">TOTAL</th>')
    html_parts.append('</tr>')
    
    # Row 2: PAR values
    html_parts.append('<tr>')
    html_parts.append('<th class="player-label par-header">PAR</th>')
    for hole in range(1, 10):
        par_val = int(first_player_data[first_player_data['Hole'] == hole]['PAR'].iloc[0])
        html_parts.append(f'<th class="par-header">{par_val}</th>')
    html_parts.append(f'<th class="totals front-back-divider par-header">{front_par_total}</th>')
    for hole in range(10, 19):
        par_val = int(first_player_data[first_player_data['Hole'] == hole]['PAR'].iloc[0])
        html_parts.append(f'<th class="par-header">{par_val}</th>')
    html_parts.append(f'<th class="totals par-header">{back_par_total}</th>')
    html_parts.append(f'<th class="totals par-header">{total_par}</th>')
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
    
    # Row 1: Hole numbers
    html_parts.append('<tr>')
    html_parts.append('<th class="player-label hole-header">Player</th>')
    for hole in range(1, 10):
        html_parts.append(f'<th class="hole-header">{hole}</th>')
    html_parts.append('<th class="hole-header totals front-back-divider">OUT</th>')
    for hole in range(10, 19):
        html_parts.append(f'<th class="hole-header">{hole}</th>')
    html_parts.append('<th class="hole-header totals">IN</th>')
    html_parts.append('<th class="hole-header totals">TOTAL</th>')
    html_parts.append('</tr>')
    
    # Row 2: PAR values (same for both sections)
    html_parts.append('<tr>')
    html_parts.append('<th class="player-label par-header">PAR</th>')
    for hole in range(1, 10):
        par_val = int(first_player_data[first_player_data['Hole'] == hole]['PAR'].iloc[0])
        html_parts.append(f'<th class="par-header">{par_val}</th>')
    html_parts.append(f'<th class="totals front-back-divider par-header">{front_par_total}</th>')
    for hole in range(10, 19):
        par_val = int(first_player_data[first_player_data['Hole'] == hole]['PAR'].iloc[0])
        html_parts.append(f'<th class="par-header">{par_val}</th>')
    html_parts.append(f'<th class="totals par-header">{back_par_total}</th>')
    html_parts.append(f'<th class="totals par-header">{total_par}</th>')
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

def generate_single_round_html_mobile(player_code, teg_num, round_num, title=None, subheader=None):
    """Generate mobile HTML for single player, single round scorecard (holes as rows)"""
    
    # Load data using existing function
    df = get_scorecard_data(teg_num, round_num, player_code)
    
    if len(df) != 18:
        return f"<div class='scorecard-container-mobile'><p>Error: Expected 18 holes, found {len(df)} holes.</p></div>"
    
    # Generate default title if not provided
    if title is None:
        player_name = df['Player'].iloc[0]
        title = f"{player_name} | TEG {teg_num}, Round {round_num}"
    
    # Generate default subheader if not provided
    if subheader is None:
        metadata = get_teg_metadata(teg_num, round_num)
        course = metadata.get('Course')
        date_str = metadata.get('Date')
        formatted_date = format_date_for_scorecard(date_str, output_format='%d %B %Y')
        
        if course and formatted_date:
            subheader = f"{course} | {formatted_date}"
        elif course:
            subheader = course
        elif formatted_date:
            subheader = formatted_date
    
    # Calculate totals (same logic as desktop)
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
    
    html_parts.append('<div class="scorecard-container-mobile layout-mobile-single-round">')

    # Header with title and optional subheader
    html_parts.append('<div class="scorecard-header">')
    html_parts.append(f'<p class="scorecard-title">{title}</p>')
    if subheader:
        html_parts.append(f'<p class="scorecard-subheader">{subheader}</p>')
    html_parts.append('</div>')

    # Gross Scores Section
    html_parts.append('<div class="section-header-mobile">Gross Scores</div>')
    html_parts.append('<table class="scorecard-table-mobile">')
    
    # Header section
    html_parts.append('<thead>')
    
    # Header row: Hole | PAR | Score
    html_parts.append('<tr>')
    html_parts.append('<th class="hole-label-mobile">Hole</th>')
    html_parts.append('<th class="par-header-mobile">PAR</th>')
    html_parts.append('<th class="player-header-mobile">Score</th>')
    html_parts.append('</tr>')
    
    html_parts.append('</thead>')
    
    # Body section - one row per hole
    html_parts.append('<tbody>')
    
    # Front 9 holes
    for hole in range(1, 10):
        hole_data = df[df['Hole'] == hole].iloc[0]
        par_val = int(hole_data['PAR'])
        vs_par = int(hole_data['GrossVP'])
        score = int(hole_data['Sc'])
        
        html_parts.append('<tr>')
        html_parts.append(f'<td class="hole-label-mobile">{hole}</td>')
        html_parts.append(f'<td class="par-header-mobile">{par_val}</td>')
        html_parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')
        html_parts.append('</tr>')
    
    # OUT row
    html_parts.append('<tr>')
    html_parts.append('<td class="hole-label-mobile"><strong>OUT</strong></td>')
    html_parts.append(f'<td class="totals-mobile">{front_totals["PAR"]}</td>')
    html_parts.append(f'<td class="totals-mobile">{front_totals["Sc"]}</td>')
    html_parts.append('</tr>')
    
    # Back 9 holes
    for hole in range(10, 19):
        hole_data = df[df['Hole'] == hole].iloc[0]
        par_val = int(hole_data['PAR'])
        vs_par = int(hole_data['GrossVP'])
        score = int(hole_data['Sc'])
        
        html_parts.append('<tr>')
        html_parts.append(f'<td class="hole-label-mobile">{hole}</td>')
        html_parts.append(f'<td class="par-header-mobile">{par_val}</td>')
        html_parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')
        html_parts.append('</tr>')
    
    # IN row
    html_parts.append('<tr>')
    html_parts.append('<td class="hole-label-mobile"><strong>IN</strong></td>')
    html_parts.append(f'<td class="totals-mobile">{back_totals["PAR"]}</td>')
    html_parts.append(f'<td class="totals-mobile">{back_totals["Sc"]}</td>')
    html_parts.append('</tr>')
    
    # TOTAL row
    html_parts.append('<tr>')
    html_parts.append('<td class="hole-label-mobile"><strong>TOTAL</strong></td>')
    html_parts.append(f'<td class="totals-mobile">{total_totals["PAR"]}</td>')
    html_parts.append(f'<td class="totals-mobile">{total_totals["Sc"]}</td>')
    html_parts.append('</tr>')
    
    html_parts.append('</tbody>')
    html_parts.append('</table>')
    
    # Stableford Section
    html_parts.append('<div class="section-header-mobile">Stableford Points</div>')
    html_parts.append('<table class="scorecard-table-mobile">')
    
    # Header
    html_parts.append('<thead>')
    html_parts.append('<tr>')
    html_parts.append('<th class="hole-label-mobile">Hole</th>')
    html_parts.append('<th class="par-header-mobile">PAR</th>')
    html_parts.append('<th class="player-header-mobile">Points</th>')
    html_parts.append('</tr>')
    html_parts.append('</thead>')
    
    # Body - Stableford scores
    html_parts.append('<tbody>')
    
    # Front 9 holes
    for hole in range(1, 10):
        hole_data = df[df['Hole'] == hole].iloc[0]
        par_val = int(hole_data['PAR'])
        stableford = int(hole_data['Stableford'])
        
        html_parts.append('<tr>')
        html_parts.append(f'<td class="hole-label-mobile">{hole}</td>')
        html_parts.append(f'<td class="par-header-mobile">{par_val}</td>')
        html_parts.append(f'<td class="score-cell" data-stableford="{stableford}"><span>{stableford}</span></td>')
        html_parts.append('</tr>')
    
    # OUT row
    html_parts.append('<tr>')
    html_parts.append('<td class="hole-label-mobile"><strong>OUT</strong></td>')
    html_parts.append(f'<td class="totals-mobile">{front_totals["PAR"]}</td>')
    html_parts.append(f'<td class="totals-mobile">{front_totals["Stableford"]}</td>')
    html_parts.append('</tr>')
    
    # Back 9 holes
    for hole in range(10, 19):
        hole_data = df[df['Hole'] == hole].iloc[0]
        par_val = int(hole_data['PAR'])
        stableford = int(hole_data['Stableford'])
        
        html_parts.append('<tr>')
        html_parts.append(f'<td class="hole-label-mobile">{hole}</td>')
        html_parts.append(f'<td class="par-header-mobile">{par_val}</td>')
        html_parts.append(f'<td class="score-cell" data-stableford="{stableford}"><span>{stableford}</span></td>')
        html_parts.append('</tr>')
    
    # IN row
    html_parts.append('<tr>')
    html_parts.append('<td class="hole-label-mobile"><strong>IN</strong></td>')
    html_parts.append(f'<td class="totals-mobile">{back_totals["PAR"]}</td>')
    html_parts.append(f'<td class="totals-mobile">{back_totals["Stableford"]}</td>')
    html_parts.append('</tr>')
    
    # TOTAL row
    html_parts.append('<tr>')
    html_parts.append('<td class="hole-label-mobile"><strong>TOTAL</strong></td>')
    html_parts.append(f'<td class="totals-mobile">{total_totals["PAR"]}</td>')
    html_parts.append(f'<td class="totals-mobile">{total_totals["Stableford"]}</td>')
    html_parts.append('</tr>')
    
    html_parts.append('</tbody>')
    html_parts.append('</table>')
    html_parts.append('</div>')
    
    return ''.join(html_parts)

def generate_tournament_html_mobile(player_code, teg_num, title=None, subheader=None):
    """Generate mobile HTML for single player tournament view (holes as rows, rounds as columns)"""
    
    # Load data using existing function
    player_data = get_scorecard_data(teg_num, player_code=player_code)
    
    if player_data.empty:
        return f"<div class='scorecard-container-mobile'><p>Error: No data found for player {player_code} in TEG {teg_num}.</p></div>"
    
    # Generate default title if not provided
    if title is None:
        player_name = player_data['Player'].iloc[0]
        title = f"{player_name} | TEG {teg_num}"
    
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
    
    rounds = sorted(player_data['Round'].unique())
    
    html_parts = []
    html_parts.append('<div class="scorecard-container-mobile layout-mobile-multi-round">')

    # Header with title and optional subheader
    html_parts.append('<div class="scorecard-header">')
    html_parts.append(f'<p class="scorecard-title">{title}</p>')
    if subheader:
        html_parts.append(f'<p class="scorecard-subheader">{subheader}</p>')
    html_parts.append('</div>')
    
    # Gross Scores Section
    html_parts.append('<div class="section-header-mobile">Gross Scores</div>')
    html_parts.append('<table class="scorecard-table-mobile">')
    
    # Header
    html_parts.append('<thead>')
    html_parts.append('<tr>')
    html_parts.append('<th class="hole-label-mobile">Hole</th>')
    html_parts.append('<th class="par-header-mobile">PAR</th>')
    for round_num in rounds:
        html_parts.append(f'<th class="round-header-mobile">{round_num}</th>')
    html_parts.append('</tr>')
    html_parts.append('</thead>')
    
    # Body - one row per hole
    html_parts.append('<tbody>')
    
    # Get PAR data (same for all rounds)
    par_data = player_data[player_data['Round'] == rounds[0]].sort_values('Hole')
    
    # Front 9 holes
    for hole in range(1, 10):
        par_val = int(par_data[par_data['Hole'] == hole]['PAR'].iloc[0])
        
        html_parts.append('<tr>')
        html_parts.append(f'<td class="hole-label-mobile">{hole}</td>')
        html_parts.append(f'<td class="par-header-mobile">{par_val}</td>')
        
        for round_num in rounds:
            round_data = player_data[player_data['Round'] == round_num]
            hole_data = round_data[round_data['Hole'] == hole]
            if not hole_data.empty:
                vs_par = int(hole_data['GrossVP'].iloc[0])
                score = int(hole_data['Sc'].iloc[0])
                html_parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')
            else:
                html_parts.append('<td>-</td>')
        
        html_parts.append('</tr>')
    
    # OUT row
    html_parts.append('<tr>')
    html_parts.append('<td class="hole-label-mobile"><strong>OUT</strong></td>')
    front_par_total = int(par_data[par_data['Hole'] <= 9]['PAR'].sum())
    html_parts.append(f'<td class="totals-mobile">{front_par_total}</td>')
    
    for round_num in rounds:
        round_data = player_data[player_data['Round'] == round_num]
        front_score_total = int(round_data[round_data['Hole'] <= 9]['Sc'].sum())
        html_parts.append(f'<td class="totals-mobile">{front_score_total}</td>')
    
    html_parts.append('</tr>')
    
    # Back 9 holes
    for hole in range(10, 19):
        par_val = int(par_data[par_data['Hole'] == hole]['PAR'].iloc[0])
        
        html_parts.append('<tr>')
        html_parts.append(f'<td class="hole-label-mobile">{hole}</td>')
        html_parts.append(f'<td class="par-header-mobile">{par_val}</td>')
        
        for round_num in rounds:
            round_data = player_data[player_data['Round'] == round_num]
            hole_data = round_data[round_data['Hole'] == hole]
            if not hole_data.empty:
                vs_par = int(hole_data['GrossVP'].iloc[0])
                score = int(hole_data['Sc'].iloc[0])
                html_parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')
            else:
                html_parts.append('<td>-</td>')
        
        html_parts.append('</tr>')
    
    # IN row
    html_parts.append('<tr>')
    html_parts.append('<td class="hole-label-mobile"><strong>IN</strong></td>')
    back_par_total = int(par_data[par_data['Hole'] > 9]['PAR'].sum())
    html_parts.append(f'<td class="totals-mobile">{back_par_total}</td>')
    
    for round_num in rounds:
        round_data = player_data[player_data['Round'] == round_num]
        back_score_total = int(round_data[round_data['Hole'] > 9]['Sc'].sum())
        html_parts.append(f'<td class="totals-mobile">{back_score_total}</td>')
    
    html_parts.append('</tr>')
    
    # TOTAL row
    html_parts.append('<tr>')
    html_parts.append('<td class="hole-label-mobile"><strong>TOTAL</strong></td>')
    total_par = int(par_data['PAR'].sum())
    html_parts.append(f'<td class="totals-mobile">{total_par}</td>')
    
    for round_num in rounds:
        round_data = player_data[player_data['Round'] == round_num]
        total_score = int(round_data['Sc'].sum())
        html_parts.append(f'<td class="totals-mobile">{total_score}</td>')
    
    html_parts.append('</tr>')
    
    html_parts.append('</tbody>')
    html_parts.append('</table>')
    
    # Stableford Section
    html_parts.append('<div class="section-header-mobile">Stableford Points</div>')
    html_parts.append('<table class="scorecard-table-mobile">')
    
    # Header
    html_parts.append('<thead>')
    html_parts.append('<tr>')
    html_parts.append('<th class="hole-label-mobile">Hole</th>')
    html_parts.append('<th class="par-header-mobile">PAR</th>')
    for round_num in rounds:
        html_parts.append(f'<th class="round-header-mobile">{round_num}</th>')
    html_parts.append('</tr>')
    html_parts.append('</thead>')
    
    # Body - Stableford scores  
    html_parts.append('<tbody>')
    
    # Front 9 holes
    for hole in range(1, 10):
        par_val = int(par_data[par_data['Hole'] == hole]['PAR'].iloc[0])
        
        html_parts.append('<tr>')
        html_parts.append(f'<td class="hole-label-mobile">{hole}</td>')
        html_parts.append(f'<td class="par-header-mobile">{par_val}</td>')
        
        for round_num in rounds:
            round_data = player_data[player_data['Round'] == round_num]
            hole_data = round_data[round_data['Hole'] == hole]
            if not hole_data.empty:
                stableford = int(hole_data['Stableford'].iloc[0])
                html_parts.append(f'<td class="score-cell" data-stableford="{stableford}"><span>{stableford}</span></td>')
            else:
                html_parts.append('<td>-</td>')
        
        html_parts.append('</tr>')
    
    # OUT row
    html_parts.append('<tr>')
    html_parts.append('<td class="hole-label-mobile"><strong>OUT</strong></td>')
    html_parts.append(f'<td class="totals-mobile">{front_par_total}</td>')
    
    for round_num in rounds:
        round_data = player_data[player_data['Round'] == round_num]
        front_stableford_total = int(round_data[round_data['Hole'] <= 9]['Stableford'].sum())
        html_parts.append(f'<td class="totals-mobile">{front_stableford_total}</td>')
    
    html_parts.append('</tr>')
    
    # Back 9 holes
    for hole in range(10, 19):
        par_val = int(par_data[par_data['Hole'] == hole]['PAR'].iloc[0])
        
        html_parts.append('<tr>')
        html_parts.append(f'<td class="hole-label-mobile">{hole}</td>')
        html_parts.append(f'<td class="par-header-mobile">{par_val}</td>')
        
        for round_num in rounds:
            round_data = player_data[player_data['Round'] == round_num]
            hole_data = round_data[round_data['Hole'] == hole]
            if not hole_data.empty:
                stableford = int(hole_data['Stableford'].iloc[0])
                html_parts.append(f'<td class="score-cell" data-stableford="{stableford}"><span>{stableford}</span></td>')
            else:
                html_parts.append('<td>-</td>')
        
        html_parts.append('</tr>')
    
    # IN row
    html_parts.append('<tr>')
    html_parts.append('<td class="hole-label-mobile"><strong>IN</strong></td>')
    html_parts.append(f'<td class="totals-mobile">{back_par_total}</td>')
    
    for round_num in rounds:
        round_data = player_data[player_data['Round'] == round_num]
        back_stableford_total = int(round_data[round_data['Hole'] > 9]['Stableford'].sum())
        html_parts.append(f'<td class="totals-mobile">{back_stableford_total}</td>')
    
    html_parts.append('</tr>')
    
    # TOTAL row
    html_parts.append('<tr>')
    html_parts.append('<td class="hole-label-mobile"><strong>TOTAL</strong></td>')
    html_parts.append(f'<td class="totals-mobile">{total_par}</td>')
    
    for round_num in rounds:
        round_data = player_data[player_data['Round'] == round_num]
        total_stableford = int(round_data['Stableford'].sum())
        html_parts.append(f'<td class="totals-mobile">{total_stableford}</td>')
    
    html_parts.append('</tr>')
    
    html_parts.append('</tbody>')
    html_parts.append('</table>')
    html_parts.append('</div>')
    
    return ''.join(html_parts)

def generate_round_comparison_html_mobile(teg_num, round_num, title=None, subheader=None):
    """Generate mobile HTML for multi-player round comparison (holes as rows, players as columns)"""
    
    # Load data using existing function
    round_data = get_scorecard_data(teg_num, round_num)
    
    if round_data.empty:
        return f"<div class='scorecard-container-mobile'><p>Error: No data found for TEG {teg_num} Round {round_num}.</p></div>"
    
    # Generate default title if not provided
    if title is None:
        title = f"TEG {teg_num}, Round {round_num}"
    
    # Generate default subheader if not provided
    if subheader is None:
        metadata = get_teg_metadata(teg_num, round_num)
        course = metadata.get('Course')
        date_str = metadata.get('Date')
        formatted_date = format_date_for_scorecard(date_str, output_format='%d %B %Y')
        
        if course and formatted_date:
            subheader = f"{course} | {formatted_date}"
        elif course:
            subheader = course
        elif formatted_date:
            subheader = formatted_date
    
    players = round_data['Pl'].unique()
    
    # Sort players by total score (ascending)
    player_totals = []
    for player in players:
        player_data = round_data[round_data['Pl'] == player]
        total_score = int(player_data['Sc'].sum())
        player_totals.append((total_score, player))
    
    player_totals.sort(key=lambda x: x[0])  # Sort by score
    sorted_players = [player for _, player in player_totals]
    
    # Calculate PAR totals (using first player's data since PAR is same for all)
    first_player_data = round_data[round_data['Pl'] == players[0]].sort_values('Hole')
    front_par_total = int(first_player_data[first_player_data['Hole'] <= 9]['PAR'].sum())
    back_par_total = int(first_player_data[first_player_data['Hole'] > 9]['PAR'].sum())
    total_par = int(first_player_data['PAR'].sum())
    
    html_parts = []
    html_parts.append('<div class="scorecard-container-mobile layout-mobile-multi-player">')

    # Header with title and optional subheader
    html_parts.append('<div class="scorecard-header">')
    html_parts.append(f'<p class="scorecard-title">{title}</p>')
    if subheader:
        html_parts.append(f'<p class="scorecard-subheader">{subheader}</p>')
    html_parts.append('</div>')
    
    # Gross Scores Section
    html_parts.append('<div class="section-header-mobile">Gross Scores</div>')
    html_parts.append('<table class="scorecard-table-mobile">')
    
    # Header
    html_parts.append('<thead>')
    html_parts.append('<tr>')
    html_parts.append('<th class="hole-label-mobile">Hole</th>')
    html_parts.append('<th class="par-header-mobile">PAR</th>')
    for player_code in sorted_players:
        html_parts.append(f'<th class="player-header-mobile">{player_code}</th>')
    html_parts.append('</tr>')
    html_parts.append('</thead>')
    
    # Body - one row per hole
    html_parts.append('<tbody>')
    
    # Front 9 holes
    for hole in range(1, 10):
        par_val = int(first_player_data[first_player_data['Hole'] == hole]['PAR'].iloc[0])
        
        html_parts.append('<tr>')
        html_parts.append(f'<td class="hole-label-mobile">{hole}</td>')
        html_parts.append(f'<td class="par-header-mobile">{par_val}</td>')
        
        for player_code in sorted_players:
            player_data = round_data[round_data['Pl'] == player_code]
            hole_data = player_data[player_data['Hole'] == hole]
            if not hole_data.empty:
                vs_par = int(hole_data['GrossVP'].iloc[0])
                score = int(hole_data['Sc'].iloc[0])
                html_parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')
            else:
                html_parts.append('<td>-</td>')
        
        html_parts.append('</tr>')
    
    # OUT row
    html_parts.append('<tr>')
    html_parts.append('<td class="hole-label-mobile"><strong>OUT</strong></td>')
    html_parts.append(f'<td class="totals-mobile">{front_par_total}</td>')
    
    for player_code in sorted_players:
        player_data = round_data[round_data['Pl'] == player_code]
        front_total = int(player_data[player_data['Hole'] <= 9]['Sc'].sum())
        html_parts.append(f'<td class="totals-mobile">{front_total}</td>')
    
    html_parts.append('</tr>')
    
    # Back 9 holes
    for hole in range(10, 19):
        par_val = int(first_player_data[first_player_data['Hole'] == hole]['PAR'].iloc[0])
        
        html_parts.append('<tr>')
        html_parts.append(f'<td class="hole-label-mobile">{hole}</td>')
        html_parts.append(f'<td class="par-header-mobile">{par_val}</td>')
        
        for player_code in sorted_players:
            player_data = round_data[round_data['Pl'] == player_code]
            hole_data = player_data[player_data['Hole'] == hole]
            if not hole_data.empty:
                vs_par = int(hole_data['GrossVP'].iloc[0])
                score = int(hole_data['Sc'].iloc[0])
                html_parts.append(f'<td class="score-cell" data-vs-par="{vs_par}"><span>{score}</span></td>')
            else:
                html_parts.append('<td>-</td>')
        
        html_parts.append('</tr>')
    
    # IN row
    html_parts.append('<tr>')
    html_parts.append('<td class="hole-label-mobile"><strong>IN</strong></td>')
    html_parts.append(f'<td class="totals-mobile">{back_par_total}</td>')
    
    for player_code in sorted_players:
        player_data = round_data[round_data['Pl'] == player_code]
        back_total = int(player_data[player_data['Hole'] > 9]['Sc'].sum())
        html_parts.append(f'<td class="totals-mobile">{back_total}</td>')
    
    html_parts.append('</tr>')
    
    # TOTAL row
    html_parts.append('<tr>')
    html_parts.append('<td class="hole-label-mobile"><strong>TOTAL</strong></td>')
    html_parts.append(f'<td class="totals-mobile">{total_par}</td>')
    
    for player_code in sorted_players:
        player_data = round_data[round_data['Pl'] == player_code]
        total_score = int(player_data['Sc'].sum())
        html_parts.append(f'<td class="totals-mobile">{total_score}</td>')
    
    html_parts.append('</tr>')
    
    html_parts.append('</tbody>')
    html_parts.append('</table>')
    
    # Stableford Section
    html_parts.append('<div class="section-header-mobile">Stableford Points</div>')
    html_parts.append('<table class="scorecard-table-mobile">')
    
    # Header
    html_parts.append('<thead>')
    html_parts.append('<tr>')
    html_parts.append('<th class="hole-label-mobile">Hole</th>')
    html_parts.append('<th class="par-header-mobile">PAR</th>')
    for player_code in sorted_players:
        html_parts.append(f'<th class="player-header-mobile">{player_code}</th>')
    html_parts.append('</tr>')
    html_parts.append('</thead>')
    
    # Body - Stableford scores  
    html_parts.append('<tbody>')
    
    # Front 9 holes
    for hole in range(1, 10):
        par_val = int(first_player_data[first_player_data['Hole'] == hole]['PAR'].iloc[0])
        
        html_parts.append('<tr>')
        html_parts.append(f'<td class="hole-label-mobile">{hole}</td>')
        html_parts.append(f'<td class="par-header-mobile">{par_val}</td>')
        
        for player_code in sorted_players:
            player_data = round_data[round_data['Pl'] == player_code]
            hole_data = player_data[player_data['Hole'] == hole]
            if not hole_data.empty:
                stableford = int(hole_data['Stableford'].iloc[0])
                html_parts.append(f'<td class="score-cell" data-stableford="{stableford}"><span>{stableford}</span></td>')
            else:
                html_parts.append('<td>-</td>')
        
        html_parts.append('</tr>')
    
    # OUT row
    html_parts.append('<tr>')
    html_parts.append('<td class="hole-label-mobile"><strong>OUT</strong></td>')
    html_parts.append(f'<td class="totals-mobile">{front_par_total}</td>')
    
    for player_code in sorted_players:
        player_data = round_data[round_data['Pl'] == player_code]
        front_stableford_total = int(player_data[player_data['Hole'] <= 9]['Stableford'].sum())
        html_parts.append(f'<td class="totals-mobile">{front_stableford_total}</td>')
    
    html_parts.append('</tr>')
    
    # Back 9 holes
    for hole in range(10, 19):
        par_val = int(first_player_data[first_player_data['Hole'] == hole]['PAR'].iloc[0])
        
        html_parts.append('<tr>')
        html_parts.append(f'<td class="hole-label-mobile">{hole}</td>')
        html_parts.append(f'<td class="par-header-mobile">{par_val}</td>')
        
        for player_code in sorted_players:
            player_data = round_data[round_data['Pl'] == player_code]
            hole_data = player_data[player_data['Hole'] == hole]
            if not hole_data.empty:
                stableford = int(hole_data['Stableford'].iloc[0])
                html_parts.append(f'<td class="score-cell" data-stableford="{stableford}"><span>{stableford}</span></td>')
            else:
                html_parts.append('<td>-</td>')
        
        html_parts.append('</tr>')
    
    # IN row
    html_parts.append('<tr>')
    html_parts.append('<td class="hole-label-mobile"><strong>IN</strong></td>')
    html_parts.append(f'<td class="totals-mobile">{back_par_total}</td>')
    
    for player_code in sorted_players:
        player_data = round_data[round_data['Pl'] == player_code]
        back_stableford_total = int(player_data[player_data['Hole'] > 9]['Stableford'].sum())
        html_parts.append(f'<td class="totals-mobile">{back_stableford_total}</td>')
    
    html_parts.append('</tr>')
    
    # TOTAL row
    html_parts.append('<tr>')
    html_parts.append('<td class="hole-label-mobile"><strong>TOTAL</strong></td>')
    html_parts.append(f'<td class="totals-mobile">{total_par}</td>')
    
    for player_code in sorted_players:
        player_data = round_data[round_data['Pl'] == player_code]
        total_stableford = int(player_data['Stableford'].sum())
        html_parts.append(f'<td class="totals-mobile">{total_stableford}</td>')
    
    html_parts.append('</tr>')
    
    html_parts.append('</tbody>')
    html_parts.append('</table>')
    html_parts.append('</div>')
    
    return ''.join(html_parts)