# teg_analysis — To-dos

Analysis package todos. Commentary/reporting pipeline tracked separately in [`reporting/STATUS.md`](reporting/STATUS.md).

---

## TEG Reports

Full detail — including the report-by-report inventory and pipeline vintages — in
[`reporting/STATUS.md`](reporting/STATUS.md). Summary of what's left, in order:

**Decisions (blocking — do these first):**

- [ ] **Storyline-first reports** — proposal in [`reporting/STORYLINE_PLAN.md`](reporting/STORYLINE_PLAN.md), not started. Reports are ~6.5/10: round-by-round detail dominates regardless of what the story plan's `narrative_structure` chose (16/17 plans picked non-chronological, 16/17 finals shipped `## Round N` anyway), and subplots are buried or absent. Plan: free beat-clustering pass (`threads.py`, new) to surface candidate subplots, then restructure `StoryPlan` around 2–4 chosen `storylines[]` with `rounds[]` made optional. Independent of the humour-dial / regeneration items below — do not bundle.
- [x] **Settle the humour dial** — done 2026-08-15. Jon's verdict: "lacking a bit in humour". `humour6` (5-7 comic landings) folded into `prompts.VOICE_CORE`, along with an outright em-dash ban and a ~15-word average sentence target. **Still needs one from-scratch generation to validate** — the dial variants on disk were rewrites of finished reports, not cold generations.
- [ ] **Generate one TEG cold under the new voice and read it** (~$0.65) — validates humour6 + the em-dash ban end to end. Blocks the full regeneration.
- [ ] **Decide whether round reports are wanted** — ~50 outstanding, ~$32. `RoundStoryPlan` is no longer a blocker (ported 2026-08-11); this is purely scope and cost now.

**Then:**

- [ ] **Re-style the whole library, and don't forget it again** — the 2026-08-13 regeneration ran `style=False`, so **16 of 17 `*_report_styled.md` files still hold pre-regeneration prose and that is what the site serves.** Free, deterministic, idempotent; bundle it with the regeneration below. Verified 2026-08-17.
- [ ] **Regenerate the library** — all of 2–18, ~$11. Not just "the stale ones": every report predates the 2026-08-15 readability decision, so this is a full pass. Clears the 566 em-dash warnings.
- [ ] **Fix raw `SI n` leaking into published prose** — the writer prompt says translate stroke index into English ("the hardest hole on the course"). TEG 8's published report does both: "the easiest hole on the course" in some places, raw "the SI 2 last" / "the SI 1 8th" in 8 others. TEGs 4, 12 and 18 have zero, so it's per-run variance, not a dead rule. Reads as machine output. Candidate 9th D3 check — mechanical and unambiguous.
- [ ] **Verify after regenerating** — `python -m teg_analysis.reporting.verify --all --rounds`; the error count is the acceptance test. Baseline as of 2026-08-17: **0 errors on all 17 tournament reports**, 4 errors in round reports, 566 em-dash warnings.
- [ ] **Trial voices through `write_from_dry`** — the swappable VOICE slot landed 2026-08-16 but no register has been run through it. Start with the house voice as a control, then the specific-to-loose ladder. Recipe ⑥ in `teg_analysis/reporting/ARTEFACTS.md`.
- [ ] **Trim `WRITER_SYSTEM`'s faithfulness block** — D3 now checks 6 of the 11 absolutes independently. Do it on evidence from fresh generations, not speculatively.
- [ ] **Read one regenerated round report before backfilling rounds** — the round writer adopted the current voice on 2026-08-15 (it had been stuck on the pre-Herron register; see `reporting/STATUS.md`). The change is untested on real output: generate one round, read it, then decide. The 18 published round reports are stale on voice as well as on schema vintage, and hold the only 4 D3 errors left in the library.
- [ ] **Decide what to do with `reply.txt`** at the repo root — a complete unpublished TEG 17 report, committed by accident in `aafad8b`. Either promote it into `data/commentary/variants/` as the plan-usage half of the quality comparison, or delete it. Don't leave it tracked at the root.
- [ ] **Bring `TIGHTEN_SYSTEM` in line with the em-dash ban, or delete the pass** — it still sets a two-per-paragraph ceiling and still licenses long sentences, the two clauses removed from `_WRITER_ECONOMY` on 2026-08-15. Nothing calls it, so this is dormant rather than broken. `reporting/STATUS.md` known issue 19.

**Done 2026-08-15** (were on this list): rebuild TEG 14's fixture chain — done by the TEG 14 regeneration, all four artefacts present. **Done 2026-08-13**: regenerate the stale tournament reports (2–8, 15, 16, 9) — the whole library went to one vintage, which also cleared the pre-TEG-8 era framing and all 81 D3 wording faults.

**Fixed 2026-08-11** (detail in `reporting/STATUS.md` → Known issues): selection weights tuned to (1.5, 0.8, 0.7); voice and faithfulness split into separate prompt constants; D3 verification layer built; shared editor↔writer vocabulary schema-enforced (the close-finish hard rule had never fired); pre-TEG-8 era leak; round pipeline brought level; arc payload weighted for both competitions; TEG 10 R3 arithmetic error; 41 beat IDs in TEG 5's published report; model pinned to `claude-opus-5`; dead `enrich` path deleted.

## REST API

- [ ] Build out `teg_analysis/api/` — currently a placeholder. Goal: expose analysis layer over HTTP so scripts, mobile, and other frontends can call it without Python. Planned before Streamlit retirement.

## General

Nothing else currently outstanding. Package is clean post Phase 1–7 cleanup; all Streamlit imports removed.
