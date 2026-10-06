"""TEGBot 5000 — ask questions about TEG stats in plain English.

The page posts one question at a time (plus the earlier turns, text only, held
in the page). The answer partial shows the reply and, folded away, every tool
call the bot made — the deterministic calculation behind the numbers.

Spend guards are in-process: a per-visitor hourly limit and a site-wide daily
cap (``TEGBOT_DAILY_LIMIT``). Deep dive questions also count against their own
site-wide daily cap (``TEGBOT_DEEP_DAILY_LIMIT``, default 30). All reset when the process restarts. Set
``TEGBOT_ENABLED=0`` to switch the bot off without a deploy of code.
"""

import html
import json
import logging
import math
import os
import random
import re
import threading
import time
import uuid
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
DEFAULT_DEEP_DAILY_LIMIT = 30
DEFAULT_DEEP_PER_VISITOR = 5
JOB_KEEP_SECONDS = 15 * 60
JOB_POLL_SECONDS = 3
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
    "Who's the favourite for the next TEG?",
    "Which course has been toughest for us?",
    "How do this year's courses compare with the last few TEGs?",
    "What handicap would Rory McIlroy need to make it fair?",
    "Who has the most Wooden Spoons?",
    "Who has the most birdies ever?",
    "What's the biggest final-round comeback?",
    "Who plays best in the final round?",
    "Who is most consistent round to round?",
    "What's the worst single hole score ever?",
    "Who has the most triple bogeys?",
    "Which hole has cost us the most shots?",
    "Who would have won more if handicaps were lower?",
    "Who has led after round 1 most often?",
    "What's the best Stableford round ever?",
    "Who has won both trophies in the same TEG?",
    "Whose scores have dropped most since their first TEG?",
    "Who plays par 5s best?",
    "Which TEG was the closest finish?",
    "Who suffers most on the front 9?",
    "What's the record for birdies in one round?",
    "Who has the best eclectic score?",
    "Which course suits our group best?",
    "Who has the longest run without a double bogey?",
    "Who blows up most after a good hole?",
    "What's the average winning Stableford total?",
]

_lock = threading.Lock()
_visitor_hits: dict[str, deque] = defaultdict(deque)
_daily = {"date": None, "count": 0, "deep": 0}
_visitor_deep: dict[str, list] = {}  # visitor -> [date, deep dives today]
_jobs: dict[str, dict] = {}


def _enabled() -> bool:
    return os.environ.get("TEGBOT_ENABLED", "1") != "0" and has_api_key()


def _daily_limit() -> int:
    try:
        return int(os.environ.get("TEGBOT_DAILY_LIMIT", DEFAULT_DAILY_LIMIT))
    except ValueError:
        return DEFAULT_DAILY_LIMIT


def _deep_daily_limit() -> int:
    try:
        return int(os.environ.get("TEGBOT_DEEP_DAILY_LIMIT", DEFAULT_DEEP_DAILY_LIMIT))
    except ValueError:
        return DEFAULT_DEEP_DAILY_LIMIT


def _deep_per_visitor() -> int:
    try:
        return int(os.environ.get("TEGBOT_DEEP_PER_VISITOR", DEFAULT_DEEP_PER_VISITOR))
    except ValueError:
        return DEFAULT_DEEP_PER_VISITOR


def _visitor_key(request: Request) -> str:
    # Rightmost entry: added by Railway's edge, so a client can't rotate it to
    # dodge the limit. Leftmost entries are whatever the client chose to send.
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[-1].strip() or (request.client.host if request.client else "?")


def _refund_slot(visitor: str, deep: bool = False) -> None:
    """Give back a question that failed through no fault of the visitor."""
    with _lock:
        if _visitor_hits[visitor]:
            _visitor_hits[visitor].pop()
        _daily["count"] = max(0, _daily["count"] - 1)
        if deep:
            _daily["deep"] = max(0, _daily["deep"] - 1)
            mine = _visitor_deep.get(visitor)
            if mine:
                mine[1] = max(0, mine[1] - 1)


