"""Player profile routes."""

import logging
from functools import lru_cache
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from markupsafe import escape

from teg_analysis.constants import PLAYER_DICT
from teg_analysis.analysis.history import (
    get_teg_winners,
    get_eagles_data,
    get_holes_in_one_data,
    calculate_trophy_jacket_doubles,
)
from teg_analysis.analysis.scoring import (
    calculate_par_performance_matrix,
    format_par_performance_table,
    format_vs_par,
    get_net_competition_measure,
)
from teg_analysis.analysis.streaks import (
    build_streaks,
    get_max_streaks,
    get_current_streaks,
    STREAK_CONFIGS,
)
from webapp.deps import (
    cached_load_all_data,
    cached_round_data,
    cached_complete_teg_data,
    cached_ranked_teg_data,
    cached_ranked_round_data,
    format_value,
)
from webapp.theme import get_plotly_theme

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

PLAYER_TABS = [
    ("overview", "Overview"),
    ("rounds", "Rounds"),
    ("scoring", "Scoring"),
    ("records", "Records & Streaks"),
    ("h2h", "Head to Head"),
]

# Reverse lookup: full name → player code
_NAME_TO_CODE = {v: k for k, v in PLAYER_DICT.items()}


def _get_player_list():
    """Return sorted list of (code, name) tuples."""
    return sorted(PLAYER_DICT.items(), key=lambda x: x[1])


def _validate_player(player_code: str) -> str:
    """Validate player code and return it uppercased, or raise 404."""
    pc = player_code.upper()
    if pc not in PLAYER_DICT:
        raise HTTPException(status_code=404, detail=f"Unknown player code: {player_code}")
    return pc


@lru_cache(maxsize=1)
def _get_winners_data():
    """Get winners DataFrame from all data (cached)."""
    all_data = cached_load_all_data()
    return get_teg_winners(all_data)


def _ordinal(n: int) -> str:
    """Return ordinal string for an integer (1st, 2nd, 3rd, 11th, etc.)."""
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    return f"{n}{['th','st','nd','rd'][n % 10] if n % 10 < 4 else 'th'}"


# ---------------------------------------------------------------------------
# Stat cards
# ---------------------------------------------------------------------------

def _build_stat_cards(player_code: str) -> list[dict]:
    """Build stat card data for a player."""
    name = PLAYER_DICT[player_code]
    cards = []

    # TEGs played
    teg_data = cached_complete_teg_data()
    player_tegs = teg_data[teg_data['Player'] == name]
    cards.append({"value": str(len(player_tegs)), "label": "TEGs Played"})

    # Avg Gross vs Par (per round)
    rd_data = cached_round_data()
    player_rds = rd_data[rd_data['Player'] == name]
    if not player_rds.empty:
        avg_gvp = player_rds['GrossVP'].mean()
        cards.append({"value": f"{avg_gvp:+.1f}", "label": "Avg Gross vs Par"})
    else:
        cards.append({"value": "–", "label": "Avg Gross vs Par"})

    # Avg Stableford (per round)
    if not player_rds.empty:
        avg_stab = player_rds['Stableford'].mean()
        cards.append({"value": f"{avg_stab:.1f}", "label": "Avg Stableford"})
    else:
        cards.append({"value": "–", "label": "Avg Stableford"})

    # Trophies
    winners = _get_winners_data()
    trophy_count = (winners['TEG Trophy'] == name).sum()
    jacket_count = (winners['Green Jacket'] == name).sum()
    total_wins = trophy_count + jacket_count
    cards.append({"value": str(total_wins), "label": "Trophies"})

    return cards


# ---------------------------------------------------------------------------
# Trophy cabinet
# ---------------------------------------------------------------------------

