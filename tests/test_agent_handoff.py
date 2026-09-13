"""Recovery scenarios use real temporary Git repos; no model calls or app deps."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import agent_handoff as handoff


class AgentHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="teg handoff ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.run_git("init", "-q")
        self.run_git("config", "user.email", "test@example.invalid")
        self.run_git("config", "user.name", "Test")
        (self.root / "work.py").write_text("value = 1\n")
        (self.root / ".gitignore").write_text(".current_session.md\n.agent-handoff/\n")
        self.run_git("add", "work.py", ".gitignore")
        self.run_git("commit", "-qm", "baseline")

    def run_git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args],
                              check=True, capture_output=True, text=True).stdout

    def event(self, name, **fields):
        return {"cwd": str(self.root), "session_id": "source", "hook_event_name": name,
                "transcript_path": "/not/read/transcript.jsonl", **fields}

    def saved(self):
        return handoff.read_json(self.root / handoff.STATE_DIR / "state.json")

    def test_quota_interruption_preserves_partial_work_and_failure(self):
        handoff.hook(self.event("UserPromptSubmit", prompt="Fix the winner ordering"), "claude")
        (self.root / "work.py").write_text("value = 2\n")
        (self.root / "new.py").write_text("unfinished = True\n")
        handoff.hook(self.event("PostToolUse", tool_name="Bash",
                               tool_input={"command": "python -m pytest tests/test_winners.py"},
                               tool_response={"exit_code": 1}), "claude")
        handoff.hook(self.event("StopFailure", error="rate_limit", error_details="quota"), "claude")
        before = (self.root / handoff.STATE_DIR / "state.json").read_bytes()
        output = handoff.hook(self.event("SessionStart", session_id="successor"), "codex")
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Fix the winner ordering", context)
        self.assertIn("new.py", context)
        self.assertIn("work.py", context)
        self.assertIn("rate_limit", context)
        self.assertEqual(self.saved()["tools"][0]["exit_code"], 1)
        self.assertNotIn("last_reply", self.saved())
        self.assertEqual(before, (self.root / handoff.STATE_DIR / "state.json").read_bytes())
        self.assertEqual((self.root / "work.py").read_text(), "value = 2\n")

    def test_notes_only_startup_creates_no_state(self):
        (self.root / handoff.NOTES_FILE).write_text("Next: fix ties. Owned: work.py.\n")
        output = handoff.hook(self.event("SessionStart"), "claude")
        self.assertIn("Next: fix ties", output["hookSpecificOutput"]["additionalContext"])
        self.assertFalse((self.root / handoff.STATE_DIR).exists())

    def test_empty_startup_is_silent(self):
        self.assertIsNone(handoff.hook(self.event("SessionStart"), "codex"))
        self.assertFalse((self.root / handoff.STATE_DIR).exists())

    def test_old_notes_do_not_hide_recent_steering(self):
        (self.root / handoff.NOTES_FILE).write_text("Goal: add search.\n")
        handoff.hook(self.event("UserPromptSubmit", prompt="Use existing filters only"), "codex")
        handoff.hook(self.event("UserPromptSubmit", prompt="Stop before deploying"), "codex")
        context = handoff.recovery_context(self.root)
        self.assertIn("Goal: add search", context)
        self.assertIn("Use existing filters only", context)
        self.assertIn("Stop before deploying", context)
        self.assertIn("current user request", context)

    def test_long_session_retains_first_request_after_recent_history_rolls_over(self):
        handoff.hook(self.event("UserPromptSubmit", prompt="Fix winner ordering"), "claude")
        for n in range(10):
            handoff.hook(self.event("UserPromptSubmit", prompt="Steering " + str(n)), "claude")
        self.assertEqual(len(self.saved()["prompts"]), 8)
        self.assertIn("Fix winner ordering", handoff.recovery_context(self.root))
        self.assertEqual(self.saved()["sessions"]["claude:source"]["first_request"]["text"],
                         "Fix winner ordering")

    def test_representative_claude_bash_response_has_unknown_exit_code(self):
        response = {"stdout": "1 passed", "stderr": "", "interrupted": False}
        record = handoff.tool_record(self.event("PostToolUse", tool_name="Bash",
                                                tool_input={"command": "python -m pytest"},
                                                tool_response=response), "claude")
        self.assertIsNone(record["exit_code"])
        self.assertEqual(record["command"], "python -m pytest")

    def test_git_change_after_last_capture_is_flagged(self):
        handoff.hook(self.event("UserPromptSubmit", prompt="Fix work.py"), "claude")
        (self.root / "work.py").write_text("value = 3\n")
        self.assertIn("Git state differs", handoff.recovery_context(self.root))

    def test_same_size_changes_to_already_dirty_files_are_flagged(self):
        (self.root / "work.py").write_text("value = 2\n")
        (self.root / "new.py").write_text("value = 2\n")
        handoff.hook(self.event("UserPromptSubmit", prompt="Fix work.py"), "claude")
        old = self.saved()["git"]
        (self.root / "work.py").write_text("value = 3\n")
        (self.root / "new.py").write_text("value = 3\n")
        current = handoff.snapshot(self.root)
        self.assertEqual(old["status"], current["status"])
        self.assertEqual(old["diff_stat"], current["diff_stat"])
        self.assertNotEqual(old["fingerprint"], current["fingerprint"])
        self.assertIn("Git state differs", handoff.recovery_context(self.root))

    def test_git_timeout_still_saves_requests_and_failures(self):
        timeout = subprocess.TimeoutExpired("git", 1)
        with patch.object(handoff, "snapshot", side_effect=timeout):
            handoff.capture(self.root, self.event("UserPromptSubmit", prompt="Fix ordering"), "claude")
            handoff.capture(self.root, self.event("StopFailure", error="rate_limit"), "claude")
            context = handoff.recovery_context(self.root)
        self.assertEqual(self.saved()["prompts"][0]["text"], "Fix ordering")
        self.assertEqual(self.saved()["last_failure"]["error"], "rate_limit")
        self.assertIn("Git state is unknown", context)
        self.assertIn("Fix ordering", context)

    def test_long_notes_keep_goal_and_next_action_in_startup_context(self):
        notes = "Goal: fix ties.\n" + "Details.\n" * 1000 + "Next action: run test_winners.\n"
        (self.root / handoff.NOTES_FILE).write_text(notes)
        context = handoff.recovery_context(self.root)
        self.assertIn("Goal: fix ties", context)
        self.assertIn("Next action: run test_winners", context)
        self.assertLess(len(context), 6000)

    def test_unknown_and_failed_tool_results_are_not_success(self):
        unknown = handoff.tool_record(self.event("PostToolUse", tool_name="Bash",
                                                tool_response="exit code unavailable"), "codex")
        self.assertIsNone(unknown["exit_code"])
        handoff.hook(self.event("PostToolUseFailure", tool_name="Bash", error="failed"), "claude")
        self.assertEqual(self.saved()["tools"][0]["error"], "failed")
        self.assertIn("null exit codes are unknown", handoff.recovery_context(self.root))

    def test_parallel_capture_does_not_drop_tool_events(self):
        events = [self.event("PostToolUse", tool_name="Bash", tool_input={"command": "cmd" + str(n)})
                  for n in range(4)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda payload: handoff.capture(self.root, payload, "codex"), events))
        self.assertEqual({tool["command"] for tool in self.saved()["tools"]},
                         {"cmd0", "cmd1", "cmd2", "cmd3"})
        self.assertEqual((self.root / handoff.STATE_DIR / "state.json").stat().st_mode & 0o777, 0o600)

    def test_successor_capture_retains_source_baseline(self):
        handoff.hook(self.event("UserPromptSubmit", prompt="Start task"), "claude")
        baseline = self.saved()["sessions"]["claude:source"]["initial_git"]
        (self.root / "work.py").write_text("value = 4\n")
        handoff.hook(self.event("UserPromptSubmit", session_id="successor", prompt="Continue"), "codex")
        state = self.saved()
        self.assertEqual(state["sessions"]["claude:source"]["initial_git"], baseline)
        self.assertNotEqual(state["sessions"]["codex:successor"]["initial_git"], baseline)
        self.assertEqual(state["prompts"][0]["text"], "Start task")

    def test_other_worktree_state_is_rejected_without_overwrite(self):
        handoff.hook(self.event("UserPromptSubmit", prompt="Task"), "claude")
        path = self.root / handoff.STATE_DIR / "state.json"
        data = self.saved()
        data["worktree"] = "/some/other/worktree"
        handoff.atomic_json(path, data)
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "another worktree"):
            handoff.hook(self.event("PostToolUse"), "codex")
        self.assertEqual(path.read_bytes(), before)

    def test_installation_is_idempotent_and_preserves_other_config(self):
        settings = self.root / ".claude/settings.json"
        original_hook = {"type": "command", "command": "existing-notification"}
        handoff.atomic_json(settings, {"model": "opusplan", "permissions": {"allow": ["Read"]},
                                      "hooks": {"Stop": [{"matcher": "anything", "hooks": [original_hook]}]}})
        first = handoff.installation(self.root)
        for path, data in first:
            handoff.atomic_json(path, data)
        self.assertEqual(first, handoff.installation(self.root))
        claude = handoff.read_json(settings)
        self.assertEqual(claude["model"], "opusplan")
        self.assertEqual(claude["permissions"], {"allow": ["Read"]})
        self.assertEqual(claude["hooks"]["Stop"][0]["hooks"], [original_hook])
        self.assertIn("StopFailure", claude["hooks"])
        codex = handoff.read_json(self.root / ".codex/hooks.json")
        self.assertNotIn("StopFailure", codex["hooks"])
        self.assertIn("Interrupt", codex["hooks"])

    def test_invalid_config_prevents_installation_plan(self):
        path = self.root / ".claude/settings.json"
        path.parent.mkdir()
        path.write_text("invalid JSON")
        with self.assertRaises(ValueError):
            handoff.installation(self.root)
        self.assertFalse((self.root / ".codex/hooks.json").exists())

    def test_shell_setup_preserves_existing_functions_and_is_idempotent(self):
        path = self.root / "test.zshrc"
        original = "# Existing setup\nexport LOCAL_SETTING=example\nto-codex() { echo old; }\n"
        path.write_text(original)
        before, updated = handoff.shell_configuration(self.root, path)
        self.assertEqual(before, original)
        self.assertTrue(updated.startswith(original))
        self.assertIn("source '", updated)  # temp root deliberately contains spaces
        path.write_text(updated)
        self.assertEqual(handoff.shell_configuration(self.root, path)[1], updated)

    def test_symlinked_configuration_is_not_replaced_or_modified(self):
        target = self.root / "managed.json"
        target.write_text('{"model":"opusplan"}')
        settings = self.root / ".claude/settings.json"
        settings.parent.mkdir()
        settings.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "symlinked"):
            handoff.installation(self.root)
        with self.assertRaisesRegex(ValueError, "symlinked"):
            handoff.shell_configuration(self.root, settings)
        with self.assertRaisesRegex(ValueError, "symlink"):
            handoff.atomic_text(settings, "replacement")
        self.assertTrue(settings.is_symlink())
        self.assertEqual(target.read_text(), '{"model":"opusplan"}')

    def test_shortcuts_use_task_root_and_preserve_caller_directory(self):
        nested = self.root / "nested"
        nested.mkdir()
        helper = Path(handoff.__file__).with_suffix(".zsh")
        code = '''source "$TEG_TEST_HELPER"
codex() { print -r -- "codex:$PWD"; print -l -- "$@"; }
claude() { print -r -- "claude:$PWD"; print -l -- "$@"; }
to-codex --model default
to-claude --model opus
print -r -- "caller:$PWD"
'''
        result = subprocess.run(["zsh", "-f", "-c", code], cwd=nested,
                                env={**os.environ, "TEG_TEST_HELPER": str(helper)},
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("claude:" + str(self.root), result.stdout)
        self.assertIn("caller:" + str(nested), result.stdout)
        self.assertIn("-C\n" + str(self.root), result.stdout)
        self.assertIn("--model\ndefault", result.stdout)
        self.assertIn("--model\nopus", result.stdout)
        self.assertEqual(result.stdout.count("Resume the next unfinished action"), 2)

    def test_hook_command_handles_spaces_and_nested_working_directory(self):
        scripts = self.root / "scripts"
        scripts.mkdir()
        shutil.copyfile(handoff.__file__, scripts / "agent_handoff.py")
        nested = self.root / "nested"
        nested.mkdir()
        payload = self.event("UserPromptSubmit", cwd=str(nested), prompt="Continue task")
        captured = subprocess.run(handoff.hook_definition("claude")["command"], shell=True,
                                  cwd=nested, input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual(captured.returncode, 0, captured.stderr)
        self.assertEqual(captured.stdout, "")
        self.assertIn("Continue task", handoff.recovery_context(self.root))
        startup = subprocess.run([sys.executable, str(scripts / "agent_handoff.py"), "hook", "--agent", "codex"],
                                 input=json.dumps(self.event("SessionStart")), capture_output=True, text=True)
        self.assertEqual(startup.returncode, 0, startup.stderr)
        self.assertEqual(json.loads(startup.stdout)["hookSpecificOutput"]["hookEventName"], "SessionStart")


if __name__ == "__main__":
    unittest.main()
