"""History section routes: /history, /honours, /results, /player-rankings."""

import logging
import re
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates
from markupsafe import escape

from teg_analysis.core.players import get_name_to_code
from teg_analysis.analysis.history import (
    prepare_complete_history_table_fast,
    calculate_trophy_jacket_doubles,
    get_eagles_data,
    get_holes_in_one_data,
)
from teg_analysis.analysis.player_rankings import (
    create_teg_ranking_table,
    create_net_competition_ranking_table,
    create_combined_position_summary,
)
from teg_analysis.core.metadata import get_scorecard_data
from teg_analysis.display.scorecards import (
    build_round_comparison_responsive,
)
from webapp.deps import (
    cached_load_all_data,
    cached_round_data,
    cached_complete_teg_data,
    cached_ranked_teg_data,
    cached_winners,
    create_leaderboard,
    format_value,
    get_available_teg_numbers,
    get_default_teg_num,
    get_net_competition_measure,
    get_rounds_for_teg,
)
from webapp.chart_utils import create_cumulative_graph, adjusted_stableford, adjusted_grossvp
from webapp.tables import df_to_html as _df_to_html

logger = logging.getLogger(__name__)

# Country (or UK nation) name -> flag-icons code. Keys are lower-cased and matched
# against the last comma-separated part of an Area string ("Region, Country").
# Add aliases (e.g. "usa"/"united states") so the CSV can be written naturally.
_COUNTRY_FLAG_CODES = {
    # Already used by existing TEGs
    "england": "gb-eng",
    "portugal": "pt",
    "spain": "es",
    # Other UK nations
    "scotland": "gb-sct",
    "wales": "gb-wls",
    "northern ireland": "gb-nir",
    "ireland": "ie",
    # Likely future destinations
    "france": "fr",
    "italy": "it",
    "usa": "us",
    "united states": "us",
    "united states of america": "us",
    "america": "us",
    "germany": "de",
    "netherlands": "nl",
    "belgium": "be",
    "switzerland": "ch",
    "austria": "at",
    "sweden": "se",
    "morocco": "ma",
    "turkey": "tr",
    "united arab emirates": "ae",
    "uae": "ae",
    "south africa": "za",
    "mauritius": "mu",
    "thailand": "th",
    "mexico": "mx",
}


def _area_flag_html(area_str: str) -> str:
    """Return a flag-icons <span> for the country in an 'Region, Country' area string."""
    parts = str(area_str).split(",")
    if len(parts) < 2:
        return ""
    country = parts[-1].strip().lower()
    code = _COUNTRY_FLAG_CODES.get(country, "")
    if not code:
        return ""
    return f"<span class='fi fi-{code} teg-flag'></span>"


router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _wrap_player_name(name) -> str:
    """Split "David MULLIN" into first/last spans so narrow screens can break
    the line between them (mirrors the Streamlit history table)."""
    if not isinstance(name, str) or not name.strip():
        return "" if name is None else escape(str(name))
    first, *rest = re.split(r"\s+", name.strip(), maxsplit=1)
    last = rest[0] if rest else ""
    return (f"<span class='player-name'><span class='first'>{escape(first)}</span> "
            f"<span class='last'>{escape(last)}</span></span>")


def _history_table_html(df: pd.DataFrame) -> str:
    """Render the TEG History table the way the Streamlit page does: a compound
    TEG/area cell (area as smaller secondary text beneath the TEG label), the
    standalone Area column dropped, the TEG Trophy winner emphasised, and player
    names wrapped in first/last spans."""
    if df is None or df.empty:
        return "<p class='text-muted text-sm'>No data available.</p>"

    name_cols = ["TEG Trophy", "Green Jacket", "HMM Wooden Spoon"]
    headers = ["TEG"] + name_cols

    rows = ["<table class='teg-table history-table'>", "<thead><tr>"]
    for col in headers:
        rows.append(f"<th>{escape(col)}</th>")
    rows.append("</tr></thead><tbody>")

    for _, row in df.iterrows():
        teg = escape(str(row.get("TEG", "")))
        area_raw = str(row.get("Area", ""))
        area = area_raw.split(",")[0].strip()
        flag_html = _area_flag_html(area_raw)
        teg_cell = (
            f"<div class='teg-cell'>"
            f"{flag_html}"
            f"<span class='teg-text'>"
            f"<span class='teg-label'>{teg}</span>"
            f"<span class='area-label'>{escape(area)}</span>"
            f"</span>"
            f"</div>"
        )
        rows.append("<tr>")
        rows.append(f"<td>{teg_cell}</td>")
        for col in name_cols:
            rows.append(f"<td>{_wrap_player_name(row.get(col))}</td>")
        rows.append("</tr>")
    rows.append("</tbody></table>")
    return "".join(rows)


