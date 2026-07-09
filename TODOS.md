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

### Commentary (reporting pipeline) — [`teg_analysis/reporting/STATUS.md`](teg_analysis/reporting/STATUS.md) - and [`teg_analysis/reporting/reporting-to-do.md`](teg_analysis/reporting/reporting-to-do.md)
LLM-powered tournament and round reports. Active agenda (Phases F–G backfill) and deferred items tracked in STATUS.md — that file *is* the to-do list for this area.

### Data updates — [below](#data-updates)
Tracked here (no sub-folder needed).

### Codebase review remediation — [`REVIEW_PLAN.md`](REVIEW_PLAN.md)
Findings + batched execution plan from the 2026-07-09 review of `webapp/` and `teg_analysis/` (9 chats, ordered, with model tiers and three owner decisions). Temporary doc — deleted when all batches land.

---

## Data updates

**Data storage & mobile score-ingestion overhaul** — done; see [`DATA_STORAGE_INGESTION_PLAN.md`](DATA_STORAGE_INGESTION_PLAN.md) (kept as a historical/reference record) and `CLAUDE.md`'s "Current state & next steps" for the current-state summary. One item remains open:

- **Phase 4.2 decision gate (human, after a season of real Live round use):** if the native `/live-round` flow was used and the Google Sheet fallback wasn't missed, remove the Sheet path entirely (`get_google_sheet`, `GOOGLE_*` env vars, `gspread`/`google-auth` deps, the `/admin/data-update` page). Until Jon says the native flow has proven itself, no code removal.


---

## How to use this file

- **Working in one folder?** Open that folder's `TODOS.md` directly — it's self-contained.
- **Prioritising across the whole project?** Read this file. Each section summarises status; follow the link for detail.
- **Mid-conversation to-do captured?** Add it to the right area's `TODOS.md` (or the Data updates section above if it doesn't fit elsewhere) before ending the session.
