"""History section routes: /history, /honours, /results, /player-rankings."""

import logging
import re
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates
from markupsafe import escape

from teg_analysis.core.players import get_name_to_code, get_player_name
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
from teg_analysis.io.file_operations import read_file
from teg_analysis.constants import ROUND_INFO_CSV
from teg_analysis.reporting.newspaper_edition import available_tegs
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
)
from webapp.chart_utils import (
    create_cumulative_graph,
    adjusted_stableford,
    adjusted_grossvp,
    get_teg_chart_readout,
    CROWDED_FIELD_THRESHOLD,
)
from webapp.tables import df_to_html as _df_to_html, EMPTY_TABLE_HTML

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


def _round_metadata_by_teg() -> dict:
    """{TEGNum: [{"round": n, "course": str, "date": str}, ...]}, sorted by round,
    from round_info.csv (the same canonical per-round source `get_teg_metadata`
    already reads). Powers the mobile History disclosure row's round-by-round
    detail. Read and grouped once per request, not per table row. Missing or
    unreadable metadata degrades to an empty dict -- the winners table itself
    must never depend on this succeeding."""
    try:
        round_info = read_file(ROUND_INFO_CSV)
    except Exception:
        logger.exception("_round_metadata_by_teg: round_info.csv unavailable")
        return {}
    result: dict = {}
    for teg_num, group in round_info.sort_values(["TEGNum", "Round"]).groupby("TEGNum"):
        result[int(teg_num)] = [
            {"round": int(r["Round"]), "course": str(r["Course"]), "date": str(r["Date"])}
            for _, r in group.iterrows()
        ]
    return result