_RANK_PAT = re.compile(r"^\d+=?$")


def _ranking_table_html(df: pd.DataFrame, player_col: str = "Player",
                        link_players: bool = False) -> str:
    """Render a player-ranking table with first/last-place conditional formatting.

    Mirrors the Streamlit ``post_process_ranking_table``: per column, the rank 1
    cell gets a green fill (white text) and the worst rank a pale-red fill (dark
    red text). Rank values are wrapped in ``<span>`` so the pill shape can sit
    behind the number. Non-rank cells (e.g. "-") are left plain.
    """
    if df is None or df.empty:
        return "<p class='text-muted text-sm'>No data available.</p>"

    cols = list(df.columns)
    if player_col not in cols:
        player_col = cols[0]
    rank_cols = [c for c in cols if c != player_col]

    # Worst (max) real rank per column, ignoring "-" and other non-rank values.
    col_max_rank = {}
    for c in rank_cols:
        nums = [int(str(v).replace("=", "")) for v in df[c] if _RANK_PAT.match(str(v))]
        col_max_rank[c] = max(nums) if nums else None

    rows = ["<table class='teg-table player-ranking-table'>", "<thead><tr>"]
    for col in cols:
        rows.append(f"<th>{escape(str(col))}</th>")
    rows.append("</tr></thead><tbody>")

    for _, row in df.iterrows():
        rows.append("<tr>")
        for col in cols:
            s = str(row[col])
            if col == player_col:
                code = get_name_to_code().get(s) if link_players else None
                if code:
                    rows.append(f"<td><a href='/player/{code}'>{escape(s)}</a></td>")
                else:
                    rows.append(f"<td>{escape(s)}</td>")
            elif _RANK_PAT.match(s):
                rank_num = int(s.replace("=", ""))
                cls = ""
                if rank_num == 1:
                    cls = " class='first-place'"
                elif col_max_rank[col] is not None and rank_num == col_max_rank[col]:
                    cls = " class='last-place'"
                rows.append(f"<td{cls}><span>{escape(s)}</span></td>")
            else:
                rows.append(f"<td>{escape(s)}</td>")
        rows.append("</tr>")
    rows.append("</tbody></table>")
    return "".join(rows)


# --- /history -----------------------------------------------------------------

@router.get("/history")
def history_page(request: Request):
    try:
        df = prepare_complete_history_table_fast()
        table_html = _history_table_html(df)
        table_html += ("<p class='text-muted text-sm mt-3'>*Green Jacket awarded in TEG 5 for "
                       "best stableford round; DM had best gross score.</p>")
    except Exception as e:
        logger.exception("history_page failed")
        table_html = f"<p class='text-muted'>Error: {e}</p>"

    return templates.TemplateResponse("data_table.html", {
        "request": request,
        "active_page": "history",
        "title": "TEG History",
        "subtitle": "TEG locations and winners by year",
        "table_html": table_html,
        "sections": None,
    })


# --- /honours -----------------------------------------------------------------

HONOURS_TABS = [
    ("trophy", "TEG Trophy"),
    ("jacket", "Green Jacket"),
    ("spoon", "Wooden Spoon"),
    ("doubles", "Doubles"),
    ("eagles", "Eagles"),
    ("hio", "Holes in One"),
]


