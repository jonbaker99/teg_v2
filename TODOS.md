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
LLM-powered tournament and round reports. Active agenda (Phases F–G backfill) and deferred items tracked in STATUS.md — that file *is* the to-do list for this area.

### Data updates — [below](#data-updates)
Tracked here (no sub-folder needed).

---

## Data updates

- [ ] Complete Phase F backfill: TEG 11 R3–R4, then TEGs 12, 13, 15, 16, 17 (tournament + 4 rounds each), TEGs 14 + 18 re-refresh. ~16 reports outstanding, ~$8. On hold pending layout/rules experiments settling.
- [ ] Pre-TEG-8 backfill (TEGs 1–7, ~$15.75): run after Phase F settled and pre-8 era-aware code verified.

---

## How to use this file

- **Working in one folder?** Open that folder's `TODOS.md` directly — it's self-contained.
- **Prioritising across the whole project?** Read this file. Each section summarises status; follow the link for detail.
- **Mid-conversation to-do captured?** Add it to the right area's `TODOS.md` (or the Data updates section above if it doesn't fit elsewhere) before ending the session.
