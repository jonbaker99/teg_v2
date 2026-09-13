#!/usr/bin/env python3
"""Local, model-free recovery hooks for Claude Code and Codex CLI.

Notes describe intent; automatic state records requests, tool outcomes and Git
state even if an agent cannot write a final handoff. One writer per worktree.
"""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time


STATE_DIR = ".agent-handoff"
NOTES_FILE = ".current_session.md"
COMMON_EVENTS = (
    "SessionStart", "UserPromptSubmit", "PostToolUse", "Stop", "PreCompact",
    "SessionEnd",
)
EXTRA_EVENTS = {
    "claude": ("PostToolUseFailure", "StopFailure"),
    "codex": ("Interrupt",),
}
PATHSPEC = ("--", ".", ":(exclude)to_do_jon.md", ":(exclude).current_session.md",
            ":(exclude).agent-handoff/**")


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clipped(value, limit=2000):
    value = str(value or "")
    return value if len(value) <= limit else value[:limit] + "\n[truncated; inspect source]"


def note_excerpt(value, limit=3500):
    if len(value) <= limit:
        return value
    # Goals tend to be at the beginning; the next action tends to be at the end.
    return value[:limit * 2 // 3] + "\n[... inspect full task notes ...]\n" + value[-limit // 3:]


def git(root, *args):
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True,
        timeout=1, env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    )
    if result.returncode:
        raise RuntimeError(clipped(result.stderr, 300))
    return result.stdout.strip()


def project_root(cwd):
    return Path(git(Path(cwd), "rev-parse", "--show-toplevel")).resolve()


def snapshot(root):
    patch = git(root, "diff", "HEAD", *PATHSPEC)
    names = git(root, "diff", "--name-only", "-z", "HEAD", *PATHSPEC)
    names += "\0" + git(root, "ls-files", "--others", "--exclude-standard", "-z", *PATHSPEC)
    metadata = []
    for name in sorted(set(names.split("\0")) - {""}):
        try:
            info = (root / name).lstat()
            metadata.append((name, info.st_size, info.st_mtime_ns, info.st_ctime_ns))
        except FileNotFoundError:
            metadata.append((name, "deleted"))
    return {
        "branch": git(root, "rev-parse", "--abbrev-ref", "HEAD"),
        "head": git(root, "rev-parse", "HEAD"),
        "status": git(root, "status", "--porcelain=v1", "--untracked-files=normal", *PATHSPEC),
        "diff_stat": git(root, "diff", "--stat", "HEAD", *PATHSPEC),
        "fingerprint": hashlib.sha256((patch + json.dumps(metadata)).encode()).hexdigest(),
    }


def read_json(path):
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object in " + str(path))
    return data


