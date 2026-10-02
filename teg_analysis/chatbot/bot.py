"""TEGBot 5000 — the Claude tool-use loop.

The model reads the question, calls the deterministic tools in ``tools.py``,
and writes the answer from their results. It never does the maths itself.

Billing is per token on the Anthropic API (key resolved by
``teg_analysis.reporting.llm.get_api_key``). The anthropic SDK is imported
lazily, so the package still imports with no SDK installed.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Optional

from teg_analysis.chatbot.prompt import build_system
from teg_analysis.chatbot.tools import TOOL_SCHEMAS, ChatData, run_tool

DEFAULT_MODEL = "claude-sonnet-5-5"
ENV_MODEL = "TEGBOT_MODEL"
MAX_TOOL_ROUNDS = 6
MAX_TOKENS = 4000
MAX_QUESTION_CHARS = 500
MAX_HISTORY_TURNS = 6

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
            turns.append({"role": item["role"], "content": item["content"][:4000]})
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
    return out


def _add_usage(total: dict, usage: Any) -> None:
    for key in ("input_tokens", "output_tokens", "cache_read_input_tokens",
                "cache_creation_input_tokens"):
        total[key] = total.get(key, 0) + (getattr(usage, key, 0) or 0)


def ask(question: str, data: ChatData, history: Optional[list] = None,
        client: Any = None, model: Optional[str] = None) -> Answer:
    """Answer one question. ``history`` is prior text-only turns from the page."""
    question = (question or "").strip()[:MAX_QUESTION_CHARS]
    if not question:
        raise ValueError("Empty question.")
    client = client or _client()
    model = model or get_model()
    system = build_system(data.holes(), data.complete(), data.players())
    messages: list[dict] = clean_history(history) + [{"role": "user", "content": question}]
    calls: list[ToolCall] = []
    usage: dict = {}

    for _ in range(MAX_TOOL_ROUNDS + 1):
        response = client.beta.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=system,
            tools=TOOL_SCHEMAS,
            messages=messages,
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        _add_usage(usage, response.usage)

        if response.stop_reason == "refusal":
            return Answer("Sorry, I can't help with that one.", calls, usage, model)
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if response.stop_reason != "tool_use" or not tool_uses:
            text = "\n\n".join(b.text for b in response.content if b.type == "text").strip()
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
