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

LEGACY ROUND FALLBACK — removed 2026-09-13, backfill complete. Every round
across TEGs 2–18 now has a round-storyline edition (`available_rounds(teg)`),
so the one-blob markdown fallback this page carried between 2026-09-11 and
2026-09-13 (`_legacy_round_report_html`, reading `round_reports/` and the
pre-2026-09-11 `teg_N_round_R_report_styled.md` naming) was deleted along
with the data it read (`data/commentary/round_reports/`, archived to
`data/commentary/archive 2026 v4/round_reports/`). **`teg_reports.css` was
NOT deleted** despite an earlier note here saying it should be — it is still
loaded globally in `base.html` because `webapp/templates/partials/
latest_round_tab.html` and `latest_teg_tab.html` render a *different*,
still-active legacy fallback (2025-vintage `drafts/` prose) via the same
`.teg-report` class. Don't remove it without checking those first.

All file reads go through `teg_analysis.io.read_text_file`, which is
volume-then-GitHub-aware on Railway (checks the mounted volume, falls back to
the GitHub API, caches the result).
"""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from github import GithubException

from teg_analysis.io import read_binary_file, read_text_file
from teg_analysis.reporting.report_pdf import PDF_DIR, pdf_filename

from teg_analysis.reporting.newspaper_edition import (
    available_report_tegs,
    available_rounds,
    build_edition,
    clear_edition_caches,
    for_page,
    has_edition,
    render_desktop_html,
)

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

# Caption shown for pre-TEG-8 tournament reports (matches streamlit/teg_reports.py)
_PRE_TEG8_CAPTION = ( ""
    # "NB: The TEG Trophy winners before TEG 8 were decided by best net; "
    # "the report here is written based on Stableford so finishing positions may be inaccurate"
)



# Edition discovery is memoised in `newspaper_edition` (a missing file costs a
# GitHub round-trip on Railway), so a newly synced report would not appear
# until the process restarted without this. Cleared on any data-cache clear
# (incl. the report-sync button).
# ---------------------------------------------------------------------------
# Pre-rendered PDFs
#
# The PDFs are built offline by `scripts/build_report_pdfs.py` and committed to
# `data/commentary/pdfs/` — the webapp only ever reads them, never renders one
# (rendering needs headless Chromium, which is deliberately not a Railway
# dependency; see `teg_analysis/reporting/report_pdf.py`).
#
# Whether a given report HAS a PDF is answered from the manifest the build
# script writes alongside them, not by probing for the file. On Railway a
# missing file costs a GitHub round-trip, and the button is rendered on every
# page load for every TEG — probing would put one of those in the hot path each
# time a report without a PDF was opened. One small cached JSON read covers the
# whole set instead.
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _pdf_manifest() -> dict:
    """The PDF build manifest, or an empty dict if there isn't one yet.

    Never raises: a missing or malformed manifest just means "no PDFs", which
    hides the download button rather than breaking the page.
    """
    try:
        return json.loads(read_text_file(f"{PDF_DIR}/manifest.json"))
    except Exception as exc:  # noqa: BLE001 - absence is normal, not an error
        logger.debug("No PDF manifest available: %s", exc)
        return {}


def _pdf_key(teg: int, round_num: Optional[int]) -> str:
    """Manifest key for one edition — matches `pdf_filename` without the suffix."""
    return pdf_filename(teg, round_num).removesuffix(".pdf")


def has_pdf(teg: int, round_num: Optional[int]) -> bool:
    """True when a pre-rendered PDF exists for this edition."""
    return _pdf_key(teg, round_num) in (_pdf_manifest().get("entries") or {})


def _clear_pdf_manifest_cache() -> None:
    _pdf_manifest.cache_clear()


try:  # pragma: no cover - trivial wiring
    from webapp import deps as _deps
    _deps.register_cache_clearer(clear_edition_caches)
    _deps.register_cache_clearer(_clear_pdf_manifest_cache)
except Exception:  # noqa: BLE001 - never let cache wiring break the route module
    pass


@router.get("/teg-reports", response_class=HTMLResponse)
def teg_reports(request: Request, teg: Optional[int] = None, round: Optional[int] = None):
    """Render the TEG Reports page for one TEG's tournament report, or one
    of its rounds.

    Query params:
      teg    TEG number (int); defaults to the most recent with a report.
      round  round number (int); omit (or pass one with no report at all)
             for the tournament report.
    """
    teg_numbers = sorted(available_report_tegs(), reverse=True)

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
                "caption": None,
                "no_report_message": None,
                "back_link": None,
                "back_label": None,
                "pdf_available": False,
            },
        )

    selected_teg = teg if teg in teg_numbers else teg_numbers[0]
    has_tournament = has_edition(selected_teg)
    round_numbers = sorted(available_rounds(selected_teg))

    if round in round_numbers:
        selected_round = round
    elif not has_tournament and round_numbers:
        # This TEG has no tournament report yet (or, for an in-progress TEG,
        # can't) — land on its first available round instead of a guaranteed
        # "no tournament report" message.
        selected_round = round_numbers[0]
    else:
        selected_round = None

    edition = None
    no_report_message = None
    try:
        edition = build_edition(selected_teg, round_num=selected_round)
    except (FileNotFoundError, GithubException, ValueError) as exc:
        what = f"round {selected_round}" if selected_round else "tournament"
        no_report_message = f"No {what} report available yet for TEG {selected_teg} ({exc})."

    desktop_html = None
    edition_json = None
    caption = None
    if edition is not None:
        desktop_html = render_desktop_html(edition, rail="s2", story_anchors=True)
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
            "caption": caption,
            "no_report_message": no_report_message,
            # A tournament report links back to its results page; a round
            # report to its round-in-context page. Both know the specific
            # teg/round to deep-link to (both routes accept those query
            # params — webapp/routes/history.py, webapp/routes/latest.py),
            # so this is only worth offering when there's a report to anchor
            # it to.
            "back_link": (
                f"/latest-round?teg={selected_teg}&round={selected_round}"
                if edition is not None and selected_round else
                f"/results?teg={selected_teg}" if edition is not None else None
            ),
            "back_label": f"Round {selected_round} detail" if selected_round else "Full Results",
            # Download button is rendered only when this edition actually has a
            # pre-rendered PDF, so a report whose PDF hasn't been built yet
            # simply shows no button rather than a link that 404s.
            "pdf_available": edition is not None and has_pdf(selected_teg, selected_round),
        },
    )


@router.get("/teg-reports/pdf")
def teg_report_pdf(teg: int, round: Optional[int] = None):
    """Serve the pre-rendered A4-width PDF for one tournament or round report.

    Bytes only — this route never renders anything. The PDFs are built offline
    (`scripts/build_report_pdfs.py`) and read through `read_binary_file`, which
    is volume-then-GitHub aware on Railway exactly like the report artefacts
    themselves.
    """
    name = pdf_filename(teg, round)
    try:
        data = read_binary_file(f"{PDF_DIR}/{name}")
    except (FileNotFoundError, GithubException) as exc:
        what = f"round {round}" if round else "tournament"
        raise HTTPException(
            status_code=404,
            detail=f"No PDF available for the TEG {teg} {what} report.",
        ) from exc

    # A filename someone will recognise in their downloads folder, rather than
    # the storage name.
    label = f"TEG-{teg}-round-{round}" if round else f"TEG-{teg}"
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{label}-report.pdf"',
            "Cache-Control": "public, max-age=3600",
        },
    )
