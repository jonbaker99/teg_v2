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

Query params (all provisional switch scaffolding for layout review — see
`webapp/report_layout_prototypes/README.md` "Still to do"; remove alongside
the CSS/template switch markup once choices are locked in):

    teg=<int>          TEG number; defaults to the most recent with an
                        edition (unchanged from before the switches).
    pal=a|b|c|d         Type & palette (elements.html .pal-a..d). Default a.
    sf=italic|roman|edge|contrast  Standfirst treatment (elements.html
                        H1/H2/H4, plus `contrast`: upright, in the palette's
                        `--font-contrast` — the opposite family from the
                        headline's `--font-display`). Default italic (today's
                        look).
    rail=s1|s2          Standings rail: s2 = rail beside the lead (default,
                        today's look), s1 = no rail, results as a full-width
                        strip (elements.html railVariants() S1).

Any unrecognised value for pal/sf/rail falls back to its default rather than
erroring — values are whitelisted against a known set before ever reaching a
CSS class or template attribute.
"""

import json
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

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

_VALID_PAL = {"a", "b", "c", "d"}
_VALID_SF = {"italic", "roman", "edge", "contrast"}
_VALID_RAIL = {"s1", "s2"}
_DEFAULT_PAL, _DEFAULT_SF, _DEFAULT_RAIL = "a", "italic", "s2"


def _switch_url(current: dict[str, object], **overrides) -> str:
    """Build a `/teg-reports-preview` link carrying all four switch params
    from `current`, with `overrides` replacing one of them — so every switch
    link preserves the other three instead of resetting them."""
    params = dict(current)
    params.update(overrides)
    return "/teg-reports-preview?" + urlencode(params)


@router.get("/teg-reports-preview", response_class=HTMLResponse)
def teg_reports_preview(
    request: Request,
    teg: Optional[int] = None,
    pal: Optional[str] = None,
    sf: Optional[str] = None,
    rail: Optional[str] = None,
):
    """Render the newspaper-layout preview page for one TEG.

    See the module docstring for the `teg`/`pal`/`sf`/`rail` query params.
    """
    teg_numbers = sorted(AVAILABLE_TEGS, reverse=True)
    selected_teg = teg if teg in AVAILABLE_TEGS else teg_numbers[0]
    selected_pal = pal if pal in _VALID_PAL else _DEFAULT_PAL
    selected_sf = sf if sf in _VALID_SF else _DEFAULT_SF
    selected_rail = rail if rail in _VALID_RAIL else _DEFAULT_RAIL

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
        desktop_html = render_desktop_html(edition, rail=selected_rail)
        edition_json = json.dumps(edition)

    current_switches = {"teg": selected_teg, "pal": selected_pal, "sf": selected_sf, "rail": selected_rail}

    def make_url(**overrides):
        return _switch_url(current_switches, **overrides)

    return templates.TemplateResponse(
        "teg_reports_preview.html",
        {
            "request": request,
            "teg_numbers": teg_numbers,
            "selected_teg": selected_teg,
            "selected_pal": selected_pal,
            "selected_sf": selected_sf,
            "selected_rail": selected_rail,
            "arrangement": arrangement,
            "desktop_html": desktop_html,
            "edition_json": edition_json,
            "no_report_message": no_report_message,
            "make_url": make_url,
        },
    )
