"""TEG Reports — render styled markdown reports to HTML for the webapp.

Reads the styled MD produced by `teg_analysis.reporting.render.style_report()`
(class-tagged headings + dateline + at-a-glance callout) and renders it to HTML
using the `markdown` library with the same extensions the streamlit page uses.

All file reads go through `teg_analysis.io.read_text_file`, which is
volume-then-GitHub-aware on Railway (checks the mounted volume, falls back to
the GitHub API, caches the result). There is no volume-aware directory
listing, so TEG/round *discovery* (for the dropdown + pills) is driven by
`data/completed_tegs.csv` instead of scanning `data/commentary/` — see
`_completed_teg_numbers` / `_available_rounds_for_teg`.

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

from pathlib import Path
from typing import Optional

import markdown as md_lib
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from github import GithubException

from teg_analysis.io import read_text_file
from teg_analysis.io.file_operations import read_file

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

DATA_DIR = "data/commentary"
DRAFTS_DIR = f"{DATA_DIR}/drafts"
ROUND_REPORTS_DIR = f"{DATA_DIR}/round_reports"
_COMPLETED_TEGS_CSV = "data/completed_tegs.csv"
_MD_EXTS = ["extra", "sane_lists", "smarty", "toc"]

# Caption shown for pre-TEG-8 tournament reports (matches streamlit/teg_reports.py)
_PRE_TEG8_CAPTION = (
    "NB: The TEG Trophy winners before TEG 8 were decided by best net; "
    "the report here is written based on Stableford so finishing positions may be inaccurate"
)


def _read_file(path: str) -> Optional[str]:
    """Return file text via the volume/GitHub-aware read path, or None if missing."""
    try:
        return read_text_file(path)
    except (FileNotFoundError, GithubException):
        return None


def _render_md(text: str) -> str:
    """Convert markdown text to HTML string."""
    return md_lib.markdown(text, extensions=_MD_EXTS)


def _first_existing(candidates: list[str]) -> Optional[str]:
    """Return the text of the first candidate path that exists, else None."""
    for path in candidates:
        text = _read_file(path)
        if text is not None:
            return text
    return None


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------

def _completed_teg_numbers() -> list[int]:
    """TEG numbers from `data/completed_tegs.csv` (played tournaments).

    Used to drive the TEG dropdown / round pills instead of scanning
    `data/commentary/` (there's no volume-aware directory listing). A
    completed TEG that has no report generated yet just falls through to the
    "no report available" message when selected.
    """
    try:
        completed = read_file(_COMPLETED_TEGS_CSV)
        if completed.empty:
            return []
        return sorted(int(n) for n in completed["TEGNum"].astype(int).unique())
    except Exception:
        return []


def _rounds_played_for_teg(teg_num: int) -> int:
    """Number of rounds played in this TEG, from `data/completed_tegs.csv` (default 4)."""
    try:
        completed = read_file(_COMPLETED_TEGS_CSV)
        row = completed[completed["TEGNum"].astype(int) == teg_num]
        if row.empty:
            return 4
        return int(row.iloc[0]["Rounds"])
    except Exception:
        return 4


def _tournament_teg_numbers() -> list[int]:
    """Return sorted list of TEG numbers that have a tournament report."""
    return sorted(_completed_teg_numbers(), reverse=True)


def _round_teg_numbers() -> list[int]:
    """Return sorted list of TEG numbers that have any round report."""
    return sorted(_completed_teg_numbers(), reverse=True)


def _available_rounds_for_teg(teg_num: int) -> list[int]:
    """Return sorted list of round numbers that have a report for the given TEG.

    Bounded probe (rounds 1..N played, from completed_tegs.csv) via the
    volume/GitHub-aware read path — there's no directory listing on Railway.
    """
    rounds = []
    for r in range(1, _rounds_played_for_teg(teg_num) + 1):
        if _load_round_report(teg_num, r)[1]:
            rounds.append(r)
    return rounds


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
        text = _read_file(f"{DRAFTS_DIR}/teg_{teg_num}_satire.md")
        if text is None:
            return None, False
        return _render_md(text), True

    # Normal: prefer styled, fallback to main_report
    text = _first_existing([
        f"{DATA_DIR}/teg_{teg_num}_report_styled.md",
        f"{DRAFTS_DIR}/teg_{teg_num}_main_report.md",
    ])
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
    text = _first_existing([
        f"{DATA_DIR}/teg_{teg_num}_round_{round_num}_report_styled.md",
        f"{ROUND_REPORTS_DIR}/TEG{teg_num}_R{round_num}_report.md",
        f"{ROUND_REPORTS_DIR}/teg_{teg_num}_round_{round_num}_report.md",
    ])
    if text is None:
        return None, False
    return _render_md(text), True


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.get("/teg-reports", response_class=HTMLResponse)
def teg_reports(
    request: Request,
    report_type: Optional[str] = None,
    teg: Optional[int] = None,
    round: Optional[int] = None,
    variant: str = "normal",
):
    """Render the TEG Reports page.

    Query params:
      teg          TEG number (int); defaults to the highest available
      report_type  which report "piece" to show: "round" or "tournament".
                   Defaults to the tournament report when one exists, else the
                   first round.
      round        round number (when report_type="round")
      variant      "normal" or "satire" (tournament reports only)

    The TEG dropdown lists every TEG that has any report; the round/tournament
    choice is presented as pills (one per available round + Tournament).
    """
    tournament_tegs = set(_tournament_teg_numbers())
    round_tegs = set(_round_teg_numbers())
    teg_numbers = sorted(tournament_tegs | round_tegs, reverse=True)

    if not teg_numbers:
        return templates.TemplateResponse(
            "teg_reports.html",
            {
                "request": request,
                "active_page": "teg-reports",
                "report_type": "tournament",
                "teg_numbers": [],
                "selected_teg": None,
                "available_rounds": [],
                "selected_round": None,
                "has_tournament": False,
                "variant": variant,
                "html": None,
                "caption": None,
                "satire_available": False,
                "no_report_message": None,
            },
        )

    if teg is None or teg not in teg_numbers:
        teg = teg_numbers[0]

    available_rounds = _available_rounds_for_teg(teg)
    has_tournament = teg in tournament_tegs

    # Resolve which piece to show for this TEG, with sensible fallbacks.
    if report_type not in ("tournament", "round"):
        report_type = "tournament" if has_tournament else "round"
    if report_type == "tournament" and not has_tournament and available_rounds:
        report_type = "round"
    if report_type == "round" and not available_rounds and has_tournament:
        report_type = "tournament"

    selected_round = None
    if report_type == "round" and available_rounds:
        selected_round = round if (round in available_rounds) else available_rounds[0]

    html = None
    caption = None
    satire_available = False
    no_report_message = None

    if report_type == "tournament":
        satire_available = _read_file(f"{DRAFTS_DIR}/teg_{teg}_satire.md") is not None
        if variant not in ("normal", "satire"):
            variant = "normal"
        html, found = _load_tournament_report(teg, variant)
        if not found:
            no_report_message = (
                f"No satire draft available for TEG {teg}." if variant == "satire"
                else f"No tournament report available yet for TEG {teg}."
            )
        if found and variant == "normal" and teg < 8:
            caption = _PRE_TEG8_CAPTION
    else:  # round
        if selected_round is not None:
            html, found = _load_round_report(teg, selected_round)
            if not found:
                no_report_message = f"No round report available for TEG {teg} Round {selected_round}."
        else:
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
            "has_tournament": has_tournament,
            "variant": variant,
            "html": html,
            "caption": caption,
            "satire_available": satire_available,
            "no_report_message": no_report_message,
        },
    )
