# Source this file from ~/.zshrc. Run the shortcuts inside the task worktree.
# Startup hooks supply recovery context; these prompts ask the successor to act.

to-codex() {
  local teg_task_root
  teg_task_root="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    print -u2 'Run to-codex inside the TEG repository or its task worktree.'
    return 1
  }
  codex -C "$teg_task_root" "$@" \
    'Continue the previous task using the startup recovery context. Read .current_session.md and .agent-handoff/state.json if present; inspect relevant Git diffs and untracked files. Resume the next unfinished action within the recorded scope and authorization. Preserve unrelated work. If the next action is unclear, ask one focused question.'
}

to-claude() {
  local teg_task_root
  teg_task_root="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    print -u2 'Run to-claude inside the TEG repository or its task worktree.'
    return 1
  }
  (
    cd "$teg_task_root" || return 1
    claude "$@" \
      'Continue the previous task using the startup recovery context. Read .current_session.md and .agent-handoff/state.json if present; inspect relevant Git diffs and untracked files. Resume the next unfinished action within the recorded scope and authorization. Preserve unrelated work. If the next action is unclear, ask one focused question.'
  )
}
