"""TEGBot 5000 — the Claude tool-use loop.

The model reads the question, then either calls a lookup in ``tools.py`` or
writes pandas code that runs in Anthropic's code-execution sandbox against
CSVs uploaded from ``ChatData.datasets()``. It writes the answer from those
results; it never does the maths itself.

Billing is per token on the Anthropic API (key resolved by
``teg_analysis.reporting.llm.get_api_key``). The anthropic SDK is imported
lazily, so the package still imports with no SDK installed.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from teg_analysis.chatbot.prompt import DEEP_ADDENDUM, build_system
from teg_analysis.chatbot.tools import TOOL_SCHEMAS, ChatData, run_tool

DEFAULT_MODEL = "claude-sonnet-5-5"
ENV_MODEL = "TEGBOT_MODEL"
MAX_TOOL_ROUNDS = 8
MAX_TOKENS = 4000
#: Deep dive: stronger model, more steps and room, longer wait.
DEEP_MODEL = "claude-opus-5-5"
ENV_DEEP_MODEL = "TEGBOT_DEEP_MODEL"
DEEP_TOOL_ROUNDS = 20
DEEP_MAX_TOKENS = 16000
DEEP_EFFORT = "high"
TIMEOUT = 90.0
DEEP_TIMEOUT = 300.0
#: Deep dive wall clock: past this, the next call must answer from what it has.
DEEP_WALL_CLOCK = 600.0
#: One retry in deep mode, so a single stalled round can't eat the whole budget.
DEEP_MAX_RETRIES = 1
logger = logging.getLogger("uvicorn.error.tegbot")
MAX_QUESTION_CHARS = 500
MAX_HISTORY_TURNS = 6
MAX_HISTORY_CHARS = 16000
MAX_METHOD_CHARS = 2500
#: Anthropic's sandbox: the model's pandas runs there, never on our server.
CODE_TOOL = {"type": "code_execution_20260521", "name": "code_execution"}

# $ per million tokens: (input, output). Cache reads bill at 10% of input,
# cache writes at 125%. Used only for the cost line in the logs.
PRICES = {
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-opus-5-5": (4.0, 20.0),
    "claude-haiku-4-5": (1.0, 5.0),
}


class TegBotError(RuntimeError):
    """Something the user should see as 'TEGBot is unavailable', not a stack trace."""


@dataclass
class ToolCall:
    name: str
    input: dict
    output: dict


@dataclass
class Answer:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    model: str = ""
    theme: str = ""
    #: ids of similar past questions the bot pointed to (validated against the log)
    related: list[str] = field(default_factory=list)
    #: the bot thinks a Deep dive would do the question justice (normal mode only)
    suggest_deep: bool = False
    #: this answer was produced in Deep dive mode
    deep: bool = False
    #: set when the analysis toolkit could not be built, so the bot ran without it
    toolkit_error: str = ""

    @property
    def method_note(self) -> str:
        """Compact record of how the answer was reached, carried into the next turn so
        follow-ups reuse the same method instead of inventing a new one."""
        parts = []
        for call in self.tool_calls:
            if call.name == "code":
                code = call.input.get("command") or call.input.get("file_text") or ""
                parts.append(f"code: {code.strip()}")
            else:
                parts.append(f"lookup {call.name}({json.dumps(call.input, default=str)})")
        note = "\n".join(parts)
        if len(note) > MAX_METHOD_CHARS:
            note = note[:MAX_METHOD_CHARS] + "\n…(truncated)"
        return note

    def history_text(self) -> str:
        """The assistant turn as replayed in later requests: answer plus method note."""
        if not self.method_note:
            return self.text
        return f"{self.text}\n\n[Method used for this answer, not shown to the user]\n{self.method_note}"

    @property
    def cost_usd(self) -> float:
        inp, out = PRICES.get(self.model, PRICES[DEFAULT_MODEL])
        u = self.usage
        return (
            u.get("input_tokens", 0) * inp
            + u.get("cache_read_input_tokens", 0) * inp * 0.1
            + u.get("cache_creation_input_tokens", 0) * inp * 1.25
            + u.get("output_tokens", 0) * out
        ) / 1_000_000


def get_model() -> str:
    return os.environ.get(ENV_MODEL) or DEFAULT_MODEL


def get_deep_model() -> str:
    return os.environ.get(ENV_DEEP_MODEL) or DEEP_MODEL


def _client(timeout: float = TIMEOUT, max_retries: int = 2):
    from teg_analysis.reporting.llm import get_api_key
    key = get_api_key()
    if not key:
        raise TegBotError("No Anthropic API key is configured.")
    import anthropic
    return anthropic.Anthropic(api_key=key, max_retries=max_retries, timeout=timeout)


# Only CLOSED fences match, so an unclosed one can't swallow the rest of the answer.
_CHART_BLOCK = re.compile(r"^[ \t]*```tegchart[ \t]*\n(.*?)\n[ \t]*```[ \t]*$", re.S | re.M)
_CHART_OPEN = re.compile(r"^[ \t]*```tegchart[ \t]*$\n?", re.M)


def strip_charts(text: str) -> str:
    """Replace bulky `tegchart` blocks with "[chart: <title>]" for the history replay."""
    def _title(match: re.Match) -> str:
        try:
            title = json.loads(match.group(1)).get("title")
        except (ValueError, AttributeError, RecursionError):
            title = None
        return f"[chart: {title if isinstance(title, str) else 'untitled'}]"[:200]
    return _CHART_OPEN.sub("", _CHART_BLOCK.sub(_title, text))


def clean_history(history: Any) -> list[dict]:
    """Keep only well-formed, text-only prior turns, newest last, size-capped."""
    if not isinstance(history, list):
        return []
    turns = []
    for item in history:
        if (isinstance(item, dict) and item.get("role") in ("user", "assistant")
                and isinstance(item.get("content"), str) and item["content"].strip()):
            turns.append({"role": item["role"], "content": strip_charts(item["content"])[:6000]})
    turns = turns[-2 * MAX_HISTORY_TURNS:]
    while turns and turns[0]["role"] != "user":
        turns.pop(0)
    # Strict alternation: drop any turn that repeats the previous role.
    out: list[dict] = []
    for t in turns:
        if out and out[-1]["role"] == t["role"]:
            out[-1] = t
        else:
            out.append(t)
    if out and out[-1]["role"] == "user":
        out.pop()
    # Keep the newest turns within a total size budget, still starting on a user turn.
    while out and sum(len(t["content"]) for t in out) > MAX_HISTORY_CHARS:
        out = out[2:]
    return out


def _add_usage(total: dict, usage: Any) -> None:
    for key in ("input_tokens", "output_tokens", "cache_read_input_tokens",
                "cache_creation_input_tokens"):
        total[key] = total.get(key, 0) + (getattr(usage, key, 0) or 0)


_last_toolkit: Optional[tuple[dict[str, bytes], str]] = None


def _toolkit_files() -> tuple[dict[str, bytes], str, str]:
    """The toolkit zips and skills index, or ({}, "", error) if it cannot be built.

    The bot must still answer basic questions without it, so failure is logged
    (and carried on the Answer) rather than raised. A failed rebuild reuses the last
    good build when there is one."""
    global _last_toolkit
    try:
        from teg_analysis.chatbot import toolkit
        built = ({toolkit.TOOLKIT_ZIP: toolkit.code_zip(), toolkit.DATA_ZIP: toolkit.data_zip()},
                 toolkit.skills_index())
        _last_toolkit = built
        return built[0], built[1], ""
    except Exception as exc:
        logger.exception("TEGBot toolkit unavailable; answering without it")
        files, index = _last_toolkit or ({}, "")
        return files, index, f"{type(exc).__name__}: {exc}"


# Uploaded sandbox files, keyed by file name with a hash of the contents. A file is
# re-uploaded only when its own contents change, so a missing file (say the toolkit
# failed to build) never forces the rest to be re-uploaded. A replaced upload is not
# deleted at once, since an in-flight request may still reference it: it is kept for
# one more generation of changes, then deleted.
_uploads: dict[str, tuple[str, str]] = {}
_retired: list[list[str]] = []
_upload_lock = threading.Lock()


def _dataset_file_ids(client: Any, data: ChatData,
                      extra: Optional[dict[str, bytes]] = None) -> list[str]:
    files = {name: df.to_csv(index=False).encode() for name, df in data.datasets().items()}
    files.update(extra or {})
    ids, replaced = [], []
    with _upload_lock:
        for name, body in files.items():
            digest = hashlib.sha256(body).hexdigest()
            current = _uploads.get(name)
            if current is None or current[0] != digest:
                new_id = client.files.upload(
                    file=(name, body, "application/zip" if name.endswith(".zip") else "text/csv")).id
                if current:
                    replaced.append(current[1])
                _uploads[name] = (digest, new_id)
            ids.append(_uploads[name][1])
        if replaced:
            _retired.append(replaced)
            while len(_retired) > 1:
                for old in _retired.pop(0):
                    try:
                        client.files.delete(old)
                    except Exception:  # best effort: a stale upload costs nothing
                        pass
    return ids


def _record_sandbox_calls(content: list, calls: list[ToolCall],
                          pending: Optional[dict] = None) -> None:
    """Add the sandbox's code and output to the workings shown under the answer.

    ``pending`` persists across responses: when the model runs code and calls a
    lookup in the same step, the code's result only arrives in the next response."""
    pending = {} if pending is None else pending
    for block in content:
        if block.type == "server_tool_use":
            call = ToolCall("code", dict(block.input or {}), {})
            pending[block.id] = call
            calls.append(call)
        elif block.type.endswith("code_execution_tool_result"):
            call = pending.pop(getattr(block, "tool_use_id", None), None)
            if call is None:
                continue
            result = block.content
            call.output = {
                key: getattr(result, key)
                for key in ("stdout", "stderr", "return_code", "error_code")
                if getattr(result, key, None) not in (None, "")
            }