def _build_trophy_cabinet(player_code: str) -> list[dict]:
    """Build trophy cabinet badges with tooltip details for a player."""
    name = PLAYER_DICT[player_code]
    badges = []

    winners = _get_winners_data()

    # Trophy wins with TEG details
    trophy_tegs = winners[winners['TEG Trophy'] == name]['TEG'].tolist()
    if trophy_tegs:
        tooltip = ', '.join(trophy_tegs)
        badges.append({"text": f"TEG Trophy ×{len(trophy_tegs)}", "style": "accent", "tooltip": tooltip})

    # Green Jacket wins with TEG details
    jacket_tegs = winners[winners['Green Jacket'] == name]['TEG'].tolist()
    if jacket_tegs:
        tooltip = ', '.join(jacket_tegs)
        badges.append({"text": f"Green Jacket ×{len(jacket_tegs)}", "style": "accent", "tooltip": tooltip})

    # Wooden Spoon with TEG details
    spoon_tegs = winners[winners['HMM Wooden Spoon'] == name]['TEG'].tolist()
    if spoon_tegs:
        tooltip = ', '.join(spoon_tegs)
        badges.append({"text": f"Wooden Spoon ×{len(spoon_tegs)}", "style": "muted", "tooltip": tooltip})

    # Eagles with details
    all_data = cached_load_all_data()
    eagles = get_eagles_data(all_data)
    player_eagles = eagles[eagles['Player'] == name] if not eagles.empty else eagles
    if len(player_eagles) > 0:
        eagle_details = '; '.join(
            f"{r['Course']} {r['Hole']}" for _, r in player_eagles.iterrows()
        )
        badges.append({"text": f"Eagles: {len(player_eagles)}", "style": "accent", "tooltip": eagle_details})

    # Holes in one with details
    hio = get_holes_in_one_data(all_data)
    player_hio = hio[hio['Player'] == name] if not hio.empty else hio
    if len(player_hio) > 0:
        hio_details = '; '.join(
            f"{r['Course']} {r['Hole']}" for _, r in player_hio.iterrows()
        )
        badges.append({"text": f"Holes in One: {len(player_hio)}", "style": "accent", "tooltip": hio_details})

    # Double winner (trophy + jacket in same TEG)
    doubles_df, _ = calculate_trophy_jacket_doubles(winners)
    if not doubles_df.empty:
        player_doubles = doubles_df[doubles_df['Player'] == name]
        if not player_doubles.empty and player_doubles.iloc[0]['Doubles'] > 0:
            # Find which TEGs were doubles
            clean = winners.replace(r'\*', '', regex=True)
            double_tegs = clean[
                (clean['TEG Trophy'] == name) & (clean['Green Jacket'] == name)
            ]['TEG'].tolist()
            tooltip = ', '.join(double_tegs)
            badges.append({
                "text": f"Double Winner ×{player_doubles.iloc[0]['Doubles']}",
                "style": "accent",
                "tooltip": tooltip,
            })

    return badges


# ---------------------------------------------------------------------------
# Header subtitle
# ---------------------------------------------------------------------------

def _build_subtitle(player_code: str) -> str:
    """Build subtitle like 'X TEGs played · First: TEG N (YYYY) · Latest: TEG N (YYYY)'."""
    name = PLAYER_DICT[player_code]
    all_data = cached_load_all_data()
    player_data = all_data[all_data['Player'] == name]

    if player_data.empty:
        return "No TEG data"

    teg_info = player_data[['TEGNum', 'Year']].drop_duplicates().sort_values('TEGNum')
    n_tegs = len(teg_info)
    first = teg_info.iloc[0]
    latest = teg_info.iloc[-1]

    return (
        f"{n_tegs} TEGs played · "
        f"First: TEG {int(first['TEGNum'])} ({int(first['Year'])}) · "
        f"Latest: TEG {int(latest['TEGNum'])} ({int(latest['Year'])})"
    )


# ---------------------------------------------------------------------------
# Table HTML builders
# ---------------------------------------------------------------------------

_NUMERIC_COLS = {
    'Score', 'Gross', 'GrossVP', 'Gross VP', 'NetVP', 'Net VP', 'Stableford',
    'Pts', 'Points', 'Total', 'Avg', 'Average', 'Count',
    'Gross Rank', 'Net Rank', 'Round Rank', 'Wins', 'Losses', 'Draws',
    'Avg Diff', 'Streak', 'Value', '%', 'Career Best', 'Current',
}
_RANK_COLS = {'#', 'Rank', 'Gross Rank', 'Net Rank', 'Round Rank'}