def _compress_ranges(nums):
    """Compress consecutive integers into range strings. Only collapse runs of 3+."""
    if not nums:
        return ""
    nums = sorted(set(nums))
    runs = []
    start = prev = nums[0]
    for n in nums[1:]:
        if n == prev + 1:
            prev = n
        else:
            runs.append((start, prev))
            start = prev = n
    runs.append((start, prev))
    parts = []
    for a, b in runs:
        if b - a >= 2:
            parts.append(f"{a}-{b}")
        elif b - a == 1:
            parts.extend([str(a), str(b)])
        else:
            parts.append(str(a))
    return ", ".join(parts)


def _summarise_wins(winners_df: pd.DataFrame, col: str) -> str:
    """Build a summary table: Player, Wins, TEGs with compressed ranges."""
    # Extract TEG number from 'TEG' column (e.g. "TEG 5" -> 5)
    df = winners_df[['TEG', col]].copy()
    df['_teg_num'] = df['TEG'].str.extract(r'(\d+)').astype(int)

    grouped = df.groupby(col)['_teg_num'].agg(['count', list]).reset_index()
    grouped.columns = ['Player', 'Wins', '_nums']
    grouped['TEGs'] = grouped['_nums'].apply(_compress_ranges)
    grouped = grouped.drop(columns=['_nums'])
    grouped = grouped.sort_values('Wins', ascending=False).reset_index(drop=True)

    return _df_to_html(grouped, link_players=True)


def _honours_tab_context(tab: str) -> dict:
    """Build context for an honours tab."""
    try:
        all_data = cached_load_all_data()
        winners_df = cached_winners()

        # The selected tab already names the section, so no per-section heading
        # is rendered (see partials/honours_tab.html). Tabs that carry extra
        # context (the Doubles count) surface it as a caption instead.
        sections = []

        if tab == "trophy":
            sections.append({"table_html": _summarise_wins(winners_df, "TEG Trophy")})

        elif tab == "jacket":
            jacket_html = _summarise_wins(winners_df, "Green Jacket")
            jacket_html += ("<p class='text-muted text-sm mt-3'>*Green Jacket awarded in TEG 5 for "
                            "best stableford round; DM had best gross score.</p>")
            sections.append({"table_html": jacket_html})

        elif tab == "spoon":
            sections.append({"table_html": _summarise_wins(winners_df, "HMM Wooden Spoon")})

        elif tab == "doubles":
            doubles_df, count = calculate_trophy_jacket_doubles(winners_df)
            if doubles_df is not None and not doubles_df.empty:
                html = (f"<p class='text-muted text-sm mb-2'>There have been {count} "
                        f"trophy / jacket doubles.</p>") + _df_to_html(doubles_df)
            else:
                html = "<p class='text-muted text-sm'>No doubles recorded.</p>"
            sections.append({"table_html": html})

        elif tab == "eagles":
            eagles = get_eagles_data(all_data)
            sections.append({"table_html": _df_to_html(eagles, link_players=True)})

        elif tab == "hio":
            hio = get_holes_in_one_data(all_data)
            if hio is not None and not hio.empty:
                sections.append({"table_html": _df_to_html(hio, link_players=True)})
            else:
                sections.append({"table_html": "<p class='text-muted text-sm'>No holes in one have yet been scored on a TEG</p>"})

        return {"sections": sections}
    except Exception as e:
        logger.exception("_honours_tab_context failed")
        return {"error": str(e)}


@router.get("/honours")
def honours_page(request: Request):
    ctx = _honours_tab_context("trophy")
    return templates.TemplateResponse("honours.html", {
        "request": request,
        "active_page": "honours",
        "tabs": HONOURS_TABS,
        "active_tab": "trophy",
        **ctx,
    })


@router.get("/honours/tab/{tab_name}")
def honours_tab(request: Request, tab_name: str):
    ctx = _honours_tab_context(tab_name)
    return templates.TemplateResponse("partials/honours_tab.html", {
        "request": request,
        **ctx,
    })


# --- /results -----------------------------------------------------------------

