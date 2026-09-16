"""Design-review dev tool — heading/title style comparison pages.

Not part of the product surface: no auth, not linked from nav, not in
STATUS/TODOS. Lets Jon compare candidate header treatments (page title,
card header, tab label, section sub-header, chart/table title) side by
side, including live-switching the existing ts-*/ch-* cookie-driven
styles already defined in theme.py + base-vars.css.
"""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from webapp.theme import TITLE_STYLES, TITLE_STYLE_IDS, CARD_HEADER_STYLES, CARD_HEADER_IDS

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/design/headers")
def design_headers(request: Request):
    return templates.TemplateResponse("design_lab.html", {
        "request": request,
        "active_page": None,
        "title_styles": TITLE_STYLES,
        "card_header_styles": CARD_HEADER_STYLES,
    })


@router.get("/design/titles")
def design_titles(request: Request):
    return templates.TemplateResponse("title_preview.html", {
        "request": request,
        "active_page": None,
    })


@router.get("/design/set-title-style")
def set_title_style(request: Request, value: str, back: str = "/design/headers"):
    resp = RedirectResponse(url=back, status_code=303)
    if value in TITLE_STYLE_IDS:
        resp.set_cookie("title_style", value, max_age=31536000, path="/")
    return resp


@router.get("/design/set-card-header")
def set_card_header(request: Request, value: str, back: str = "/design/headers"):
    resp = RedirectResponse(url=back, status_code=303)
    if value in CARD_HEADER_IDS:
        resp.set_cookie("card_header", value, max_age=31536000, path="/")
    return resp


@router.get("/design/preview")
def design_preview(request: Request):
    """Full-page mockup (title/tabs/sections/table/chart, dummy content
    resembling /latest-round) so Jon can see combinations of all five header
    levels together, not just isolated snippets. Page title / card header use
    the real cookie-driven ts-*/ch-* infra (a page reload on change, like
    /design/headers); tab label / section sub-header / chart title have no
    server-side infra yet, so they're switched client-side via the same
    hh-tab-*/hh-subhead-*/hh-charttitle-* classes design_lab.html defines."""
    return templates.TemplateResponse("design_lab_preview.html", {
        "request": request,
        "active_page": None,
        "title_styles": TITLE_STYLES,
        "card_header_styles": CARD_HEADER_STYLES,
    })


@router.get("/design/apply-starting-combo")
def apply_starting_combo(request: Request):
    """One-click convenience: sets title/card-header cookies to Jon's stated
    starting point (Page title A, Card header off) and lands on the preview
    page, where the other three dropdowns already default to his other picks
    (Tab label Alt B, Section sub-header Alt C, Chart/table title Alt A)."""
    resp = RedirectResponse(url="/design/preview", status_code=303)
    resp.set_cookie("title_style", "a", max_age=31536000, path="/")
    resp.set_cookie("card_header", "ch0", max_age=31536000, path="/")
    return resp
