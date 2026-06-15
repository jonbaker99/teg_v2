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
from webapp.chart_utils import get_chart_style

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

PLAYER_TABS = [
    ("overview", "Overview"),
    ("rounds", "Rounds"),
    ("scoring", "Scoring"),
    ("records", "Records & Streaks"),
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
# Overview metrics (with cross-player rankings)
# ---------------------------------------------------------------------------

def _rank_str(series: pd.Series, name: str, ascending: bool) -> str:
    """Rank ``name`` within a per-player Series; joint ranks get an '=' suffix."""
    s = series.dropna()
    if name not in s.index:
        return "–"
    ranks = s.rank(method="min", ascending=ascending)
    r = int(ranks[name])
    tied = int((ranks == r).sum()) > 1
    return f"{r}=" if tied else str(r)


def _ordinal_rank(rank_str: str) -> str:
    """Convert a raw rank string to ordinal form: '1=' → '1st =', '3' → '3rd'."""
    if rank_str in ("–", ""):
        return rank_str
    tied = rank_str.endswith("=")
    n = int(rank_str.rstrip("="))
    return _ordinal(n) + (" =" if tied else "")


def _metric_specs(all_data, rd_data, winners):
    """Per-player Series for every overview metric.

    Returns a list of (label, series, ascending, formatter, unranked_if_zero).
    ``ascending`` controls rank direction; ``unranked_if_zero`` suppresses the
    rank for honour/count metrics where the player has a zero tally.
    """
    players = [n for n in PLAYER_DICT.values() if (all_data["Player"] == n).any()]
    clean = winners.replace(r"\*", "", regex=True)

    tegs_played = all_data.groupby("Player")["TEGNum"].nunique()
    avg_gvp = rd_data.groupby("Player")["GrossVP"].mean()
    avg_stab = rd_data.groupby("Player")["Stableford"].mean()

    trophy = clean["TEG Trophy"].value_counts()
    jacket = clean["Green Jacket"].value_counts()
    spoon = clean["HMM Wooden Spoon"].value_counts()
    total_trophies = trophy.add(jacket, fill_value=0)

    doubles_df, _ = calculate_trophy_jacket_doubles(winners)
    doubles = (doubles_df.set_index("Player")["Doubles"]
               if not doubles_df.empty else pd.Series(dtype=float))

    eagles = get_eagles_data(all_data)
    eagles_ct = eagles["Player"].value_counts() if not eagles.empty else pd.Series(dtype=int)
    hio = get_holes_in_one_data(all_data)
    hio_ct = hio["Player"].value_counts() if not hio.empty else pd.Series(dtype=int)
    birdies_ct = all_data[all_data["GrossVP"] == -1]["Player"].value_counts()

    def fill(s):
        return s.reindex(players).fillna(0)

    int_fmt = lambda v: str(int(round(v)))
    return [
        ("TEGs Played",      fill(tegs_played),       False, int_fmt,                 False),
        ("Avg Gross vs Par", avg_gvp.reindex(players), True,  lambda v: f"{v:+.1f}",  False),
        ("Avg Stableford",   avg_stab.reindex(players), False, lambda v: f"{v:.1f}",  False),
        ("Total Trophies",   fill(total_trophies),    False, int_fmt,                 True),
        ("TEG Trophies",     fill(trophy),            False, int_fmt,                 True),
        ("Green Jackets",    fill(jacket),            False, int_fmt,                 True),
        ("Wooden Spoons",    fill(spoon),             False, int_fmt,                 True),
        ("Doubles",          fill(doubles),           False, int_fmt,                 True),
        ("Holes in One",     fill(hio_ct),            False, int_fmt,                 True),
        ("Eagles",           fill(eagles_ct),         False, int_fmt,                 True),
        ("Birdies",          fill(birdies_ct),        False, int_fmt,                 True),
    ]


# Headline metric cards. Row 1: career overview (4 cards). Row 2: scoring feats.
# Trophies are broken down in the dedicated Trophy Cabinet section below.
_METRIC_ROWS = [
    ["TEGs Played", "Total Trophies", "Avg Gross vs Par", "Avg Stableford"],
    ["Holes in One", "Eagles", "Birdies"],
]


def _build_overview_metrics(player_code: str) -> list[list[dict]]:
    """Build the headline metric cards, grouped into themed rows.

    Each card has value, label and cross-player rank. The Eagles and Holes in One
    cards also carry a ``tooltip`` listing where they were scored.
    """
    name = PLAYER_DICT[player_code]
    all_data = cached_load_all_data()
    rd_data = cached_round_data()
    winners = _get_winners_data()

    by_label = {}
    for label, series, ascending, fmt, unranked_if_zero in _metric_specs(all_data, rd_data, winners):
        if name in series.index and pd.notna(series[name]):
            raw = series[name]
            value = fmt(raw)
            rank = "–" if (unranked_if_zero and raw == 0) else _ordinal_rank(_rank_str(series, name, ascending))
        else:
            value, rank = "–", "–"
        by_label[label] = {"value": value, "label": label, "rank": rank}

    # Eagle / hole-in-one locations as hover detail on their metric cards.
    eagles = get_eagles_data(all_data)
    pe = eagles[eagles["Player"] == name] if not eagles.empty else eagles
    by_label["Eagles"]["tooltip"] = (
        "; ".join(f"{r['Course']} ({r['Hole']})" for _, r in pe.iterrows())
        if len(pe) else "No eagles yet")

    hio = get_holes_in_one_data(all_data)
    ph = hio[hio["Player"] == name] if not hio.empty else hio
    by_label["Holes in One"]["tooltip"] = (
        "; ".join(f"{r['Course']} ({r['Hole']})" for _, r in ph.iterrows())
        if len(ph) else "No holes in one yet")

    return [[by_label[lbl] for lbl in row] for row in _METRIC_ROWS]


def _build_trophy_section(player_code: str) -> dict:
    """Build trophy-cabinet data: counts and cross-player ranks for each honour.

    Rank is suppressed when the player has none of that honour. Doubles are
    reported separately as a footnote rather than as a standalone count.
    """
    name = PLAYER_DICT[player_code]
    all_data = cached_load_all_data()
    rd_data = cached_round_data()
    winners = _get_winners_data()

    specs = {label: (series, ascending) for label, series, ascending, _f, _z
             in _metric_specs(all_data, rd_data, winners)}

    def get(label):
        series, ascending = specs[label]
        count = int(series[name]) if name in series.index and pd.notna(series[name]) else 0
        rank = _ordinal_rank(_rank_str(series, name, ascending)) if count > 0 else ""
        return count, rank

    trophies, trophy_rank = get("TEG Trophies")
    jackets, jacket_rank = get("Green Jackets")
    spoons, spoon_rank = get("Wooden Spoons")
    doubles, doubles_rank = get("Doubles")

    return {
        "trophies": trophies,
        "jackets": jackets,
        "spoons": spoons,
        "doubles": doubles,
        "trophy_rank": trophy_rank,
        "jacket_rank": jacket_rank,
        "spoon_rank": spoon_rank,
        "doubles_rank": doubles_rank,
    }


# ---------------------------------------------------------------------------
# Career highlights / colour points
# ---------------------------------------------------------------------------

def _records_held(name: str) -> list[dict]:
    """Return the all-time TEG records this player holds, with value and context.

    Each record is a dict: ``label`` (record name), ``value`` (the record figure),
    ``detail`` (where/when it was set — TEG, year, area or course), and ``shared``
    (True when the record is jointly held). Count records (trophies, eagles) have
    no single location, so ``detail`` is empty for them.
    """
    all_data = cached_load_all_data()
    rd_data = cached_round_data()
    teg_data = cached_ranked_teg_data()
    winners = _get_winners_data().replace(r"\*", "", regex=True)

    records: list[dict] = []

    def teg_detail(row):
        return f"TEG {int(row['TEGNum'])} · {int(row['Year'])} · {row['Area']}"

    def round_detail(row):
        return f"TEG {int(row['TEGNum'])} R{int(row['Round'])} · {int(row['Year'])} · {row['Course']}"

    def extremum(df, col, kind, label, fmt_key, detail_fn):
        """Add a min/max record if held by ``name``; pick the player's own holding row."""
        target = df[col].min() if kind == "min" else df[col].max()
        holders = set(df[df[col] == target]["Player"])
        if name not in holders:
            return
        row = df[(df["Player"] == name) & (df[col] == target)].iloc[0]
        records.append({
            "label": label,
            "value": format_value(target, fmt_key),
            "detail": detail_fn(row),
            "shared": len(holders) > 1,
        })

    extremum(teg_data, "GrossVP", "min", "Lowest TEG (gross)", "GrossVP", teg_detail)
    extremum(teg_data, "Stableford", "max", "Highest TEG (Stableford)", "Stableford", teg_detail)
    extremum(rd_data, "GrossVP", "min", "Lowest round (gross)", "GrossVP", round_detail)
    extremum(rd_data, "Stableford", "max", "Highest round (Stableford)", "Stableford", round_detail)

    eagles = get_eagles_data(all_data)
    eagles_ct = eagles["Player"].value_counts() if not eagles.empty else pd.Series(dtype=int)

    def count_record(vc, label, unit):
        if vc.empty:
            return
        top = vc.max()
        holders = set(vc[vc == top].index)
        if name not in holders:
            return
        n = int(top)
        records.append({
            "label": label,
            "value": f"{n} {unit}{'' if n == 1 else 's'}",
            "detail": "",
            "shared": len(holders) > 1,
        })

    count_record(winners["TEG Trophy"].value_counts(), "Most TEG Trophies", "title")
    count_record(winners["Green Jacket"].value_counts(), "Most Green Jackets", "jacket")
    count_record(eagles_ct, "Most Eagles", "eagle")

    return records


def _build_highlights(player_code: str) -> list[dict]:
    """Build 'colour' points: best/worst course, best round/TEG, records, eagles."""
    name = PLAYER_DICT[player_code]
    all_data = cached_load_all_data()
    rd_data = cached_round_data()
    ranked_teg = cached_ranked_teg_data()
    items = []

    # Best / worst course by average gross vs par (min 2 rounds for stability)
    player_rd = rd_data[rd_data["Player"] == name]
    if not player_rd.empty:
        by_course = player_rd.groupby("Course")["GrossVP"].agg(["mean", "count"])
        by_course = by_course[by_course["count"] >= 2]
        if not by_course.empty:
            best_c = by_course["mean"].idxmin()
            worst_c = by_course["mean"].idxmax()
            items.append({"label": "Best Course", "value": best_c,
                          "detail": f"avg {by_course.loc[best_c, 'mean']:+.1f} over "
                                    f"{int(by_course.loc[best_c, 'count'])} rounds"})
            items.append({"label": "Worst Course", "value": worst_c,
                          "detail": f"avg {by_course.loc[worst_c, 'mean']:+.1f} over "
                                    f"{int(by_course.loc[worst_c, 'count'])} rounds"})

        # Best round
        br = player_rd.loc[player_rd["GrossVP"].idxmin()]
        items.append({"label": "Best Round", "value": format_value(br["GrossVP"], "GrossVP"),
                      "detail": f"TEG {int(br['TEGNum'])} R{int(br['Round'])} · {br['Course']}"})

    # Best TEG
    player_teg = ranked_teg[ranked_teg["Player"] == name]
    if not player_teg.empty:
        bt = player_teg.loc[player_teg["GrossVP"].idxmin()]
        items.append({"label": "Best TEG", "value": format_value(bt["GrossVP"], "GrossVP"),
                      "detail": f"TEG {int(bt['TEGNum'])}"})

    return items


# ---------------------------------------------------------------------------
# Header subtitle
# ---------------------------------------------------------------------------

def _build_subtitle(player_code: str) -> str:
    """Build subtitle like 'First: TEG N (YYYY) · Latest: TEG N (YYYY)'."""
    name = PLAYER_DICT[player_code]
    all_data = cached_load_all_data()
    player_data = all_data[all_data['Player'] == name]

    if player_data.empty:
        return "No TEG data"

    teg_info = player_data[['TEGNum', 'Year']].drop_duplicates().sort_values('TEGNum')
    first = teg_info.iloc[0]
    latest = teg_info.iloc[-1]

    return (
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


_WIN_RESULTS = {"Trophy", "Jacket", "Double"}


def _build_teg_results_table_html(df):
    """Render the per-TEG results table with win/loss colour in the rank/result cells.

    Green pill: a competition win (Result = Trophy/Jacket/Double, or a 1st-place
    Gross/Net rank). Red pill: the Wooden Spoon (Result = Spoon).
    """
    if df is None or df.empty:
        return "<p class='text-muted text-sm'>No TEG data.</p>"

    cols = list(df.columns)

    def col_cls(col):
        return 'col-rank' if col in _RANK_COLS else ('col-num' if col in _NUMERIC_COLS else 'col-player')

    rows = ["<table class='teg-table player-results-table'>", "<thead><tr>"]
    for col in cols:
        rows.append(f"<th class='{col_cls(col)}'>{escape(str(col))}</th>")
    rows.append("</tr></thead><tbody>")

    for _, row in df.iterrows():
        rows.append("<tr>")
        for col in cols:
            val = str(row[col])
            extra = ""
            if col == 'Result' and val in _WIN_RESULTS:
                extra = " result-win"
            elif col == 'Result' and val == 'Spoon':
                extra = " result-loss"
            elif col in ('Gross Rank', 'Net Rank') and val == '1st':
                extra = " result-win"
            cell = f"<span>{escape(val)}</span>" if extra else escape(val)
            rows.append(f"<td class='{col_cls(col)}{extra}'>{cell}</td>")
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
        teg_table_html = _build_teg_results_table_html(teg_table_df)
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

        fig.update_layout(**get_chart_style('streamlit'))
        chart_json = fig.to_json()

    return {
        "teg_table_html": teg_table_html,
        "chart_json": chart_json,
        "highlights": _build_highlights(player_code),
        "records_held": _records_held(PLAYER_DICT[player_code]),
        "metrics": _build_overview_metrics(player_code),
        "trophy": _build_trophy_section(player_code),
    }


# ---------------------------------------------------------------------------
# Tab: Rounds
# ---------------------------------------------------------------------------

def _build_rounds_chart(player_code: str) -> str | None:
    """Bar chart of gross vs par for every round, coloured by score and grouped
    by TEG (a small gap separates TEGs; rounds within a TEG sit flush)."""
    name = PLAYER_DICT[player_code]
    rd_data = cached_round_data()
    player_rd = rd_data[rd_data['Player'] == name].sort_values(['TEGNum', 'Round'])
    if player_rd.empty:
        return None

    xs, ys, customdata, teg_groups = [], [], [], []
    pos = 0
    prev_teg = None
    group_start = 0
    for _, r in player_rd.iterrows():
        teg = int(r['TEGNum'])
        if prev_teg is not None and teg != prev_teg:
            teg_groups.append(((group_start + pos - 1) / 2, prev_teg))
            pos += 1  # blank slot → visual gap between TEGs
            group_start = pos
        xs.append(pos)
        ys.append(float(r['GrossVP']))
        customdata.append([f"TEG {teg}", int(r['Round']), str(r.get('Course', ''))])
        prev_teg = teg
        pos += 1
    if prev_teg is not None:
        teg_groups.append(((group_start + pos - 1) / 2, prev_teg))

    fig = go.Figure(go.Bar(
        x=xs, y=ys, customdata=customdata,
        marker=dict(color=ys, colorscale='RdYlGn', reversescale=True, cmid=0,
                    line=dict(width=0)),
        hovertemplate=("%{customdata[0]} · R%{customdata[1]}<br>"
                       "%{customdata[2]}<br>Gross vs Par: %{y:+}<extra></extra>"),
    ))
    for cx, teg in teg_groups:
        fig.add_annotation(x=cx, y=0, yref='paper', yshift=-18,
                           text=str(teg), showarrow=False,
                           font=dict(size=9, color='gray'))
    fig.update_layout(
        yaxis_title="Gross vs Par",
        margin=dict(r=20, t=10, b=46, l=50),
        font=dict(family="monospace"),
        showlegend=False, bargap=0.0,
    )
    fig.add_annotation(x=0, y=0, yref='paper', xref='paper', yshift=-32,
                       text="TEG", showarrow=False, xanchor='right',
                       font=dict(size=9, color='gray'))
    fig.update_xaxes(showticklabels=False, fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    fig.update_layout(**get_chart_style('streamlit'))
    return fig.to_json()


def _build_rounds_context(player_code: str) -> dict:
    """Build context for the rounds tab."""
    name = PLAYER_DICT[player_code]

    chart_json = _build_rounds_chart(player_code)

    ranked_rd = cached_ranked_round_data()
    player_rd = ranked_rd[ranked_rd['Player'] == name].copy()

    if player_rd.empty:
        return {"rounds_table_html": "<p class='text-muted text-sm'>No round data.</p>",
                "rounds_chart_json": chart_json}

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
    return {"rounds_table_html": _build_simple_table_html(rd_df),
            "rounds_chart_json": chart_json}


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

        fig.update_layout(**get_chart_style('streamlit'))
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
# Roster (landing page cards)
# ---------------------------------------------------------------------------

def _build_roster() -> list[dict]:
    """Build roster card data for every player, ordered by honours then name.

    Each card carries identity (code/name/initials), a one-line career summary
    and three headline stats, plus trophy/jacket/spoon badges.
    """
    all_data = cached_load_all_data()
    rd_data = cached_round_data()
    winners = _get_winners_data()

    cards = []
    for code, name in PLAYER_DICT.items():
        player_data = all_data[all_data['Player'] == name]
        if player_data.empty:
            continue

        teg_info = player_data[['TEGNum', 'Year']].drop_duplicates().sort_values('TEGNum')
        n_tegs = len(teg_info)
        since_year = int(teg_info.iloc[0]['Year'])

        player_rds = rd_data[rd_data['Player'] == name]
        avg_gvp = player_rds['GrossVP'].mean() if not player_rds.empty else None
        avg_stab = player_rds['Stableford'].mean() if not player_rds.empty else None

        trophy_count = int((winners['TEG Trophy'] == name).sum())
        jacket_count = int((winners['Green Jacket'] == name).sum())
        spoon_count = int((winners['HMM Wooden Spoon'] == name).sum())
        total_trophies = trophy_count + jacket_count

        badges = []
        if trophy_count:
            badges.append({"text": f"Trophy ×{trophy_count}", "style": "accent"})
        if jacket_count:
            badges.append({"text": f"Jacket ×{jacket_count}", "style": "accent"})
        if spoon_count:
            badges.append({"text": f"Spoon ×{spoon_count}", "style": "muted"})

        cards.append({
            "code": code,
            "name": name,
            "n_tegs": n_tegs,
            "since_year": since_year,
            "avg_gvp": f"{avg_gvp:+.1f}" if avg_gvp is not None else "–",
            "avg_stab": f"{avg_stab:.1f}" if avg_stab is not None else "–",
            "total_trophies": total_trophies,
            "badges": badges,
        })

    cards.sort(key=lambda c: (-c["total_trophies"], -c["n_tegs"], c["name"]))
    return cards


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/player")
async def player_index(request: Request):
    return templates.TemplateResponse("player_index.html", {
        "request": request,
        "active_page": "player",
        "player_list": _get_player_list(),
        "roster": _build_roster(),
    })


@router.get("/player/{player_code}")
async def player_page(request: Request, player_code: str):
    pc = _validate_player(player_code)
    name = PLAYER_DICT[pc]
    theme = request.state.theme

    subtitle = _build_subtitle(pc)
    overview_ctx = _build_overview_context(pc, theme)

    return templates.TemplateResponse("player.html", {
        "request": request,
        "active_page": "player",
        "player_code": pc,
        "player_name": name,
        "player_list": _get_player_list(),
        "subtitle": subtitle,
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
    else:
        raise HTTPException(status_code=404, detail=f"Unknown tab: {tab_name}")

    return templates.TemplateResponse(template, {
        "request": request,
        "player_code": pc,
        **ctx,
    })