RESULTS_CHART_TYPES = [("standard", "Standard"), ("adjusted", "Adjusted scale"), ("ranking", "Ranking")]


def _teg_is_complete(teg_num: int) -> bool:
    """True if the TEG appears in the completed-TEGs status file (mirrors the
    Streamlit 'final results' check)."""
    try:
        from teg_analysis.io.file_operations import read_file
        completed = read_file('data/completed_tegs.csv')
        return (not completed.empty) and int(teg_num) in completed['TEGNum'].astype(int).values
    except Exception:
        return False


def _leaderboard_table_html(df: pd.DataFrame) -> str:
    """Render a results leaderboard: full-width, rank/score columns centred,
    player linked, and the leading row(s) tinted (rank starting with '1')."""
    if df is None or df.empty:
        return "<p class='text-muted text-sm'>No data available.</p>"

    rows = ["<table class='teg-table leaderboard-table'>", "<thead><tr>"]
    for col in df.columns:
        cls = "col-rank" if col == "Rank" else ("col-player" if col == "Player" else "col-num")
        rows.append(f"<th class='{cls}'>{escape(str(col))}</th>")
    rows.append("</tr></thead><tbody>")

    for _, row in df.iterrows():
        tr_cls = " class='top-rank'" if str(row["Rank"]).startswith("1") else ""
        rows.append(f"<tr{tr_cls}>")
        for col in df.columns:
            val = row[col]
            if col == "Player":
                code = get_name_to_code().get(str(val))
                cell = (f"<a href='/player/{code}'>{escape(str(val))}</a>" if code
                        else escape(str(val)))
                rows.append(f"<td class='col-player'>{cell}</td>")
            elif col == "Rank":
                rows.append(f"<td class='col-rank'>{escape(str(val))}</td>")
            elif col == "Total":
                rows.append(f"<td class='col-num total'>{escape(str(val))}</td>")
            else:
                rows.append(f"<td class='col-num'>{escape(str(val))}</td>")
        rows.append("</tr>")
    rows.append("</tbody></table>")
    return "".join(rows)


def _results_chart_meta(tab: str, variant: str, net_measure: str, teg_name: str) -> dict:
    """Title / subtitle / note / data-source for the race chart.

    The chart itself is a placeholder pending the chart rebuild (see
    webapp/README look-and-feel roadmap, item 1b); ``series`` records where the
    underlying data comes from so the placeholder can point at it.
    """
    if tab == "gross":
        competition = "Green Jacket"
        if variant == "ranking":
            short, direction, series = "Tournament ranking progression", "Lower = better", "Rank_GrossVP_TEG"
        elif variant == "adjusted":
            short, direction, series = "Cumulative gross score (adjusted scale vs. bogey)", "Lower = better", "GrossVP Cum TEG via adjusted_grossvp"
        else:
            short, direction, series = "Cumulative gross score vs. par", "Lower = better", "GrossVP Cum TEG"
    else:
        competition = "TEG Trophy"
        stableford = net_measure == "Stableford"
        if variant == "ranking":
            short, direction, series = "Tournament ranking progression", "Lower = better", "Rank_Stableford_TEG"
        elif variant == "adjusted":
            if stableford:
                short, direction, series = "Cumulative stableford points (adjusted scale)", "Higher = better", "Stableford Cum TEG via adjusted_stableford"
            else:
                short, direction, series = "Cumulative net score (adjusted scale vs. par)", "Lower = better", "NetVP Cum TEG via adjusted_grossvp"
        else:
            if stableford:
                short, direction, series = "Cumulative stableford points", "Higher = better", "Stableford Cum TEG"
            else:
                short, direction, series = "Cumulative net score vs. par", "Lower = better", "NetVP Cum TEG"

    if variant == "ranking":
        note = "Shows tournament ranking progression (1st, 2nd, 3rd, etc.)."
    elif variant == "adjusted":
        note = ("Adjusted view 'zooms in' by showing performance vs. par to more "
                "clearly show gaps between players.")
    else:
        note = ""

    return {
        "chart_title": f"{competition} race: {teg_name}",
        "chart_subtitle": f"{short} | {direction}",
        "chart_note": note,
        "chart_series": series,
    }


