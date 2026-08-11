---
description: Audit CLAUDE.md for drift — contradictions with the codebase, dead references, and instructions made obsolete by newer capabilities
---

Audit `CLAUDE.md` for drift. Do not edit anything yet — report first, then ask what to fix.

Work through these four passes and report findings under each heading. Be specific: quote the line, say what's wrong, propose the replacement.

## Pass 1 — Contradicts the codebase

For every factual claim in `CLAUDE.md`, check it against the repo:

- Do all referenced files, directories, modules and functions still exist? (`webapp/PARITY_AUDIT.md`, `teg_analysis/api/`, `scripts/check_pandas_compat.py`, every path in the docs tables, etc.)
- Do the development commands still run as written?
- Do the described invariants still hold in the code, or has something been added that violates one?
- Does the architecture description match the actual folder structure?
- Are the stated environment variables still the ones the app reads?

## Pass 2 — Internally contradictory

Read the whole file for statements that conflict with each other. Past examples: a command block calling Streamlit the "production app" while the overview said the webapp had replaced it; a checklist saying `pytest tests/ -v` while a note said never to use bare `pytest`.

## Pass 3 — Obsolete or inefficient given current capabilities

This is the pass that's easy to skip and matters most. Check current Claude Code documentation (web search if needed) and identify:

- **Workarounds now handled natively.** Anything the file tells you to do manually that the tool now does for you.
- **Rituals now automated.** Protocols the file mandates that a setting, alias or feature now handles.
- **Pinned versions.** Model names, package versions, tool behaviours stated as fact. Model *aliases* are fine; pinned version strings are not.
- **Better mechanisms available.** Content that would work better as a subagent, skill, hook or slash command than as always-loaded context.
- **Capability assumptions.** Instructions written around a limitation that no longer exists.

## Pass 4 — Structure and cost

- Line count. Over ~200 lines, adherence degrades — say which sections to move.
- Any section describing *state* (what's done, what's next, recent work) rather than durable instruction. That belongs in `STATUS.md`.
- Duplication — the same rule stated in two places.
- Rules buried inside narrative prose that should be stated as rules.
- Anything so specific it should be a scoped doc rather than always-loaded context.

## Output

Report as a table: `Line | Issue | Severity | Proposed fix`. Severity is high (actively misleading), medium (stale but harmless), low (structural).

Then ask which fixes to apply. When applying them, update the freshness date at the top of `CLAUDE.md` to today.