def _build_simple_table_html(df, highlight_col=None, highlight_val=None):
    """Build a simple HTML table from a DataFrame with escaped values."""
    if df is None or df.empty:
        return "<p class='text-muted text-sm'>No data available.</p>"

    rows = ["<table class='teg-table'>", "<thead><tr>"]
    for col in df.columns:
        cls = 'col-rank' if col in _RANK_COLS else ('col-num' if col in _NUMERIC_COLS else 'col-player')
        rows.append(f"<th class='{cls}'>{escape(str(col))}</th>")
    rows.append("</tr></thead><tbody>")

    for _, row in df.iterrows():
        row_class = ""
        if highlight_col and highlight_val and str(row.get(highlight_col, '')) == str(highlight_val):
            row_class = ' class="top-rank"'
        rows.append(f"<tr{row_class}>")
        for col in df.columns:
            cls = 'col-rank' if col in _RANK_COLS else ('col-num' if col in _NUMERIC_COLS else 'col-player')
            val = escape(str(row[col]))
            rows.append(f"<td class='{cls}'>{val}</td>")
        rows.append("</tr>")

    rows.append("</tbody></table>")
    return "".join(rows)


# ---------------------------------------------------------------------------
# Per-TEG gross/net rank computation
# ---------------------------------------------------------------------------

def _compute_teg_ranks(teg_num: int, rd_data: pd.DataFrame) -> dict[str, dict]:
    """Compute per-player gross and net finishing positions for a single TEG.

    Returns dict keyed by player name: {"gross_rank": "1st", "net_rank": "2nd"}.
    """
    teg_rd = rd_data[rd_data['TEGNum'] == teg_num]
    if teg_rd.empty:
        return {}

    net_measure = get_net_competition_measure(teg_num)
    result = {}

    # Gross ranks
    gross_totals = teg_rd.groupby('Player')['GrossVP'].sum().sort_values()
    gross_totals_rank = gross_totals.rank(method='min').astype(int)

    # Net ranks
    net_ascending = net_measure == 'NetVP'
    net_totals = teg_rd.groupby('Player')[net_measure].sum().sort_values(ascending=net_ascending)
    net_totals_rank = net_totals.rank(method='min', ascending=net_ascending).astype(int)

    for player_name in gross_totals.index:
        g_rank = int(gross_totals_rank[player_name])
        n_rank = int(net_totals_rank[player_name]) if player_name in net_totals_rank.index else None
        result[player_name] = {
            "gross_rank": _ordinal(g_rank),
            "net_rank": _ordinal(n_rank) if n_rank else "–",
        }

    return result


# ---------------------------------------------------------------------------
# Tab: Overview
# ---------------------------------------------------------------------------

def _build_overview_context(player_code: str, theme: str) -> dict:
    """Build context for the overview tab."""
    name = PLAYER_DICT[player_code]

    # TEG results table
    ranked_teg = cached_ranked_teg_data()
    player_teg = ranked_teg[ranked_teg['Player'] == name].copy()

    winners = _get_winners_data()
    rd_data = cached_round_data()

    if not player_teg.empty:
        rows = []
        for _, r in player_teg.sort_values('TEGNum', ascending=False).iterrows():
            teg_num = int(r['TEGNum'])
            year = int(r['Year']) if 'Year' in r.index else ''
            gross_vp = format_value(r['GrossVP'], 'GrossVP')

            net_measure = get_net_competition_measure(teg_num)
            if net_measure == 'Stableford':
                net_val = format_value(r['Stableford'], 'Stableford')
                net_label = f"{net_val} pts"
            else:
                net_val = format_value(r['NetVP'], 'NetVP')
                net_label = net_val

            # Per-TEG finishing positions
            teg_ranks = _compute_teg_ranks(teg_num, rd_data)
            player_ranks = teg_ranks.get(name, {})
            gross_rank = player_ranks.get("gross_rank", "–")
            net_rank = player_ranks.get("net_rank", "–")

            # Result markers
            teg_label = f"TEG {teg_num}"
            teg_winners = winners[winners['TEG'] == teg_label]
            result = ""
            if not teg_winners.empty:
                w = teg_winners.iloc[0]
                if w['TEG Trophy'] == name:
                    result = "Trophy"
                if w['Green Jacket'] == name:
                    result = "Jacket" if not result else "Double"
                if w['HMM Wooden Spoon'] == name:
                    result = "Spoon"

            rows.append({
                'TEG': teg_num,
                'Year': year,
                'Gross VP': gross_vp,
                'Net/Stab': net_label,
                'Gross Rank': gross_rank,
                'Net Rank': net_rank,
                'Result': result,
            })

        teg_table_df = pd.DataFrame(rows)
        teg_table_html = _build_simple_table_html(teg_table_df)
    else:
        teg_table_html = "<p class='text-muted text-sm'>No TEG data.</p>"

    # Career trend chart (gross vs par per TEG)
    chart_json = None
    if not player_teg.empty:
        chart_data = player_teg.sort_values('TEGNum')
        avg_gvp = chart_data['GrossVP'].mean()

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=chart_data['TEGNum'],
            y=chart_data['GrossVP'],
            mode='lines+markers',
            name='Gross vs Par',
            line=dict(width=2),
        ))
        fig.add_hline(
            y=avg_gvp, line_dash="dash", line_color="gray",
            annotation_text=f"Avg: {avg_gvp:+.1f}",
            annotation_position="top left",
        )
        fig.update_layout(
            xaxis_title="TEG",
            yaxis_title="Gross vs Par (total)",
            margin=dict(r=20, t=10, b=40, l=50),
            font=dict(family="monospace"),
            hovermode='x unified',
        )
        fig.layout.xaxis.fixedrange = True
        fig.layout.yaxis.fixedrange = True

        plotly_theme = get_plotly_theme(theme)
        if plotly_theme:
            fig.update_layout(**plotly_theme)

        chart_json = fig.to_json()

    return {
        "teg_table_html": teg_table_html,
        "chart_json": chart_json,
    }


