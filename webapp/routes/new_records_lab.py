"""New-record marking prototype -- dev tool for choosing how /records flags
records set in the "new" TEG (in-progress, else last completed).

Not part of the product surface: no auth, not linked from nav, not in
STATUS. Style switching is client-side only (data attributes on a wrapper,
remembered in localStorage); the real /records already emits the
``rec-*--new`` classes, unstyled. Once a style is chosen, move its CSS from
webapp/static/new-records-lab.css into production and delete this lab.
"""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from webapp.deps import get_current_in_progress_teg_fast, get_last_completed_teg_fast
from webapp.routes.records import TABS, _new_banner, _tab_context, new_record_teg

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

ROW_STYLES = [
    ("star", "Star"), ("pill", "NEW pill"), ("green", "Green bold"),
    ("bar", "Left bar"), ("when", "Occasion chip"), ("combo", "Combo"),
]
TAB_STYLES = [("none", "None"), ("dot", "Dot"), ("star", "Star"), ("count", "Count")]
QUICK_TEGS = [18, 17, 10]


@router.get("/design/new-records")
def new_records_lab(request: Request, teg: int | None = None, tab: str = "teg"):
    tab = tab if tab in {t for t, _ in TABS} else "teg"
    detected = new_record_teg()
    in_progress, _ = get_current_in_progress_teg_fast()
    in_progress = int(in_progress) if in_progress else None
    last_completed, _ = get_last_completed_teg_fast()
    last_completed = int(last_completed) if last_completed else None

    new_teg = teg if teg is not None else detected
    if teg is not None and teg != detected:
        reason = f"TEG {teg} set by the URL override (the site would use TEG {detected})."
    elif new_teg is not None and new_teg == in_progress:
        reason = f"TEG {new_teg} is in progress, so its records count as new."
    else:
        reason = f"No TEG is in progress, so the last completed TEG ({new_teg}) counts as new."
    is_in_progress = new_teg is not None and new_teg == in_progress

    tab_counts = {}
    for tab_id, _label in TABS:
        tab_counts[tab_id] = _tab_context(tab_id, new_teg=new_teg).get("new_count", 0)
    ctx = _tab_context(tab, new_teg=new_teg)

    return templates.TemplateResponse("new_records_lab.html", {
        "request": request,
        "active_page": None,
        "tabs": TABS,
        "active_tab": tab,
        "teg": new_teg,
        "reason": reason,
        "is_in_progress": is_in_progress,
        "new_banner": _new_banner(ctx, new_teg),
        "tab_counts": tab_counts,
        "row_styles": ROW_STYLES,
        "tab_styles": TAB_STYLES,
        "quick_tegs": QUICK_TEGS,
        **ctx,
    })
