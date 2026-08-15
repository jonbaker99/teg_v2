"""The model call for the reporting pipeline — API billing or claude.ai plan usage.

Two providers, one switch:

- **`agent` (the default).** The prompt is written to a file and the process waits
  for an answer. Whoever answers — the `teg-report-respond` skill in a Claude Code
  session, or you pasting into a browser tab — is the thing doing the inference, so
  it draws on plan usage and costs nothing per token. See `mailbox.py`.
- **`api`.** The Anthropic API, as before: prompt caching on the large stable system
  prompt, `messages.parse` for structured output, adaptive thinking. Costs money.

Set the provider with `TEG_LLM_PROVIDER=api|agent`, or `llm.use_provider("api")`
around a block. **The default is `agent` so no run ever spends API credit unless
it was asked for**; `api` is the deliberate choice for unattended batch work.

The switch is the only thing callers see. Both providers take the same arguments
and return the same `(result, usage)` shape, so the pipeline — the four-call
chain, `backfill_all`, the round reports — is identical under either.

The anthropic SDK is imported lazily, so the package still works with no SDK and
no key installed. Under `agent` neither is needed at all.
"""

from __future__ import annotations

import json
import os
import tomllib
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Type, Tuple

import pydantic
from pydantic import BaseModel

DEFAULT_MODEL = "claude-opus-5"

# Providers. `agent` is the default: it costs nothing, and choosing to spend API
# credit should be an explicit act rather than what happens when you forget.
PROVIDER_API = "api"
PROVIDER_AGENT = "agent"
PROVIDERS = (PROVIDER_AGENT, PROVIDER_API)
DEFAULT_PROVIDER = PROVIDER_AGENT
ENV_PROVIDER = "TEG_LLM_PROVIDER"

#: How many times a structured call is re-asked when the answer fails schema
#: validation. The API path never had a retry; this is a net gain, not a
#: workaround for the agent path being flakier.
MAX_STRUCTURED_ATTEMPTS = 3

# Key resolution: ANTHROPIC_API_KEY from the environment first (the supported
# route — Railway env var locally and on deploy), then a gitignored secrets.toml.
# Paths are cwd-relative (repo root), consistent with the rest of the package.
#
# `secrets.toml` at the repo root is the canonical file. The two `.streamlit/`
# paths are a DEPRECATED fallback kept only so existing local checkouts keep
# working while streamlit is retired — nothing here imports streamlit, and the
# `.streamlit/` locations should not be used for new setups. Remove them once
# no local checkout still relies on them.
_SECRETS_CANDIDATES = (
    "secrets.toml",                        # canonical (gitignored)
    ".streamlit/secrets.toml",             # deprecated — streamlit legacy
    "streamlit/.streamlit/secrets.toml",   # deprecated — streamlit legacy
)

_provider_override: Optional[str] = None


# ---------------------------------------------------------------------------
# Provider selection
# ---------------------------------------------------------------------------
def get_provider() -> str:
    """The active provider: `use_provider()` override, else env, else `agent`."""
    if _provider_override is not None:
        return _provider_override
    raw = (os.environ.get(ENV_PROVIDER) or "").strip().lower()
    if not raw:
        return DEFAULT_PROVIDER
    if raw not in PROVIDERS:
        raise ValueError(
            f"{ENV_PROVIDER}={raw!r} is not a provider. Use one of: {', '.join(PROVIDERS)}."
        )
    return raw


@contextmanager
def use_provider(name: str):
    """Force a provider for the duration of a block. For notebooks and tests.

        with llm.use_provider("api"):
            backfill_all(range(8, 19))
    """
    global _provider_override
    if name not in PROVIDERS:
        raise ValueError(f"unknown provider {name!r}; use one of: {', '.join(PROVIDERS)}")
    previous = _provider_override
    _provider_override = name
    try:
        yield
    finally:
        _provider_override = previous


@dataclass(frozen=True)
class AgentUsage:
    """Stand-in for the API's usage object. Token counts are genuinely unknown.

    Under the agent provider the tokens are spent inside somebody else's session,
    so there is nothing to report. Callers that log usage must handle `None`
    counts rather than assume a number.
    """
    provider: str = PROVIDER_AGENT
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    requested_model: Optional[str] = None
    request_path: Optional[str] = None
    attempts: int = 1


# ---------------------------------------------------------------------------
# API key (api provider only)
# ---------------------------------------------------------------------------
def _key_from_secrets_toml() -> Optional[str]:
    for candidate in _SECRETS_CANDIDATES:
        path = Path(candidate)
        if not path.is_file():
            continue
        try:
            data = tomllib.loads(path.read_text())
        except (OSError, tomllib.TOMLDecodeError):
            continue
        key = data.get("ANTHROPIC_API_KEY")
        if key:
            return key
    return None


def get_api_key() -> Optional[str]:
    """ANTHROPIC_API_KEY from the environment, else from a gitignored secrets.toml.

    The environment variable is the supported route. See `_SECRETS_CANDIDATES` for
    the file fallback and which paths are deprecated.

    `TEG_ANTHROPIC_API_KEY` is accepted as an alias so the key can be namespaced
    in a shared environment (the Claude-Code-on-the-web container) without
    colliding with a generic `ANTHROPIC_API_KEY` belonging to something else.
    The unprefixed name still wins when both are set.

    Only the `api` provider needs this; under `agent` there is no key at all.
    """
    return (os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("TEG_ANTHROPIC_API_KEY")
            or _key_from_secrets_toml())


