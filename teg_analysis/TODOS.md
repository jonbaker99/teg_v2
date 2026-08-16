# teg_analysis — To-dos

Analysis package todos. Commentary/reporting pipeline tracked separately in [`reporting/STATUS.md`](reporting/STATUS.md).

---

## TEG Reports

Full detail — including the report-by-report inventory and pipeline vintages — in
[`reporting/STATUS.md`](reporting/STATUS.md). Summary of what's left, in order:

**Decisions (blocking — do these first):**

- [x] **Settle the humour dial** — done 2026-08-15. Jon's verdict: "lacking a bit in humour". `humour6` (5-7 comic landings) folded into `prompts.VOICE_CORE`, along with an outright em-dash ban and a ~15-word average sentence target. **Still needs one from-scratch generation to validate** — the dial variants on disk were rewrites of finished reports, not cold generations.
- [ ] **Generate one TEG cold under the new voice and read it** (~$0.65) — validates humour6 + the em-dash ban end to end. Blocks the full regeneration.
- [ ] **Decide whether round reports are wanted** — ~50 outstanding, ~$32. `RoundStoryPlan` is no longer a blocker (ported 2026-08-11); this is purely scope and cost now.

**Then:**

- [ ] **Rebuild TEG 14's fixture chain** — missing `dry_draft.md` and `report_final.md`, so the two cheapest iteration loops are broken on the standing anchor case. One generation, ~$0.65.
- [ ] **Regenerate the stale tournament reports** — TEGs 2–8, 15, 16, plus 9. ~$6.50. Clears the pre-TEG-8 era framing in the published prose, the 81 wording faults D3 reports, and the three-vintage inconsistency in one pass.
- [ ] **Fix raw `SI n` leaking into published prose** — the writer prompt says translate stroke index into English ("the hardest hole on the course"). TEG 8's published report does both: "the easiest hole on the course" in some places, raw "the SI 2 last" / "the SI 1 8th" in 8 others. TEGs 4, 12 and 18 have zero, so it's per-run variance, not a dead rule. Reads as machine output. Candidate D3 check — mechanical and unambiguous.
- [ ] **Verify after regenerating** — `python -m teg_analysis.reporting.verify --all --rounds`; the error count is the acceptance test.
- [ ] **Trial voices through `write_from_dry`** — the swappable VOICE slot landed 2026-08-16 but no register has been run through it. Start with the house voice as a control, then the specific-to-loose ladder. Recipe ⑥ in `teg_analysis/reporting/ARTEFACTS.md`.
- [ ] **Trim `WRITER_SYSTEM`'s faithfulness block** — D3 now checks 6 of the 11 absolutes independently. Do it on evidence from fresh generations, not speculatively.
- [ ] **Read one regenerated round report before backfilling rounds** — the round writer adopted the current voice on 2026-08-15 (it had been stuck on the pre-Herron register; see `reporting/STATUS.md`). The change is untested on real output: generate one round, read it, then decide. The 17 published round reports are now stale on voice as well as on schema vintage.

**Fixed 2026-08-11** (detail in `reporting/STATUS.md` → Known issues): selection weights tuned to (1.5, 0.8, 0.7); voice and faithfulness split into separate prompt constants; D3 verification layer built; shared editor↔writer vocabulary schema-enforced (the close-finish hard rule had never fired); pre-TEG-8 era leak; round pipeline brought level; arc payload weighted for both competitions; TEG 10 R3 arithmetic error; 41 beat IDs in TEG 5's published report; model pinned to `claude-opus-5`; dead `enrich` path deleted.

## REST API

- [ ] Build out `teg_analysis/api/` — currently a placeholder. Goal: expose analysis layer over HTTP so scripts, mobile, and other frontends can call it without Python. Planned before Streamlit retirement.

## General

Nothing else currently outstanding. Package is clean post Phase 1–7 cleanup; all Streamlit imports removed.
