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


#: Above this many players, on-chart end-of-line labels start to collide (the
#: readout list below the chart -- see get_teg_chart_readout -- carries player
#: identity/value instead; see webapp/MOBILE_PLAN.md R4's "do not force direct
#: labels onto large fields" gate). No TEG in the current data reaches this,
#: so it's exercised by synthetic tests, not live data.
CROWDED_FIELD_THRESHOLD = 6


def get_teg_player_color_map(df, chosen_teg) -> dict:
    """Player code -> hex colour for one TEG's tournament race chart, in the
    exact same order/assignment create_cumulative_graph uses internally
    (first appearance in Round/Hole-sorted TEG data, taken from
    px.colors.qualitative.Plotly).

    Callers that render a player-colour readout OUTSIDE the actual Plotly
    figure (webapp/routes/history.py's chart_readout list) must call this
    rather than re-deriving their own mapping -- see get_round_player_color_map
    for why two independently computed maps can disagree.
    """
    teg_data = df[df['TEG'] == chosen_teg].sort_values(['Round', 'Hole'])
    codes = teg_data['Pl'].unique()
    colors = px.colors.qualitative.Plotly[:len(codes)]
    return dict(zip(codes, colors))


def get_teg_chart_readout(df, chosen_teg, y_series, y_calculation=None, chart_type='default') -> list:
    """Player code/final-value/colour list for the tournament race chart's
    below-chart readout. Mirrors the final value each player's end-of-line
    annotation would show (see create_cumulative_graph) -- the readout exists
    precisely so that value/identity stays visible without hovering the
    chart, and stays legible even for fields too crowded for on-chart labels.
    """
    teg_data = df[df['TEG'] == chosen_teg].sort_values(['Round', 'Hole'])
    color_map = get_teg_player_color_map(df, chosen_teg)
    readout = []
    for player in teg_data['Pl'].unique():
        player_data = teg_data[teg_data['Pl'] == player]
        y_values = y_calculation(player_data) if y_calculation else player_data[y_series]
        if y_values.empty:
            continue
        readout.append({
            "code": str(player),
            "value": format_value(y_values.iloc[-1], chart_type),
            "color": color_map.get(player, ''),
        })
    return readout