def _build_race_figure_json(tab: str, variant: str, net_measure: str, teg_name: str) -> str | None:
    """Build race chart JSON for the given (tab, variant, net_measure) combination."""
    try:
        df = cached_load_all_data()
        stableford = net_measure == "Stableford"

        if tab == "gross":
            if variant == "ranking":
                y_series, y_calc, chart_type, ylabel = "Rank_GrossVP_TEG", None, "ranking", "Tournament Ranking"
            elif variant == "adjusted":
                y_series, y_calc, chart_type, ylabel = "GrossVP Cum TEG", adjusted_grossvp, "gross", "Gross vs bogey"
            else:
                y_series, y_calc, chart_type, ylabel = "GrossVP Cum TEG", None, "gross", "Cumulative gross vs par"
        else:
            if variant == "ranking":
                y_series, y_calc, chart_type, ylabel = "Rank_Stableford_TEG", None, "ranking", "Tournament Ranking"
            elif variant == "adjusted":
                if stableford:
                    y_series, y_calc, chart_type, ylabel = "Stableford Cum TEG", adjusted_stableford, "stableford", "Stableford (adjusted)"
                else:
                    y_series, y_calc, chart_type, ylabel = "NetVP Cum TEG", adjusted_grossvp, "gross", "Net vs par (adjusted)"
            else:
                if stableford:
                    y_series, y_calc, chart_type, ylabel = "Stableford Cum TEG", None, "stableford", "Cumulative Stableford"
                else:
                    y_series, y_calc, chart_type, ylabel = "NetVP Cum TEG", None, "gross", "Cumulative net vs par"

        fig = create_cumulative_graph(
            df, teg_name, y_series, title="",
            y_calculation=y_calc, y_axis_label=ylabel, chart_type=chart_type,
        )
        return fig.to_json()
    except Exception:
        return None


