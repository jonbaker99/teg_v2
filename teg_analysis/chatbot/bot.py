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
import os
import threading
from dataclasses import dataclass, field
from typing import Any, Optional

from teg_analysis.chatbot.prompt import build_system
from teg_analysis.chatbot.tools import TOOL_SCHEMAS, ChatData, run_tool

DEFAULT_MODEL = "claude-sonnet-5-5"
ENV_MODEL = "TEGBOT_MODEL"
MAX_TOOL_ROUNDS = 8
MAX_TOKENS = 4000
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


def _client():
    from teg_analysis.reporting.llm import get_api_key
    key = get_api_key()
    if not key:
        raise TegBotError("No Anthropic API key is configured.")
    import anthropic
    return anthropic.Anthropic(api_key=key, max_retries=2, timeout=90.0)


def clean_history(history: Any) -> list[dict]:
    """Keep only well-formed, text-only prior turns, newest last, size-capped."""
    if not isinstance(history, list):
        return []
    turns = []
    for item in history:
        if (isinstance(item, dict) and item.get("role") in ("user", "assistant")
                and isinstance(item.get("content"), str) and item["content"].strip()):
            turns.append({"role": item["role"], "content": item["content"][:6000]})
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


# Uploaded sandbox files, keyed by a hash of their contents. Re-uploaded only
# when the data changes; the superseded upload is deleted.
_uploads: dict[str, list[str]] = {}
_upload_lock = threading.Lock()


def _dataset_file_ids(client: Any, data: ChatData) -> list[str]:
    files = {name: df.to_csv(index=False).encode() for name, df in data.datasets().items()}
    digest = hashlib.sha256(b"".join(n.encode() + b for n, b in sorted(files.items()))).hexdigest()
    with _upload_lock:
        if digest not in _uploads:
            ids = [client.files.upload(file=(name, body, "text/csv")).id
                   for name, body in files.items()]
            for old in [i for d, old_ids in _uploads.items() for i in old_ids]:
                try:
                    client.files.delete(old)
                except Exception:  # best effort: a stale upload costs nothing
                    pass
            _uploads.clear()
            _uploads[digest] = ids
        return _uploads[digest]


def _record_sandbox_calls(content: list, calls: list[ToolCall]) -> None:
    """Add the sandbox's code and output to the workings shown under the answer."""
    pending: dict[str, ToolCall] = {}
    for block in content:
        if block.type == "server_tool_use":
            call = ToolCall("code", dict(block.input or {}), {})
            pending[block.id] = call
            calls.append(call)
        elif block.type.endswith("code_execution_tool_result"):
            call = pending.get(getattr(block, "tool_use_id", None))
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


def ask(question: str, data: ChatData, history: Optional[list] = None,
        client: Any = None, model: Optional[str] = None) -> Answer:
    """Answer one question. ``history`` is prior text-only turns from the page."""
    question = (question or "").strip()[:MAX_QUESTION_CHARS]
    if not question:
        raise ValueError("Empty question.")
    client = client or _client()
    model = model or get_model()
    system = build_system(data.holes(), data.complete(), data.players())
    uploads = [{"type": "container_upload", "file_id": fid}
               for fid in _dataset_file_ids(client, data)]
    messages: list[dict] = clean_history(history) + [
        {"role": "user", "content": [{"type": "text", "text": question}, *uploads]},
    ]
    calls: list[ToolCall] = []
    usage: dict = {}
    container = None

    for attempt in range(MAX_TOOL_ROUNDS + 1):
        last = attempt == MAX_TOOL_ROUNDS
        response = client.beta.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=system,
            tools=[*TOOL_SCHEMAS, CODE_TOOL],
            messages=messages,
            # Out of steps: answer from what the tools already returned.
            tool_choice={"type": "none" if last else "auto"},
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            **({"container": container} if container else {}),
        )
        _add_usage(usage, response.usage)
        container = getattr(getattr(response, "container", None), "id", None) or container
        _record_sandbox_calls(response.content, calls)

        if response.stop_reason == "refusal":
            return Answer("Sorry, I can't help with that one.", calls, usage, model)
        if response.stop_reason == "pause_turn":
            # The sandbox hit its step limit mid-turn; resending resumes it.
            messages.append({"role": "assistant", "content": response.content})
            continue
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if response.stop_reason != "tool_use" or not tool_uses:
            text = _final_text(response.content)
            if response.stop_reason == "max_tokens":
                text += "\n\n_(Answer cut short.)_"
            return Answer(text or "I couldn't find an answer to that.", calls, usage, model)

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
                  calls, usage, model)