def _final_text(content: list) -> str:
    """The answer: text after the last tool activity (earlier text is narration)."""
    last_tool = max((i for i, b in enumerate(content)
                     if b.type in ("server_tool_use", "tool_use")
                     or b.type.endswith("_tool_result")), default=-1)
    texts = [b.text for b in content[last_tool + 1:] if b.type == "text"]
    if not texts:
        texts = [b.text for b in content if b.type == "text"]
    return "\n\n".join(texts).strip()


_TRAILER = re.compile(r"^\s*(THEME|RELATED|DEEP)\s*:\s*(.*?)\s*$", re.IGNORECASE)


def past_block(past: list[dict], themes: list[str]) -> str:
    """System text listing past questions and themes, for linking and tagging."""
    lines = ["Themes in use: " + (", ".join(themes) if themes else "(none yet)")]
    lines.append("Questions other players asked before (short id: question):")
    lines += [f"{p['id'][:8]}: {p['question'][:200]}" for p in past] or ["(none yet)"]
    return "\n".join(lines)


def split_trailer(text: str, past: list[dict]) -> tuple[str, str, list[str]]:
    """Strip the THEME/RELATED lines from the end of an answer; resolve related ids."""
    text, theme, related, _ = split_trailer_full(text, past)
    return text, theme, related


