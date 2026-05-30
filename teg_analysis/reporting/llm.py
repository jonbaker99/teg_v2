"""Thin Anthropic client wrapper for the reporting pipeline.

- Reads ANTHROPIC_API_KEY from the environment.
- Prompt caching on the (large, stable) system prompt; the per-TEG data goes in
  the user turn so the cached prefix is reused across reports.
- Structured output via the Pydantic-validated messages.parse helper.
- Adaptive thinking (effort defaults to high on Opus 4.7) for editorial quality.

The anthropic SDK is imported lazily so the rest of the reporting package
(Stages 1-2, pure Python) works without it installed and without a key.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Optional, Type, Tuple

from pydantic import BaseModel

DEFAULT_MODEL = "claude-opus-4-7"

# Mirror the Streamlit app's key resolution (env var, then a gitignored
# secrets.toml) WITHOUT importing streamlit, so teg_analysis stays UI-agnostic.
# Paths are cwd-relative (repo root), consistent with the rest of the package.
_SECRETS_CANDIDATES = (".streamlit/secrets.toml", "streamlit/.streamlit/secrets.toml")


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
    """ANTHROPIC_API_KEY from the environment, else from .streamlit/secrets.toml."""
    return os.environ.get("ANTHROPIC_API_KEY") or _key_from_secrets_toml()


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
            "ANTHROPIC_API_KEY not found in environment or .streamlit/secrets.toml"
        )
    return anthropic.Anthropic(api_key=key)


def generate_structured(system: str, user: str, schema: Type[BaseModel],
                        model: str = DEFAULT_MODEL, max_tokens: int = 16000) -> Tuple[BaseModel, object]:
    """Call Claude and return (validated_pydantic_object, usage).

    The system prompt is cached; the user message carries the volatile per-TEG data.
    """
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


def generate_text(system: str, user: str, model: str = DEFAULT_MODEL,
                  max_tokens: int = 8000) -> Tuple[str, object]:
    """Call Claude for free-form prose; return (text, usage). System prompt cached."""
    client = _client()
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    return text, resp.usage
