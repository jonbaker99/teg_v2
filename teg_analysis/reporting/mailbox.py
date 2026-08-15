"""The file hand-off that lets report generation run on plan usage instead of the API.

The problem this solves: a Python process cannot call claude.ai. The only thing
that can is an agent session (Claude Code / Cowork) or a person in a browser tab.
So instead of calling an API, the pipeline **writes the prompt to a file and
waits** for an answer file to appear. Whoever writes that answer — a Claude Code
skill, or you pasting into ChatGPT — is the thing doing the inference, and it
draws on plan usage rather than per-token API billing.

The protocol is deliberately dumb: one directory per call.

    data/llm_mailbox/<run_id>/<seq>_<label>_<stage>/
        request.md    written by the pipeline; paste-ready, self-contained
        meta.json     machine metadata (stage, schema name, expected format)
        response.md   YOU write this, for prose calls
        response.json YOU write this, for structured calls

The pipeline polls for the response file, reads it, and carries on. Nothing else
in the pipeline changes: the four-call chain sequences itself because each call
blocks until answered, and `backfill_all` keeps exactly one implementation.

`data/llm_mailbox/CURRENT` names the run directory currently being served, so a
responder never has to guess and never picks up a stale request from a crashed
run.

CLI (used by the `teg-report-respond` skill and usable by hand):

    python -m teg_analysis.reporting.mailbox status
    python -m teg_analysis.reporting.mailbox next          # path of next pending request
    python -m teg_analysis.reporting.mailbox show          # print that request
    python -m teg_analysis.reporting.mailbox answer <dir> --file answer.txt
    python -m teg_analysis.reporting.mailbox answer <dir> --stdin
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

MAILBOX_ROOT = "data/llm_mailbox"
CURRENT_FILE = f"{MAILBOX_ROOT}/CURRENT"

REQUEST_NAME = "request.md"
RUN_META_NAME = "run.json"
META_NAME = "meta.json"
RESPONSE_TEXT = "response.md"
RESPONSE_JSON = "response.json"

ENV_TIMEOUT = "TEG_LLM_TIMEOUT"
DEFAULT_TIMEOUT_SECS = 1800          # 30 minutes — generous; a stall should fail, not hang
# Poll fast at first, then settle. A real answer takes tens of seconds, but the
# cheap early polls make a quick hand-off feel immediate and keep tests brisk.
POLL_START_SECS = 0.25
POLL_MAX_SECS = 2.0

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _slug(text: str) -> str:
    return _SAFE.sub("-", str(text)).strip("-") or "call"


def timeout_secs() -> float:
    raw = os.environ.get(ENV_TIMEOUT)
    if not raw:
        return float(DEFAULT_TIMEOUT_SECS)
    try:
        return float(raw)
    except ValueError:
        return float(DEFAULT_TIMEOUT_SECS)


# ---------------------------------------------------------------------------
# Run lifecycle
# ---------------------------------------------------------------------------
class Run:
    """One pipeline invocation's mailbox. Sequential; not thread-safe by design.

    The pipeline is a chain — call N+1 depends on call N — so there is never more
    than one request outstanding. That is what keeps the responder's job trivial:
    answer the pending request, there is only ever one.
    """

    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id or time.strftime("%Y%m%d-%H%M%S") + f"-{os.getpid()}"
        self.dir = Path(MAILBOX_ROOT) / self.run_id
        self._seq = 0

    def start(self) -> "Run":
        self.dir.mkdir(parents=True, exist_ok=True)
        # The owning PID lets a responder tell "still computing the next bundle"
        # (which legitimately takes ~30s) from "the pipeline died and nobody
        # cleared CURRENT" — otherwise a crashed or notebook run leaves the
        # responder waiting on work that will never arrive.
        (self.dir / RUN_META_NAME).write_text(json.dumps({
            "pid": os.getpid(),
            "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }, indent=2))
        Path(CURRENT_FILE).parent.mkdir(parents=True, exist_ok=True)
        Path(CURRENT_FILE).write_text(self.run_id + "\n")
        return self

    def finish(self) -> None:
        """Clear the CURRENT pointer so a responder stops looking here.

        Leaves the run directory in place — the prompts and answers are the
        record of what was generated, and are worth keeping until pruned.
        """
        cur = Path(CURRENT_FILE)
        try:
            if cur.is_file() and cur.read_text().strip() == self.run_id:
                cur.unlink()
        except OSError:
            pass

    def next_dir(self, stage: str, label: str) -> Path:
        self._seq += 1
        name = f"{self._seq:03d}_{_slug(label)}_{_slug(stage)}"
        path = self.dir / name
        path.mkdir(parents=True, exist_ok=True)
        return path


_active_run: Optional[Run] = None


def active_run() -> Run:
    """The run for this process, started lazily on first use."""
    global _active_run
    if _active_run is None:
        _active_run = Run().start()
    return _active_run


def reset_active_run() -> None:
    """Drop the process-level run (used by tests and by long notebook sessions)."""
    global _active_run
    if _active_run is not None:
        _active_run.finish()
    _active_run = None


# ---------------------------------------------------------------------------
# Writing a request
# ---------------------------------------------------------------------------
_TEXT_INSTRUCTIONS = """\
Reply with the finished text and **nothing else** — no preamble, no commentary,
no explanation of what you did, no markdown code fence around the whole thing.
Save your reply to `{response_path}`.
"""

_JSON_INSTRUCTIONS = """\
Reply with **a single JSON object and nothing else** — no preamble, no commentary,
no markdown code fence. It must validate against the JSON Schema in the
"OUTPUT SCHEMA" section below. Fields marked `required` must all be present, and
any field with an `enum` must use one of the listed values exactly.
Save your reply to `{response_path}`.
"""


def write_request(directory: Path, *, system: str, user: str, stage: str,
                  label: str, expects: str, schema: Optional[dict] = None,
                  model: Optional[str] = None, attempt: int = 1,
                  previous_error: Optional[str] = None,
                  previous_output: Optional[str] = None) -> Path:
    """Write `request.md` + `meta.json` into `directory`. Returns the request path.

    `request.md` is deliberately self-contained: everything needed to answer it is
    in the one file, so it works equally as an agent's input and as something you
    paste into a ChatGPT or Gemini tab.
    """
    response_name = RESPONSE_JSON if expects == "json" else RESPONSE_TEXT
    response_path = directory / response_name
    instructions = (_JSON_INSTRUCTIONS if expects == "json" else _TEXT_INSTRUCTIONS)
    instructions = instructions.format(response_path=response_path)

    parts = [
        f"# TEG report call — {stage} ({label})",
        "",
        "> This is a prompt hand-off. Answer it as if you were the model being "
        "called. Everything you need is in this file.",
        "",
        "## What to do",
        "",
        instructions.strip(),
        "",
    ]

    if attempt > 1:
        parts += [
            f"## Retry — attempt {attempt}",
            "",
            "Your previous answer did not validate. Fix it and answer again.",
            "",
            "**Validation error:**",
            "",
            "```",
            (previous_error or "").strip(),
            "```",
            "",
            "**What you sent last time:**",
            "",
            "```",
            (previous_output or "").strip()[:4000],
            "```",
            "",
        ]

    parts += [
        "---",
        "",
        "## SYSTEM PROMPT",
        "",
        system.strip(),
        "",
        "---",
        "",
        "## USER MESSAGE",
        "",
        user.strip(),
        "",
    ]

    if schema is not None:
        parts += [
            "---",
            "",
            "## OUTPUT SCHEMA (JSON Schema — your reply must validate against this)",
            "",
            "```json",
            json.dumps(schema, indent=2, ensure_ascii=False),
            "```",
            "",
        ]

    request_path = directory / REQUEST_NAME
    request_path.write_text("\n".join(parts))

    meta = {
        "stage": stage,
        "label": label,
        "expects": expects,
        "attempt": attempt,
        "response_file": response_name,
        "response_path": str(response_path),
        "requested_model": model,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "schema_name": (schema or {}).get("title"),
    }
    (directory / META_NAME).write_text(json.dumps(meta, indent=2))
    return request_path


# ---------------------------------------------------------------------------
# Waiting for a response
# ---------------------------------------------------------------------------
class MailboxTimeout(RuntimeError):
    pass


def response_path(directory: Path) -> Optional[Path]:
    """The response file in `directory`, if one has been written."""
    for name in (RESPONSE_JSON, RESPONSE_TEXT):
        p = directory / name
        if p.is_file() and p.stat().st_size > 0:
            return p
    return None


def wait_for_response(directory: Path, timeout: Optional[float] = None) -> str:
    """Block until a response file appears in `directory`; return its contents.

    Raises `MailboxTimeout` with the request path in the message, so a stalled
    run tells you exactly which prompt nobody answered.
    """
    limit = timeout if timeout is not None else timeout_secs()
    deadline = time.time() + limit
    announced = False
    interval = POLL_START_SECS
    while time.time() < deadline:
        found = response_path(directory)
        if found is not None:
            # A responder may still be mid-write; a short settle beats a torn read.
            time.sleep(0.2)
            return found.read_text()
        if not announced:
            print(f"[mailbox] waiting for a response to {directory / REQUEST_NAME}",
                  flush=True)
            announced = True
        time.sleep(interval)
        interval = min(interval * 1.5, POLL_MAX_SECS)
    raise MailboxTimeout(
        f"no response after {limit:.0f}s for {directory / REQUEST_NAME}. "
        f"Answer it (or run the `teg-report-respond` skill) and re-run, or raise "
        f"{ENV_TIMEOUT}."
    )


def strip_fences(text: str) -> str:
    """Remove a wrapping markdown code fence, if the responder added one.

    The prompt asks for a bare answer, but a fence is the single most common
    thing a chat model adds anyway — especially when pasting by hand. Stripping
    it here is cheaper than a retry round-trip.
    """
    s = text.strip()
    if not s.startswith("```"):
        return s
    lines = s.splitlines()
    if len(lines) < 2:
        return s
    lines = lines[1:]
    while lines and not lines[-1].strip().startswith("```"):
        # Trailing prose after the closing fence — rare, but drop nothing silently.
        break
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Discovery — used by the responder (skill or human)
# ---------------------------------------------------------------------------
def current_run_dir() -> Optional[Path]:
    cur = Path(CURRENT_FILE)
    if not cur.is_file():
        return None
    try:
        run_id = cur.read_text().strip()
    except OSError:
        return None
    if not run_id:
        return None
    path = Path(MAILBOX_ROOT) / run_id
    return path if path.is_dir() else None


def run_is_alive(run_dir: Path) -> bool:
    """Is the process that owns this run still running?

    Treats an unreadable or absent `run.json` as alive: a missing PID is not
    evidence of death, and wrongly declaring a live run finished would abandon a
    pipeline mid-chain.
    """
    try:
        pid = json.loads((run_dir / RUN_META_NAME).read_text())["pid"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return True
    try:
        os.kill(int(pid), 0)          # signal 0 = liveness check, no signal sent
    except ProcessLookupError:
        return False
    except (PermissionError, OverflowError, ValueError):
        return True                   # exists but not ours, or nonsense PID
    return True


def pending_requests(run_dir: Optional[Path] = None) -> list[Path]:
    """Request directories in the active run that have no response yet."""
    run_dir = run_dir or current_run_dir()
    if run_dir is None:
        return []
    out = []
    for d in sorted(run_dir.iterdir()):
        if not d.is_dir():
            continue
        if not (d / REQUEST_NAME).is_file():
            continue
        if response_path(d) is None:
            out.append(d)
    return out


def next_pending(run_dir: Optional[Path] = None) -> Optional[Path]:
    reqs = pending_requests(run_dir)
    return reqs[0] if reqs else None


def read_meta(directory: Path) -> dict:
    try:
        return json.loads((directory / META_NAME).read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def write_answer(directory: Path, text: str) -> Path:
    """Write an answer into a request directory, in the format it expects."""
    meta = read_meta(directory)
    name = meta.get("response_file") or RESPONSE_TEXT
    path = directory / name
    path.write_text(text)
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _cmd_status() -> int:
    run_dir = current_run_dir()
    if run_dir is None:
        print("no active run (data/llm_mailbox/CURRENT is absent)")
        return 1
    pend = pending_requests(run_dir)
    print(f"run: {run_dir}")
    if not run_is_alive(run_dir):
        print("WARNING: the process that started this run is gone — it crashed or "
              "was interrupted. Nothing further will arrive.")
    print(f"pending: {len(pend)}")
    for d in pend:
        meta = read_meta(d)
        print(f"  {d}  stage={meta.get('stage')} expects={meta.get('expects')} "
              f"attempt={meta.get('attempt')}")
    return 0


def _cmd_next() -> int:
    d = next_pending()
    if d is None:
        print("NONE")
        return 1
    print(str(d))
    return 0


def _cmd_wait(timeout: float) -> int:
    """Block until a request needs answering, then print its directory.

    Prints `DONE` when the run has finished (the pipeline cleared CURRENT), and
    `NONE` on timeout. This exists so a responder runs one blocking command per
    request instead of polling in a loop.
    """
    deadline = time.time() + timeout
    interval = POLL_START_SECS
    saw_run = current_run_dir() is not None
    while time.time() < deadline:
        run_dir = current_run_dir()
        if run_dir is None:
            if saw_run:
                print("DONE")
                return 0
        else:
            saw_run = True
            d = next_pending(run_dir)
            if d is not None:
                print(str(d))
                return 0
            if not run_is_alive(run_dir):
                print("DONE")
                return 0
        time.sleep(interval)
        interval = min(interval * 1.5, POLL_MAX_SECS)
    print("NONE")
    return 1


def _cmd_show(directory: Optional[str]) -> int:
    d = Path(directory) if directory else next_pending()
    if d is None:
        print("NONE", file=sys.stderr)
        return 1
    print((d / REQUEST_NAME).read_text())
    return 0


def _cmd_answer(directory: str, *, file: Optional[str], use_stdin: bool) -> int:
    d = Path(directory)
    if not (d / REQUEST_NAME).is_file():
        print(f"not a request directory: {d}", file=sys.stderr)
        return 2
    if use_stdin:
        text = sys.stdin.read()
    elif file:
        text = Path(file).read_text()
    else:
        print("give --file PATH or --stdin", file=sys.stderr)
        return 2
    meta = read_meta(d)
    if meta.get("expects") == "json":
        text = strip_fences(text)
    out = write_answer(d, text)
    print(str(out))
    return 0


def main(argv: Optional[list] = None) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="python -m teg_analysis.reporting.mailbox",
                                description="Serve prompt hand-offs for report generation.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="show the active run and pending requests")
    sub.add_parser("next", help="print the next pending request directory, or NONE")
    wait = sub.add_parser("wait", help="block until a request needs answering; "
                                       "prints its directory, or DONE when the run ends")
    wait.add_argument("--timeout", type=float, default=900.0)
    show = sub.add_parser("show", help="print a request (defaults to the next pending one)")
    show.add_argument("directory", nargs="?")
    ans = sub.add_parser("answer", help="write an answer into a request directory")
    ans.add_argument("directory")
    ans.add_argument("--file")
    ans.add_argument("--stdin", action="store_true")

    args = p.parse_args(argv)
    if args.cmd == "status":
        return _cmd_status()
    if args.cmd == "next":
        return _cmd_next()
    if args.cmd == "wait":
        return _cmd_wait(args.timeout)
    if args.cmd == "show":
        return _cmd_show(args.directory)
    if args.cmd == "answer":
        return _cmd_answer(args.directory, file=args.file, use_stdin=args.stdin)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