def _take_slot(visitor: str, deep: bool = False) -> str | None:
    """Reserve one question. Returns a refusal message, or None if allowed."""
    now = time.time()
    today = datetime.now(timezone.utc).date()
    with _lock:
        if _daily["date"] != today:
            _daily.update(date=today, count=0, deep=0)
            _visitor_deep.clear()
        if _daily["count"] >= _daily_limit():
            return "TEGBot has answered its fill of questions today. Try again tomorrow."
        if deep and _daily["deep"] >= _deep_daily_limit():
            return "TEGBot has done all the deep dives it can today. Ask it normally, or try again tomorrow."
        mine = _visitor_deep.setdefault(visitor, [today, 0])
        if deep and mine[1] >= _deep_per_visitor():
            return "That's your deep dives for today. Ask normally, or try again tomorrow."
        hits = _visitor_hits[visitor]
        while hits and now - hits[0] > 3600:
            hits.popleft()
        if len(hits) >= PER_VISITOR_HOURLY:
            return "That's a lot of questions for one hour. Give TEGBot a breather."
        hits.append(now)
        _daily["count"] += 1
        if deep:
            _daily["deep"] += 1
            mine[1] += 1
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


# Only CLOSED fences match; an unclosed one loses just its opening line.
_CHART_BLOCK = re.compile(r"^[ \t]*```tegchart[ \t]*\n(.*?)\n[ \t]*```[ \t]*$", re.S | re.M)
_CHART_OPEN = re.compile(r"^[ \t]*```tegchart[ \t]*$\n?", re.M)
_CHART_SLOT = "TEGCHARTSLOT"
CHART_MAX_SERIES = 8
CHART_MAX_POINTS = 60
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def _chart_text(value, limit: int) -> str | None:
    """A short plain string: no control characters or angle brackets (Plotly reads a little HTML)."""
    if not isinstance(value, str):
        return None
    return _CONTROL.sub(" ", value).replace("<", "").replace(">", "").strip()[:limit]


def _chart_number(value) -> float | int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return value


def validate_chart(raw: str) -> dict | None:
    """Parse and strictly validate a `tegchart` JSON spec; None if anything is off.

    Returns a rebuilt dict holding only the known keys, so nothing else the model
    wrote reaches the page.
    """
    def _no_constants(name):
        raise ValueError(name)  # reject NaN / Infinity
    try:
        spec = json.loads(raw, parse_constant=_no_constants)
    except (ValueError, RecursionError):
        return None
    if not isinstance(spec, dict) or spec.get("type") not in ("bar", "line"):
        return None
    title = _chart_text(spec.get("title"), 120)
    x_label = _chart_text(spec.get("x_label", ""), 60)
    y_label = _chart_text(spec.get("y_label", ""), 60)
    if not title or x_label is None or y_label is None:
        return None
    xs, series_in = spec.get("x"), spec.get("series")
    if (not isinstance(xs, list) or not isinstance(series_in, list)
            or not 2 <= len(xs) <= CHART_MAX_POINTS or not 1 <= len(series_in) <= CHART_MAX_SERIES):
        return None
    x = []
    for v in xs:
        v = _chart_text(v, 40) if isinstance(v, str) else _chart_number(v)
        if v is None or v == "":
            return None
        x.append(v)
    series = []
    for s in series_in:
        if not isinstance(s, dict) or not isinstance(s.get("values"), list) or len(s["values"]) != len(x):
            return None
        name = _chart_text(s.get("name"), 60)
        values = [None if v is None else _chart_number(v) for v in s["values"]]
        if not name or any(v is None and raw_v is not None for v, raw_v in zip(values, s["values"])):
            return None
        series.append({"name": name, "values": values})
    if len({s["name"] for s in series}) != len(series):
        return None
    out = {"type": spec["type"], "title": title, "x_label": x_label, "y_label": y_label,
           "x": x, "series": series}
    if spec.get("y_reverse") is True:
        out["y_reverse"] = True
    return out


def _chart_div(spec: dict) -> str:
    data = html.escape(json.dumps(spec, ensure_ascii=False, allow_nan=False), quote=True)
    return f'<div class="tegbot-chart" data-chart="{data}"></div>'


