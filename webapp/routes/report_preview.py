"""TEG Reports preview — /teg-reports-preview.

Wires the settled newspaper layout (see
`webapp/report_layout_prototypes/README.md`) into the site as a standalone
preview page: NOT linked from `base.html`'s nav, and does not touch
`/teg-reports` (`webapp/routes/reports.py`) at all. We switch over to this
layout only once the preview is right, as a separate change.

Only TEGs with storyline-first artefacts (`AVAILABLE_TEGS`) have an edition;
everything else falls through to `no_report_message`, same pattern as
`reports.py`.

Desktop is rendered server-side (`render_desktop_html` — a straight Python
port of `composite.html`'s JS, no interactivity needed). Mobile pattern A
needs an index screen and a per-article screen with hash routing for the
phone's Back gesture, so the edition is also embedded as JSON and
`webapp/static/newspaper_preview.js` renders it client-side into
`#mobile-stage`; a CSS breakpoint in `newspaper_preview.css` shows only one of
the two stages at a time.
"""

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from github import GithubException

from teg_analysis.reporting.newspaper_edition import (
    AVAILABLE_TEGS,
    build_edition,
    choose_arrangement,
    render_desktop_html,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/teg-reports-preview", response_class=HTMLResponse)
def teg_reports_preview(request: Request, teg: Optional[int] = None):
    """Render the newspaper-layout preview page for one TEG.

    Query params:
      teg   TEG number; defaults to the most recent with an edition. Any TEG
            outside AVAILABLE_TEGS (or with an unreadable artefact) shows
            `no_report_message` instead of a report.
    """
    teg_numbers = sorted(AVAILABLE_TEGS, reverse=True)
    selected_teg = teg if teg in AVAILABLE_TEGS else teg_numbers[0]

    edition = None
    desktop_html = None
    arrangement = None
    edition_json = None
    no_report_message = None

    try:
        edition = build_edition(selected_teg)
    except (FileNotFoundError, GithubException, ValueError) as exc:
        no_report_message = f"No newspaper edition available for TEG {selected_teg} ({exc})."

    if edition is not None:
        arrangement = choose_arrangement(edition)
        desktop_html = render_desktop_html(edition)
        edition_json = json.dumps(edition)

    return templates.TemplateResponse(
        "teg_reports_preview.html",
        {
            "request": request,
            "teg_numbers": teg_numbers,
            "selected_teg": selected_teg,
            "arrangement": arrangement,
            "desktop_html": desktop_html,
            "edition_json": edition_json,
            "no_report_message": no_report_message,
        },
    )
