# teg_analysis — To-dos

Analysis package todos. Commentary/reporting pipeline tracked separately in [`reporting/STATUS.md`](reporting/STATUS.md).

---

## Finalise reporting pipeline

Full detail in [`reporting/STATUS.md`](reporting/STATUS.md). Summary of what's left:

- [ ] **Phase F backfill** — ~16 reports outstanding (TEG 11 R3–R4, TEGs 12/13/15/16/17 tournament + rounds, TEGs 14/18 re-refresh). ~$8. On hold pending layout/rules experiments settling.
- [ ] **Phase G backfill** — pre-TEG-8 era-aware reports (TEGs 1–7, ~$15.75). Code complete; backfill deferred until after Phase F settled.
- [ ] **Settle layout/rules experiments** — the on-hold blocker for the backfill runs.
- [ ] **TEG 10 R3 arithmetic fix** — "fourteen-point swing" should be "sixteen"; fix on next re-gen.

## REST API

- [ ] Build out `teg_analysis/api/` — currently a placeholder. Goal: expose analysis layer over HTTP so scripts, mobile, and other frontends can call it without Python. Planned before Streamlit retirement.

## General

Nothing else currently outstanding. Package is clean post Phase 1–7 cleanup; all Streamlit imports removed.
