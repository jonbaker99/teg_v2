"""Toolkit for TEGBot's code sandbox: the site's analysis code plus skill folders.

Two zips are attached to each request and unpacked once per container by
``SETUP_CMD``. Runs only in Anthropic's sandbox, never on our server.

- ``code_zip()``: ``teg_analysis/`` (minus chatbot, reporting) and ``skills/``.
- ``data_zip()``: the current data files under ``data/``.
- ``skills_index()``: system-prompt text listing the skills.

To add a skill, drop a folder with a ``SKILL.md`` into ``skills/``.
"""
from __future__ import annotations

import functools
import io
import re
import zipfile
from pathlib import Path

TOOLKIT_ZIP = "teg_toolkit.zip"   # code + skills
DATA_ZIP = "teg_data.zip"         # current data files

ROOT_IN_SANDBOX = "/tmp/teg"

SETUP_CMD = (
    f'mkdir -p {ROOT_IN_SANDBOX} && '
    f'python3 -m zipfile -e "$INPUT_DIR/{TOOLKIT_ZIP}" {ROOT_IN_SANDBOX} && '
    f'python3 -m zipfile -e "$INPUT_DIR/{DATA_ZIP}" {ROOT_IN_SANDBOX} && '
    f'echo "TEG toolkit ready in {ROOT_IN_SANDBOX}"'
)

_HERE = Path(__file__).resolve().parent
_SKILLS_DIR = _HERE / "skills"
_PACKAGE_DIR = _HERE.parent.parent  # teg_analysis/
_EXCLUDED_TOP = {"chatbot", "reporting", "__pycache__"}
_FIXED_TIME = (2020, 1, 1, 0, 0, 0)

# Data the engine and helpers read (paths relative to the repo root).
# (path, required)
DATA_FILES = [
    ("data/all-scores.parquet", True),
    ("data/all-data.parquet", True),
    ("data/round_pars.csv", True),
    ("data/course_pars.csv", True),
    ("data/round_info.csv", True),
    ("data/teg_rosters.csv", True),
    ("data/handicaps.csv", True),
    ("data/players.csv", True),
    ("data/completed_tegs.csv", True),
    ("data/future_tegs.csv", False),
    ("data/in_progress_tegs.csv", False),
    ("data/teg_winners.csv", False),
    # Tables the site has already calculated; see skills/teg-analysis/reference/precomputed.md.
    ("data/streaks.parquet", False),
    ("data/bestball.parquet", False),
    ("data/commentary_round_summary.parquet", False),
    ("data/commentary_tournament_summary.parquet", False),
    ("data/commentary_round_events.parquet", False),
    ("data/commentary_round_streaks.parquet", False),
    ("data/commentary_tournament_streaks.parquet", False),
]

# Names for ``tegstats.load_precomputed`` (file stems under data/).
PRECOMPUTED = [p[len("data/"):-len(".parquet")] for p, _ in DATA_FILES
               if p.endswith(".parquet") and p not in ("data/all-scores.parquet", "data/all-data.parquet")]


def _add(zf: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=_FIXED_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    zf.writestr(info, data)


def _walk(base: Path):
    """Files under ``base``, sorted, skipping caches."""
    for p in sorted(base.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
            yield p


@functools.lru_cache(maxsize=1)
def code_zip() -> bytes:
    """Deterministic zip of the package and skills. Cached for the process life."""
    entries: dict[str, bytes] = {}
    for p in _walk(_PACKAGE_DIR):
        rel = p.relative_to(_PACKAGE_DIR)
        if rel.parts[0] in _EXCLUDED_TOP:
            continue
        if p.suffix == ".py":  # allowlist: code only, nothing else under teg_analysis/
            entries[f"teg_analysis/{rel.as_posix()}"] = p.read_bytes()
    for p in _walk(_SKILLS_DIR):
        if p.suffix not in (".py", ".md"):
            continue
        entries[f"skills/{p.relative_to(_SKILLS_DIR).as_posix()}"] = p.read_bytes()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name in sorted(entries):
            _add(zf, name, entries[name])
    return buf.getvalue()


_data_cache: bytes | None = None


def clear_data_cache() -> None:
    """Forget the cached data zip. ``webapp.deps.clear_all_data_caches`` calls this."""
    global _data_cache
    _data_cache = None


def data_zip() -> bytes:
    """Zip of the current data files, read through ``teg_analysis.io`` (volume-aware).

    Cached in-process until ``clear_data_cache()``. Same data gives the same bytes. A missing required file raises
    ``FileNotFoundError``; missing optional files are skipped.
    """
    global _data_cache
    if _data_cache is not None:
        return _data_cache
    from teg_analysis.io.file_operations import read_binary_file

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for path, required in sorted(DATA_FILES):
            try:
                _add(zf, path, read_binary_file(path))
            except FileNotFoundError:
                if required:
                    raise
    _data_cache = buf.getvalue()
    return _data_cache


_FM = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def parse_frontmatter(text: str) -> dict[str, str]:
    """Minimal ``key: value`` frontmatter reader (values may be quoted)."""
    m = _FM.match(text)
    out: dict[str, str] = {}
    if not m:
        return out
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip().strip("\"'")
    return out


def skills() -> list[dict[str, str]]:
    """``[{name, description, path}]`` for every skill, ``path`` as in the sandbox."""
    out = []
    for md in sorted(_SKILLS_DIR.glob("*/SKILL.md")):
        fm = parse_frontmatter(md.read_text(encoding="utf-8"))
        out.append({
            "name": fm.get("name", md.parent.name),
            "description": fm.get("description", ""),
            "path": f"{ROOT_IN_SANDBOX}/skills/{md.parent.name}/SKILL.md",
        })
    return out


def skills_index() -> str:
    """Text for the system prompt: how to set up, and one entry per skill."""
    lines = [
        "Toolkit: the site's own analysis code, with skills, is attached as "
        f"{TOOLKIT_ZIP} and {DATA_ZIP}. Run this once per container before using it:",
        SETUP_CMD,
        "Then read a skill's SKILL.md before using it:",
    ]
    for s in skills():
        lines.append(f"- {s['name']}: {s['description']} ({s['path']})")
    return "\n".join(lines)