def _extract_charts(text: str) -> tuple[str, list[str]]:
    """Swap each `tegchart` block for a slot token; return the text and the HTML per slot.

    Only the first valid chart gets a div; invalid or extra blocks are dropped (logged).
    """
    htmls: list[str] = []
    state = {"kept": False}

    def _swap(match: re.Match) -> str:
        spec = None if state["kept"] else validate_chart(match.group(1))
        if spec is None:
            logger.warning("tegbot: dropped %s chart block", "extra" if state["kept"] else "invalid")
            htmls.append("")
        else:
            state["kept"] = True
            htmls.append(_chart_div(spec))
        return f"\n\n{_CHART_SLOT}{len(htmls) - 1}\n\n"
    return _CHART_OPEN.sub("", _CHART_BLOCK.sub(_swap, text)), htmls


def render_answer_html(text: str) -> str:
    """Markdown → HTML with raw HTML escaped and only on-site links kept."""
    text, charts = _extract_charts(text)
    out = markdown.markdown(
        _blank_line_before_lists(html.escape(text, quote=False)), extensions=["tables"])
    for i, div in enumerate(charts):
        out = out.replace(f"<p>{_CHART_SLOT}{i}</p>", div)

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
    if call.name == "web_search":
        found = call.output.get("results")
        shown_out = ("\n".join(f"{r['title']} — {r['url']}" for r in found) if found is not None
                     else json.dumps(call.output))
        return {"name": "Web search", "input": str(call.input.get("query", "")),
                "output": shown_out[:6000]}
    return {"name": f"Lookup: {call.name}",
            "input": json.dumps(call.input, indent=1, default=str),
            "output": json.dumps(call.output, indent=1, default=str)[:6000]}


def _chat_data() -> ChatData:
    ranked = {"teg": deps.cached_ranked_teg_data, "round": deps.cached_ranked_round_data,
              "frontback": deps.cached_ranked_frontback_data}
    from webapp.routes.simulation import default_prediction, live_prediction, what_it_takes
    return ChatData(all_data=deps.cached_load_all_data, winners=deps.cached_winners,
                    ranked=lambda scope: ranked[scope](), predictions=default_prediction,
                    live_predictions=live_prediction, what_it_takes=what_it_takes)


def _recent_questions() -> list[dict]:
    try:
        return qa_log.recent_questions(4)
    except OSError:
        return []


@router.get("/tegbot")
def tegbot_page(request: Request):
    return templates.TemplateResponse("tegbot.html", {
        "request": request,
        "active_page": "tegbot",
        "enabled": _enabled(),
        "placeholder": random.choice(EXAMPLE_QUESTIONS),
        # Shuffled per visit; the page shows four at a time and "more ideas" moves on.
        "examples": random.sample(EXAMPLE_QUESTIONS, len(EXAMPLE_QUESTIONS)),
        "recent": _recent_questions(),
        "max_chars": bot.MAX_QUESTION_CHARS,
    })


@router.post("/tegbot/ask")
def tegbot_ask(request: Request, question: str = Form(""), history: str = Form("[]"),
               conv: str = Form(""), deep: str = Form("")):
    question = question.strip()[:bot.MAX_QUESTION_CHARS]
    deep_mode = deep.strip().lower() in ("1", "on", "true", "yes")
    ctx = {"request": request, "question": question}

    def _reply(**extra):
        return templates.TemplateResponse("partials/tegbot_answer.html", {**ctx, **extra})

    if not question:
        return _reply(error="Ask me something first.")
    if not _enabled():
        return _reply(error="TEGBot is switched off at the moment.")
    visitor = _visitor_key(request)
    refusal = _take_slot(visitor, deep_mode)
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

    if deep_mode:
        # Deep runs can outlast Railway's 5 minute HTTP limit: run in the background, poll.
        job_id = _start_job(question, prior, past, themes, conv, visitor)
        return _working_reply(request, job_id, question, 0)
    return _reply(**_run_question(question, prior, past, themes, conv, visitor, False))


def _can_dig(answer, deep_mode: bool) -> bool:
    """Offer "Dig deeper" on answers that did real analysis or where the bot asked for it.
    Not on deep answers, refusals/off-topic, or lookup-only answers."""
    if deep_mode or getattr(answer, "theme", "") == "Off-topic":
        return False
    ran_code = any(c.name == "code" for c in answer.tool_calls)
    return ran_code or bool(getattr(answer, "suggest_deep", False))


