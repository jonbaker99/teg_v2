"""Shared log of every TEGBot question and answer, for the "What others asked" page.

One JSON object per line (JSONL), appended as each answer is given. On Railway
it lives on the volume (``/mnt/data_repo/tegbot/qa_log.jsonl``). It sits outside
``data/``, so it is not part of the GitHub sync and a question never triggers a
commit. Locally it lives under ``data/tegbot/`` (gitignored). Set
``TEGBOT_LOG_PATH`` to put it anywhere else (tests do).

No visitor identity is stored: no IP, no name. Entries in one chat share a
random ``conv`` id made by the page, so follow-ups display with their thread.
"""

from __future__ import annotations

import json
import os
import re
import threading
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

from teg_analysis.io.volume_operations import _get_local_path, _get_volume_path, _is_railway

ENV_LOG_PATH = "TEGBOT_LOG_PATH"
LOG_FILE = "tegbot/qa_log.jsonl"
LOCAL_LOG_FILE = "data/tegbot/qa_log.jsonl"
MAX_FIELD_CHARS = 20_000
_CONV_RE = re.compile(r"^[0-9a-f]{8,32}$")
_lock = threading.Lock()


def log_path() -> Path:
    if os.environ.get(ENV_LOG_PATH):
        return Path(os.environ[ENV_LOG_PATH])
    if _is_railway():
        return Path(_get_volume_path(LOG_FILE))
    return _get_local_path(LOCAL_LOG_FILE)


def clean_conv_id(value: str | None) -> str:
    """The page's chat id if well-formed, else a fresh one (never trust the client)."""
    value = (value or "").strip().lower()
    return value if _CONV_RE.match(value) else uuid.uuid4().hex


def append_entry(*, conv: str, question: str, answer: str, workings: list[dict],
                 model: str, cost_usd: float, seconds: float) -> dict:
    entry = {
        "id": uuid.uuid4().hex,
        "conv": clean_conv_id(conv),
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "question": question[:MAX_FIELD_CHARS],
        "answer": answer[:MAX_FIELD_CHARS],
        "workings": [{k: str(v)[:MAX_FIELD_CHARS] for k, v in w.items()} for w in workings],
        "model": model,
        "cost_usd": round(cost_usd, 5),
        "seconds": round(seconds, 1),
    }
    path = log_path()
    line = json.dumps(entry, ensure_ascii=False) + "\n"
    with _lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line)
    return entry


def read_entries() -> list[dict]:
    """Every logged entry, oldest first. Unreadable lines are skipped."""
    path = log_path()
    if not path.exists():
        return []
    entries = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(entry, dict) and entry.get("question"):
                entries.append(entry)
    return entries


def conversations(limit: int = 50) -> list[list[dict]]:
    """Chats newest first (by latest question), each a list of entries in order."""
    threads: "OrderedDict[str, list[dict]]" = OrderedDict()
    for entry in read_entries():
        conv = entry.get("conv") or entry["id"]
        threads.setdefault(conv, []).append(entry)
        threads.move_to_end(conv)
    return list(reversed(threads.values()))[:limit]
