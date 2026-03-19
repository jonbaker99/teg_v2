"""Latest TEG section routes: /latest-round, /latest-teg, /handicaps."""

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates

from teg_analysis.constants import PLAYER_DICT, HANDICAPS_CSV
from teg_analysis.io.file_operations import read_file
from teg_analysis.analysis.aggregation import (
    get_round_data,
    get_latest_round_defaults,
    get_teg_data_inc_in_progress,
    prepare_round_context_display,
    prepare_teg_context_display,
    get_round_metric_mappings,
)
from teg_analysis.analysis.records import identify_aggregate_records_and_pbs
from teg_analysis.analysis.streaks import get_player_window_streaks, build_streaks
from teg_analysis.analysis.scoring import count_scores_by_player
from webapp.deps import (
    cached_load_all_data,
    cached_round_data,
    cached_ranked_teg_data,
    cached_ranked_round_data,
    get_available_teg_numbers,
    get_default_teg_num,
    get_rounds_for_teg,
)

_NAME_TO_CODE = {v: k for k, v in PLAYER_DICT.items()}

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _df_to_html(df: pd.DataFrame, table_class: str = "teg-table") -> str:
    if df is None or df.empty:
        return "<p class='text-muted text-sm'>No data available.</p>"
    rows = [f"<table class='{table_class}'><thead><tr>"]
    for col in df.columns:
        rows.append(f"<th>{col}</th>")
    rows.append("</tr></thead><tbody>")
    for _, row in df.iterrows():
        rows.append("<tr>")
        for col in df.columns:
            rows.append(f"<td>{row[col]}</td>")
        rows.append("</tr>")
    rows.append("</tbody></table>")
    return "".join(rows)


# --- /latest-round ------------------------------------------------------------

LATEST_ROUND_TABS = [
    ("scoreboard", "Scoreboards"),
    ("scorecard", "Scorecard"),
    ("scoring", "Scoring"),
    ("streaks", "Streaks"),
    ("records", "Records & PBs"),
]


def _latest_round_tab_context(teg_num: int, round_num: int, tab: str) -> dict:
    try:
        rd_data = cached_round_data()
        teg_rd = rd_data[(rd_data['TEGNum'] == teg_num) & (rd_data['Round'] == round_num)]

        if teg_rd.empty:
            return {"error": f"No data for TEG {teg_num} Round {round_num}"}

        sections = []

        if tab == "scoreboard":
            try:
                ranked = cached_ranked_round_data()
                teg_str = f"TEG {teg_num}"
                _, inv_mapping = get_round_metric_mappings()
                # Show 4 metric sub-tables: Sc, Stableford, GrossVP, NetVP
                for metric in ['Sc', 'Stableford', 'GrossVP', 'NetVP']:
                    friendly = inv_mapping.get(metric, metric)
                    try:
                        ctx_df = prepare_round_context_display(ranked, teg_str, round_num, metric, friendly)
                        sections.append({"title": friendly, "table_html": _df_to_html(ctx_df)})
                    except Exception:
                        pass
                if not sections:
                    # Fallback to simple table
                    display_cols = ['Player', 'GrossVP', 'Stableford']
                    available = [c for c in display_cols if c in teg_rd.columns]
                    display = teg_rd[available].sort_values('GrossVP', ascending=True) if 'GrossVP' in available else teg_rd[available]
                    sections.append({"title": "Round Scoreboard", "table_html": _df_to_html(display)})
            except Exception:
                display_cols = ['Player', 'GrossVP', 'Stableford']
                available = [c for c in display_cols if c in teg_rd.columns]
                display = teg_rd[available].sort_values('GrossVP', ascending=True) if 'GrossVP' in available else teg_rd[available]
                sections.append({"title": "Round Scoreboard", "table_html": _df_to_html(display)})

        elif tab == "scorecard":
            link = f"/scorecard?teg={teg_num}&round={round_num}"
            sections.append({
                "title": "Scorecard",
                "table_html": f'<p><a href="{link}" class="text-link">View Scorecard for TEG {teg_num} Round {round_num}</a></p>',
            })

        elif tab == "records":
            try:
                ranked = cached_ranked_round_data()
                results = identify_aggregate_records_and_pbs(ranked, str(teg_num), round_num)
                for key in ['records', 'personal_bests', 'personal_worsts']:
                    items = results.get(key, [])
                    if items:
                        df = pd.DataFrame(items)
                        sections.append({"title": key.replace('_', ' ').title(), "table_html": _df_to_html(df)})
                if not sections:
                    sections.append({"title": "Records & PBs", "table_html": "<p class='text-muted text-sm'>No records or PBs in this round.</p>"})
            except Exception as e:
                sections.append({"title": "Records & PBs", "table_html": f"<p class='text-muted text-sm'>Error: {e}</p>"})

        elif tab == "scoring":
            all_data = cached_load_all_data()
            round_data = all_data[(all_data['TEGNum'] == teg_num) & (all_data['Round'] == round_num)]
            if not round_data.empty:
                counts = count_scores_by_player(round_data)
                # Reset index so the GrossVP values become a column for display
                counts_display = counts.reset_index()
                sections.append({"title": "Score Counts (Gross vs Par)", "table_html": _df_to_html(counts_display)})
            else:
                sections.append({"title": "Scoring", "table_html": "<p class='text-muted text-sm'>No scoring data.</p>"})

        elif tab == "streaks":
            try:
                all_data = cached_load_all_data()
                streaks_df = build_streaks(all_data)
                teg_str = f"TEG {teg_num}"
                streak_result = get_player_window_streaks(all_data, streaks_df, teg=teg_str, round_num=round_num)
                if streak_result is not None and not streak_result.empty:
                    sections.append({"title": "Streaks", "table_html": _df_to_html(streak_result)})
                else:
                    sections.append({"title": "Streaks", "table_html": "<p class='text-muted text-sm'>No streak data for this round.</p>"})
            except Exception as e:
                sections.append({"title": "Streaks", "table_html": f"<p class='text-muted text-sm'>Error: {e}</p>"})

        return {"sections": sections}
    except Exception as e:
        return {"error": str(e)}