def _results_context(teg_num: int, tab: str = "net", chart_variant: str = "adjusted") -> dict:
    """Build context for full results page."""
    try:
        if tab == "scorecards":
            rounds = get_rounds_for_teg(teg_num)
            parts = ['<link rel="stylesheet" href="/static/scorecard.css?v=20">']
            for r in rounds:
                try:
                    rd = get_scorecard_data(teg_num, r)
                    if rd is None or rd.empty:
                        continue
                    # Responsive block: landscape on desktop/iPad, portrait on phone.
                    block = build_round_comparison_responsive(rd, uid=f"res{teg_num}r{r}")
                    parts.append("<section class='sc-round'>")
                    parts.append(f"<h2 class='section-title'>Round {r}</h2>")
                    parts.append(block)
                    parts.append("</section>")
                except Exception:
                    continue
            table_html = "".join(parts) if len(parts) > 1 else "<p class='text-muted'>No rounds found.</p>"
            return {"result_title": "Scorecards", "table_html": table_html, "raw_table": True}

        if tab == "report":
            from pathlib import Path
            import markdown as md_lib
            # Prefer the styled report; fall back to the plain main report draft.
            candidates = [
                Path(f"data/commentary/teg_{teg_num}_report_styled.md"),
                Path(f"data/commentary/drafts/teg_{teg_num}_main_report.md"),
                Path(f"data/commentary/teg_{teg_num}_main_report.md"),
            ]
            path = next((p for p in candidates if p.is_file()), None)
            if path is not None:
                html = md_lib.markdown(
                    path.read_text(encoding="utf-8"),
                    extensions=["extra", "sane_lists", "smarty", "toc"],
                )
                caption = ""
                if int(teg_num) < 8:
                    caption = ("<p class='text-muted text-sm'>NB: Before TEG 8 the TEG Trophy was "
                               "decided by best net score (total net vs par), not Stableford points.</p>")
                return {
                    "result_title": "Report",
                    "table_html": f'{caption}<div class="teg-report">{html}</div>',
                }
            return {
                "result_title": "Report",
                "table_html": (
                    f"<p class='text-muted text-sm'>No report available yet for TEG {teg_num}.</p>"
                ),
            }

        rd_data = cached_round_data()
        teg_rd = rd_data[rd_data['TEGNum'] == teg_num]

        if teg_rd.empty:
            return {"error": f"No data found for TEG {teg_num}"}

        teg_name = f"TEG {teg_num}"
        complete = _teg_is_complete(teg_num)
        leader_label = "Champion" if complete else "Leader"
        status_word = "Final" if complete else "Latest"
        net_measure = get_net_competition_measure(teg_num)
        net_ascending = net_measure == 'NetVP'

        if tab == "gross":
            competition = "Green Jacket"
            value_col = 'GrossVP'
            lb = create_leaderboard(teg_rd, value_col, ascending=True)
        else:
            competition = "TEG Trophy"
            value_col = net_measure
            lb = create_leaderboard(teg_rd, value_col, ascending=net_ascending)

        # Champion / wooden spoon from the (unformatted) leaderboard order.
        champion = str(lb.iloc[0]['Player']) if not lb.empty else ""
        spoon = str(lb.iloc[-1]['Player']) if not lb.empty else ""
        if tab == "gross":
            callout = f"{leader_label}: <strong>{escape(champion)}</strong>"
        else:
            callout = (f"{leader_label}: <strong>{escape(champion)}</strong> &nbsp;|&nbsp; "
                       f"Wooden spoon: <strong>{escape(spoon)}</strong>")

        # Format score columns (+/- signs etc.) then build the full-width table.
        for col in [c for c in lb.columns if c not in ['Rank', 'Player']]:
            lb[col] = lb[col].apply(lambda x: format_value(x, value_col))
        table_html = _leaderboard_table_html(lb)

        # Phone-only card reflow of the same standings (MOBILE_PLAN M2.7).
        # Rendered by partials/lb_cards.html; hidden above 640px by mobile.css.
        round_cols = [c for c in lb.columns if c not in ('Rank', 'Player', 'Total')]
        lb_cards = [{
            "rank": str(row['Rank']),
            "player": str(row['Player']),
            "code": get_name_to_code().get(str(row['Player'])),
            "rounds": [(c, str(row[c])) for c in round_cols],
            "total": str(row['Total']),
            "lead": str(row['Rank']).startswith('1'),
        } for _, row in lb.iterrows()]
        lb_hero = {
            "label": leader_label,
            "champion": champion,
            "champion_total": lb_cards[0]["total"] if lb_cards else "",
            "spoon": spoon if tab != "gross" else None,
            "spoon_total": lb_cards[-1]["total"] if lb_cards else "",
            "unit": "pts" if value_col == "Stableford" else "vs par",
        }

        chart_meta = _results_chart_meta(tab, chart_variant, net_measure, teg_name)
        figure_json = _build_race_figure_json(tab, chart_variant, net_measure, teg_name)
        return {
            "is_leaderboard": True,
            "section_title": f"{competition} {status_word} Leaderboard",
            "callout": callout,
            "table_html": table_html,
            "lb_cards": lb_cards,
            "lb_hero": lb_hero,
            "teg_name": teg_name,
            "chart_types": RESULTS_CHART_TYPES,
            "active_chart_variant": chart_variant,
            "figure_json": figure_json,
            **chart_meta,
        }
    except Exception as e:
        logger.exception("_results_context failed")
        return {"error": str(e)}


@router.get("/results")
def results_page(request: Request):
    teg_num = get_default_teg_num()
    teg_numbers = get_available_teg_numbers()
    ctx = _results_context(teg_num, "net")
    return templates.TemplateResponse("results.html", {
        "request": request,
        "active_page": "results",
        "teg_numbers": teg_numbers,
        "selected_teg": teg_num,
        "active_tab": "net",
        **ctx,
    })


