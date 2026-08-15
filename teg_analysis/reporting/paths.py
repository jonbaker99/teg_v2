"""Where report artefacts are written, and how variants are kept apart.

Every report artefact used to land in a hardcoded `data/commentary`. That is
still the default and still where the site reads from. What this module adds is
a **variant** namespace: set `TEG_REPORT_VARIANT=gpt5` and the same pipeline
writes to `data/commentary/variants/gpt5/` instead, so output from a different
model (or a different prompt experiment) can sit alongside the canonical set
rather than overwriting it.

Nothing reads a variant directory automatically — the webapp and
`render.style_report` only ever see the canonical directory unless the env var
is set. Move a variant into place deliberately with `promote_variant`.

Usage:
    from teg_analysis.reporting.paths import output_dir
    path = f"{output_dir()}/teg_{teg_num}_report_final.md"

`output_dir()` is a function, not a constant, because the variant is resolved
per call — a notebook can flip `TEG_REPORT_VARIANT` between runs in one session.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from pathlib import Path
from typing import Optional

CANONICAL_OUTPUT_DIR = "data/commentary"
VARIANTS_DIRNAME = "variants"

#: Variant names become a directory name, so they are restricted to characters
#: that cannot escape the variants root. A rejected name raises rather than
#: being silently sanitised — a typo that quietly wrote somewhere else would be
#: worse than a crash.
_VARIANT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

ENV_VARIANT = "TEG_REPORT_VARIANT"


def get_variant() -> Optional[str]:
    """The variant name from the environment, or None for the canonical set."""
    raw = (os.environ.get(ENV_VARIANT) or "").strip()
    if not raw:
        return None
    if not _VARIANT_RE.match(raw):
        raise ValueError(
            f"{ENV_VARIANT}={raw!r} is not a valid variant name. Use letters, "
            "digits, dot, dash or underscore (max 64 chars), starting with a "
            "letter or digit."
        )
    return raw


def variants_root() -> str:
    return f"{CANONICAL_OUTPUT_DIR}/{VARIANTS_DIRNAME}"


def variant_dir(variant: str) -> str:
    """The output directory for a named variant. Does not create it."""
    if not _VARIANT_RE.match(variant):
        raise ValueError(f"invalid variant name {variant!r}")
    return f"{variants_root()}/{variant}"


def output_dir(create: bool = True) -> str:
    """Where report artefacts are written for the current variant.

    Returns `data/commentary` unless `TEG_REPORT_VARIANT` is set, in which case
    it returns `data/commentary/variants/<variant>`. Creates the directory by
    default, because every caller is about to write into it.
    """
    variant = get_variant()
    path = variant_dir(variant) if variant else CANONICAL_OUTPUT_DIR
    if create:
        Path(path).mkdir(parents=True, exist_ok=True)
    return path


def list_variants() -> list[str]:
    """Variant names that currently exist on disk, sorted."""
    root = Path(variants_root())
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir())


# ---------------------------------------------------------------------------
# Manifests — what actually produced a variant
# ---------------------------------------------------------------------------
MANIFEST_NAME = "manifest.json"


def write_manifest(entry: dict, variant: Optional[str] = None) -> Optional[str]:
    """Append a run record to the current variant's manifest. No-op if canonical.

    The manifest exists because a variant directory is otherwise anonymous: three
    weeks later there is no way to tell which folder was Gemini and which was a
    prompt experiment. Under the `agent` provider the model is whatever the
    responding session happened to be, so `model` records the *requested* model
    and `provider` records that it was not enforced.
    """
    variant = variant or get_variant()
    if not variant:
        return None
    path = Path(variant_dir(variant)) / MANIFEST_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        existing = json.loads(path.read_text()) if path.is_file() else []
    except (OSError, json.JSONDecodeError):
        existing = []
    if not isinstance(existing, list):
        existing = [existing]
    existing.append({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), **entry})
    path.write_text(json.dumps(existing, indent=2))
    return str(path)


def read_manifest(variant: str) -> list:
    path = Path(variant_dir(variant)) / MANIFEST_NAME
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else [data]


# ---------------------------------------------------------------------------
# Promotion — moving a variant's output into the canonical set
# ---------------------------------------------------------------------------
def _artefact_names(teg_num: int, round_num: Optional[int] = None) -> list[str]:
    """The artefact filenames for one report, canonical-relative.

    Tournament reports and round reports have different filename shapes; this
    keeps the two in one place so promotion cannot miss one.
    """
    if round_num is None:
        stem = f"teg_{teg_num}"
        return [f"{stem}_story_plan.json", f"{stem}_dry_draft.md",
                f"{stem}_report_A_around_draft.md", f"{stem}_report_final.md",
                f"{stem}_report_styled.md"]
    stem = f"teg_{teg_num}_round_{round_num}"
    return [f"{stem}_story_plan.json", f"{stem}_dry_draft.md",
            f"{stem}_report_A_around_draft.md", f"{stem}_report_final.md",
            f"{stem}_report_styled.md"]


def promote_variant(variant: str, teg_num: int, round_num: Optional[int] = None,
                    dry_run: bool = False) -> list[str]:
    """Copy one report's artefacts from a variant into `data/commentary`.

    This is the deliberate "I pick this one" step. Overwrites the canonical
    files, so the canonical set should be committed (or already pushed) first —
    promotion does not take a backup.

    `dry_run=True` returns the copies it would make without touching anything.
    Returns the destination paths that were (or would be) written.
    """
    src_dir = Path(variant_dir(variant))
    if not src_dir.is_dir():
        raise FileNotFoundError(f"no such variant: {src_dir}")
    dest_dir = Path(CANONICAL_OUTPUT_DIR)
    dest_dir.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    for name in _artefact_names(teg_num, round_num):
        src = src_dir / name
        if not src.is_file():
            continue
        dest = dest_dir / name
        if not dry_run:
            shutil.copy2(src, dest)
        written.append(str(dest))
    if not written:
        raise FileNotFoundError(
            f"variant {variant!r} has no artefacts for TEG {teg_num}"
            + (f" round {round_num}" if round_num is not None else "")
        )
    return written