@router.get("/latest-round")
async def latest_round_page(request: Request):
    rd_data = cached_round_data()
    teg_str, round_num = get_latest_round_defaults(rd_data)
    # teg_str is like 'TEG 18' — extract the number
    teg_num = int(teg_str.replace('TEG ', '')) if isinstance(teg_str, str) else int(teg_str)
    teg_numbers = get_available_teg_numbers()
    rounds = get_rounds_for_teg(teg_num)
    ctx = _latest_round_tab_context(teg_num, int(round_num), "scoreboard")
    return templates.TemplateResponse("latest_round.html", {
        "request": request,
        "active_page": "latest-round",
        "teg_numbers": teg_numbers,
        "selected_teg": teg_num,
        "rounds": rounds,
        "selected_round": round_num,
        "tabs": LATEST_ROUND_TABS,
        "active_tab": "scoreboard",
        **ctx,
    })


@router.get("/latest-round/tab")
async def latest_round_tab(request: Request, teg: int = Query(...), round: int = Query(...), tab: str = Query("scoreboard")):
    ctx = _latest_round_tab_context(teg, round, tab)
    return templates.TemplateResponse("partials/latest_round_tab.html", {
        "request": request,
        **ctx,
    })


# --- /latest-teg --------------------------------------------------------------

LATEST_TEG_TABS = [
    ("aggregate", "Aggregate Score"),
    ("scoring", "Scoring"),
    ("streaks", "Streaks"),
    ("records", "Records & PBs"),
]


def _latest_teg_tab_context(teg_num: int, tab: str) -> dict:
    """Build template context for a latest-teg tab."""
    try:
        sections = []

        if tab == "aggregate":
            ranked = cached_ranked_teg_data()
            teg_str = f"TEG {teg_num}"
            _, inv_mapping = get_round_metric_mappings()
            for metric in ['Sc', 'Stableford', 'GrossVP', 'NetVP']:
                friendly = inv_mapping.get(metric, metric)
                try:
                    ctx_df = prepare_teg_context_display(ranked, teg_str, metric, friendly)
                    sections.append({"title": friendly, "table_html": _df_to_html(ctx_df)})
                except Exception:
                    pass
            if not sections:
                sections.append({"title": "Aggregate Score", "table_html": "<p class='text-muted text-sm'>No aggregate data available.</p>"})

        elif tab == "scoring":
            all_data = cached_load_all_data()
            teg_data = all_data[all_data['TEGNum'] == teg_num]
            if not teg_data.empty:
                counts = count_scores_by_player(teg_data)
                counts_display = counts.reset_index()
                sections.append({"title": "Score Counts (Gross vs Par)", "table_html": _df_to_html(counts_display)})
            else:
                sections.append({"title": "Scoring", "table_html": "<p class='text-muted text-sm'>No scoring data.</p>"})

        elif tab == "streaks":
            try:
                all_data = cached_load_all_data()
                streaks_df = build_streaks(all_data)
                teg_str = f"TEG {teg_num}"
                streak_result = get_player_window_streaks(all_data, streaks_df, teg=teg_str)
                if streak_result is not None and not streak_result.empty:
                    sections.append({"title": "Streaks", "table_html": _df_to_html(streak_result)})
                else:
                    sections.append({"title": "Streaks", "table_html": "<p class='text-muted text-sm'>No streak data for this TEG.</p>"})
            except Exception as e:
                sections.append({"title": "Streaks", "table_html": f"<p class='text-muted text-sm'>Error: {e}</p>"})

        elif tab == "records":
            try:
                ranked = cached_ranked_teg_data()
                results = identify_aggregate_records_and_pbs(ranked, str(teg_num))
                for key in ['records', 'personal_bests', 'personal_worsts']:
                    items = results.get(key, [])
                    if items:
                        df = pd.DataFrame(items)
                        sections.append({"title": key.replace('_', ' ').title(), "table_html": _df_to_html(df)})
                if not sections:
                    sections.append({"title": "Records & PBs", "table_html": "<p class='text-muted text-sm'>No records or PBs in this TEG.</p>"})
            except Exception as e:
                sections.append({"title": "Records & PBs", "table_html": f"<p class='text-muted text-sm'>Error: {e}</p>"})

        return {"sections": sections}
    except Exception as e:
        return {"error": str(e)}


