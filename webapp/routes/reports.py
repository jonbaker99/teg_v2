"""TEG Reports — render styled markdown reports to HTML for the webapp.

Reads the styled MD produced by `teg_analysis.reporting.render.style_report()`
(class-tagged headings + dateline + at-a-glance callout) and renders it to HTML
using the `markdown` library with the same extensions the streamlit page uses.

Filename conventions supported
-------------------------------
Tournament reports (DATA_DIR = data/commentary/):
  1. teg_{N}_report_styled.md          (preferred)
  2. data/commentary/drafts/teg_{N}_main_report.md  (fallback)

Round reports:
  1. data/commentary/teg_{N}_round_{r}_report_styled.md   (preferred)
  2. data/commentary/round_reports/TEG{N}_R{r}_report.md  (new format)
  3. data/commentary/round_reports/teg_{N}_round_{r}_report.md (old format)

Satire (tournament only):
  data/commentary/drafts/teg_{N}_satire.md
"""

import re
from pathlib import Path
from typing import Optional

import markdown as md_lib
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

DATA_DIR = Path("data/commentary")
DRAFTS_DIR = DATA_DIR / "drafts"
ROUND_REPORTS_DIR = DATA_DIR / "round_reports"
_MD_EXTS = ["extra", "sane_lists", "smarty", "toc"]

# Caption shown for pre-TEG-8 tournament reports (matches streamlit/teg_reports.py)
_PRE_TEG8_CAPTION = (
    "NB: The TEG Trophy winners before TEG 8 were decided by best net; "
    "the report here is written based on Stableford so finishing positions may be inaccurate"
)


def _read_file(path: Path) -> Optional[str]:
    """Return file text if it exists, else None."""
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return None


def _render_md(text: str) -> str:
    """Convert markdown text to HTML string."""
    return md_lib.markdown(text, extensions=_MD_EXTS)


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------

def _tournament_teg_numbers() -> list[int]:
    """Return sorted list of TEG numbers that have a tournament report."""
    nums = set()
    if DATA_DIR.is_dir():
        for p in DATA_DIR.iterdir():
            # styled variant
            m = re.match(r"^teg_(\d+)_report_styled\.md$", p.name)
            if m:
                nums.add(int(m.group(1)))
    if DRAFTS_DIR.is_dir():
        for p in DRAFTS_DIR.iterdir():
            m = re.match(r"^teg_(\d+)_main_report\.md$", p.name)
            if m:
                nums.add(int(m.group(1)))
    return sorted(nums, reverse=True)


def _round_teg_numbers() -> list[int]:
    """Return sorted list of TEG numbers that have any round report."""
    nums = set()
    # Styled variants in DATA_DIR
    if DATA_DIR.is_dir():
        for p in DATA_DIR.iterdir():
            m = re.match(r"^teg_(\d+)_round_\d+_report_styled\.md$", p.name)
            if m:
                nums.add(int(m.group(1)))
    # New and old format in ROUND_REPORTS_DIR
    if ROUND_REPORTS_DIR.is_dir():
        for p in ROUND_REPORTS_DIR.iterdir():
            # New format: TEG{N}_R{r}_report.md
            m = re.match(r"^TEG(\d+)_R\d+_report\.md$", p.name)
            if m:
                nums.add(int(m.group(1)))
            # Old format: teg_{N}_round_{r}_report.md
            m = re.match(r"^teg_(\d+)_round_\d+_report\.md$", p.name)
            if m:
                nums.add(int(m.group(1)))
    return sorted(nums, reverse=True)


def _available_rounds_for_teg(teg_num: int) -> list[int]:
    """Return sorted list of round numbers that have a report for the given TEG."""
    rounds = set()
    # Styled variants in DATA_DIR
    if DATA_DIR.is_dir():
        for p in DATA_DIR.iterdir():
            m = re.match(rf"^teg_{teg_num}_round_(\d+)_report_styled\.md$", p.name)
            if m:
                rounds.add(int(m.group(1)))
    if ROUND_REPORTS_DIR.is_dir():
        for p in ROUND_REPORTS_DIR.iterdir():
            # New format: TEG{N}_R{r}_report.md
            m = re.match(rf"^TEG{teg_num}_R(\d+)_report\.md$", p.name)
            if m:
                rounds.add(int(m.group(1)))
            # Old format
            m = re.match(rf"^teg_{teg_num}_round_(\d+)_report\.md$", p.name)
            if m:
                rounds.add(int(m.group(1)))
    return sorted(rounds)


# ---------------------------------------------------------------------------
# Content loading
# ---------------------------------------------------------------------------

