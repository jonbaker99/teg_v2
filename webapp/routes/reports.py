"""TEG Reports — render the styled markdown reports to HTML for the webapp.

Reads the styled MD produced by `teg_analysis.reporting.render.style_report()`
(class-tagged headings + dateline + at-a-glance callout) and renders it to HTML
using the `markdown` library with the same extensions the streamlit page uses.
"""

import re
from pathlib import Path
from typing import List, Optional

import markdown as md_lib
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

DATA_DIR = Path("data/commentary")
_TOURNEY_RE = re.compile(r"^teg_(\d+)_report_styled\.md$")
_ROUND_RE = re.compile(r"^teg_(\d+)_round_(\d+)_report_styled\.md$")
_MD_EXTS = ["extra", "sane_lists", "smarty", "toc"]


def _available_reports(report_type: str):
    if not DATA_DIR.is_dir():
        return []
    reports = []
    for p in DATA_DIR.iterdir():
        if report_type == "tournament":
            m = _TOURNEY_RE.match(p.name)
            if m:
                reports.append({"value": m.group(1), "label": f"TEG {m.group(1)}"})
        elif report_type == "round":
            m = _ROUND_RE.match(p.name)
            if m:
                reports.append({"value": f"{m.group(1)}_round_{m.group(2)}", "label": f"TEG {m.group(1)} - Round {m.group(2)}"})
    
    return sorted(reports, key=lambda x: x["value"], reverse=True)


def _render_report_html(teg: int) -> Optional[str]:
    """Read the styled MD for `teg` and return rendered HTML, or None if absent."""
    path = DATA_DIR / f"teg_{teg}_report_styled.md"
    if not path.is_file():
        return None
    return md_lib.markdown(path.read_text(encoding="utf-8"), extensions=_MD_EXTS)


@router.get("/teg-reports", response_class=HTMLResponse)
async def teg_reports(request: Request, report_type: str = "tournament", report_id: Optional[str] = None):
    available = _available_reports(report_type)
    
    # Auto-select the first available report if none selected or if type switched
    if report_id is None or not any(r["value"] == report_id for r in available):
        report_id = available[0]["value"] if available else None

    html = None
    if report_id:
        filename = f"teg_{report_id}_report_styled.md" if report_type == "tournament" else f"teg_{report_id}_report_styled.md"
        path = DATA_DIR / filename
        if path.is_file():
            html = md_lib.markdown(path.read_text(encoding="utf-8"), extensions=_MD_EXTS)

    return templates.TemplateResponse(
        "teg_reports.html",
        {
            "request": request,
            "active_page": "teg-reports",
            "report_type": report_type,
            "available_reports": available,
            "selected_report": report_id,
            "html": html,
        },
    )
