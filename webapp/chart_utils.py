"""Chart utilities for the webapp — copied from streamlit/make_charts.py with st import removed."""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px


# Named chart styles. Each is a dict of Plotly layout overrides passed to
# fig.update_layout(**style). Nested keys (xaxis, yaxis, legend, margin) are
# merged with existing layout settings, not replaced.
CHART_STYLES = {
    # Replicates what Streamlit's Plotly theme does to the figure: transparent
    # backgrounds (inherit the white card), a single very-faint horizontal grid,
    # and no axis/zero lines. The raw Plotly default would instead give the
    # lavender plot background + heavy grid we're trying to get rid of.
    "streamlit": {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "xaxis": {
            "showgrid": False,
            "zeroline": False,
            "showline": False,
        },
        "yaxis": {
            "showgrid": True,
            "gridcolor": "rgba(0,0,0,0.06)",
            "gridwidth": 1,
            "zeroline": False,
            "showline": False,
        },
    },

    # Minimal white, faint horizontal grid only. Editorial / printed-programme feel.
    "editorial-a": {
        "paper_bgcolor": "#ffffff",
        "plot_bgcolor": "#ffffff",
        "font": {"family": "'Lora', Georgia, 'Times New Roman', serif", "color": "#222222", "size": 11},
        "xaxis": {
            "showgrid": False,
            "zeroline": False,
            "showline": True,
            "linecolor": "#d8d0c8",
            "linewidth": 1,
            "ticks": "outside",
            "tickcolor": "#d8d0c8",
        },
        "yaxis": {
            "showgrid": True,
            "gridcolor": "#eeece8",
            "gridwidth": 1,
            "zeroline": True,
            "zerolinecolor": "#c8c0b8",
            "zerolinewidth": 1.5,
            "showline": False,
        },
        "legend": {
            "orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0,
            "bgcolor": "rgba(0,0,0,0)", "borderwidth": 0,
        },
        "margin": {"r": 120, "t": 16, "b": 24, "l": 4},
    },

    # Warm cream background, no grid — clean "printed on paper" look.
    "editorial-b": {
        "paper_bgcolor": "#faf7f2",
        "plot_bgcolor": "#faf7f2",
        "font": {"family": "'Lora', Georgia, 'Times New Roman', serif", "color": "#2d2926", "size": 11},
        "xaxis": {
            "showgrid": False,
            "zeroline": False,
            "showline": True,
            "linecolor": "#c4b8a8",
            "linewidth": 1,
            "ticks": "outside",
            "tickcolor": "#c4b8a8",
        },
        "yaxis": {
            "showgrid": False,
            "zeroline": True,
            "zerolinecolor": "#c4b8a8",
            "zerolinewidth": 1.5,
            "showline": False,
            "ticks": "outside",
            "tickcolor": "#c4b8a8",
        },
        "legend": {
            "orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0,
            "bgcolor": "rgba(0,0,0,0)", "borderwidth": 0,
        },
        "margin": {"r": 120, "t": 16, "b": 24, "l": 4},
    },

    # Dark background — sports analytics / broadcast dashboard look.
    "dashboard-a": {
        "paper_bgcolor": "#0f1117",
        "plot_bgcolor": "#0f1117",
        "font": {"family": "'Roboto Mono', 'Courier New', monospace", "color": "#e2e8f0", "size": 11},
        "xaxis": {
            "showgrid": True,
            "gridcolor": "#1e2533",
            "gridwidth": 1,
            "zeroline": False,
            "showline": True,
            "linecolor": "#2d3748",
            "linewidth": 1,
            "tickcolor": "#4a5568",
        },
        "yaxis": {
            "showgrid": True,
            "gridcolor": "#1e2533",
            "gridwidth": 1,
            "zeroline": True,
            "zerolinecolor": "#4a5568",
            "zerolinewidth": 1,
            "showline": False,
            "tickcolor": "#4a5568",
        },
        "legend": {
            "orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0,
            "bgcolor": "rgba(0,0,0,0)", "borderwidth": 0,
            "font": {"color": "#e2e8f0"},
        },
        "margin": {"r": 120, "t": 16, "b": 24, "l": 4},
    },

    # Light grey surround, white plot area, strong zero line — clean modern data-viz.
    "dashboard-b": {
        "paper_bgcolor": "#f0f4f8",
        "plot_bgcolor": "#ffffff",
        "font": {"family": "'Inter', 'Roboto', 'Helvetica Neue', sans-serif", "color": "#1a202c", "size": 11},
        "xaxis": {
            "showgrid": False,
            "zeroline": False,
            "showline": True,
            "linecolor": "#cbd5e0",
            "linewidth": 1,
        },
        "yaxis": {
            "showgrid": True,
            "gridcolor": "#edf2f7",
            "gridwidth": 1,
            "zeroline": True,
            "zerolinecolor": "#718096",
            "zerolinewidth": 2,
            "showline": False,
        },
        "legend": {
            "orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0,
            "bgcolor": "rgba(255,255,255,0.85)", "borderwidth": 1, "bordercolor": "#e2e8f0",
        },
        "margin": {"r": 120, "t": 16, "b": 24, "l": 4},
    },
}

