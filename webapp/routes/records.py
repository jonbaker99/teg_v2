"""Records routes."""

import re
from html import escape
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates

from webapp.deps import (
    cached_load_all_data,
    cached_ranked_teg_data,
    cached_ranked_round_data,
    cached_ranked_frontback_data,
    cached_round_data,
    cached_9_data,
    get_filtered_teg_data,
    get_current_in_progress_teg_fast,
    get_last_completed_teg_fast,
)
from teg_analysis.display.scorecards import _player_name_spans
from teg_analysis.display.formatters import (
    prepare_records_table,
    prepare_worst_records_table,
    score_count_record_holders,
)
from teg_analysis.core.players import get_player_dict
from teg_analysis.analysis.streaks import (
    prepare_record_best_streaks_data,
    prepare_record_worst_streaks_data,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

TABS = [
    ("teg", "TEG Records"),
    ("round", "Round Records"),
    ("9hole", "9-Hole Records"),
    ("streaks", "Streaks"),
    ("score_counts", "Score Counts"),
]

# Columns that should be right-aligned (numeric content)
_NUMERIC_COLS = {
    'Score', 'Gross', 'Net', 'Stableford', 'Pts', 'Points', 'Total',
    'Vs Par', 'GrossVP', 'NetVP', 'Count', 'Rounds', 'TEGs',
    'Streak', 'Length', 'Best', 'Worst', 'Avg', 'Average',
}

# Columns that should be centered (rank-like)
_RANK_COLS = {'Rank', '#', ''}

# Sentinel values used in place of a player identity when a record is shared
# by 3+ people (see prepare_streak_records_table / prepare_score_count_records_table):
# the "who" moves into the other detail column as an initials list instead.
# Used to correct the per-row exception below.
_PLACEHOLDER_IDENTITY_RE = re.compile(r'^\(\d+\s+times?\)$')


def _is_placeholder_identity(val) -> bool:
    val_str = str(val).strip()
    return val_str == '→' or bool(_PLACEHOLDER_IDENTITY_RE.match(val_str))


def _pick_detail_col_idx(df: pd.DataFrame, cols: list, candidates: list) -> int:
    """Of the two non-value/title columns, pick the one that's the long
    "detail" (venue/date) string to collapse behind a tap, vs. the short
    "identity" (name) one always shown -- e.g. teg/round/9hole put the name
    in column 2 and venue/date in column 3, every row, consistently. Decided
    once per render from average string length, not re-derived per row: for
    those tabs the two columns play a fixed role throughout the table.

    Streaks/score_counts break that column-level consistency: whenever a
    record is shared by 3+ people, the "name" column holds a placeholder
    ('->' or '(N times)') and the *other* column holds the real identity
    (an initials list), row by row within the same table. So this picks a
    per-table default by average length, and the caller applies a narrow,
    per-row override only for those placeholder values -- not a second
    general heuristic, just correcting the one known exception.
    """
    if len(candidates) != 2:
        return candidates[-1] if candidates else -1
    a, b = candidates
    avg_len_a = df[cols[a]].dropna().astype(str).str.len().mean() if not df.empty else 0
    avg_len_b = df[cols[b]].dropna().astype(str).str.len().mean() if not df.empty else 0
    return b if avg_len_b >= avg_len_a else a


# Mobile-only label prefix dropped on the TEG/Round/9-Hole stacked lists:
# the section heading ("Best TEGs", "Worst Rounds") already says it.
_LABEL_PREFIX_RE = re.compile(r'^(Best|Worst)\s+')


def _build_records_html(
    df: pd.DataFrame,
    identity_is_player: bool = True,
) -> str:
    """Convert a records DataFrame to a styled HTML table (desktop/iPad,
    unchanged) plus a mobile-only tap-to-reveal list of the same rows.
    Used by latest.py's record summaries; /records itself now renders only
    _build_stacked_records_list at every width.
    mobile.css shows exactly one of the two per breakpoint (same
    dual-markup + CSS-toggle mechanism as .lb-table-card/.lb-cards).

    identity_is_player: whether the identity column holds a player name
    (the default, and true for every /records section, which is why the
    full/short-name-span treatment applies there). Callers whose identity
    column holds something else -- e.g. latest.py's Personal Bests/Worsts
    sections, where it's a metric's friendly name -- pass False so that
    value is rendered as-is instead of being run through _player_name_spans
    (which would otherwise abbreviate it, e.g. "Gross vs Par" -> "G.Par")."""
    if df is None or df.empty:
        return "<p class='text-muted text-sm'>No data available.</p>"

    cols = list(df.columns)
    # Determine which column index holds the score value (first numeric-like column)
    value_col_idx = None
    for i, col in enumerate(cols):
        col_str = str(col).strip()
        if col_str in _NUMERIC_COLS or (col_str in _RANK_COLS and i > 0) or _looks_numeric(df, col):
            value_col_idx = i
            break

    # The remaining columns (not the title, not the value) are the
    # identity/detail pair the mobile list needs to tell apart. A caller
    # with no real "detail" data (e.g. latest.py's single-round/TEG record
    # summaries, which have nothing like /records' venue+date "when") may
    # pass only one such column -- that one is always identity, with an
    # empty (but present) detail panel, rather than risk the length
    # heuristic below misreading an always-empty filler column as identity.
    other_idx = [i for i in range(1, len(cols)) if i != value_col_idx]
    detail_col_idx = _pick_detail_col_idx(df, cols, other_idx) if len(other_idx) == 2 else None
    identity_col_idx = None
    if detail_col_idx is not None:
        identity_col_idx = [i for i in other_idx if i != detail_col_idx][0]
    elif len(other_idx) == 1:
        identity_col_idx = other_idx[0]

    rows = []
    rows.append("<table class='records-table records-table--borderless'>")
    list_items = []

    prev_title = None
    for _, row in df.iterrows():
        title_val = row[cols[0]]
        if title_val != prev_title:
            if prev_title is not None:
                rows.append("</tbody>")
            rows.append("<tbody>")
            prev_title = title_val
            show_title = True
        else:
            show_title = False

        rows.append("<tr>")
        for i, col in enumerate(cols):
            val = row[col]
            if i == 0:
                if show_title:
                    rows.append(f"<td class='col-player'>{val}</td>")
                else:
                    rows.append("<td class='col-player'></td>")
            elif i == value_col_idx:
                rows.append(f"<td class='col-num' style='font-weight:700'>{val}</td>")
            else:
                rows.append(f"<td class='col-player'>{val}</td>")
        rows.append("</tr>")

        # Mobile row: same label/value, but identity vs. detail swap per-row
        # when the "identity" slot actually holds a shared-record placeholder
        # (see _is_placeholder_identity) -- the initials list in the other
        # column is the real answer to "who" for those rows.
        label_html = row[cols[0]] if show_title else ""
        value_html = row[cols[value_col_idx]] if value_col_idx is not None else ""
        if identity_col_idx is not None:
            raw_id_val = row[cols[identity_col_idx]]
            det_val = row[cols[detail_col_idx]] if detail_col_idx is not None else ""
            is_placeholder = detail_col_idx is not None and _is_placeholder_identity(raw_id_val)
            if is_placeholder:
                id_val, det_val = det_val, raw_id_val
            else:
                id_val = raw_id_val
            # A genuine single-player identity (not a "(N times)"/"->"
            # placeholder swapped for an initials list, see
            # _is_placeholder_identity) is a real "First Last" name -- narrow
            # enough at 320-390px that .rec-identity's nowrap+ellipsis
            # (mobile.css) truncates it unreadably (e.g. "John PATTER...").
            # Emit the full/short pair so CSS can swap to "J.PATTERSON"
            # there instead of truncating. Swapped-in initials lists ("AB /
            # HM") are already short -- left untouched.
            id_html = (
                _player_name_spans(id_val)
                if identity_is_player and not is_placeholder and id_val not in (None, "")
                else id_val
            )
        else:
            id_val, det_val = "", ""
            id_html = ""

        if detail_col_idx is None:
            # No real detail to reveal (e.g. latest.py's single-record
            # summaries) -- render a plain, non-expandable row: no chevron,
            # no tap affordance, no empty <details> to open onto nothing.
            list_items.append(
                "<div class='rec-row rec-row--flat'>"
                "<div class='rec-summary rec-summary--flat'>"
                f"<span class='rec-label'>{label_html}</span>"
                f"<span class='rec-value'>{value_html}</span>"
                f"<span class='rec-identity'>{id_html}</span>"
                "</div>"
                "</div>"
            )
        else:
            list_items.append(
                "<details class='rec-row'>"
                "<summary class='rec-summary'>"
                f"<span class='rec-label'>{label_html}</span>"
                f"<span class='rec-value'>{value_html}</span>"
                f"<span class='rec-identity'>{id_html}</span>"
                "<span class='rec-chevron' aria-hidden='true'></span>"
                "</summary>"
                f"<div class='rec-detail'>{det_val}</div>"
                "</details>"
            )

    rows.append("</tbody></table>")
    rows.append("<div class='records-list'>")
    rows.extend(list_items)
    rows.append("</div>")
    return "".join(rows)


# Stacked-list records whose value is below this are hidden on mobile: a
# count of 1 (e.g. "Most Eagles in a Round") is held by many and says little.
_STACKED_MIN_VALUE = 2


def _stacked_value_threshold(value: str) -> int:
    """Parse the leading digits of a stacked-list value for the
    _STACKED_MIN_VALUE comparison. Streak Record values can carry a
    trailing '*' ("and counting", e.g. "1206*"), so a plain int() would
    crash; no leading digits means 0."""
    match = re.match(r'\d+', str(value))
    return int(match.group()) if match else 0


_TEG_IN_WHEN_RE = re.compile(r'TEG\s*(\d+)')


def _record_teg(when) -> int | None:
    """TEG number a record occasion was set in: the LAST "TEG N" in ``when``.
    A streak can span TEGs ("TEG 7, R1 H8 to R2 H12"); the record was reached
    in the final one. None if the string names no TEG."""
    matches = _TEG_IN_WHEN_RE.findall(str(when or ""))
    return int(matches[-1]) if matches else None


def new_record_teg() -> int | None:
    """The TEG whose records count as "new": the in-progress TEG if there is
    one, else the last completed TEG, else None."""
    in_progress, _ = get_current_in_progress_teg_fast()
    if in_progress:
        return int(in_progress)
    completed, _ = get_last_completed_teg_fast()
    return int(completed) if completed else None


def _build_stacked_records_list(
    holders: list,
    min_value: int | None = _STACKED_MIN_VALUE,
    new_teg: int | None = None,
) -> str:
    """Mobile-only stacked list for Score Counts and Streaks: one group per
    record (label + value on top), then one row per holder -- full player
    name with the occasion(s) beside it in muted text. ui-polish.js drops
    every occasion onto its own line under the name, list-wide, as soon as
    any one row would not fit beside its name (.is-wrapped).
    Holdings arrive one per occasion (score_count_record_holders); a player
    holding a record more than once gets one row listing each occasion.
    Records below ``min_value`` are left out (None keeps every record --
    TEG/Round/9-Hole values are scores, not counts).
    ``new_teg`` marks records set in that TEG: ``rec-when--new`` on the
    occasion, ``rec-holder--new`` on the holder row, ``rec-group--new`` on the
    group. Unstyled in production; see /design/new-records."""
    return _stacked_records_html(holders, min_value, new_teg)[0]


def _stacked_records_html(holders: list, min_value: int | None, new_teg: int | None) -> tuple[str, list]:
    """(html, new_holders) for _build_stacked_records_list. new_holders is
    a list of (label, player name) taken after the min_value filter, so it
    matches what is shown."""
    names = get_player_dict()
    if min_value is not None:
        holders = [h for h in holders if _stacked_value_threshold(h['value']) >= min_value]
    if not holders:
        return "<p class='text-muted text-sm'>No records.</p>", []
    new_holders: list = []
    parts = ["<div class='records-list records-list--stacked'>"]
    for label in dict.fromkeys(h['label'] for h in holders):
        group = [h for h in holders if h['label'] == label]
        by_player: dict = {}
        for h in group:
            by_player.setdefault(h['player'], []).append(h['when'])
        group_new = new_teg is not None and any(
            _record_teg(w) == new_teg for whens in by_player.values() for w in whens
        )
        parts.append(
            f"<div class='rec-group{' rec-group--new' if group_new else ''}'>"
            "<div class='rec-group-head'>"
            f"<span class='rec-label'>{escape(label)}</span>"
            f"<span class='rec-value'>{escape(group[0]['value'])}</span>"
            "</div>"
        )
        for code, whens in by_player.items():
            flags = [new_teg is not None and _record_teg(w) == new_teg for w in whens]
            holder_new = any(flags)
            if holder_new:
                new_holders.append((label, names.get(code, code)))
            when_html = "".join(
                f"<span class='rec-when{' rec-when--new' if is_new else ''}'>{escape(w)}</span>"
                for w, is_new in zip(whens, flags)
            )
            sr = "<span class='rec-sr-only'> (new record)</span>" if holder_new else ""
            parts.append(
                f"<div class='rec-holder{' rec-holder--new' if holder_new else ''}'>"
                f"<span class='rec-identity'>{escape(names.get(code, code))}{sr}</span>"
                f"<span class='rec-whens'>{when_html}</span>"
                "</div>"
            )
        parts.append("</div>")
    parts.append("</div>")
    return "".join(parts), new_holders


def _looks_numeric(df: pd.DataFrame, col: str) -> bool:
    """Check if a column's non-null values are numeric."""
    try:
        sample = df[col].dropna().head(5)
        if sample.empty:
            return False
        if pd.api.types.is_numeric_dtype(sample):
            return True
        # Try converting string values
        pd.to_numeric(sample.astype(str).str.replace('=', '', regex=False), errors='raise')
        return True
    except (ValueError, TypeError):
        return False


def _score_record_holders(df: pd.DataFrame) -> list:
    """Holders for the stacked list from a prepare_records_table /
    prepare_worst_records_table frame (positional columns: label, value,
    player, when). The "Best "/"Worst " label prefix is dropped."""
    if df is None or df.empty:
        return []
    return [
        {'label': _LABEL_PREFIX_RE.sub('', str(r.iloc[0])), 'value': str(r.iloc[1]),
         'player': r.iloc[2], 'when': r.iloc[3]}
        for _, r in df.iterrows()
    ]


def _streak_holders(df: pd.DataFrame) -> list:
    """Holders for the stacked list from prepare_record_*_streaks_data."""
    if df is None or df.empty:
        return []
    return [
        {'label': r['Streak Type'], 'value': str(r['Record']), 'player': r['Player'], 'when': r['When']}
        for _, r in df.iterrows()
    ]


def _section(
    title: str,
    holders: list,
    min_value: int | None = _STACKED_MIN_VALUE,
    new_teg: int | None = None,
) -> dict:
    """Build a section dict: title plus the stacked list, which /records
    shows at every width (the old table is gone). ``new_count`` is the number
    of holder rows set in ``new_teg``."""
    table_html, new_holders = _stacked_records_html(holders, min_value, new_teg)
    return {
        "title": title,
        "table_html": table_html,
        "record_count": len(holders),
        "new_count": len(new_holders),
        "new_holders": new_holders,
    }


def _tab_context(tab_name: str, new_teg: int | None = None) -> dict:
    """Build context for a records tab."""
    try:
        sections = []
        caption = None

        if tab_name in ("teg", "round", "9hole"):
            # Values are scores, not counts: never hidden by min_value.
            ranked, worst_data, scope, best_title, worst_title = {
                "teg": (cached_ranked_teg_data, get_filtered_teg_data, 'teg', "Best TEGs", "Worst TEGs"),
                "round": (cached_ranked_round_data, cached_round_data, 'round', "Best Rounds", "Worst Rounds"),
                "9hole": (cached_ranked_frontback_data, cached_9_data, 'frontback',
                          "Best 9-Hole Scores", "Worst 9-Hole Scores"),
            }[tab_name]
            best = prepare_records_table(ranked(), scope)
            sections.append(_section(best_title, _score_record_holders(best), min_value=None, new_teg=new_teg))
            worst = prepare_worst_records_table(worst_data(), scope)
            sections.append(_section(worst_title, _score_record_holders(worst), min_value=None, new_teg=new_teg))

        elif tab_name == "streaks":
            all_data = cached_load_all_data()
            sections.append(_section("Best Streaks", _streak_holders(prepare_record_best_streaks_data(all_data)), new_teg=new_teg))
            sections.append(_section("Worst Streaks", _streak_holders(prepare_record_worst_streaks_data(all_data)), new_teg=new_teg))
            caption = "* and counting..."

        elif tab_name == "score_counts":
            holders = score_count_record_holders(cached_load_all_data())
            sections.append(_section("Best Score Counts", [h for h in holders if h['best']], new_teg=new_teg))
            sections.append(_section("Worst Score Counts", [h for h in holders if not h['best']], new_teg=new_teg))
            caption = "Eagles, Birdies and Pars also include better scores"

        return {
            "sections": sections,
            "caption": caption,
            "new_count": sum(sec["new_count"] for sec in sections),
            # Labels lose their Best/Worst prefix in the list; restore it from
            # the section title so the banner can tell them apart.
            "new_holders": [
                (f"{sec['title'].split()[0]} {label}", who)
                for sec in sections for label, who in sec["new_holders"]
            ],
        }

    except Exception as e:
        return {"error": str(e)}


def _new_banner(ctx: dict, new_teg: int | None) -> dict | None:
    """Summary banner data for the /design/new-records prototype (never
    emitted on production /records): None when there is nothing new."""
    if new_teg is None or not ctx.get("new_count"):
        return None
    in_progress, _ = get_current_in_progress_teg_fast()
    return {
        "teg": new_teg,
        "count": ctx["new_count"],
        "in_progress": bool(in_progress) and int(in_progress) == new_teg,
        "entries": ctx["new_holders"],
    }


@router.get("/records")
def records_page(request: Request, tab: str = Query("teg")):
    tab = tab if tab in {tab_id for tab_id, _label in TABS} else "teg"
    ctx = _tab_context(tab, new_teg=new_record_teg())
    return templates.TemplateResponse("records.html", {
        "request": request,
        "active_page": "records",
        "tabs": TABS,
        "active_tab": tab,
        **ctx,
    })


@router.get("/records/tab/{tab_name}")
def records_tab(request: Request, tab_name: str, new_teg: int | None = None, banner: int = 0):
    """``new_teg`` overrides detection and ``banner=1`` adds the summary
    banner (both used by the /design/new-records prototype's tab loads)."""
    new_teg = new_teg if new_teg is not None else new_record_teg()
    ctx = _tab_context(tab_name, new_teg=new_teg)
    return templates.TemplateResponse("partials/records_tab.html", {
        "request": request,
        "new_banner": _new_banner(ctx, new_teg) if banner else None,
        **ctx,
    })
