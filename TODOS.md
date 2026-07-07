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

---

## Data updates

**Data storage & mobile score-ingestion overhaul** — [`DATA_STORAGE_INGESTION_PLAN.md`](DATA_STORAGE_INGESTION_PLAN.md). Architecture review (Fable) recommends keeping the Railway volume + GitHub sync (hardened, not replaced) and building a native mobile round-entry page to replace Google Sheets as the capture step. Phased plan with per-step model tags and ready-to-use kick-off prompts. Status: Phase 0 not started. Also supersedes `DATA_RATIONALISATION_PLAN.md`'s open investigation (resolved at Phase 1.5).


---

## How to use this file

- **Working in one folder?** Open that folder's `TODOS.md` directly — it's self-contained.
- **Prioritising across the whole project?** Read this file. Each section summarises status; follow the link for detail.
- **Mid-conversation to-do captured?** Add it to the right area's `TODOS.md` (or the Data updates section above if it doesn't fit elsewhere) before ending the session.