# Human-readable label + description for each style (used on the prototype page).
CHART_STYLE_META = {
    "streamlit":   ("Streamlit Match",    "Current appearance — matches the deployed Streamlit app."),
    "editorial-a": ("Editorial A",        "White background, faint horizontal grid, serif font. Printed-programme feel."),
    "editorial-b": ("Editorial B",        "Warm cream background, no grid, clean tick marks. Ink-on-paper look."),
    "dashboard-a": ("Dashboard A (Dark)", "Dark background, subtle grid, monospace — broadcast/analytics dashboard."),
    "dashboard-b": ("Dashboard B",        "Light grey surround, white plot area, strong zero line — modern data-viz."),
}


def get_chart_style(name: str) -> dict:
    """Return a Plotly layout-override dict for the named style."""
    return CHART_STYLES.get(name, CHART_STYLES["streamlit"])


def add_round_annotations(fig, max_round):
    for round_num in range(1, max_round + 1):
        x_pos = (round_num - 1) * 18
        fig.add_vline(x=x_pos, line=dict(color='rgba(0,0,0,0.08)', width=1))
        fig.add_annotation(x=x_pos + 9, y=0.08, text=f'R{round_num}',
                           showarrow=False, yref='paper', yshift=-40)


def add_series_markers(fig, size=3, border_width=1):
    """Add white-filled circle markers with a coloured outline to every scatter
    trace — mirrors Streamlit's `_add_series_markers` (streamlit/leaderboard.py).
    Must run after line colours have been assigned so the marker outline can
    inherit each trace's line colour."""
    for tr in fig.data:
        if getattr(tr, "type", None) != "scatter":
            continue
        line_col = tr.line.color if tr.line is not None else None
        if tr.mode is None or "markers" not in tr.mode:
            tr.mode = "lines+markers"
        tr.marker = dict(
            symbol="circle",
            size=size,
            color="white",                                  # fill
            line=dict(width=border_width, color=line_col),  # outline
        )
    return fig


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
        return f"{value:.0f}"