def split_trailer_full(text: str, past: list[dict]) -> tuple[str, str, list[str], bool]:
    """As ``split_trailer`` but also returns the DEEP flag (False when absent)."""
    lines = text.rstrip().split("\n")
    theme, related_raw, deep_raw = "", "", ""
    while lines:
        m = _TRAILER.match(lines[-1])
        if not m:
            if not lines[-1].strip():
                lines.pop()
                continue
            break
        key = m.group(1).upper()
        if key == "THEME":
            theme = m.group(2)
        elif key == "DEEP":
            deep_raw = m.group(2)
        else:
            related_raw = m.group(2)
        lines.pop()
    by_short = {p["id"][:8]: p["id"] for p in past}
    related = []
    for token in re.split(r"[,\s]+", related_raw.lower()):
        full = by_short.get(token[:8])
        if full and full not in related:
            related.append(full)
    suggest = deep_raw.strip().lower().startswith("yes")
    return "\n".join(lines).strip(), theme.strip(), related[:3], suggest


def ask(question: str, data: ChatData, history: Optional[list] = None,
        client: Any = None, model: Optional[str] = None,
        past: Optional[list[dict]] = None, themes: Optional[list[str]] = None,
        deep: bool = False) -> Answer:
    """Answer one question. ``history`` is prior text-only turns from the page;
    ``past`` / ``themes`` come from the shared Q&A log (for "Others asked" and tagging).
    ``deep`` switches to the Deep dive limits: stronger model, high effort, more steps."""
    question = (question or "").strip()[:MAX_QUESTION_CHARS]
    if not question:
        raise ValueError("Empty question.")
    client = client or (_client(DEEP_TIMEOUT, DEEP_MAX_RETRIES) if deep else _client())
    started = time.monotonic()
    model = model or (get_deep_model() if deep else get_model())
    max_rounds = DEEP_TOOL_ROUNDS if deep else MAX_TOOL_ROUNDS
    max_tokens = DEEP_MAX_TOKENS if deep else MAX_TOKENS
    past = past or []
    toolkit_files, skills_index, toolkit_error = _toolkit_files()
    system = build_system(data.holes(), data.complete(), data.players(), skills_index)
    system.append({"type": "text", "text": past_block(past, themes or [])})
    if deep:
        system.append({"type": "text", "text": DEEP_ADDENDUM})
    uploads = [{"type": "container_upload", "file_id": fid}
               for fid in _dataset_file_ids(client, data, toolkit_files)]
    messages: list[dict] = clean_history(history) + [
        {"role": "user", "content": [{"type": "text", "text": question}, *uploads]},
    ]
    calls: list[ToolCall] = []
    usage: dict = {}
    container = None
    open_code: dict[str, ToolCall] = {}

    for attempt in range(max_rounds + 1):
        # Out of steps, or (deep) out of time: this call must answer from what it has.
        last = attempt == max_rounds or (deep and time.monotonic() - started > DEEP_WALL_CLOCK)
        response = client.beta.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            tools=[*TOOL_SCHEMAS, CODE_TOOL],
            messages=messages,
            # Out of steps: answer from what the tools already returned.
            tool_choice={"type": "none" if last else "auto"},
            output_config={"effort": DEEP_EFFORT if deep else "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            **({"container": container} if container else {}),
        )
        _add_usage(usage, response.usage)
        container = getattr(getattr(response, "container", None), "id", None) or container
        _record_sandbox_calls(response.content, calls, open_code)

        if response.stop_reason == "refusal":
            return Answer("Sorry, I can't help with that one.", calls, usage, model,
                          deep=deep, toolkit_error=toolkit_error)
        if response.stop_reason == "pause_turn":
            # The sandbox hit its step limit mid-turn; resending resumes it.
            messages.append({"role": "assistant", "content": response.content})
            continue
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if response.stop_reason != "tool_use" or not tool_uses:
            text, theme, related, suggest = split_trailer_full(_final_text(response.content), past)
            if response.stop_reason == "max_tokens":
                text += "\n\n_(Answer cut short.)_"
            return Answer(text or "I couldn't find an answer to that.", calls, usage, model,
                          theme=theme, related=related, suggest_deep=suggest and not deep,
                          deep=deep, toolkit_error=toolkit_error)

        # Append the full assistant content unchanged (thinking blocks included).
        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in tool_uses:
            output = run_tool(block.name, block.input, data)
            calls.append(ToolCall(block.name, dict(block.input or {}), output))
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(output, default=str),
                **({"is_error": True} if "error" in output else {}),
            })
        messages.append({"role": "user", "content": results})

    return Answer("That needed more steps than I'm allowed. Try a narrower question.",
                  calls, usage, model, deep=deep, toolkit_error=toolkit_error)