def _run_question(question: str, prior: list, past: list, themes: list, conv: str,
                  visitor: str, deep_mode: bool) -> dict:
    """Ask the bot, log it, and return the answer partial's context. On failure the
    visitor's slot is refunded and the context carries an error."""
    started = time.time()
    try:
        answer = bot.ask(question, _chat_data(), history=prior, past=past, themes=themes,
                         conv=conv, **({"deep": True} if deep_mode else {}))
    except Exception:
        logger.exception("TEGBot failed on %r", question)
        _refund_slot(visitor, deep_mode)
        return {"error": "TEGBot fell over. Try again in a moment."}
    seconds = time.time() - started
    logger.info(
        "TEGBot q=%r deep=%s model=%s tools=%s secs=%.1f cost=$%.4f usage=%s",
        question, deep_mode, answer.model, [c.name for c in answer.tool_calls], seconds,
        answer.cost_usd, answer.usage,
    )
    workings = [_working(c) for c in answer.tool_calls]
    try:
        qa_log.append_entry(conv=conv, question=question, answer=answer.text, workings=workings,
                            model=answer.model, cost_usd=answer.cost_usd, seconds=seconds,
                            theme=answer.theme, related=answer.related, deep=deep_mode)
    except OSError:
        # The shared log is a nice-to-have; never lose the visitor's answer over it.
        logger.exception("TEGBot could not write the Q&A log")
    return dict(
        answer_text=answer.history_text(),
        answer_html=render_answer_html(answer.text),
        tool_calls=workings,
        sources=list(getattr(answer, "sources", []) or []),
        deep=deep_mode,
        suggest_deep=bool(getattr(answer, "suggest_deep", False)) and not deep_mode,
        deep_reason=str(getattr(answer, "deep_reason", "") or "") if not deep_mode else "",
        can_dig=_can_dig(answer, deep_mode),
        related=[{"id": p["id"], "question": p["question"]}
                 for rid in answer.related for p in past if p["id"] == rid],
    )


# --- deep dives run as background jobs, polled by the page ---------------------

def _purge_jobs() -> None:
    cutoff = time.time() - JOB_KEEP_SECONDS
    with _lock:
        for jid in [j for j, v in _jobs.items() if v["finished"] and v["finished"] < cutoff
                    or v["started"] < cutoff - 2 * JOB_KEEP_SECONDS]:
            del _jobs[jid]


def _start_job(question: str, prior: list, past: list, themes: list, conv: str,
               visitor: str) -> str:
    _purge_jobs()
    job_id = uuid.uuid4().hex
    job = {"question": question, "started": time.time(), "finished": None, "result": None}
    with _lock:
        _jobs[job_id] = job

    def _work():
        try:
            result = _run_question(question, prior, past, themes, conv, visitor, True)
        except Exception:  # _run_question handles bot errors; this is belt and braces
            logger.exception("TEGBot job crashed")
            _refund_slot(visitor, True)
            result = {"error": "TEGBot fell over. Try again in a moment."}
        job["result"] = result
        job["finished"] = time.time()

    threading.Thread(target=_work, name=f"tegbot-{job_id[:8]}", daemon=True).start()
    return job_id


def _elapsed(seconds: float) -> str:
    seconds = int(seconds)
    return f"{seconds // 60}m {seconds % 60:02d}s" if seconds >= 60 else f"{seconds}s"


def _working_reply(request: Request, job_id: str, question: str, seconds: float):
    return templates.TemplateResponse("partials/tegbot_working.html", {
        "request": request, "job_id": job_id, "question": question,
        "elapsed": _elapsed(seconds), "poll_seconds": JOB_POLL_SECONDS})


@router.get("/tegbot/job/{job_id}")
def tegbot_job(request: Request, job_id: str):
    """Poll a deep dive: the working partial while it runs, the answer when done."""
    job = _jobs.get(job_id)
    if job is None:
        return templates.TemplateResponse("partials/tegbot_answer.html", {
            "request": request, "question": "",
            "error": "That deep dive has expired or was never started. Please ask again."})
    if job["result"] is None:
        return _working_reply(request, job_id, job["question"], time.time() - job["started"])
    return templates.TemplateResponse("partials/tegbot_answer.html", {
        "request": request, "question": job["question"], **job["result"]})


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