def create_cumulative_graph(df, chosen_teg, y_series, title, y_calculation=None, y_axis_label=None, chart_type='default', plotly_theme=None):
    teg_data = df[df['TEG'] == chosen_teg].sort_values(['Round', 'Hole'])
    teg_data['x_value'] = (teg_data['Round'] - 1) * 18 + teg_data['Hole']

    max_round = teg_data['Round'].max()
    x_axis_max = max_round * 18

    fig = go.Figure()

    colors = px.colors.qualitative.Plotly[:len(teg_data['Pl'].unique())]
    color_map = dict(zip(teg_data['Pl'].unique(), colors))

    traces = []
    for player in teg_data['Pl'].unique():
        player_data = teg_data[teg_data['Pl'] == player]

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
            font=dict(size=10, color=color_map[player])
        )

    fig.add_traces(traces)

    fig.update_layout(
        yaxis_title=y_axis_label if y_axis_label else f'Cumulative {y_series}',
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, traceorder='normal', itemsizing='constant'),
        margin=dict(r=100, t=0, b=10, l=0),
        font=dict(family="monospace")
    )

    add_round_annotations(fig, max_round)

    # Small padding each side so lines/markers don't sit flush against the axes
    # (matches Streamlit's leaderboard, which sets range=[0.5, 72.5]).
    fig.update_xaxes(tickvals=[], range=[0.5, x_axis_max + 0.5], showspikes=False)

    if chart_type == 'ranking':
        fig.update_yaxes(autorange='reversed')

    for trace in fig.data:
        player = trace.name
        color = color_map[player]
        fig.update_traces(selector=dict(name=player), line=dict(color=color))

    # Markers (and their legend symbols) — added after colours are assigned.
    add_series_markers(fig)

    fig.layout.xaxis.fixedrange = True
    fig.layout.yaxis.fixedrange = True

    fig.update_layout(**(plotly_theme if plotly_theme is not None else get_chart_style('streamlit')))

    return fig


def create_round_graph(df, chosen_teg, chosen_round, y_series, title,
                       y_calculation=None, y_axis_label=None, chart_type='default', plotly_theme=None):
    """Cumulative chart through the holes of a single round (x = hole 1..18)."""
    rd_data = df[(df['TEG'] == chosen_teg) & (df['Round'] == chosen_round)].sort_values(['Hole'])
    rd_data = rd_data.copy()
    rd_data['x_value'] = rd_data['Hole']
    x_axis_max = 18

    fig = go.Figure()
    colors = px.colors.qualitative.Plotly[:len(rd_data['Pl'].unique())]
    color_map = dict(zip(rd_data['Pl'].unique(), colors))

    traces = []
    for player in rd_data['Pl'].unique():
        player_data = rd_data[rd_data['Pl'] == player]
        y_values = y_calculation(player_data) if y_calculation else player_data[y_series]

        traces.append(go.Scatter(
            x=player_data['x_value'], y=y_values, mode='lines+markers', name=player,
            line=dict(width=2),
            marker=dict(symbol="circle", size=6, line=dict(width=1, color="white")),
        ))

        last_x = player_data['x_value'].iloc[-1]
        last_y = y_values.iloc[-1]
        fig.add_annotation(
            x=last_x, y=last_y, text=f"{player}: {format_value(last_y, chart_type)}",
            showarrow=False, xanchor='left', yanchor='middle', xshift=5,
            font=dict(size=10, color=color_map[player]),
        )

    fig.add_traces(traces)
    fig.update_layout(
        yaxis_title=y_axis_label if y_axis_label else f'Cumulative {y_series}',
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, traceorder='normal', itemsizing='constant'),
        margin=dict(r=100, t=0, b=10, l=0),
        font=dict(family="monospace"),
    )
    fig.update_xaxes(visible=True, showline=True, linewidth=1, linecolor="#ccc",
                     ticks="outside", tickmode="linear", tick0=1, dtick=1,
                     title_text="Hole", range=[0.5, 18.5])
    if chart_type == 'ranking':
        fig.update_yaxes(autorange='reversed')
    for trace in fig.data:
        fig.update_traces(selector=dict(name=trace.name), line=dict(color=color_map[trace.name]))
    fig.layout.yaxis.fixedrange = True
    fig.update_layout(**(plotly_theme if plotly_theme is not None else get_chart_style('streamlit')))
    return fig


def adjusted_stableford(data):
    return data['Stableford Cum TEG'] - (2 * data['TEG Count'])


def adjusted_grossvp(data):
    return data['GrossVP Cum TEG'] - data['TEG Count']