def _load_tournament_report(teg_num: int, variant: str) -> tuple[Optional[str], bool]:
    """Load tournament report HTML.

    Returns (html_or_None, file_found).
    For variant='satire', returns satire file if available.
    For variant='normal', prefers styled then falls back to main_report.
    """
    if variant == "satire":
        text = _read_file(DRAFTS_DIR / f"teg_{teg_num}_satire.md")
        if text is None:
            return None, False
        return _render_md(text), True

    # Normal: prefer styled, fallback to main_report
    text = _read_file(DATA_DIR / f"teg_{teg_num}_report_styled.md")
    if text is None:
        text = _read_file(DRAFTS_DIR / f"teg_{teg_num}_main_report.md")
    if text is None:
        return None, False
    return _render_md(text), True


def _load_round_report(teg_num: int, round_num: int) -> tuple[Optional[str], bool]:
    """Load round report HTML with fallback chain.

    Priority:
      1. data/commentary/teg_{N}_round_{r}_report_styled.md
      2. data/commentary/round_reports/TEG{N}_R{r}_report.md
      3. data/commentary/round_reports/teg_{N}_round_{r}_report.md
    """
    candidates = [
        DATA_DIR / f"teg_{teg_num}_round_{round_num}_report_styled.md",
        ROUND_REPORTS_DIR / f"TEG{teg_num}_R{round_num}_report.md",
        ROUND_REPORTS_DIR / f"teg_{teg_num}_round_{round_num}_report.md",
    ]
    for path in candidates:
        text = _read_file(path)
        if text is not None:
            return _render_md(text), True
    return None, False


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.get("/teg-reports", response_class=HTMLResponse)
async def teg_reports(
    request: Request,
    report_type: str = "tournament",
    teg: Optional[int] = None,
    round: Optional[int] = None,
    variant: str = "normal",
):
    """Render the TEG Reports page.

    Query params:
      report_type  "tournament" or "round" (default: "tournament")
      teg          TEG number (int); defaults to highest available
      round        Round number (int, only relevant when report_type="round")
      variant      "normal" or "satire" (only relevant when report_type="tournament")
    """
    # Collect available TEG numbers for the chosen type
    if report_type == "round":
        teg_numbers = _round_teg_numbers()
    else:
        report_type = "tournament"  # normalise any unknown value
        teg_numbers = _tournament_teg_numbers()

    # Default TEG to the highest available
    if not teg_numbers:
        return templates.TemplateResponse(
            "teg_reports.html",
            {
                "request": request,
                "active_page": "teg-reports",
                "report_type": report_type,
                "teg_numbers": [],
                "selected_teg": None,
                "available_rounds": [],
                "selected_round": None,
                "variant": variant,
                "html": None,
                "caption": None,
                "satire_available": False,
                "no_report_message": None,
            },
        )

    if teg is None or teg not in teg_numbers:
        teg = teg_numbers[0]

    # Round reports: pick round
    available_rounds = []
    selected_round = None
    if report_type == "round":
        available_rounds = _available_rounds_for_teg(teg)
        if available_rounds:
            if round is None or round not in available_rounds:
                selected_round = available_rounds[0]
            else:
                selected_round = round

    # Load content
    html = None
    caption = None
    satire_available = False
    no_report_message = None

    if report_type == "tournament":
        # Check satire availability for the toggle
        satire_available = (DRAFTS_DIR / f"teg_{teg}_satire.md").is_file()

        # Normalise variant
        if variant not in ("normal", "satire"):
            variant = "normal"

        html, found = _load_tournament_report(teg, variant)
        if not found:
            if variant == "satire":
                no_report_message = f"No satire draft available for TEG {teg}."
            else:
                no_report_message = f"No tournament report available yet for TEG {teg}."

        # Pre-TEG-8 caption for normal reports
        if found and variant == "normal" and teg < 8:
            caption = _PRE_TEG8_CAPTION

    else:  # round
        if selected_round is not None:
            html, found = _load_round_report(teg, selected_round)
            if not found:
                no_report_message = f"No round report available for TEG {teg} Round {selected_round}."
        elif not available_rounds:
            no_report_message = f"No round reports available for TEG {teg}."

    return templates.TemplateResponse(
        "teg_reports.html",
        {
            "request": request,
            "active_page": "teg-reports",
            "report_type": report_type,
            "teg_numbers": teg_numbers,
            "selected_teg": teg,
            "available_rounds": available_rounds,
            "selected_round": selected_round,
            "variant": variant,
            "html": html,
            "caption": caption,
            "satire_available": satire_available,
            "no_report_message": no_report_message,
        },
    )
