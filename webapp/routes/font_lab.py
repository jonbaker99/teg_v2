"""Font-choice prototype -- dev tool for picking sans / table-number / serif
fonts against real leaderboard and records content.

Not part of the product surface: no auth, not linked from nav, not in
STATUS/TODOS. Font swapping is entirely client-side via CSS custom
properties (no cookies, no reload) so options can be compared instantly;
`.col-num` / `.col-player` are the real classes `_leaderboard_table_html`
(webapp/routes/history.py) and `_build_records_html` (webapp/routes/
records.py) already emit, so the same font-lab.css rules apply to both
tables with no changes to production table-generation code.
"""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from webapp.deps import get_default_teg_num
from webapp.routes.history import _results_context
from webapp.routes.records import _tab_context
from webapp.theme import FONT_PAIRINGS, FONT_PAIRING_IDS

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/design/fonts")
def font_lab(request: Request):
    teg_num = get_default_teg_num()
    lb_ctx = _results_context(teg_num, "net", "adjusted", link_players=False)
    records_ctx = _tab_context("teg")
    return templates.TemplateResponse("font_lab.html", {
        "request": request,
        "active_page": None,
        "lb": lb_ctx,
        "records": records_ctx,
        "selected_teg": teg_num,
    })


@router.get("/design/typography")
def typography_lab(request: Request):
    """Site-wide sans+serif pairing picker -- unlike /design/fonts (instant,
    client-side, scoped to this page's own sample content), this sets the
    real font_pairing cookie base.html reads on every page, so the pairing
    can be judged against the whole live site, not just a sample. Includes a
    real leaderboard table + a prose paragraph on-page (same reasoning as
    font_lab.html's sample content) so the active pairing can be judged
    without navigating away first."""
    teg_num = get_default_teg_num()
    lb_ctx = _results_context(teg_num, "net", "adjusted", link_players=False)
    return templates.TemplateResponse("typography_lab.html", {
        "request": request,
        "active_page": None,
        "font_pairings": FONT_PAIRINGS,
        "lb": lb_ctx,
        "selected_teg": teg_num,
    })


@router.get("/design/set-font-pairing")
def set_font_pairing(request: Request, value: str, back: str = "/design/typography"):
    resp = RedirectResponse(url=back, status_code=303)
    if value in FONT_PAIRING_IDS:
        resp.set_cookie("font_pairing", value, max_age=31536000, path="/")
    return resp
