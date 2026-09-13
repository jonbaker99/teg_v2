# TEG v2 — To-do Index

Central index. Each area owns its own `TODOS.md`; this file points to them and summarises current priority.

---

## Core areas

### `webapp/` — [TODOS.md](webapp/TODOS.md)
Active development. Known bugs to fix before publish, charts rebuild, mobile phase M1, cosmetic parity items.

### `streamlit/` — [TODOS.md](streamlit/TODOS.md)
Stable/deployed. Only maintenance and minor fixes.

### `teg_analysis/` — [TODOS.md](teg_analysis/TODOS.md)
Analysis package. REST API placeholder, any outstanding analytical work.

---

## Specific areas

### Commentary (reporting pipeline) — [`teg_analysis/reporting/STATUS.md`](teg_analysis/reporting/STATUS.md)
LLM-powered tournament and round reports. **Read [`STATUS.md`](teg_analysis/reporting/STATUS.md) → START HERE first** — it is the pick-up ledger and *is* the to-do list for this area.

Two open workstreams:
- **Report quality.** The scoring and voice layers were reworked end to end on 2026-08-14 (counterfactual `importance`, symmetric detection, `win_anatomy`, storyline hierarchy, champion register), then the readability pass landed on 2026-08-15 (em-dashes banned, humour at `humour6`, ~15-word sentences). TEGs 4, 8, 12, 14 and 18 were regenerated as tests and read well, but **all five predate the readability pass**. **Next: one cold generation (~$0.65) to validate the new voice, then regenerate the library (~$11).** ⚠️ **Nothing is user-visible yet, and it's worse than "not yet" suggests — 16 of 17 `*_report_styled.md` files (what the site serves) do not match their own `report_final.md`,** because every run used `style=False`. Re-styling is free; don't forget it again. Round reports (49 outstanding) were not touched: the round *code* is level with the tournament pipeline, the published round reports are two generations behind it.
- **Get off per-call API billing — built 2026-08-15; the mechanism has been run, the comparison hasn't.** Report generation can run on claude.ai plan usage (`--plan`) or hand prompts to another model for pasting (`--paste gpt5`); the API stays the default. See [README.md](teg_analysis/reporting/README.md) → *Who answers the prompts*. Evidence on disk (a tracked `reply.txt` holding a complete unpublished TEG 17 report, plus the TEG 14 hand-off regeneration) says whole reports have gone through the hand-off. **Outstanding: read a plan-usage report against an API report of the same TEG and record a verdict**, then decide which provider the full regeneration runs on.

The experiment log is in [`EXPERIMENTS.md`](teg_analysis/reporting/EXPERIMENTS.md).

### Data updates — [below](#data-updates)
Tracked here (no sub-folder needed).

### Shared Codex / Claude CLI work — [below](#shared-codex--claude-cli-work)
Shared rules and automatic checkpoint/startup recovery are built; runtime trust verification and quota-triggered launching remain open.

---

## Shared Codex / Claude CLI work

Readiness review, 2026-09-12. Scope: both command-line tools; switching must not require a requested final handoff.

- [x] Add local worktree recovery: semantic `.current_session.md` notes plus automatic `.agent-handoff/state.json` facts. Both CLIs load source state at startup; first requests and initial dirty Git baselines survive agent switches. Independent tasks must use separate worktrees; the state lock is not a writer-ownership lock.
- [x] Add automatic prompt/tool-event capture, Git snapshots and content/metadata fingerprints. Capture failures and untracked work without relying on a final response; semantic decisions still need notes during work. Built 2026-09-12 in `scripts/agent_handoff.py`.
- [ ] Reconcile stale root `STATUS.md` and reporting onboarding snapshots; shorten `CLAUDE.md`, which exceeds its own approximate 200-line limit. Commit recovery scripts, shared rules and project hooks before creating new worktrees; they are currently uncommitted. Include Codex-facing symlink/skills/configuration when committing this setup.
- [ ] Add a small CLI supervisor for quota-triggered failover. Use Claude's documented `StopFailure` rate-limit event and Codex structured failure events; verify both on installed versions. Release source writer ownership before starting the successor in the same task worktree. Bound retries and stop when both accounts are unavailable or user input is required.
- [ ] Verify installed hook execution and trust setup once on both real CLIs. Codex project hook definitions need `/hooks` review/trust. Event fixtures and direct hook commands are tested; actual account quota exhaustion has not been exercised. Existing global notification hooks are preserved.
- [x] Exercise simulated interruption recovery with a partial edit, failed test, untracked work, missing final reply, concurrent state capture, slow Git, long request history and shell shortcuts. Focused stdlib tests pass; live supervisor ownership/failover tests belong to the still-open supervisor item.
- [ ] Align the existing local development venv with `.python-version` (3.12); it currently runs 3.14. Use the installed Python 3.12 for recovery checks meanwhile.
- [ ] Harden report-specific continuity separately: exclusive responder claims, recovery after mailbox timeout/dead pipeline, and platform-neutral tool instructions in the Codex responder skill. Reuse the existing report mailbox rather than treating it as a general coding handoff.

---

## Data updates

**Data storage & mobile score-ingestion overhaul** — done; see [`DATA_STORAGE_INGESTION_PLAN.md`](DATA_STORAGE_INGESTION_PLAN.md) (kept as a historical/reference record) and `CLAUDE.md`'s "Current state & next steps" for the current-state summary. One item remains open:

- **Phase 4.2 decision gate (human, after a season of real Live round use):** if the native `/live-round` flow was used and the Google Sheet fallback wasn't missed, remove the Sheet path entirely (`get_google_sheet`, `GOOGLE_*` env vars, `gspread`/`google-auth` deps, the `/admin/data-update` page). Until Jon says the native flow has proven itself, no code removal.


---

## How to use this file

- **Working in one folder?** Open that folder's `TODOS.md` directly — it's self-contained.
- **Prioritising across the whole project?** Read this file. Each section summarises status; follow the link for detail.
- **Mid-conversation to-do captured?** Add it to the right area's `TODOS.md` (or the Data updates section above if it doesn't fit elsewhere) before ending the session.
