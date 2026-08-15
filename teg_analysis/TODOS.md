# teg_analysis — To-dos

Analysis package todos. Commentary/reporting pipeline tracked separately in [`reporting/STATUS.md`](reporting/STATUS.md).

---

## TEG Reports

Full detail — including the report-by-report inventory and pipeline vintages — in
[`reporting/STATUS.md`](reporting/STATUS.md). Summary of what's left, in order:

**Decisions (blocking — do these first):**

- [ ] **Settle the humour dial** — a 3 / 6 / 8 / 8b A/B was run on TEGs 14 and 18; outputs are on disk, unpublished, **no verdict recorded**. Pick a level, fold it into `WRITER_SYSTEM`, log it in `reporting/EXPERIMENTS.md`. Blocks all regeneration.
- [ ] **Decide whether round reports are wanted** — ~50 outstanding, ~$32. `RoundStoryPlan` is no longer a blocker (ported 2026-08-11); this is purely scope and cost now.

**Then:**

- [ ] **Rebuild TEG 14's fixture chain** — missing `dry_draft.md` and `report_final.md`, so the two cheapest iteration loops are broken on the standing anchor case. One generation, ~$0.65.
- [ ] **Regenerate the stale tournament reports** — TEGs 2–8, 15, 16, plus 9. ~$6.50. Clears the pre-TEG-8 era framing in the published prose, the 81 wording faults D3 reports, and the three-vintage inconsistency in one pass.
- [ ] **Verify after regenerating** — `python -m teg_analysis.reporting.verify --all --rounds`; the error count is the acceptance test.
- [ ] **Trim `WRITER_SYSTEM`'s faithfulness block** — D3 now checks 6 of the 11 absolutes independently. Do it on evidence from fresh generations, not speculatively.
- [ ] **Read one regenerated round report before backfilling rounds** — the round writer adopted the current voice on 2026-08-15 (it had been stuck on the pre-Herron register; see `reporting/STATUS.md`). The change is untested on real output: generate one round, read it, then decide. The 17 published round reports are now stale on voice as well as on schema vintage.

**Fixed 2026-08-11** (detail in `reporting/STATUS.md` → Known issues): selection weights tuned to (1.5, 0.8, 0.7); voice and faithfulness split into separate prompt constants; D3 verification layer built; shared editor↔writer vocabulary schema-enforced (the close-finish hard rule had never fired); pre-TEG-8 era leak; round pipeline brought level; arc payload weighted for both competitions; TEG 10 R3 arithmetic error; 41 beat IDs in TEG 5's published report; model pinned to `claude-opus-5`; dead `enrich` path deleted.

## REST API

- [ ] Build out `teg_analysis/api/` — currently a placeholder. Goal: expose analysis layer over HTTP so scripts, mobile, and other frontends can call it without Python. Planned before Streamlit retirement.

## General

Nothing else currently outstanding. Package is clean post Phase 1–7 cleanup; all Streamlit imports removed.
