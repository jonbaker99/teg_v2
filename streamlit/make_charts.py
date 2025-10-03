import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

def add_round_annotations(fig, max_round):
    for round_num in range(1, max_round + 1):
        x_pos = (round_num - 1) * 18
        fig.add_vline(x=x_pos, line=dict(color='lightgrey', width=1))
        fig.add_annotation(x=x_pos + 9, y=0.08, text=f'R{round_num}', 
                           showarrow=False, yref='paper', yshift=-40)

def format_value(value, chart_type):
    if chart_type == 'stableford':
        return f"{value:.0f}"
    elif chart_type == 'gross':
        if value > 0:
            return f"+{value:.0f}"
        elif value < 0:
            return f"{value:.0f}"
        else:
            return "="
    elif chart_type == 'ranking':
        # Format ranking as ordinal (1st, 2nd, 3rd, etc.)
        rank = int(value)
        if rank == 1:
            return "1st"
        elif rank == 2:
            return "2nd"
        elif rank == 3:
            return "3rd"
        else:
            return f"{rank}th"
    else:
        return f"{value:.0f}"  # Default formatting

def create_cumulative_graph(df, chosen_teg, y_series, title, y_calculation=None, y_axis_label=None, chart_type='default'):
    # Filter data based on the chosen TEG
    teg_data = df[df['TEG'] == chosen_teg].sort_values(['Round', 'Hole'])
    teg_data['x_value'] = (teg_data['Round'] - 1) * 18 + teg_data['Hole']  # Create x-axis value based on rounds and holes

    max_round = teg_data['Round'].max()
    x_axis_max = max_round * 18

    fig = go.Figure()

    # Generate color palette for players
    colors = px.colors.qualitative.Plotly[:len(teg_data['Pl'].unique())]
    color_map = dict(zip(teg_data['Pl'].unique(), colors))

    traces = []
    for player in teg_data['Pl'].unique():
        player_data = teg_data[teg_data['Pl'] == player]
        
        # Apply custom y-calculation if provided
        if y_calculation:
            y_values = y_calculation(player_data)
        else:
            y_values = player_data[y_series]
        
        traces.append(go.Scatter(
            x=player_data['x_value'],
            y=y_values,
            mode='lines',
            name=player,
            line=dict(width=2),
        ))
        
        # Add end label
        last_x = player_data['x_value'].iloc[-1]
        last_y = y_values.iloc[-1]
        formatted_value = format_value(last_y, chart_type)
        fig.add_annotation(
            x=last_x,
            y=last_y,
            text=f"{player}: {formatted_value}",
            showarrow=False,
            xanchor='left',
            yanchor='middle',
            xshift=5,
            font=dict(
                size=10,  # Increased from 8 to 10
                color=color_map[player]
            )
        )

    fig.add_traces(traces)

    fig.update_layout(
        #title=title,
        #xaxis_title='Rounds',
        yaxis_title=y_axis_label if y_axis_label else f'Cumulative {y_series}',
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, traceorder='normal', itemsizing='constant'),
        margin=dict(r=100, t=0, b=10, l=0),
        font=dict(family="monospace")
    )

    add_round_annotations(fig, max_round)

    fig.update_xaxes(tickvals=[], range=[0, x_axis_max])

    # For ranking charts, reverse the y-axis so 1st place is at the top
    if chart_type == 'ranking':
        fig.update_yaxes(autorange='reversed')

    for trace in fig.data:
        player = trace.name
        color = color_map[player]
        fig.update_traces(selector=dict(name=player), line=dict(color=color))

    #fig.update_layout(modebar_remove=['zoom', 'pan'])
    fig.layout.xaxis.fixedrange = True
    fig.layout.yaxis.fixedrange = True

    return fig

# Define custom calculations
def adjusted_stableford(data):
    return data['Stableford Cum TEG'] - (2 * data['TEG Count'])

def adjusted_grossvp(data):
    return data['GrossVP Cum TEG'] - data['TEG Count']



def create_round_graph(df, chosen_teg, chosen_round, y_series, title, y_calculation=None, y_axis_label=None, chart_type='default'):
    # Filter data based on the chosen TEG
    rd_data = df[(df['TEG'] == chosen_teg) & (df['Round'] == chosen_round)].sort_values(['Hole'])
    rd_data['x_value'] = rd_data['Hole']  # Create x-axis value based on rounds and holes

    #max_round = teg_data['Round'].max()
    x_axis_max = 18

    fig = go.Figure()

    # Generate color palette for players
    colors = px.colors.qualitative.Plotly[:len(rd_data['Pl'].unique())]
    color_map = dict(zip(rd_data['Pl'].unique(), colors))

    traces = []
    for player in rd_data['Pl'].unique():
        player_data = rd_data[rd_data['Pl'] == player]
        
        # Apply custom y-calculation if provided
        if y_calculation:
            y_values = y_calculation(player_data)
        else:
            y_values = player_data[y_series]
        
        traces.append(go.Scatter(
            x=player_data['x_value'],
            y=y_values,
            mode='lines',
            name=player,
            line=dict(width=2),
        ))
        
        # Add end label
        last_x = player_data['x_value'].iloc[-1]
        last_y = y_values.iloc[-1]
        formatted_value = format_value(last_y, chart_type)
        fig.add_annotation(
            x=last_x,
            y=last_y,
            text=f"{player}: {formatted_value}",
            showarrow=False,
            xanchor='left',
            yanchor='middle',
            xshift=5,
            font=dict(
                size=10,  # Increased from 8 to 10
                color=color_map[player]
            )
        )

    fig.add_traces(traces)

    fig.update_layout(
        #title=title,
        #xaxis_title='Rounds',
        yaxis_title=y_axis_label if y_axis_label else f'Cumulative {y_series}',
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, traceorder='normal', itemsizing='constant'),
        margin=dict(r=100, t=0, b=10, l=0),
        font=dict(family="monospace")
    )

    # add_round_annotations(fig, max_round)

    fig.update_xaxes(tickvals=[], range=[0, x_axis_max])

    for trace in fig.data:
        player = trace.name
        color = color_map[player]
        fig.update_traces(selector=dict(name=player), line=dict(color=color))

    #fig.update_layout(modebar_remove=['zoom', 'pan'])
    fig.layout.xaxis.fixedrange = True
    fig.layout.yaxis.fixedrange = True

    return fig