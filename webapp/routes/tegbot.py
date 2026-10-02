"""TEGBot 5000 — ask questions about TEG stats in plain English.

The page posts one question at a time (plus the earlier turns, text only, held
in the page). The answer partial shows the reply and, folded away, every tool
call the bot made — the deterministic calculation behind the numbers.

Spend guards are in-process: a per-visitor hourly limit and a site-wide daily
cap (``TEGBOT_DAILY_LIMIT``). Both reset when the process restarts. Set
``TEGBOT_ENABLED=0`` to switch the bot off without a deploy of code.
"""

import html
import json
import logging
import os
import re
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

import markdown
from fastapi import APIRouter, Form, Request
from fastapi.templating import Jinja2Templates

import webapp.deps as deps
from teg_analysis.chatbot import bot
from teg_analysis.chatbot.tools import ChatData
from teg_analysis.reporting.llm import has_api_key

# The app sets no logging config, so a plain module logger drops INFO. A child of
# uvicorn's logger uses its handler, so the per-question cost line reaches Railway.
logger = logging.getLogger("uvicorn.error.tegbot")
router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

PER_VISITOR_HOURLY = 20
DEFAULT_DAILY_LIMIT = 200

EXAMPLE_QUESTIONS = [
    "Who's won the most TEG Trophies?",
    "Who bounces back best from bogeys?",
    "Who has the best average on par 3s?",
    "What's the best gross round ever?",
    "How many podium finishes has each player had?",
]

_lock = threading.Lock()
_visitor_hits: dict[str, deque] = defaultdict(deque)
_daily = {"date": None, "count": 0}


def _enabled() -> bool:
    return os.environ.get("TEGBOT_ENABLED", "1") != "0" and has_api_key()


def _daily_limit() -> int:
    try:
        return int(os.environ.get("TEGBOT_DAILY_LIMIT", DEFAULT_DAILY_LIMIT))
    except ValueError:
        return DEFAULT_DAILY_LIMIT


def _visitor_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else "?")


def _take_slot(visitor: str) -> str | None:
    """Reserve one question. Returns a refusal message, or None if allowed."""
    now = time.time()
    today = datetime.now(timezone.utc).date()
    with _lock:
        if _daily["date"] != today:
            _daily.update(date=today, count=0)
        if _daily["count"] >= _daily_limit():
            return "TEGBot has answered its fill of questions today. Try again tomorrow."
        hits = _visitor_hits[visitor]
        while hits and now - hits[0] > 3600:
            hits.popleft()
        if len(hits) >= PER_VISITOR_HOURLY:
            return "That's a lot of questions for one hour. Give TEGBot a breather."
        hits.append(now)
        _daily["count"] += 1
    return None


_HREF = re.compile(r'<a href="([^"]*)"')
_LIST_START = re.compile(r"^\s*(?:[-*+]|\d+\.)\s")


def _blank_line_before_lists(text: str) -> str:
    """Markdown needs a blank line before a list; models often skip it."""
    out: list[str] = []
    for line in text.splitlines():
        if _LIST_START.match(line) and out and out[-1].strip() and not _LIST_START.match(out[-1]):
            out.append("")
        out.append(line)
    return "\n".join(out)


def render_answer_html(text: str) -> str:
    """Markdown → HTML with raw HTML escaped and only on-site links kept."""
    out = markdown.markdown(
        _blank_line_before_lists(html.escape(text, quote=False)), extensions=["tables"])

    def _keep_local(match: re.Match) -> str:
        href = match.group(1)
        if href.startswith("/") and not href.startswith("//"):
            return f'<a href="{href}"'
        return "<a"
    return _HREF.sub(_keep_local, out)


def _chat_data() -> ChatData:
    return ChatData(all_data=deps.cached_load_all_data, winners=deps.cached_winners)


@router.get("/tegbot")
def tegbot_page(request: Request):
    return templates.TemplateResponse("tegbot.html", {
        "request": request,
        "active_page": "tegbot",
        "enabled": _enabled(),
        "examples": EXAMPLE_QUESTIONS,
        "max_chars": bot.MAX_QUESTION_CHARS,
    })


@router.post("/tegbot/ask")
def tegbot_ask(request: Request, question: str = Form(""), history: str = Form("[]")):
    question = question.strip()[:bot.MAX_QUESTION_CHARS]
    ctx = {"request": request, "question": question}

    def _reply(**extra):
        return templates.TemplateResponse("partials/tegbot_answer.html", {**ctx, **extra})

    if not question:
        return _reply(error="Ask me something first.")
    if not _enabled():
        return _reply(error="TEGBot is switched off at the moment.")
    refusal = _take_slot(_visitor_key(request))
    if refusal:
        return _reply(error=refusal)
    try:
        prior = json.loads(history)
    except (json.JSONDecodeError, TypeError):
        prior = []

    started = time.time()
    try:
        answer = bot.ask(question, _chat_data(), history=prior)
    except Exception:
        logger.exception("TEGBot failed on %r", question)
        return _reply(error="TEGBot fell over. Try again in a moment.")
    logger.info(
        "TEGBot q=%r tools=%s secs=%.1f cost=$%.4f usage=%s",
        question, [c.name for c in answer.tool_calls], time.time() - started,
        answer.cost_usd, answer.usage,
    )
    return _reply(
        answer_text=answer.text,
        answer_html=render_answer_html(answer.text),
        tool_calls=[
            {"name": c.name,
             "input": json.dumps(c.input, indent=1, default=str),
             "output": json.dumps(c.output, indent=1, default=str)[:6000]}
            for c in answer.tool_calls
        ],
    )