# ---------------------------------------------------------------------------
# Tab: Rounds
# ---------------------------------------------------------------------------

def _build_rounds_context(player_code: str) -> dict:
    """Build context for the rounds tab."""
    name = PLAYER_DICT[player_code]

    ranked_rd = cached_ranked_round_data()
    player_rd = ranked_rd[ranked_rd['Player'] == name].copy()

    if player_rd.empty:
        return {"rounds_table_html": "<p class='text-muted text-sm'>No round data.</p>"}

    # Find PB values for highlighting
    best_gross = player_rd['GrossVP'].min()
    best_stab = player_rd['Stableford'].max()

    rows = []
    for _, r in player_rd.sort_values(['TEGNum', 'Round'], ascending=[False, True]).iterrows():
        gross_vp = format_value(r['GrossVP'], 'GrossVP')
        stab = format_value(r['Stableford'], 'Stableford')
        is_pb_gross = (r['GrossVP'] == best_gross)
        is_pb_stab = (r['Stableford'] == best_stab)

        course = r.get('Course', '') if 'Course' in r.index else ''

        rows.append({
            'TEG': int(r['TEGNum']),
            'Rd': int(r['Round']),
            'Course': course,
            'Score': int(r['Sc']),
            'Gross VP': gross_vp + (' *' if is_pb_gross else ''),
            'Stableford': stab + (' *' if is_pb_stab else ''),
        })

    rd_df = pd.DataFrame(rows)
    return {"rounds_table_html": _build_simple_table_html(rd_df)}


# ---------------------------------------------------------------------------
# Tab: Scoring
# ---------------------------------------------------------------------------

def _build_scoring_context(player_code: str, theme: str) -> dict:
    """Build context for the scoring tab."""
    name = PLAYER_DICT[player_code]
    all_data = cached_load_all_data()
    player_data = all_data[all_data['Player'] == name]

    sections = []

    # Par performance
    if not player_data.empty:
        matrix = calculate_par_performance_matrix(player_data)
        formatted = format_par_performance_table(matrix.copy())
        sections.append({
            "title": "Average Score by Par",
            "table_html": _build_simple_table_html(formatted),
        })

    # Score distribution
    if not player_data.empty:
        grossvp_counts = player_data['GrossVP'].value_counts().sort_index()

        score_labels = {
            -3: 'Albatross', -2: 'Eagle', -1: 'Birdie', 0: 'Par',
            1: 'Bogey', 2: 'Double', 3: 'Triple', 4: '+4', 5: '+5',
        }

        dist_rows = []
        total = len(player_data)
        for val in sorted(grossvp_counts.index):
            count = grossvp_counts[val]
            label = score_labels.get(int(val), format_vs_par(val))
            pct = (count / total * 100) if total > 0 else 0
            dist_rows.append({
                'Score': label,
                'Count': int(count),
                '%': f"{pct:.1f}%",
            })

        dist_df = pd.DataFrame(dist_rows)
        sections.append({
            "title": "Score Distribution",
            "table_html": _build_simple_table_html(dist_df),
        })

        # Score distribution chart
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=[r['Score'] for r in dist_rows],
            y=[int(r['Count']) for r in dist_rows],
        ))
        fig.update_layout(
            xaxis_title="Score vs Par",
            yaxis_title="Count",
            margin=dict(r=20, t=10, b=40, l=50),
            font=dict(family="monospace"),
        )
        fig.layout.xaxis.fixedrange = True
        fig.layout.yaxis.fixedrange = True

        plotly_theme = get_plotly_theme(theme)
        if plotly_theme:
            fig.update_layout(**plotly_theme)

        sections.append({
            "title": "Score Distribution Chart",
            "chart_json": fig.to_json(),
        })

    return {"sections": sections}


