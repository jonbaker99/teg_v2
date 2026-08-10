# teg_analysis — To-dos

Analysis package todos. Commentary/reporting pipeline tracked separately in [`reporting/STATUS.md`](reporting/STATUS.md).

---

## TEG Reports

Full detail — including the report-by-report inventory and pipeline vintages — in
[`reporting/STATUS.md`](reporting/STATUS.md). Summary of what's left, in order:

**Decisions (blocking — do these first):**

- [ ] **Settle the humour dial** — a 3 / 6 / 8 / 8b A/B was run on TEGs 14 and 18; outputs are on disk, unpublished, **no verdict recorded**. Pick a level, fold it into `WRITER_SYSTEM`, log it in `reporting/EXPERIMENTS.md`. Blocks all regeneration.
- [ ] **Decide the fate of `enrich_report_with_history()`** — built, documented, **zero callers**. Wire into `backfill.py` or delete. Same question, lower stakes, for `tighten_prose()`.

**Then:**

- [ ] **Fix the pre-TEG-8 era leak** — `events.hole_evidence()` attaches Stableford points to every hole regardless of era, so TEGs 5/6/7's reports frame the net-vs-par Trophy race in Stableford terms. Make it era-aware (`era.trophy_metric`), then regenerate.
- [ ] **Regenerate the stale tournament reports** so the library is one vintage — TEGs 2–8, 15, 16 predate the narrative-vehicle/payoff work and TEG 9 is partial. 10 reports, ~$6.50. (Tournament *coverage* is already complete: TEGs 2–18 is the full set, there is no TEG 1 in the data.)
- [ ] **Round reports — decide whether they're wanted.** If yes: port narrative vehicles + payoffs to `RoundStoryPlan` first (it's a generation behind `StoryPlan`), then backfill the 50 outstanding rounds (~$32; the Batch API item in STATUS.md would roughly halve that).
- [ ] **TEG 10 R3 arithmetic fix** — "fourteen-point swing" should be "sixteen"; fixes itself on re-gen.

## REST API

- [ ] Build out `teg_analysis/api/` — currently a placeholder. Goal: expose analysis layer over HTTP so scripts, mobile, and other frontends can call it without Python. Planned before Streamlit retirement.

## General

Nothing else currently outstanding. Package is clean post Phase 1–7 cleanup; all Streamlit imports removed.
