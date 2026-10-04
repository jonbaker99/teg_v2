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
import random
import re
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

import markdown
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from starlette.concurrency import run_in_threadpool
from fastapi.templating import Jinja2Templates

import webapp.deps as deps
from teg_analysis.chatbot import bot, qa_log
from teg_analysis.chatbot.tools import ChatData
from teg_analysis.reporting.llm import has_api_key
from webapp.admin_auth import is_authed

# The app sets no logging config, so a plain module logger drops INFO. A child of
# uvicorn's logger uses its handler, so the per-question cost line reaches Railway.
logger = logging.getLogger("uvicorn.error.tegbot")
router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

PER_VISITOR_HOURLY = 20
DEFAULT_DAILY_LIMIT = 200
MAX_HISTORY_BYTES = 64_000

#: The input's placeholder and the five example buttons are drawn at random from here.
EXAMPLE_QUESTIONS = [
    "Who's won the most TEG Trophies?",
    "Who bounces back best from bogeys?",
    "Who has the best average on par 3s?",
    "What's the best gross round ever?",
    "How many podium finishes has each player had?",
    "Who plays best in first rounds?",
    "When was the last eagle?",
    "Which course has the hardest par 3s?",
    "How often does the leader after round 1 win?",
    "Who is best on the back 9?",
    "Who has the longest run of pars or better?",
    "What happened the last time we played Boavista?",
    "Who has improved most over the years?",
    "Who finishes strongest over the last 3 holes?",
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
    # Rightmost entry: added by Railway's edge, so a client can't rotate it to
    # dodge the limit. Leftmost entries are whatever the client chose to send.
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[-1].strip() or (request.client.host if request.client else "?")


def _refund_slot(visitor: str) -> None:
    """Give back a question that failed through no fault of the visitor."""
    with _lock:
        if _visitor_hits[visitor]:
            _visitor_hits[visitor].pop()
        _daily["count"] = max(0, _daily["count"] - 1)


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
_IMG = re.compile(r"<img\b[^>]*>")
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
        if href.startswith("/") and not href.startswith("//") and "\\" not in href:
            return f'<a class="tb-page-link" href="{href}"'
        return "<a"
    out = _IMG.sub("", out)  # no external images (tracking pixels)
    return _box_method(_HREF.sub(_keep_local, out))


_METHOD_START = re.compile(r"<p>(?:<(?:strong|em)>)?\s*How (?:I worked this out|this was worked out)\b",
                           re.IGNORECASE)


def _box_method(out: str) -> str:
    """Put the "How I worked this out" note, and anything after it, in a small box."""
    m = _METHOD_START.search(out)
    if not m:
        return out
    return f'{out[:m.start()]}<div class="tb-how">{out[m.start():]}</div>'



def _working(call: "bot.ToolCall") -> dict:
    """One entry in "Show the workings": code as code, lookups as JSON."""
    if call.name == "code":
        shown_in = call.input.get("command") or call.input.get("file_text") or json.dumps(call.input)
        shown_out = call.output.get("stdout", "") + call.output.get("stderr", "")
        return {"name": "Code run in the sandbox", "input": shown_in[:6000],
                "output": (shown_out or json.dumps(call.output))[:6000]}
    return {"name": f"Lookup: {call.name}",
            "input": json.dumps(call.input, indent=1, default=str),
            "output": json.dumps(call.output, indent=1, default=str)[:6000]}


def _chat_data() -> ChatData:
    ranked = {"teg": deps.cached_ranked_teg_data, "round": deps.cached_ranked_round_data,
              "frontback": deps.cached_ranked_frontback_data}
    from webapp.routes.simulation import default_prediction
    return ChatData(all_data=deps.cached_load_all_data, winners=deps.cached_winners,
                    ranked=lambda scope: ranked[scope](), predictions=default_prediction)


@router.get("/tegbot")
def tegbot_page(request: Request):
    return templates.TemplateResponse("tegbot.html", {
        "request": request,
        "active_page": "tegbot",
        "enabled": _enabled(),
        "placeholder": random.choice(EXAMPLE_QUESTIONS),
        "examples": random.sample(EXAMPLE_QUESTIONS, 5),
        "max_chars": bot.MAX_QUESTION_CHARS,
    })


@router.post("/tegbot/ask")
def tegbot_ask(request: Request, question: str = Form(""), history: str = Form("[]"),
               conv: str = Form("")):
    question = question.strip()[:bot.MAX_QUESTION_CHARS]
    ctx = {"request": request, "question": question}

    def _reply(**extra):
        return templates.TemplateResponse("partials/tegbot_answer.html", {**ctx, **extra})

    if not question:
        return _reply(error="Ask me something first.")
    if not _enabled():
        return _reply(error="TEGBot is switched off at the moment.")
    visitor = _visitor_key(request)
    refusal = _take_slot(visitor)
    if refusal:
        return _reply(error=refusal)
    try:
        prior = json.loads(history) if len(history) <= MAX_HISTORY_BYTES else []
    except (json.JSONDecodeError, TypeError):
        prior = []

    conv = qa_log.clean_conv_id(conv)
    try:
        past = [p for p in qa_log.past_questions() if p["conv"] != conv]
        themes = qa_log.themes()
    except OSError:
        past, themes = [], []

    started = time.time()
    try:
        answer = bot.ask(question, _chat_data(), history=prior, past=past, themes=themes)
    except Exception:
        logger.exception("TEGBot failed on %r", question)
        _refund_slot(visitor)
        return _reply(error="TEGBot fell over. Try again in a moment.")
    seconds = time.time() - started
    logger.info(
        "TEGBot q=%r tools=%s secs=%.1f cost=$%.4f usage=%s",
        question, [c.name for c in answer.tool_calls], seconds, answer.cost_usd, answer.usage,
    )
    workings = [_working(c) for c in answer.tool_calls]
    try:
        qa_log.append_entry(conv=conv, question=question, answer=answer.text, workings=workings,
                            model=answer.model, cost_usd=answer.cost_usd, seconds=seconds,
                            theme=answer.theme, related=answer.related)
    except OSError:
        # The shared log is a nice-to-have; never lose the visitor's answer over it.
        logger.exception("TEGBot could not write the Q&A log")
    return _reply(
        answer_text=answer.history_text(),
        answer_html=render_answer_html(answer.text),
        tool_calls=workings,
        related=[{"id": p["id"], "question": p["question"]}
                 for rid in answer.related for p in past if p["id"] == rid],
    )


def _when(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return ""
    return f"{dt.day} {dt:%b %Y}, {dt:%H:%M} UTC"


def _entry_view(e: dict) -> dict:
    return {**e, "when": _when(e.get("at")), "answer_html": render_answer_html(e.get("answer", "")),
            "workings": [w for w in e.get("workings", []) if isinstance(w, dict)]}


@router.get("/tegbot/asked")
def tegbot_asked(request: Request, view: str = "newest", theme: str = ""):
    """Shared Q&A log. view=newest: latest chats first. view=themes: chats grouped by
    the theme of their first question (theme= narrows to one)."""
    view = view if view in ("newest", "themes") else "newest"
    threads = [[_entry_view(e) for e in conv] for conv in qa_log.conversations(limit=500)]
    groups = []
    if view == "themes":
        by_theme: dict[str, list] = {}
        for conv in threads:
            by_theme.setdefault(conv[0].get("theme") or "Unsorted", []).append(conv)
        order = sorted(by_theme, key=lambda t: (t in ("Off-topic", "Unsorted"), -len(by_theme[t]), t))
        groups = [{"theme": t, "conversations": by_theme[t]} for t in order
                  if not theme or t == theme]
    return templates.TemplateResponse("tegbot_asked.html", {
        "request": request,
        "active_page": "tegbot",
        "view": view,
        "conversations": threads[:50],
        "groups": groups,
    })


# --- admin: prune and organise the log ---------------------------------------

@router.get("/admin/tegbot")
def admin_tegbot(request: Request, msg: str = ""):
    if not is_authed(request):
        return RedirectResponse("/admin/login", status_code=303)
    entries = list(reversed(qa_log.read_entries()))
    return templates.TemplateResponse("admin_tegbot.html", {
        "request": request,
        "active_page": None,
        "entries": [{**e, "when": _when(e.get("at"))} for e in entries],
        "themes": qa_log.themes(),
        "msg": msg,
    })


@router.post("/admin/tegbot/delete")
async def admin_tegbot_delete(request: Request):
    # async only to read the variable-length checkbox list; the work is a small file rewrite.
    if not is_authed(request):
        return RedirectResponse("/admin/login", status_code=303)
    form = await request.form()
    ids = {str(v) for v in form.getlist("ids")}
    removed = await run_in_threadpool(qa_log.delete_entries, ids) if ids else 0
    return RedirectResponse(f"/admin/tegbot?msg=Deleted+{removed}+question{'s' if removed != 1 else ''}",
                            status_code=303)


@router.post("/admin/tegbot/themes")
def admin_tegbot_themes(request: Request):
    if not is_authed(request):
        return RedirectResponse("/admin/login", status_code=303)
    from teg_analysis.chatbot.themes import regroup_themes
    try:
        result = regroup_themes()
        msg = f"Sorted {result['updated']} questions into {len(result['themes'])} themes"
    except Exception:
        logger.exception("TEGBot theme regroup failed")
        msg = "Theme sorting failed; see the logs"
    return RedirectResponse(f"/admin/tegbot?msg={quote_plus(msg)}", status_code=303)