def create_cumulative_graph(df, chosen_teg, y_series, title, y_calculation=None, y_axis_label=None, chart_type='default', plotly_theme=None):
    teg_data = df[df['TEG'] == chosen_teg].sort_values(['Round', 'Hole'])
    teg_data['x_value'] = (teg_data['Round'] - 1) * 18 + teg_data['Hole']

    max_round = teg_data['Round'].max()
    x_axis_max = max_round * 18

    fig = go.Figure()

    players = teg_data['Pl'].unique()
    color_map = get_teg_player_color_map(df, chosen_teg)
    # Above the threshold, on-chart labels would collide -- skip them and
    # rely on the below-chart readout (get_teg_chart_readout) instead of
    # forcing direct labels onto a crowded field.
    crowded = len(players) > CROWDED_FIELD_THRESHOLD

    traces = []
    for player in players:
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

        if not crowded:
            last_x = player_data['x_value'].iloc[-1]
            last_y = y_values.iloc[-1]
            formatted_value = format_value(last_y, chart_type)
            # Short "code value" form (no colon) -- matches the proven Latest
            # Round end-of-line label, which needs far less width than the
            # old "Player: value" text did.
            fig.add_annotation(
                x=last_x,
                y=last_y,
                text=f"{player} {formatted_value}",
                showarrow=False,
                xanchor='left',
                yanchor='middle',
                xshift=4,
                font=dict(size=9, color=color_map[player])
            )

    fig.add_traces(traces)

    fig.update_layout(
        yaxis_title=y_axis_label if y_axis_label else f'Cumulative {y_series}',
        hovermode='x unified',
        # Native legend stays off -- the below-chart readout (rendered by the
        # caller from get_teg_chart_readout) already covers "which colour is
        # which player", tappable without hover, so the legend was pure
        # duplication of that plus the end-of-line labels. Matches the
        # proven Latest Round chart contract (create_round_graph).
        showlegend=False,
        margin=dict(r=36, t=8, b=10, l=0),
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


def get_round_player_color_map(df, chosen_teg, chosen_round) -> dict:
    """Player code -> hex colour for one round's chart, in the exact same
    order/assignment create_round_graph uses internally (first appearance in
    Hole-sorted round data, taken from px.colors.qualitative.Plotly).

    Callers that render a player-colour legend/readout OUTSIDE the actual
    Plotly figure (webapp/routes/latest.py's chart_readout list, rendered by
    partials/latest_round_tab.html's .lr-readout buttons) must call this
    rather than re-deriving their own mapping, so a player's colour always
    matches between the chart lines and the readout -- two independently
    computed `dict(zip(unique_codes, palette))`s would only agree if both
    walk the codes in the identical order, which is easy to accidentally
    break (e.g. a differently-filtered or differently-sorted frame).
    """
    rd_data = df[(df['TEG'] == chosen_teg) & (df['Round'] == chosen_round)].sort_values(['Hole'])
    codes = rd_data['Pl'].unique()
    colors = px.colors.qualitative.Plotly[:len(codes)]
    return dict(zip(codes, colors))


def create_round_graph(df, chosen_teg, chosen_round, y_series, title,
                       y_calculation=None, y_axis_label=None, chart_type='default', plotly_theme=None,
                       scale='normal', rewind=18, focus_player=''):
    """Cumulative chart through the holes of a single round (x = hole 1..18)."""
    rd_data = df[(df['TEG'] == chosen_teg) & (df['Round'] == chosen_round)].sort_values(['Hole'])
    rd_data = rd_data.copy()
    rd_data['x_value'] = rd_data['Hole']
    x_axis_max = 18

    fig = go.Figure()
    color_map = get_round_player_color_map(df, chosen_teg, chosen_round)

    traces = []
    for player in rd_data['Pl'].unique():
        player_data = rd_data[rd_data['Pl'] == player]
        y_values = y_calculation(player_data) if y_calculation else player_data[y_series]
        if scale == 'adjusted':
            if chart_type == 'stableford':
                y_values = y_values - (2 * player_data['Hole'])
            elif chart_type == 'gross':
                y_values = y_values - player_data['Hole']
        visible = player_data['Hole'] <= max(1, min(int(rewind or 18), 18))
        line_opacity = 1 if (not focus_player or player == focus_player) else 0.18

        traces.append(go.Scatter(
            x=player_data.loc[visible, 'x_value'], y=y_values.loc[visible], mode='lines+markers', name=player,
            line=dict(width=2),
            marker=dict(symbol="circle", size=6, line=dict(width=1, color="white")),
            opacity=line_opacity,
        ))
        if not visible.all():
            future = player_data[player_data['Hole'] >= max(1, min(int(rewind or 18), 18))]
            traces.append(go.Scatter(
                x=future['x_value'], y=y_values.loc[future.index],
                mode='lines+markers', name=player, showlegend=False,
                line=dict(width=2), marker=dict(symbol="circle", size=5), opacity=0.2,
                # Tags this as the faint "future" continuation so the focus()
                # JS in latest_round.html can keep it capped at its faded
                # opacity even when this player is the focused one, instead
                # of raising it to full opacity (which defeated the rewind
                # fade and made the whole line look "un-rewound").
                meta="future",
            ))

        # Short end-of-line label (player code + value, e.g. "GW 44") --
        # kept per the approved reference, which shows exactly this next to
        # each line's last plotted point. Native legend stays off
        # (showlegend=False below) since .lr-readout already covers the
        # "which colour is which player" job; these annotations instead
        # cover "what's each player's live value", right at the line ends,
        # which the readout re-states below the chart but not inline. Two
        # letters + a short number needs far less width than the player's
        # full name did, so the right margin can stay tight.
        label_idx = player_data.loc[visible, 'Hole'].idxmax() if visible.any() else player_data['Hole'].idxmax()
        last_x = player_data.loc[label_idx, 'x_value']
        last_y = y_values.loc[label_idx]
        fig.add_annotation(
            x=last_x, y=last_y, text=f"{player} {format_value(last_y, chart_type)}",
            showarrow=False, xanchor='left', yanchor='middle', xshift=4,
            font=dict(size=9, color=color_map[player]),
        )

    fig.add_traces(traces)
    fig.update_layout(
        hovermode='x unified',
        # Native Plotly legend stays off -- .lr-readout (the player
        # focus/value buttons below the chart) already does that job. The
        # y-axis title text is dropped too (numeric ticks alone, per the
        # reference) to free up horizontal space on phone widths; the tight
        # right margin only needs to fit the short end-of-line labels above,
        # not the wide legend/title layout this used to carry.
        showlegend=False,
        margin=dict(r=36, t=8, b=10, l=0),
        font=dict(family="monospace"),
    )
    fig.update_xaxes(visible=True, showline=True, linewidth=1, linecolor="#ccc",
                     ticks="outside", tickmode="linear", tick0=1, dtick=3,
                     title_text="Hole", range=[0.5, 18.5],
                     # Light vertical gridlines (following the same reduced
                     # tick spacing), matching the reference's combined
                     # horizontal+vertical grid -- the horizontal grid
                     # already comes from get_chart_style()'s yaxis.showgrid.
                     showgrid=True, gridcolor="rgba(0,0,0,0.06)", gridwidth=1)
    fig.update_yaxes(title_text=None)
    if int(rewind or 18) != 18:
        # Rewind uses the endpoint as the inspection point. Future holes remain
        # visible as a faint continuation without a misleading unified hover.
        fig.update_layout(hovermode=False)
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