# ---------------------------------------------------------------------------
# Tab: Records & Streaks
# ---------------------------------------------------------------------------

def _build_records_context(player_code: str) -> dict:
    """Build context for the records & streaks tab."""
    name = PLAYER_DICT[player_code]
    sections = []

    # Personal bests — TEG level
    ranked_teg = cached_ranked_teg_data()
    player_teg = ranked_teg[ranked_teg['Player'] == name]

    if not player_teg.empty:
        pb_rows = []
        best_gross_idx = player_teg['GrossVP'].idxmin()
        best_gross = player_teg.loc[best_gross_idx]
        pb_rows.append({
            'Record': 'Best TEG (Gross)',
            'Value': format_value(best_gross['GrossVP'], 'GrossVP'),
            'TEG': f"TEG {int(best_gross['TEGNum'])}",
        })
        best_stab_idx = player_teg['Stableford'].idxmax()
        best_stab = player_teg.loc[best_stab_idx]
        pb_rows.append({
            'Record': 'Best TEG (Stableford)',
            'Value': format_value(best_stab['Stableford'], 'Stableford'),
            'TEG': f"TEG {int(best_stab['TEGNum'])}",
        })
        sections.append({
            "title": "Personal Bests — TEG",
            "table_html": _build_simple_table_html(pd.DataFrame(pb_rows)),
        })

    # Personal bests — Round level
    ranked_rd = cached_ranked_round_data()
    player_rd = ranked_rd[ranked_rd['Player'] == name]

    if not player_rd.empty:
        rd_pb_rows = []
        best_rd_gross_idx = player_rd['GrossVP'].idxmin()
        best_rd_gross = player_rd.loc[best_rd_gross_idx]
        rd_pb_rows.append({
            'Record': 'Best Round (Gross)',
            'Value': format_value(best_rd_gross['GrossVP'], 'GrossVP'),
            'TEG': f"TEG {int(best_rd_gross['TEGNum'])} R{int(best_rd_gross['Round'])}",
        })
        best_rd_stab_idx = player_rd['Stableford'].idxmax()
        best_rd_stab = player_rd.loc[best_rd_stab_idx]
        rd_pb_rows.append({
            'Record': 'Best Round (Stableford)',
            'Value': format_value(best_rd_stab['Stableford'], 'Stableford'),
            'TEG': f"TEG {int(best_rd_stab['TEGNum'])} R{int(best_rd_stab['Round'])}",
        })
        sections.append({
            "title": "Personal Bests — Round",
            "table_html": _build_simple_table_html(pd.DataFrame(rd_pb_rows)),
        })

    # Personal worsts — TEG level
    if not player_teg.empty:
        pw_rows = []
        worst_gross_idx = player_teg['GrossVP'].idxmax()
        worst_gross = player_teg.loc[worst_gross_idx]
        pw_rows.append({
            'Record': 'Worst TEG (Gross)',
            'Value': format_value(worst_gross['GrossVP'], 'GrossVP'),
            'TEG': f"TEG {int(worst_gross['TEGNum'])}",
        })
        worst_stab_idx = player_teg['Stableford'].idxmin()
        worst_stab = player_teg.loc[worst_stab_idx]
        pw_rows.append({
            'Record': 'Worst TEG (Stableford)',
            'Value': format_value(worst_stab['Stableford'], 'Stableford'),
            'TEG': f"TEG {int(worst_stab['TEGNum'])}",
        })
        sections.append({
            "title": "Personal Worsts — TEG",
            "table_html": _build_simple_table_html(pd.DataFrame(pw_rows)),
        })

    # Streaks
    all_data = cached_load_all_data()
    try:
        streaks_df = build_streaks(all_data)
        player_streaks = streaks_df[streaks_df['Pl'] == player_code]

        if not player_streaks.empty:
            max_s = get_max_streaks(player_streaks)
            current_s = get_current_streaks(player_streaks)

            good_mapping = STREAK_CONFIGS['good']['column_mapping']
            bad_mapping = STREAK_CONFIGS['bad']['column_mapping']

            streak_rows = []
            for label, col in {**good_mapping, **bad_mapping}.items():
                max_val = int(max_s[col].iloc[0]) if col in max_s.columns else 0
                cur_val = int(current_s[col].iloc[0]) if col in current_s.columns else 0
                streak_rows.append({
                    'Streak': label,
                    'Career Best': max_val,
                    'Current': cur_val,
                })

            sections.append({
                "title": "Streaks",
                "table_html": _build_simple_table_html(pd.DataFrame(streak_rows)),
            })
    except (KeyError, ValueError) as exc:
        logger.warning("Could not build streaks for %s: %s", player_code, exc)

    return {"sections": sections}


