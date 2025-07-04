"""
Golf Scorecard Generation Utilities
Converts pandas DataFrames to beautiful HTML golf scorecards
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from utils import get_scorecard_data, get_teg_metadata, format_date_for_scorecard

def load_scorecard_css():
    """Load the scorecard CSS file and inject it into Streamlit"""
    css_file = Path(__file__).parent / "scorecard_styles.css"
    
    try:
        with open(css_file, 'r') as f:
            css_content = f.read()
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        # Fallback: inline CSS if file not found
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
        
        .scorecard-container {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            max-width: 1400px;
            margin: 0 auto 30px auto;
            font-family: 'Roboto', Arial, sans-serif;
        }
        
        .scorecard-header {
            text-align: center;
            margin-bottom: 20px;
        }
        
        .scorecard-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 2px;
            font-size: 14px;
            margin-bottom: 20px;
        }
        
        .scorecard-table th,
        .scorecard-table td {
            padding: 6px;
            text-align: center;
            border: none;
            font-weight: bold;
            min-width: 32px;
            height: 32px;
            vertical-align: middle;
            position: relative;
            background-color: #f8f9fa;
        }
        
        .score-cell {
            position: relative;
            background-color: white;
        }
        
        .score-cell::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 28px;
            height: 28px;
            border-radius: 4px;
            z-index: 1;
        }
        
        .score-cell span {
            position: relative;
            z-index: 2;
        }
        
        /* Score colors */
        .score-cell[data-vs-par="-2"]::before { background-color: #FFD700; }
        .score-cell[data-vs-par="-1"]::before { background-color: #90EE90; }
        .score-cell[data-vs-par="0"]::before { background-color: #E6F3FF; }
        .score-cell[data-vs-par="1"]::before { background-color: #FFE4B5; }
        .score-cell[data-vs-par="2"]::before { background-color: #FFA07A; }
        .score-cell[data-vs-par="3"]::before,
        .score-cell[data-vs-par="4"]::before,
        .score-cell[data-vs-par="5"]::before,
        .score-cell[data-vs-par="6"]::before,
        .score-cell[data-vs-par="7"]::before,
        .score-cell[data-vs-par="8"]::before,
        .score-cell[data-vs-par="9"]::before,
        .score-cell[data-vs-par="10"]::before { background-color: #8B0000; }
        
        /* Stableford colors */
        .score-cell[data-stableford="0"]::before { background-color: #ffffff; border: 1px solid #ddd; }
        .score-cell[data-stableford="1"]::before { background-color: #e3f2fd; }
        .score-cell[data-stableford="2"]::before { background-color: #bbdefb; }
        .score-cell[data-stableford="3"]::before { background-color: #90caf9; }
        .score-cell[data-stableford="4"]::before { background-color: #64b5f6; }
        .score-cell[data-stableford="5"]::before,
        .score-cell[data-stableford="6"]::before,
        .score-cell[data-stableford="7"]::before,
        .score-cell[data-stableford="8"]::before { background-color: #1976d2; }
        
        /* White text for dark backgrounds */
        .score-cell[data-vs-par="3"] span,
        .score-cell[data-vs-par="4"] span,
        .score-cell[data-vs-par="5"] span,
        .score-cell[data-vs-par="6"] span,
        .score-cell[data-vs-par="7"] span,
        .score-cell[data-vs-par="8"] span,
        .score-cell[data-vs-par="9"] span,
        .score-cell[data-vs-par="10"] span,
        .score-cell[data-stableford="5"] span,
        .score-cell[data-stableford="6"] span,
        .score-cell[data-stableford="7"] span,
        .score-cell[data-stableford="8"] span {
            color: white;
        }
        
        /* Layout styling */
        .layout-single-round .label-column {
            text-align: left;
            min-width: 80px;
            padding-left: 8px;
        }
        
        .layout-single-round .hole-header {
            border-bottom: 2px solid #333;
        }
        
        .layout-single-round .front-back-divider {
            border-right: 3px solid #333;
        }
        
        .totals {
            font-weight: bold;
            background-color: #f8f9fa;
        }
        
        @media (max-width: 768px) {
            .scorecard-table { font-size: 12px; }
            .scorecard-table th, .scorecard-table td { 
                padding: 4px; 
                min-width: 28px; 
                height: 28px; 
            }
            .layout-single-round .label-column {
                min-width: 60px;
                font-size: 11px;
            }
        }
        </style>
        """, unsafe_allow_html=True)

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
    
    
    # Debug - remove this after testing
    st.write("DEBUG metadata:", get_teg_metadata(teg_num))
    
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