def has_api_key() -> bool:
    return bool(get_api_key())


def _client():
    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError("anthropic SDK not installed (pip install anthropic)") from e
    key = get_api_key()
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not found in environment or secrets.toml. "
            f"(Provider is {PROVIDER_API}; unset {ENV_PROVIDER} to run on plan "
            "usage instead, which needs no key.)"
        )
    return anthropic.Anthropic(api_key=key)


# ---------------------------------------------------------------------------
# Public interface — identical under both providers
# ---------------------------------------------------------------------------
def generate_structured(system: str, user: str, schema: Type[BaseModel],
                        model: str = DEFAULT_MODEL, max_tokens: int = 16000,
                        stage: str = "structured",
                        label: str = "") -> Tuple[BaseModel, object]:
    """Call the model and return (validated_pydantic_object, usage).

    `stage` and `label` name the call in the mailbox (`story_plan`, `teg14`), so a
    hand-off is identifiable without opening it. They are ignored by the API path.
    """
    if get_provider() == PROVIDER_API:
        return _api_structured(system, user, schema, model=model, max_tokens=max_tokens)
    return _agent_structured(system, user, schema, model=model, stage=stage, label=label)


def generate_text(system: str, user: str, model: str = DEFAULT_MODEL,
                  max_tokens: int = 8000, thinking: bool = True,
                  stage: str = "text", label: str = "") -> Tuple[str, object]:
    """Call the model for free-form prose; return (text, usage).

    `thinking=False` for models that don't support adaptive thinking (e.g. Haiku 4.5,
    used by the repetition lint). Ignored by the agent path, where the responding
    session's own settings decide.
    """
    if get_provider() == PROVIDER_API:
        return _api_text(system, user, model=model, max_tokens=max_tokens,
                         thinking=thinking)
    return _agent_text(system, user, model=model, stage=stage, label=label)


# ---------------------------------------------------------------------------
# api provider
# ---------------------------------------------------------------------------
def _api_structured(system: str, user: str, schema: Type[BaseModel],
                    model: str, max_tokens: int) -> Tuple[BaseModel, object]:
    """The system prompt is cached; the user message carries the volatile data."""
    client = _client()
    resp = client.messages.parse(
        model=model,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
        output_format=schema,
    )
    return resp.parsed_output, resp.usage


def _api_text(system: str, user: str, model: str, max_tokens: int,
              thinking: bool) -> Tuple[str, object]:
    client = _client()
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": user}],
    }
    if thinking:
        kwargs["thinking"] = {"type": "adaptive"}
    resp = client.messages.create(**kwargs)
    text = "".join(b.text for b in resp.content if b.type == "text")
    return text, resp.usage


# ---------------------------------------------------------------------------
# agent provider — the file hand-off
# ---------------------------------------------------------------------------
def _agent_text(system: str, user: str, model: str, stage: str,
                label: str) -> Tuple[str, object]:
    # Imported lazily, like the anthropic SDK above: it keeps `mailbox` out of the
    # package's import graph so `python -m teg_analysis.reporting.mailbox` runs
    # without runpy's double-import warning.
    from teg_analysis.reporting import mailbox

    run = mailbox.active_run()
    directory = run.next_dir(stage=stage, label=label or stage)
    request = mailbox.write_request(directory, system=system, user=user, stage=stage,
                                    label=label or stage, expects="text", model=model)
    raw = mailbox.wait_for_response(directory)
    return raw.strip(), AgentUsage(requested_model=model, request_path=str(request))


def _agent_structured(system: str, user: str, schema: Type[BaseModel], model: str,
                      stage: str, label: str) -> Tuple[BaseModel, object]:
    """Hand off, then validate the answer here instead of in the SDK.

    The API path gets validation free from `messages.parse`. Off the API there is
    no such helper — including for ChatGPT or Gemini — so the schema travels in
    the prompt (`model_json_schema()`, enums and all) and validation happens on
    the way back in. A failure is re-asked with the exact Pydantic error attached,
    up to `MAX_STRUCTURED_ATTEMPTS`.
    """
    from teg_analysis.reporting import mailbox   # lazy — see `_agent_text`

    run = mailbox.active_run()
    json_schema = schema.model_json_schema()
    last_error: Optional[str] = None
    last_output: Optional[str] = None
    request_path: Optional[str] = None

    for attempt in range(1, MAX_STRUCTURED_ATTEMPTS + 1):
        directory = run.next_dir(stage=stage, label=label or stage)
        request_path = str(mailbox.write_request(
            directory, system=system, user=user, stage=stage, label=label or stage,
            expects="json", schema=json_schema, model=model, attempt=attempt,
            previous_error=last_error, previous_output=last_output,
        ))
        raw = mailbox.strip_fences(mailbox.wait_for_response(directory))
        try:
            parsed = schema.model_validate_json(raw)
        except (pydantic.ValidationError, json.JSONDecodeError, ValueError) as e:
            last_error, last_output = str(e), raw
            print(f"[llm] {stage} attempt {attempt} failed validation; re-asking",
                  flush=True)
            continue
        return parsed, AgentUsage(requested_model=model, request_path=request_path,
                                  attempts=attempt)

    raise RuntimeError(
        f"{stage}: no valid {schema.__name__} after {MAX_STRUCTURED_ATTEMPTS} attempts. "
        f"Last error:\n{last_error}\nLast request: {request_path}"
    )
