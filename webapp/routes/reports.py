"""TEG Reports — tournament and round reports, newspaper layout.

Both are rendered through the newspaper-edition pipeline
(`teg_analysis.reporting.newspaper_edition`): `build_edition` parses the
storyline-first artefacts for a TEG (or a TEG/round) into an edition dict,
`render_desktop_html` renders the desktop layout server-side, and the edition
is also embedded as JSON for `webapp/static/newspaper_preview.js` to render
mobile pattern A client-side. The page extends `base.html` (site nav
retained) — see `templates/teg_reports.html`; only the "paper" card itself
carries the newspaper design's own fonts/palette/reset, scoped via `.np-page`,
not the whole page. This replaced the old one-blob markdown render and the
standalone `/teg-reports-preview` page (2026-09-11) — see
`webapp/report_layout_prototypes/README.md` for the design record. Only TEGs
with storyline-first artefacts (`available_tegs()`) get a tournament report;
only rounds with the round-storyline pipeline's artefacts
(`teg_analysis.reporting.round_storyline`, `available_rounds(teg)`) get a
newspaper round report. The TEG dropdown itself is driven by the union of both
(`available_report_tegs()`) — a TEG whose only report so far is a round one
is still selectable, landing on its first available round rather than a
guaranteed "no tournament report" message.

Round reports were dropped from the UI entirely on 2026-09-11 pending the
round-storyline pipeline (`teg_analysis/reporting/STATUS.md` → START HERE,
item 2) and re-added here once it landed — built the same way, not by
reviving the old markdown renderer. `round=None` (the default) is the
tournament report unless the TEG has none, in which case its first round
takes over as the default; passing a `round` in `available_rounds(teg)`
always switches to that round's edition.

LEGACY ROUND FALLBACK (2026-09-12, backfill in progress). Round-storyline
coverage is climbing as `round_storyline.py` backfill runs land — check
`STATUS.md` → START HERE for the current count rather than trusting a number
here, since it goes stale within a single backfill session. Rather than show
"no report" for a round not yet converted, a round pill for which
`available_rounds(teg)` has no newspaper edition falls back to the OLD
one-blob markdown render this page used before 2026-09-11 —
`_legacy_round_report_html`, reviving the file-fallback chain
(`teg_N_round_R_report_styled.md` → `round_reports/TEG{N}_R{r}_report.md` →
`round_reports/teg_{N}_round_{r}_report.md`) and the `.teg-report` CSS
(`/static/teg_reports.css`, still loaded globally) rather than reinventing
either. This is a deliberate, temporary bridge, not a second permanent
pipeline: as rounds get regenerated through `round_storyline.py`, they
silently take over their pill (a newspaper edition is always preferred over
a legacy one for the same round — see `_round_kind`), and once backfill is
complete this whole fallback becomes dead code, at which point delete it
along with `teg_reports.css` and `round_reports/`.

All file reads go through `teg_analysis.io.read_text_file`, which is
volume-then-GitHub-aware on Railway (checks the mounted volume, falls back to
the GitHub API, caches the result).
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

import markdown as md_lib
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from github import GithubException

from teg_analysis.io import read_text_file
from teg_analysis.reporting.newspaper_edition import (
    available_report_tegs,
    available_rounds,
    build_edition,
    clear_edition_caches,
    for_page,
    has_edition,
    render_desktop_html,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

# Caption shown for pre-TEG-8 tournament reports (matches streamlit/teg_reports.py)
_PRE_TEG8_CAPTION = (
    "NB: The TEG Trophy winners before TEG 8 were decided by best net; "
    "the report here is written based on Stableford so finishing positions may be inaccurate"
)

_DATA_DIR = "data/commentary"
_ROUND_REPORTS_DIR = f"{_DATA_DIR}/round_reports"
_MD_EXTS = ["extra", "sane_lists", "smarty", "toc"]


# ---------------------------------------------------------------------------
# Legacy round-report fallback — see the module docstring.
# ---------------------------------------------------------------------------
@lru_cache(maxsize=None)
def _legacy_round_report_text(teg_num: int, round_num: int) -> Optional[str]:
    """Raw markdown for a round that has no round-storyline edition, or None.

    Same fallback chain `webapp/routes/reports.py` used before the 2026-09-11
    switchover: the legacy pipeline's styled output, then either filename
    convention `round_reports/` (the pre-pipeline 2025 vintage) has used.
    Cached — a miss costs a GitHub 404 round-trip on Railway; cleared by
    `clear_edition_caches` alongside the newspaper-edition discovery caches.
    """
    for path in (
        f"{_DATA_DIR}/teg_{teg_num}_round_{round_num}_report_styled.md",
        f"{_ROUND_REPORTS_DIR}/TEG{teg_num}_R{round_num}_report.md",
        f"{_ROUND_REPORTS_DIR}/teg_{teg_num}_round_{round_num}_report.md",
    ):
        try:
            return read_text_file(path)
        except (FileNotFoundError, GithubException):
            continue
    return None


def _legacy_round_report_html(teg_num: int, round_num: int) -> Optional[str]:
    text = _legacy_round_report_text(teg_num, round_num)
    return md_lib.markdown(text, extensions=_MD_EXTS) if text is not None else None


@lru_cache(maxsize=None)
def _legacy_round_numbers(teg_num: int) -> tuple[int, ...]:
    """Rounds of `teg_num` with a legacy report, probed 1..N against
    `completed_tegs.csv`'s round count — same bound `available_rounds` uses,
    so the two probes agree on how many rounds a TEG has."""
    from teg_analysis.io.file_operations import read_file
    from teg_analysis.reporting.newspaper_edition import COMPLETED_TEGS_CSV
    try:
        completed = read_file(COMPLETED_TEGS_CSV)
        row = completed[completed["TEGNum"].astype(int) == teg_num]
        total_rounds = int(row.iloc[0]["Rounds"]) if not row.empty else 4
    except Exception:          # noqa: BLE001
        total_rounds = 4
    return tuple(r for r in range(1, total_rounds + 1)
                 if _legacy_round_report_text(teg_num, r) is not None)


def _round_kind(teg_num: int, round_num: int) -> str:
    """'new' (round-storyline edition), 'legacy' (old markdown), or 'none'."""
    if round_num in available_rounds(teg_num):
        return "new"
    if round_num in _legacy_round_numbers(teg_num):
        return "legacy"
    return "none"


@lru_cache(maxsize=1)
def _teg_numbers_with_any_report() -> tuple[int, ...]:
    """Superset of `available_report_tegs()` that also counts a legacy-only
    round report — a TEG with nothing through either storyline-first pipeline
    yet, but with `round_reports/` or a legacy-styled round file, must still
    be selectable or its rounds could never be reached."""
    from teg_analysis.io.file_operations import read_file
    from teg_analysis.reporting.newspaper_edition import COMPLETED_TEGS_CSV, available_report_tegs
    already = set(available_report_tegs())
    try:
        completed = read_file(COMPLETED_TEGS_CSV)
        candidates = sorted(int(n) for n in completed["TEGNum"].astype(int).unique())
    except Exception:          # noqa: BLE001
        return tuple(sorted(already))
    return tuple(t for t in candidates if t in already or _legacy_round_numbers(t))


def _clear_legacy_round_caches() -> None:
    _legacy_round_report_text.cache_clear()
    _legacy_round_numbers.cache_clear()
    _teg_numbers_with_any_report.cache_clear()


# Edition discovery is memoised in `newspaper_edition` (a missing file costs a
# GitHub round-trip on Railway), so a newly synced report would not appear
# until the process restarted without this. Cleared on any data-cache clear
# (incl. the report-sync button).
try:  # pragma: no cover - trivial wiring
    from webapp import deps as _deps
    _deps.register_cache_clearer(clear_edition_caches)
    _deps.register_cache_clearer(_clear_legacy_round_caches)
except Exception:  # noqa: BLE001 - never let cache wiring break the route module
    pass


@router.get("/teg-reports", response_class=HTMLResponse)
def teg_reports(request: Request, teg: Optional[int] = None, round: Optional[int] = None):
    """Render the TEG Reports page for one TEG's tournament report, or one
    of its rounds.

    Query params:
      teg    TEG number (int); defaults to the most recent with a report.
      round  round number (int); omit (or pass one with no report at all,
             new or legacy) for the tournament report.
    """
    teg_numbers = sorted(_teg_numbers_with_any_report(), reverse=True)

    if not teg_numbers:
        return templates.TemplateResponse(
            "teg_reports.html",
            {
                "request": request,
                "active_page": "teg-reports",
                "wide": True,
                "newspaper_page": True,
                "teg_numbers": [],
                "selected_teg": None,
                "has_tournament": False,
                "round_numbers": [],
                "selected_round": None,
                "desktop_html": None,
                "edition_json": None,
                "legacy_html": None,
                "caption": None,
                "no_report_message": None,
                "back_link": None,
                "back_label": None,
            },
        )

    selected_teg = teg if teg in teg_numbers else teg_numbers[0]
    has_tournament = has_edition(selected_teg)
    # The pill list is the union of new (round-storyline) and legacy-only
    # rounds — a round with BOTH always resolves "new" (`_round_kind`), so a
    # regenerated round silently takes over its existing pill rather than
    # gaining a duplicate.
    new_rounds = set(available_rounds(selected_teg))
    round_numbers = sorted(new_rounds | set(_legacy_round_numbers(selected_teg)))

    if round in round_numbers:
        selected_round = round
    elif not has_tournament and round_numbers:
        # This TEG has no tournament report yet (or, for an in-progress TEG,
        # can't) — land on its first available round instead of a guaranteed
        # "no tournament report" message.
        selected_round = round_numbers[0]
    else:
        selected_round = None

    round_kind = _round_kind(selected_teg, selected_round) if selected_round else "none"

    edition = None
    legacy_html = None
    no_report_message = None
    if round_kind == "legacy":
        legacy_html = _legacy_round_report_html(selected_teg, selected_round)
        if legacy_html is None:  # cache raced with a delete between the two lookups
            no_report_message = (
                f"No round {selected_round} report available yet for TEG {selected_teg}.")
    else:
        try:
            edition = build_edition(selected_teg, round_num=selected_round)
        except (FileNotFoundError, GithubException, ValueError) as exc:
            what = f"round {selected_round}" if selected_round else "tournament"
            no_report_message = f"No {what} report available yet for TEG {selected_teg} ({exc})."

    desktop_html = None
    edition_json = None
    caption = None
    if edition is not None:
        desktop_html = render_desktop_html(edition, rail="s2")
        edition_json = json.dumps(for_page(edition))
        if selected_teg < 8:
            caption = _PRE_TEG8_CAPTION

    return templates.TemplateResponse(
        "teg_reports.html",
        {
            "request": request,
            "active_page": "teg-reports",
            "wide": True,
            "newspaper_page": True,
            "teg_numbers": teg_numbers,
            "selected_teg": selected_teg,
            "has_tournament": has_tournament,
            "round_numbers": round_numbers,
            "selected_round": selected_round,
            "desktop_html": desktop_html,
            "edition_json": edition_json,
            "legacy_html": legacy_html,
            "caption": caption,
            "no_report_message": no_report_message,
            # A tournament report links back to its results page; a round
            # report (new or legacy) to its round-in-context page. Both know
            # the specific teg/round to deep-link to (both routes accept
            # those query params — webapp/routes/history.py,
            # webapp/routes/latest.py), so this is only worth offering when
            # there's a report to anchor it to.
            "back_link": (
                f"/latest-round?teg={selected_teg}&round={selected_round}"
                if (edition is not None or legacy_html is not None) and selected_round else
                f"/results?teg={selected_teg}" if edition is not None else None
            ),
            "back_label": f"Round {selected_round}" if selected_round else "Full Results",
        },
    )