@router.get("/results/table")
def results_table(request: Request, teg: int = Query(...), tab: str = Query("net"),
                        chart_variant: str = Query("adjusted")):
    ctx = _results_context(teg, tab, chart_variant)
    return templates.TemplateResponse("partials/results_table.html", {
        "request": request,
        "selected_teg": teg,
        "active_tab": tab,
        **ctx,
    })


# --- /player-rankings ---------------------------------------------------------

PLAYER_RANKINGS_TABS = [
    ("trophy", "TEG Trophy"),
    ("jacket", "Green Jacket"),
]


PR_ROW_DIMS = [("Player", "Full Name"), ("Pl", "Initials")]
PR_COL_DIMS = [("TEGNum", "TEG Number"), ("TEG", "TEG Name")]


def _format_ranking_for_display(ranking: pd.DataFrame, player_col: str) -> pd.DataFrame:
    """Stringify TEG column headers and show '-' for non-participation.

    Keeps the header as the value of the selected column dimension: a bare
    number when columns are TEG numbers (e.g. ``2``), or the full TEG name when
    columns are TEG names (e.g. ``TEG 2``)."""
    df = ranking.copy()
    rename = {}
    for col in df.columns:
        if col == player_col:
            continue
        try:
            rename[col] = str(int(col))
        except (ValueError, TypeError):
            rename[col] = str(col)
    df = df.rename(columns=rename)
    for col in [c for c in df.columns if c != player_col]:
        df[col] = df[col].apply(lambda x: "-" if pd.isna(x) else str(x))
    return df


def _player_rankings_context(tab: str, row_dim: str = "Player", col_dim: str = "TEGNum") -> dict:
    try:
        if row_dim not in ("Player", "Pl"):
            row_dim = "Player"
        if col_dim not in ("TEGNum", "TEG"):
            col_dim = "TEGNum"
        teg_data = cached_complete_teg_data()
        if tab == "trophy":
            ranking = create_net_competition_ranking_table(teg_data, row_dim, col_dim)
            rank_title = "TEG Trophy Rankings by TEG (Net Competition)"
            caption = "Uses Net vs Par for TEGs 2-7, Stableford Points for TEG 8+."
            summary_title = "TEG Trophy rankings summary"
        else:
            ranking = create_teg_ranking_table(teg_data, "GrossVP", row_dim, col_dim)
            rank_title = "Green Jacket Rankings by TEG (Gross vs Par)"
            caption = "Lower scores are better. Ties marked '='; '-' = did not participate."
            summary_title = "Green Jacket rankings summary"

        summary = create_combined_position_summary(ranking, row_dim)
        display = _format_ranking_for_display(ranking, row_dim)

        sections = [
            {"title": rank_title, "caption": caption,
             "table_html": _ranking_table_html(display, player_col=row_dim,
                                                link_players=(row_dim == "Player"))},
            {"title": summary_title, "caption": None,
             "table_html": _df_to_html(summary, table_class="teg-table position-table")},
        ]
        return {"sections": sections, "row_dims": PR_ROW_DIMS, "col_dims": PR_COL_DIMS,
                "selected_row_dim": row_dim, "selected_col_dim": col_dim}
    except Exception as e:
        logger.exception("_player_rankings_context failed")
        return {"error": str(e)}


@router.get("/player-rankings")
def player_rankings_page(request: Request, row_dim: str = Query("Player"), col_dim: str = Query("TEGNum")):
    default_tab = "trophy"
    ctx = _player_rankings_context(default_tab, row_dim, col_dim)
    return templates.TemplateResponse("player_rankings.html", {
        "request": request,
        "active_page": "player-rankings",
        "tabs": PLAYER_RANKINGS_TABS,
        "active_tab": default_tab,
        **ctx,
    })


@router.get("/player-rankings/tab")
def player_rankings_tab(request: Request, tab: str = "trophy",
                              row_dim: str = Query("Player"), col_dim: str = Query("TEGNum")):
    ctx = _player_rankings_context(tab, row_dim, col_dim)
    return templates.TemplateResponse("partials/player_rankings_tab.html", {
        "request": request,
        "active_tab": tab,
        **ctx,
    })
