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
_STYLED_RE = re.compile(r"^teg_(\d+)_report_styled\.md$")
_MD_EXTS = ["extra", "sane_lists", "smarty", "toc"]


def _available_tegs() -> List[int]:
    """TEGs that have a styled report on disk, most recent first."""
    if not DATA_DIR.is_dir():
        return []
    tegs = []
    for p in DATA_DIR.iterdir():
        m = _STYLED_RE.match(p.name)
        if m:
            tegs.append(int(m.group(1)))
    return sorted(tegs, reverse=True)


def _render_report_html(teg: int) -> Optional[str]:
    """Read the styled MD for `teg` and return rendered HTML, or None if absent."""
    path = DATA_DIR / f"teg_{teg}_report_styled.md"
    if not path.is_file():
        return None
    return md_lib.markdown(path.read_text(encoding="utf-8"), extensions=_MD_EXTS)


@router.get("/teg-reports", response_class=HTMLResponse)
async def teg_reports(request: Request, teg: Optional[int] = None):
    available = _available_tegs()
    if teg is None and available:
        teg = available[0]

    html = _render_report_html(teg) if teg is not None else None

    return templates.TemplateResponse(
        "teg_reports.html",
        {
            "request": request,
            "active_page": "teg-reports",
            "available_tegs": available,
            "selected_teg": teg,
            "html": html,
        },
    )