def atomic_text(path, text):
    if path.is_symlink():
        raise ValueError("Refusing to replace a symlink: " + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        if path.exists():
            os.fchmod(fd, path.stat().st_mode & 0o777)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def atomic_json(path, data):
    atomic_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


@contextmanager
def state_lock(root):
    directory = root / STATE_DIR
    directory.mkdir(mode=0o700, exist_ok=True)
    with (directory / "state.lock").open("a") as handle:
        deadline = time.monotonic() + 0.5
        while True:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Recovery state is busy; checkpoint was not saved")
                time.sleep(0.02)
        try:
            yield directory / "state.json"
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def tool_record(payload, agent):
    inputs = payload.get("tool_input") or {}
    if not isinstance(inputs, dict):
        inputs = {}
    response = payload.get("tool_response")
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except ValueError:
            response = None
    code = response.get("exit_code") if isinstance(response, dict) else None
    return {
        "at": stamp(), "agent": agent, "tool": payload.get("tool_name"),
        "command": clipped(inputs.get("command") or inputs.get("cmd"), 1500),
        "file": inputs.get("file_path"), "exit_code": code,
        "error": clipped(payload.get("error"), 500),
        "event": payload.get("hook_event_name"),
    }


def capture(root, payload, agent):
    event = payload["hook_event_name"]
    with state_lock(root) as path:
        data = read_json(path)
        if data and data.get("worktree") != str(root):
            raise ValueError("Recovery state belongs to another worktree; move it aside first")
        # Save lifecycle facts even when Git cannot produce a fresh snapshot.
        try:
            current = snapshot(root)
            data.pop("git_error", None)
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
            current = None
            data["git_error"] = clipped(str(error), 500)
        session = agent + ":" + str(payload.get("session_id", "unknown"))
        sessions = data.setdefault("sessions", {})
        if session not in sessions:
            sessions[session] = {"started_at": stamp(), "initial_git": current}
        if event == "UserPromptSubmit" and "first_request" not in sessions[session]:
            sessions[session]["first_request"] = {
                "at": stamp(), "agent": agent, "text": clipped(payload.get("prompt"), 8000),
            }
        data["sessions"] = dict(list(sessions.items())[-8:])
        data.update({
            "version": 1, "worktree": str(root), "updated_at": stamp(),
            "agent": agent, "session_id": payload.get("session_id"),
            "event": event,
            "transcript_path": payload.get("transcript_path"),
        })
        if current is not None:
            data["git"] = current
        notes = root / NOTES_FILE
        if notes.exists():
            data["notes_hash"] = hashlib.sha256(notes.read_bytes()).hexdigest()
        if event == "UserPromptSubmit":
            prompts = data.setdefault("prompts", [])
            prompts.append({"at": stamp(), "agent": agent,
                            "text": clipped(payload.get("prompt"), 8000)})
            data["prompts"] = prompts[-8:]
        elif event in ("PostToolUse", "PostToolUseFailure"):
            tools = data.setdefault("tools", [])
            tools.append(tool_record(payload, agent))
            data["tools"] = tools[-16:]
        elif event == "Stop":
            data["last_reply"] = {"at": stamp(), "agent": agent,
                                  "text": clipped(payload.get("last_assistant_message"), 4000)}
        elif event == "StopFailure":
            data["last_failure"] = {"at": stamp(), "agent": agent,
                                    "error": payload.get("error"),
                                    "details": clipped(payload.get("error_details"), 1000)}
        atomic_json(path, data)


def recovery_context(root):
    path = root / STATE_DIR / "state.json"
    data = read_json(path)
    if data and data.get("worktree") != str(root):
        raise ValueError("Recovery state belongs to another worktree; move it aside first")
    notes = root / NOTES_FILE
    if not data and not notes.exists():
        return ""
    try:
        current = snapshot(root)
        current_error = None
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        current = None
        current_error = clipped(str(error), 500)
    pieces = [
        "Local cross-agent recovery context. Follow the current user request; these are previous-task records.",
        "For a continuation request, resume the recorded next action within existing authorization, rather than only describing it.",
        "For a new task, use these records only to protect unrelated unfinished work.",
        "One writer per worktree. Inspect relevant diffs and untracked files before editing; the dirty tree may contain other tasks.",
        "Task notes: " + str(notes),
        note_excerpt(notes.read_text(encoding="utf-8")) if notes.exists() else "No semantic task notes exist.",
    ]
    if data:
        pieces.append("Last automatic checkpoint: " + data.get("updated_at", "unknown")
                      + " / " + str(data.get("agent")) + " / " + str(data.get("event")))
        if data.get("git_error"):
            pieces.append("The last checkpoint could not refresh Git state: " + data["git_error"])
        if current is not None and data.get("git") != current:
            pieces.append("Git state differs from the last checkpoint. Reconcile it before relying on old check results.")
        if data.get("notes_hash") and notes.exists():
            if hashlib.sha256(notes.read_bytes()).hexdigest() != data["notes_hash"]:
                pieces.append("Task notes changed after the last automatic checkpoint.")
        prompts = data.get("prompts", [])
        session = str(data.get("agent")) + ":" + str(data.get("session_id", "unknown"))
        first = data.get("sessions", {}).get(session, {}).get("first_request")
        if first:
            pieces.append("First request in the last recorded session (may predate later steering):\n"
                          + note_excerpt(json.dumps(first, ensure_ascii=False), 1500))
        if prompts:
            pieces.append("Recent user requests (may include steering, not a new objective):\n"
                          + note_excerpt(json.dumps(prompts[-3:], ensure_ascii=False), 2500))
        if data.get("last_reply"):
            pieces.append("Previous agent response:\n" + note_excerpt(json.dumps(data["last_reply"], ensure_ascii=False), 1000))
        if data.get("last_failure"):
            pieces.append("Recorded API failure (check its timestamp):\n" + json.dumps(data["last_failure"], ensure_ascii=False))
        pieces.append("Recent tools; null exit codes are unknown, never proof of passing tests:\n"
                      + clipped(json.dumps(data.get("tools", [])[-6:], ensure_ascii=False), 1200))
        pieces.append("Full automatic state and initial session baselines: " + str(path))
    if current is not None:
        pieces.extend([
            "Current branch / HEAD: " + current["branch"] + " / " + current["head"],
            "Current status (includes untracked files):\n" + clipped(current["status"], 1500),
            "Current tracked diff summary:\n" + clipped(current["diff_stat"], 700),
        ])
    else:
        pieces.append("Current Git state is unknown; inspect it directly: " + current_error)
    try:
        pieces.append("Last commit:\n" + clipped(git(root, "log", "-1", "--format=%h %s", "--stat", *PATHSPEC), 700))
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        pieces.append("Last commit unavailable: " + clipped(str(error), 300))
    pieces.append("Update .current_session.md with goal, decisions, owned files, checks and next action during work. Automatic capture does not infer intent or completion.")
    return "\n\n".join(pieces)


def hook(payload, agent):
    root = project_root(payload.get("cwd") or os.getcwd())
    event = payload.get("hook_event_name")
    if event == "SessionStart":
        context = recovery_context(root)
        # Merely opening a successor must not erase source state.
        return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": context}} if context else None
    if event in COMMON_EVENTS + EXTRA_EVENTS[agent]:
        capture(root, payload, agent)
    return None


def hook_definition(agent, event=None):
    definition = {
        "type": "command",
        "command": 'python3 "$(git rev-parse --show-toplevel)/scripts/agent_handoff.py" hook --agent ' + agent,
        "timeout": 3 if event in ("SessionEnd", "Interrupt") else 10,
    }
    if agent == "codex" and event == "SessionStart":
        definition["additionalContextLimit"] = 3500
    return definition


def installation(root):
    """Prepare both config updates before writing either one."""
    plans = []
    for agent, relative in (("codex", ".codex/hooks.json"), ("claude", ".claude/settings.json")):
        path = root / relative
        if path.is_symlink():
            raise ValueError("Project hook config is symlinked; inspect its target before installing: " + str(path))
        data = read_json(path)
        events = data.setdefault("hooks", {})
        if not isinstance(events, dict):
            raise ValueError("Expected hooks object in " + str(path))
        # Replace only our handlers; preserve other hooks and configuration.
        for event, groups in list(events.items()):
            if not isinstance(groups, list):
                raise ValueError("Expected hook groups array in " + str(path))
            retained = []
            for group in groups:
                if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                    raise ValueError("Expected hook group with handlers in " + str(path))
                if not all(isinstance(h, dict) for h in group["hooks"]):
                    raise ValueError("Expected hook handler objects in " + str(path))
                handlers = [h for h in group.get("hooks", [])
                            if "/scripts/agent_handoff.py\" hook --agent " not in h.get("command", "")]
                if handlers:
                    retained.append({**group, "hooks": handlers})
            events[event] = retained
        for event in COMMON_EVENTS + EXTRA_EVENTS[agent]:
            events.setdefault(event, []).append({"hooks": [hook_definition(agent, event)]})
        plans.append((path, data))
    return plans


def shell_configuration(root, path):
    """Load replacement functions last; keep the user's existing shell setup."""
    if path.is_symlink():
        raise ValueError("Shell config is symlinked; inspect its target before using --shell: " + str(path))
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    source = "source " + shlex.quote(str(root / "scripts/agent_handoff.zsh"))
    lines = [line for line in original.splitlines() if line != source]
    updated = "\n".join(lines).rstrip() + "\n" + source + "\n"
    return original, updated


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    hooks = commands.add_parser("hook", help="Read one lifecycle event as JSON on stdin")
    hooks.add_argument("--agent", choices=("claude", "codex"), required=True)
    commands.add_parser("show", help="Show recovery context without changing it")
    install = commands.add_parser("install", help="Merge recovery hooks into both project configs")
    install.add_argument("--dry-run", action="store_true")
    install.add_argument("--shell", action="store_true", help="Also load improved shortcuts from ~/.zshrc, keeping a backup")
    args = parser.parse_args(argv)
    try:
        if args.action == "hook":
            payload = json.load(sys.stdin)
            if not isinstance(payload, dict):
                raise ValueError("Hook input must be a JSON object")
            output = hook(payload, args.agent)
            if output:
                print(json.dumps(output, ensure_ascii=False))
        else:
            root = project_root(os.getcwd())
            if args.action == "show":
                print(recovery_context(root) or "No recovery state exists yet.")
            else:
                plans = installation(root)
                shell_path = Path.home() / ".zshrc"
                shell = shell_configuration(root, shell_path) if args.shell else None
                for path, data in plans:
                    if not args.dry_run:
                        atomic_json(path, data)
                    print(("Would update " if args.dry_run else "Updated ") + str(path))
                    print("Recovery events: " + ", ".join(data["hooks"]))
                if shell is not None:
                    original, updated = shell
                    if not args.dry_run and original != updated:
                        backup = shell_path.with_name(shell_path.name + ".teg-agent-handoff.bak")
                        if shell_path.exists() and not backup.exists():
                            atomic_text(backup, original)
                        atomic_text(shell_path, updated)
                    print(("Would update " if args.dry_run else "Updated ") + str(shell_path))
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print("Agent recovery: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
