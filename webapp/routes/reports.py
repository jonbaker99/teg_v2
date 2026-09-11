"""TEG Reports — tournament reports, newspaper layout.

Tournament reports are rendered through the newspaper-edition pipeline
(`teg_analysis.reporting.newspaper_edition`): `build_edition` parses the two
storyline-first artefacts for a TEG into an edition dict, `render_desktop_html`
renders the desktop layout server-side, and the edition is also embedded as
JSON for `webapp/static/newspaper_preview.js` to render mobile pattern A
client-side. The page extends `base.html` (site nav retained) — see
`templates/teg_reports.html`; only the "paper" card itself carries the
newspaper design's own fonts/palette/reset, scoped via `.np-page`, not the
whole page. This replaced the old one-blob markdown render and the standalone
`/teg-reports-preview` page (2026-09-11) — see
`webapp/report_layout_prototypes/README.md` for the design record. Only TEGs
with storyline-first artefacts (`available_tegs()`) get a report.

Round reports are temporarily off (2026-09-11, Jon's call) — there is no
newspaper-layout equivalent yet (tracked in `teg_analysis/reporting/STATUS.md`
→ START HERE → *Next*, item 2 "Build the round-report equivalent"). Re-add a
round path here once that lands, rather than reviving the old markdown
renderer — the round page should get the same newspaper treatment.

All file reads go through `teg_analysis.io.read_text_file`, which is
volume-then-GitHub-aware on Railway (checks the mounted volume, falls back to
the GitHub API, caches the result).
"""

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from github import GithubException

from teg_analysis.reporting.newspaper_edition import (
    available_tegs,
    build_edition,
    clear_edition_caches,
    for_page,
    render_desktop_html,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

# Caption shown for pre-TEG-8 tournament reports (matches streamlit/teg_reports.py)
_PRE_TEG8_CAPTION = (
    "NB: The TEG Trophy winners before TEG 8 were decided by best net; "
    "the report here is written based on Stableford so finishing positions may be inaccurate"
)


# Edition discovery is memoised in `newspaper_edition` (a missing file costs a
# GitHub round-trip on Railway), so a newly synced report would not appear
# until the process restarted without this. Cleared on any data-cache clear
# (incl. the report-sync button).
try:  # pragma: no cover - trivial wiring
    from webapp import deps as _deps
    _deps.register_cache_clearer(clear_edition_caches)
except Exception:  # noqa: BLE001 - never let cache wiring break the route module
    pass


@router.get("/teg-reports", response_class=HTMLResponse)
def teg_reports(request: Request, teg: Optional[int] = None):
    """Render the TEG Reports page for one TEG's tournament report.

    Query params:
      teg   TEG number (int); defaults to the most recent with a report.
    """
    teg_numbers = sorted(available_tegs(), reverse=True)

    if not teg_numbers:
        return templates.TemplateResponse(
            "teg_reports.html",
            {
                "request": request,
                "active_page": "teg-reports",
                "wide": True,
                "teg_numbers": [],
                "selected_teg": None,
                "desktop_html": None,
                "edition_json": None,
                "caption": None,
                "no_report_message": None,
            },
        )

    selected_teg = teg if teg in teg_numbers else teg_numbers[0]

    edition = None
    no_report_message = None
    try:
        edition = build_edition(selected_teg)
    except (FileNotFoundError, GithubException, ValueError) as exc:
        no_report_message = f"No tournament report available yet for TEG {selected_teg} ({exc})."

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
            "teg_numbers": teg_numbers,
            "selected_teg": selected_teg,
            "desktop_html": desktop_html,
            "edition_json": edition_json,
            "caption": caption,
            "no_report_message": no_report_message,
        },
    )