def _history_table_html(df: pd.DataFrame, round_metadata: dict | None = None) -> str:
    """Render the TEG History table the way the Streamlit page does: a compound
    TEG/area cell (area as smaller secondary text beneath the TEG label), the
    standalone Area column dropped, the TEG Trophy winner emphasised, and player
    names wrapped in first/last spans.

    When `round_metadata` (see `_round_metadata_by_teg`) has an entry for a TEG,
    its TEG cell becomes a disclosure toggle revealing a full-width row with the
    area and each round's course/date -- the mobile History layout's expandable
    detail (desktop is unaffected; the toggle is a real <button>, but its default
    chrome is reset to match the plain cell it replaces, so it looks identical
    until interacted with). A TEG absent from round_metadata (e.g. a not-yet-
    played "TBC" entry) renders a plain, non-interactive TEG cell instead."""
    if df is None or df.empty:
        return "<p class='text-muted text-sm'>No data available.</p>"

    round_metadata = round_metadata or {}
    name_cols = ["TEG Trophy", "Green Jacket", "HMM Wooden Spoon"]
    # Trailing unlabelled column: the round/course/date disclosure "+/-"
    # indicator. Desktop keeps the TEG cell itself as the full-width click
    # target (unchanged) and never shows this column (display:none,
    # base-vars.css); mobile hides the indicator that used to overlay the TEG
    # cell and shows it here instead, in a narrow final column.
    headers = ["TEG"] + name_cols + [""]
    # Mobile columns are too narrow for "HMM Wooden Spoon" etc. on one line;
    # desktop keeps the full name (default-visible .th-full), mobile swaps to
    # the approved prototype's short Trophy/Jacket/Spoon heading (.th-short,
    # hidden by default in base-vars.css, shown only in .history-page).
    short_headers = {"TEG Trophy": "Trophy", "Green Jacket": "Jacket", "HMM Wooden Spoon": "Spoon"}

    rows = ["<table class='teg-table history-table'>", "<thead><tr>"]
    for col in headers:
        short = short_headers.get(col)
        if short:
            rows.append(f"<th><span class='th-full'>{escape(col)}</span><span class='th-short'>{escape(short)}</span></th>")
        elif col:
            rows.append(f"<th>{escape(col)}</th>")
        else:
            rows.append("<th class='history-toggle-th'></th>")
    rows.append("</tr></thead><tbody>")

    for _, row in df.iterrows():
        teg_raw = str(row.get("TEG", ""))
        # Split the trailing "(YYYY)" out of its own span -- desktop keeps
        # showing it inline (unstyled, so visually identical to before); the
        # mobile column is narrow enough that "TEG 2" alone already needs
        # two lines with the flag, so mobile.css hides .teg-year there.
        teg_parts = re.match(r"^(.*?)(?:\s*\(([^)]*)\))?$", teg_raw)
        teg_main = escape(teg_parts.group(1) if teg_parts else teg_raw)
        teg_year = escape(teg_parts.group(2)) if teg_parts and teg_parts.group(2) else ""
        area_raw = str(row.get("Area", ""))
        area = area_raw.split(",")[0].strip()
        flag_html = _area_flag_html(area_raw)
        teg_num_match = re.search(r"\d+", teg_raw)
        teg_num = int(teg_num_match.group()) if teg_num_match else None
        rounds = round_metadata.get(teg_num) if teg_num is not None else None

        # Year renders twice, CSS-toggled by viewport (same technique as the
        # short/full headers above): desktop's original compound label keeps
        # it on the TEG-number line (.teg-year, default-visible); the
        # approved prototype's compact mobile line puts it with the flag/
        # area instead (.teg-year--mobile, hidden by default, shown only in
        # .history-page) -- "TEG 2" alone fits the narrow column, but the
        # year is still visible at a glance rather than hidden behind a tap.
        # Mobile's collapsed row shows two lines: "TEG n" then flag + year --
        # no region text there (region only appears in the expanded detail
        # row). The flag renders twice, CSS-toggled by viewport (same
        # technique as the year above): desktop puts it on the region line,
        # sized to that line's text height (.teg-flag-desktop, inside
        # .area-row); mobile shows a second copy inline with the year on its
        # own line (.teg-mobile-meta).
        teg_flag_desktop = f"<span class='teg-flag-desktop'>{flag_html}</span>" if flag_html else ""
        teg_label = (
            f"<span class='teg-text'>"
            f"<span class='teg-label'>{teg_main}"
            + (f" <span class='teg-year'>({teg_year})</span>" if teg_year else "")
            + f"</span>"
            f"<span class='area-row'>{teg_flag_desktop}<span class='area-label'>{escape(area)}</span></span>"
            f"<span class='teg-mobile-meta'>{flag_html}"
            + (f"<span class='teg-year--mobile'>{teg_year}</span>" if teg_year else "")
            + f"</span>"
            f"</span>"
        )
        detail_id = f"history-{teg_num}-details"
        if rounds:
            teg_cell = (
                f"<button type='button' class='teg-cell history-toggle action' "
                f"data-history-toggle aria-expanded='false' aria-controls='{detail_id}'>"
                f"{teg_label}</button>"
            )
        else:
            teg_cell = f"<div class='teg-cell'>{teg_label}</div>"

        rows.append("<tr>")
        rows.append(f"<td>{teg_cell}</td>")
        for col in name_cols:
            rows.append(f"<td>{_wrap_player_name(row.get(col))}</td>")
        if rounds:
            rows.append(
                "<td class='history-toggle-td'>"
                "<span class='history-toggle-indicator' aria-hidden='true'></span></td>"
            )
        else:
            rows.append("<td class='history-toggle-td'></td>")
        rows.append("</tr>")

        if rounds:
            # "Round N:" + course + comma-separated date -- the comma sits in
            # its own span (.history-meta-sep) so mobile.css can drop it when
            # the three parts stack onto separate lines instead of reading as
            # one sentence.
            courses = "".join(
                f"<li><b>Round {r['round']}:</b> <span>{escape(r['course'])}"
                f"<span class='history-meta-sep'>,</span></span> "
                f"<small>{escape(r['date'])}</small></li>"
                for r in rounds
            )
            # colspan matches the visible column count (TEG + 3 name columns),
            # not len(headers): the trailing toggle column gets its own empty
            # cell instead, so a revealed detail row keeps the same column
            # count as every other row and table-layout:fixed's width math
            # stays stable.
            rows.append(
                f"<tr class='history-detail-row' id='{detail_id}' hidden>"
                f"<td colspan='{len(headers) - 1}'>"
                f"<div class='history-meta'><p><b>{escape(area_raw)}</b></p>"
                f"<ol>{courses}</ol></div>"
                f"</td><td class='history-toggle-td'></td></tr>"
            )
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
        round_metadata = _round_metadata_by_teg()
        table_html = _history_table_html(df, round_metadata)
        table_html += ("<p class='text-muted text-sm mt-3'>*Green Jacket awarded in TEG 5 for "
                       "best stableford round; DM had best gross score.</p>")
    except Exception as e:
        logger.exception("history_page failed")
        table_html = f"<p class='text-muted'>Error: {e}</p>"

    return templates.TemplateResponse("data_table.html", {
        "request": request,
        "active_page": "history",
        "title": "TEG History",
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

HONOURS_TITLES = {
    "trophy": "TEG Trophy wins",
    "jacket": "Green Jacket wins",
    "spoon": "Wooden Spoons",
    "doubles": "Trophy / Jacket doubles",
    "eagles": "TEG Eagles",
    "hio": "TEG Holes in One",
}


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


def _honours_wins_table(df: pd.DataFrame, count_col: str) -> str:
    """Bespoke winners table for the /honours Trophy/Jacket/Spoon/Doubles tabs,
    styled per the /latest-round mobile table reference
    (design_principles.md -> Tables -> "Mobile table pattern"): a fixed
    <colgroup> (Player/count/TEGs, or Player/count for Doubles' 2-column
    shape), uppercase tracked headers matching cell alignment, the win/double
    count as the primary bold tabular-nums number, a TEGs column that's
    allowed to wrap instead of truncating or forcing scroll. No leader-row
    shading -- it's an honours list, not a leaderboard. Player
    names are never shortened -- no Initial.SURNAME form -- and are allowed
    to wrap onto a second line rather than being truncated."""
    if df is None or df.empty:
        return EMPTY_TABLE_HTML

    has_tegs = 'TEGs' in df.columns

    colgroup = (
        "<col style='width:40%'><col style='width:15%'><col style='width:45%'>"
        if has_tegs else
        "<col style='width:70%'><col style='width:30%'>"
    )

    rows = [
        "<table class='teg-table honours-table'><colgroup>", colgroup, "</colgroup>",
        "<thead><tr>",
        "<th scope='col'>Player</th>",
        f"<th scope='col' class='honours-count-col'>{escape(str(count_col))}</th>",
    ]
    if has_tegs:
        rows.append("<th scope='col'>TEGs</th>")
    rows.append("</tr></thead><tbody>")

    for _, row in df.iterrows():
        rows.append("<tr>")
        rows.append(f"<td class='honours-player-cell'>{_wrap_player_name(row.get('Player'))}</td>")
        rows.append(f"<td class='honours-count-cell'>{escape(str(row[count_col]))}</td>")
        if has_tegs:
            rows.append(f"<td class='honours-tegs-cell'>{escape(str(row.get('TEGs', '')))}</td>")
        rows.append("</tr>")
    rows.append("</tbody></table>")
    return "".join(rows)


def _honours_feats_list(df: pd.DataFrame) -> str:
    """Eagles / Holes in One as a plain list, not a table: bold player name,
    then a muted line "September 2011, Bletchingley. TEG 4, Round 4, Hole 8."
    The two halves are separate blocks, so every entry breaks between course
    and TEG/round/hole (consistent across rows, whatever the width).
    Expects get_eagles_data's shape (Hole = "TEG 4 | Rd 4 | Hole 8")."""
    items = []
    for _, row in df.iterrows():
        date = pd.to_datetime(row.get('Date'), dayfirst=True, errors='coerce')
        when = date.strftime('%B %Y') if not pd.isna(date) else str(row.get('Date', ''))
        where = str(row.get('Hole', '')).replace(' | ', ', ').replace('Rd ', 'Round ')
        items.append(
            "<li class='honours-feat'>"
            f"<span class='honours-feat-player'>{escape(str(row.get('Player', '')))}</span>"
            "<span class='honours-feat-detail'>"
            f"<span>{escape(when)}, {escape(str(row.get('Course', '')))}.</span> "
            f"<span>{escape(where)}.</span>"
            "</span></li>"
        )
    return f"<ul class='honours-feats'>{''.join(items)}</ul>"


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

    return _honours_wins_table(grouped, 'Wins')


def _honours_tab_context(tab: str) -> dict:
    """Build context for an honours tab."""
    try:
        all_data = cached_load_all_data()
        winners_df = cached_winners()

        # Each tab gets a section heading (HONOURS_TITLES) above its content;
        # extra context (the Doubles count, Jacket footnote) is a caption.
        sections = []

        if tab == "trophy":
            sections.append({"table_html": _summarise_wins(winners_df, "TEG Trophy"), "no_pin": True})

        elif tab == "jacket":
            jacket_html = _summarise_wins(winners_df, "Green Jacket")
            jacket_html += ("<p class='caption'>*Green Jacket awarded in TEG 5 for "
                            "best stableford round; DM had best gross score.</p>")
            sections.append({"table_html": jacket_html, "no_pin": True})

        elif tab == "spoon":
            sections.append({"table_html": _summarise_wins(winners_df, "HMM Wooden Spoon"), "no_pin": True})

        elif tab == "doubles":
            doubles_df, count = calculate_trophy_jacket_doubles(winners_df)
            if doubles_df is not None and not doubles_df.empty:
                html = (f"<p class='caption'>There have been {count} "
                        f"trophy / jacket doubles.</p>") + _honours_wins_table(doubles_df, "Doubles")
            else:
                html = "<p class='text-muted text-sm'>No doubles recorded.</p>"
            sections.append({"table_html": html, "no_pin": True})

        elif tab == "eagles":
            eagles = get_eagles_data(all_data)
            if eagles is not None and not eagles.empty:
                sections.append({"table_html": _honours_feats_list(eagles)})
            else:
                sections.append({"table_html": "<p class='text-muted text-sm'>No eagles have yet been scored on a TEG</p>"})

        elif tab == "hio":
            hio = get_holes_in_one_data(all_data)
            if hio is not None and not hio.empty:
                sections.append({"table_html": _honours_feats_list(hio)})
            else:
                sections.append({"table_html": "<p class='text-muted text-sm'>No holes in one have yet been scored on a TEG</p>"})

        if sections:
            sections[0]["title"] = HONOURS_TITLES.get(tab)
        return {"sections": sections}
    except Exception as e:
        logger.exception("_honours_tab_context failed")
        return {"error": str(e)}


@router.get("/honours")
def honours_page(request: Request, tab: str = Query("trophy")):
    tab = tab if tab in {tab_id for tab_id, _label in HONOURS_TABS} else "trophy"
    ctx = _honours_tab_context(tab)
    return templates.TemplateResponse("honours.html", {
        "request": request,
        "active_page": "honours",
        "tabs": HONOURS_TABS,
        "active_tab": tab,
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


def _split_player_name(name) -> tuple:
    """Split "David MULLIN" into (first, last) plain strings -- the same
    forename/surname split _wrap_player_name uses, but unescaped and
    unwrapped so Jinja can emit the .player-name/.first/.last spans itself
    (partials/_standings_table.html). Mirrors _wrap_player_name exactly so
    the two never drift."""
    if not isinstance(name, str) or not name.strip():
        return ("" if name is None else str(name), "")
    first, *rest = re.split(r"\s+", name.strip(), maxsplit=1)
    return (first, rest[0] if rest else "")


def _standings_rows(df: pd.DataFrame, link_players: bool = False) -> dict:
    """Structured standings for the unified Jinja renderer (I1): round labels
    plus one dict per player, built once and shared by the desktop table
    columns and the phone round-strip inside the same <tr> -- so the two
    copies can never drift the way a duplicated card partial could.

    ``link_players=False`` (default -- player profiles hidden 2026-09-18, not
    ready to be live) omits the player code so the template renders plain
    text instead of a link to ``/player/<code>``. Pass ``link_players=True``
    to restore click-through once the profile pages are ready."""
    if df is None or df.empty:
        return {"round_labels": [], "rows": []}

    round_labels = [c for c in df.columns if c not in ("Rank", "Player", "Total")]
    rows = []
    for _, row in df.iterrows():
        rank = str(row["Rank"])
        player = str(row["Player"])
        first, last = _split_player_name(player)
        rows.append({
            "rank": rank,
            "player": player,
            "first": first,
            "last": last,
            "code": get_name_to_code().get(player) if link_players else None,
            "rounds": [(label, str(row[label])) for label in round_labels],
            "total": str(row["Total"]),
            "lead": rank.startswith("1"),
        })
    return {"round_labels": round_labels, "rows": rows}


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


def _race_series_spec(tab: str, variant: str, net_measure: str) -> tuple:
    """Resolve (y_series, y_calculation, chart_type, y_axis_label) for a
    tournament race chart's (tab, variant, net_measure) combination. Shared
    by _build_race_figure_json and _build_race_chart_readout so the figure
    and its below-chart readout always describe the same series."""
    stableford = net_measure == "Stableford"

    if tab == "gross":
        if variant == "ranking":
            return "Rank_GrossVP_TEG", None, "ranking", "Tournament Ranking"
        elif variant == "adjusted":
            return "GrossVP Cum TEG", adjusted_grossvp, "gross", "Gross vs bogey"
        else:
            return "GrossVP Cum TEG", None, "gross", "Cumulative gross vs par"

    if variant == "ranking":
        return "Rank_Stableford_TEG", None, "ranking", "Tournament Ranking"
    elif variant == "adjusted":
        if stableford:
            return "Stableford Cum TEG", adjusted_stableford, "stableford", "Stableford (adjusted)"
        else:
            return "NetVP Cum TEG", adjusted_grossvp, "gross", "Net vs par (adjusted)"
    else:
        if stableford:
            return "Stableford Cum TEG", None, "stableford", "Cumulative Stableford"
        else:
            return "NetVP Cum TEG", None, "gross", "Cumulative net vs par"


def _build_race_figure_json(tab: str, variant: str, net_measure: str, teg_name: str) -> str | None:
    """Build race chart JSON for the given (tab, variant, net_measure) combination."""
    try:
        df = cached_load_all_data()
        y_series, y_calc, chart_type, ylabel = _race_series_spec(tab, variant, net_measure)
        fig = create_cumulative_graph(
            df, teg_name, y_series, title="",
            y_calculation=y_calc, y_axis_label=ylabel, chart_type=chart_type,
        )
        return fig.to_json()
    except Exception:
        return None


def _build_race_chart_readout(tab: str, variant: str, net_measure: str, teg_name: str) -> list:
    """Player code/name/value/colour list for the race chart's below-chart
    readout (see get_teg_chart_readout) -- identifies each line without
    hovering the chart, and stays legible even on fields too crowded for
    the chart's own on-chart labels (create_cumulative_graph's
    CROWDED_FIELD_THRESHOLD)."""
    try:
        df = cached_load_all_data()
        y_series, y_calc, chart_type, _ylabel = _race_series_spec(tab, variant, net_measure)
        readout = get_teg_chart_readout(df, teg_name, y_series, y_calculation=y_calc, chart_type=chart_type)
        for item in readout:
            item["name"] = get_player_name(item["code"])
        return readout
    except Exception:
        return []


def _results_context(teg_num: int, tab: str = "net", chart_variant: str = "adjusted",
                      link_players: bool = False, scorecard_type: str = "one_round_all_players",
                      scorecard_round: int | None = None,
                      scorecard_player: str | None = None) -> dict:
    """Build context for full results page.

    ``link_players=False`` (default -- player profiles hidden 2026-09-18, not
    ready to be live) drops the click-through to player profiles in the
    unified standings table (both its desktop columns and its phone round-
    strip render from the same row, see `_standings_rows`). Pass
    ``link_players=True`` to restore click-through once the profile pages
    are ready; /leaderboard and /results both reuse this context builder via
    the default."""
    # Local import to avoid a module-load cycle: webapp.routes.latest already
    # imports _wrap_player_name from this module at import time.
    from webapp.routes.latest import _teg_context_header
    complete = _teg_is_complete(teg_num)
    context_header = _teg_context_header(teg_num)
    try:
        if tab == "scorecards":
            from webapp.routes.scorecard import scorecard_view_context

            scorecard = scorecard_view_context(
                teg_num, scorecard_round, scorecard_player, scorecard_type, embedded=True,
            )
            if "error" in scorecard:
                return {"error": scorecard["error"], "teg_complete": complete,
                        "context_header": context_header}
            return {"scorecard_view": True, "teg_complete": complete,
                    "context_header": context_header, **scorecard}

        # (No `report` tab here: /results' Report tab is a link to /teg-reports,
        # which renders the newspaper edition. The old markdown-blob render of
        # data/commentary/teg_N_report_styled.md was removed with it.)

        rd_data = cached_round_data()
        teg_rd = rd_data[rd_data['TEGNum'] == teg_num]

        if teg_rd.empty:
            return {"error": f"No data found for TEG {teg_num}"}

        teg_name = f"TEG {teg_num}"
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

        # Format score columns (+/- signs etc.), then build the unified
        # structured standings (I1) -- one Jinja table that reflows into a
        # compact round-strip at phone width, replacing both the old HTML-
        # string table and the now-deleted .lb-cards duplicate.
        for col in [c for c in lb.columns if c not in ['Rank', 'Player']]:
            lb[col] = lb[col].apply(lambda x: format_value(x, value_col))
        standings = _standings_rows(lb, link_players=link_players)

        lb_hero = {
            "label": leader_label,
            "champion": champion,
            "champion_total": standings["rows"][0]["total"] if standings["rows"] else "",
            "spoon": spoon if tab != "gross" else None,
            "spoon_total": standings["rows"][-1]["total"] if standings["rows"] else "",
            "unit": "pts" if value_col == "Stableford" else "vs par",
        }

        chart_meta = _results_chart_meta(tab, chart_variant, net_measure, teg_name)
        figure_json = _build_race_figure_json(tab, chart_variant, net_measure, teg_name)
        chart_readout = _build_race_chart_readout(tab, chart_variant, net_measure, teg_name)
        return {
            "is_leaderboard": True,
            # C5: drop the trailing "Leaderboard" -- the page h1 already says
            # "Leaderboard"/"Results"; repeating it here is a redundant label
            # when the tournament is in progress ("... Latest Leaderboard").
            "section_title": f"{competition} {status_word}",
            "callout": callout,
            "standings": standings,
            "lb_hero": lb_hero,
            "link_player_cards": link_players,
            "chart_readout": chart_readout,
            "chart_crowded_threshold": CROWDED_FIELD_THRESHOLD,
            "teg_name": teg_name,
            "chart_types": RESULTS_CHART_TYPES,
            "active_chart_variant": chart_variant,
            "figure_json": figure_json,
            "teg_complete": complete,
            "context_header": context_header,
            **chart_meta,
        }
    except Exception as e:
        logger.exception("_results_context failed")
        return {"error": str(e)}


@router.get("/results")
def results_page(
    request: Request,
    teg: Optional[int] = Query(None),
    tab: str = Query("net"),
    chart_variant: str = Query("adjusted"),
    type: str = Query("one_round_all_players"),
    round: str | None = Query(None),
    player: str | None = Query(None),
):
    teg_numbers = get_available_teg_numbers()
    # Deep-link support (e.g. from /teg-reports' "Back to Results" link) — an
    # invalid/absent teg falls back to the default, same as every other page's
    # teg-selector pattern.
    teg_num = teg if teg in teg_numbers else get_default_teg_num()
    tab = tab if tab in {"net", "gross", "scorecards"} else "net"
    chart_variant = (chart_variant if chart_variant in {value for value, _label in RESULTS_CHART_TYPES}
                     else "adjusted")
    # /results has no player-profile click-through (unlike /leaderboard, which
    # reuses this same context builder via the default).
    from webapp.routes.scorecard import parse_scorecard_round
    selected_round = parse_scorecard_round(round)
    ctx = _results_context(teg_num, tab, chart_variant, link_players=False,
                           scorecard_type=type, scorecard_round=selected_round, scorecard_player=player)
    return templates.TemplateResponse("results.html", {
        "request": request,
        "active_page": "results",
        "teg_numbers": teg_numbers,
        "selected_teg": teg_num,
        "active_tab": tab,
        "sc_saved_type": ctx.get("selected_type", type),
        "sc_saved_round": ctx.get("selected_round", selected_round),
        "sc_saved_player": ctx.get("selected_player", player),
        "active_chart_variant": chart_variant,
        # TEGs with a newspaper edition — drives whether the Report tab (a real
        # link to /teg-reports, not an HTMX swap) is shown. lru_cached in
        # newspaper_edition and cleared via deps.register_cache_clearer, so this
        # is a dict lookup, not a filesystem/GitHub probe, after the first call.
        "report_tegs": list(available_tegs()),
        **ctx,
    })


@router.get("/results/table")
def results_table(request: Request, teg: int = Query(...), tab: str = Query("net"),
                        chart_variant: str = Query("adjusted"),
                        type: str = Query("one_round_all_players"),
                        round: str | None = Query(None), player: str | None = Query(None)):
    from webapp.routes.scorecard import parse_scorecard_round
    ctx = _results_context(teg, tab, chart_variant, link_players=False,
                           scorecard_type=type, scorecard_round=parse_scorecard_round(round),
                           scorecard_player=player)
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


def _player_rankings_context(tab: str, row_dim: str = "Pl", col_dim: str = "TEGNum") -> dict:
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
def player_rankings_page(
    request: Request,
    tab: str = Query("trophy"),
    row_dim: str = Query("Pl"),
    col_dim: str = Query("TEGNum"),
):
    tab = tab if tab in {tab_id for tab_id, _label in PLAYER_RANKINGS_TABS} else "trophy"
    ctx = _player_rankings_context(tab, row_dim, col_dim)
    return templates.TemplateResponse("player_rankings.html", {
        "request": request,
        "active_page": "player-rankings",
        "tabs": PLAYER_RANKINGS_TABS,
        "active_tab": tab,
        **ctx,
    })


@router.get("/player-rankings/tab")
def player_rankings_tab(request: Request, tab: str = "trophy",
                              row_dim: str = Query("Pl"), col_dim: str = Query("TEGNum")):
    ctx = _player_rankings_context(tab, row_dim, col_dim)
    return templates.TemplateResponse("partials/player_rankings_tab.html", {
        "request": request,
        "active_tab": tab,
        **ctx,
    })