# ---------------------------------------------------------------------------
# Tab: Head to Head
# ---------------------------------------------------------------------------

def _build_h2h_context(player_code: str) -> dict:
    """Build context for the head-to-head tab."""
    name = PLAYER_DICT[player_code]

    ranked_teg = cached_ranked_teg_data()
    player_teg = ranked_teg[ranked_teg['Player'] == name]

    if player_teg.empty:
        return {"h2h_table_html": "<p class='text-muted text-sm'>No data.</p>"}

    player_tegs = set(player_teg['TEGNum'].unique())

    h2h_rows = []
    for opp_code, opp_name in sorted(PLAYER_DICT.items(), key=lambda x: x[1]):
        if opp_code == player_code:
            continue

        opp_teg = ranked_teg[ranked_teg['Player'] == opp_name]
        opp_tegs = set(opp_teg['TEGNum'].unique())
        shared_tegs = player_tegs & opp_tegs

        if not shared_tegs:
            continue

        wins = 0
        losses = 0
        draws = 0
        total_diff = 0

        for teg_num in shared_tegs:
            p_gross = player_teg[player_teg['TEGNum'] == teg_num]['GrossVP'].iloc[0]
            o_gross = opp_teg[opp_teg['TEGNum'] == teg_num]['GrossVP'].iloc[0]
            diff = p_gross - o_gross
            total_diff += diff

            if diff < 0:
                wins += 1
            elif diff > 0:
                losses += 1
            else:
                draws += 1

        n = len(shared_tegs)
        avg_diff = total_diff / n if n > 0 else 0

        h2h_rows.append({
            'Opponent': opp_name,
            'TEGs': n,
            'Wins': wins,
            'Losses': losses,
            'Draws': draws,
            'Avg Diff': f"{avg_diff:+.1f}",
        })

    h2h_df = pd.DataFrame(h2h_rows)
    return {"h2h_table_html": _build_simple_table_html(h2h_df)}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/player/{player_code}")
async def player_page(request: Request, player_code: str):
    pc = _validate_player(player_code)
    name = PLAYER_DICT[pc]
    theme = request.state.theme

    stat_cards = _build_stat_cards(pc)
    trophy_cabinet = _build_trophy_cabinet(pc)
    subtitle = _build_subtitle(pc)
    overview_ctx = _build_overview_context(pc, theme)

    return templates.TemplateResponse("player.html", {
        "request": request,
        "active_page": "player",
        "player_code": pc,
        "player_name": name,
        "player_list": _get_player_list(),
        "subtitle": subtitle,
        "stat_cards": stat_cards,
        "trophy_cabinet": trophy_cabinet,
        "tabs": PLAYER_TABS,
        "active_tab": "overview",
        **overview_ctx,
    })


@router.get("/player/{player_code}/tab/{tab_name}")
async def player_tab(request: Request, player_code: str, tab_name: str):
    pc = _validate_player(player_code)
    theme = request.state.theme

    if tab_name == "overview":
        ctx = _build_overview_context(pc, theme)
        template = "partials/player_overview.html"
    elif tab_name == "rounds":
        ctx = _build_rounds_context(pc)
        template = "partials/player_rounds.html"
    elif tab_name == "scoring":
        ctx = _build_scoring_context(pc, theme)
        template = "partials/player_scoring.html"
    elif tab_name == "records":
        ctx = _build_records_context(pc)
        template = "partials/player_records.html"
    elif tab_name == "h2h":
        ctx = _build_h2h_context(pc)
        template = "partials/player_h2h.html"
    else:
        raise HTTPException(status_code=404, detail=f"Unknown tab: {tab_name}")

    return templates.TemplateResponse(template, {
        "request": request,
        "player_code": pc,
        **ctx,
    })