@router.get("/latest-teg")
async def latest_teg_page(request: Request):
    teg_num = get_default_teg_num()
    teg_numbers = get_available_teg_numbers()
    ctx = _latest_teg_tab_context(teg_num, "aggregate")
    return templates.TemplateResponse("latest_teg.html", {
        "request": request,
        "active_page": "latest-teg",
        "teg_numbers": teg_numbers,
        "selected_teg": teg_num,
        "tabs": LATEST_TEG_TABS,
        "active_tab": "aggregate",
        **ctx,
    })


@router.get("/latest-teg/tab")
async def latest_teg_tab(request: Request, teg: int = Query(...), tab: str = Query("aggregate")):
    ctx = _latest_teg_tab_context(teg, tab)
    return templates.TemplateResponse("partials/latest_teg_tab.html", {
        "request": request,
        **ctx,
    })


# --- /handicaps ---------------------------------------------------------------

@router.get("/handicaps")
async def handicaps_page(request: Request):
    try:
        hc_df = read_file(HANDICAPS_CSV)

        sections = []

        # --- Current handicaps with change from previous TEG ---
        last_row = hc_df.iloc[-1]
        prev_row = hc_df.iloc[-2] if len(hc_df) > 1 else None

        current_rows = []
        for col in hc_df.columns:
            if col == 'TEG':
                continue
            hc = last_row[col]
            if hc == 0:
                continue
            name = PLAYER_DICT.get(col, col)
            row_dict = {'Player': name, 'Handicap': hc}
            if prev_row is not None and prev_row[col] != 0:
                delta = hc - prev_row[col]
                if delta > 0:
                    row_dict['Change'] = f"+{delta:.0f}" if float(delta) == int(delta) else f"+{delta}"
                elif delta < 0:
                    row_dict['Change'] = f"{delta:.0f}" if float(delta) == int(delta) else f"{delta}"
                else:
                    row_dict['Change'] = "="
            else:
                row_dict['Change'] = "new"
            current_rows.append(row_dict)

        if current_rows:
            current_df = pd.DataFrame(current_rows).sort_values('Handicap')
            sections.append({"title": f"Current Handicaps ({last_row['TEG']})", "table_html": _df_to_html(current_df)})

        # --- Full history table ---
        display = hc_df.copy()
        for col in display.columns:
            if col != 'TEG':
                display[col] = display[col].apply(lambda x: '-' if x == 0 else x)

        # Map initials to full names
        rename_map = {}
        for col in display.columns:
            if col != 'TEG' and col in PLAYER_DICT:
                rename_map[col] = PLAYER_DICT[col]
        display = display.rename(columns=rename_map)

        # Most recent TEG first
        display = display.iloc[::-1].reset_index(drop=True)

        sections.append({"title": "Handicap History", "table_html": _df_to_html(display)})

    except Exception as e:
        sections = [{"title": "Error", "table_html": f"<p class='text-muted'>{e}</p>"}]

    return templates.TemplateResponse("data_table.html", {
        "request": request,
        "active_page": "handicaps",
        "title": "Handicaps",
        "subtitle": "Player handicaps by TEG",
        "table_html": "",
        "sections": sections,
    })
