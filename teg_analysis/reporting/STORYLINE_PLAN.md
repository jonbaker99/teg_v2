# Storyline-first reports — proposal

**Status:** proposal, not started. Written 2026-08-18 after a codebase review with Jon; not yet
actioned. Delete or fold into `STATUS.md` once Phase 1 lands or the approach is rejected — this file
is a working plan, not a permanent doc (see `CLAUDE.md` → Documentation rule 3).

## Situation

Reports are ~6.5/10. They explain how the tournament was won — that part works. Round-by-round
detail dominates every report regardless of what the editor plan chose, and subplots are buried or
absent.

**Confirmed against the actual artefacts, not just the prose:**

- 16 of 17 story plans (`data/commentary/teg_*_story_plan.json`) chose a non-chronological
  `narrative_structure` (`in_medias_res` ×7, `three_act` ×5, `theme_led` ×2, `chronological` only
  once — TEG 7).
- **16 of 17 finished reports shipped four `## Round N` sections anyway.** Only TEG 16 broke the
  pattern. The editor's structural choice is being overwritten downstream, not ignored at source.
- Three places do the overwriting, and fixing one alone changes nothing:
  1. `StoryPlan.rounds[]` (`story_plan.py`) is a **required** field with a per-round
     `chosen_headline` and `angle` — the plan is a round-by-round outline before the dry draft ever
     runs, whatever `narrative_structure` says.
  2. `DRY_DRAFT_SYSTEM_DETAILED` (`authoring.py`, the production default, A/B-settled) instructs
     "One section PER ROUND, in order, using the plan's `chosen_headline` as the heading" —
     `narrative_structure` is documented in `ARTEFACTS.md` as **deliberately ignored** at this stage.
  3. `render.py` injects deterministic per-round standings under `## Round N` markers, so
     round-by-round is the well-tested, low-friction path for both the writer and the renderer.
- Reports are already long: 1,700–2,300 words, plus two mandatory closing sections (`## How it was
  decided`, `## Player-by-player summary`). Adding storyline sections *on top of* rounds, rather than
  instead of them, is the most likely failure mode of this change.
- Nothing in the pipeline clusters beats across rounds today. Beats are scored individually
  (importance / rarity / entertainment in `scoring.py` / `events.py`); `vehicle_fit.py` scores named
  *frames* against the whole beat set, but nothing groups beats into a subject-based thread spanning
  rounds. That is very likely why subplots don't surface — there's no candidate list for the editor
  to draw one from, only individual beats and whole-tournament frame scores.

## Objective

Reports built around 2–4 chosen storylines, with round-by-round detail used only when a storyline
genuinely calls for it (expected: rare). The winner's story (`why_the_champion_won`, already
working) is always storyline 1. Length should not grow — storyline sections replace round sections,
not add to them.

## Where the proposal changes from what was asked

Two changes to the original framing, both from what the code already does:

1. **No new pipeline stage.** Stage 3 (the story plan, `story_plan.py`) already owns theme, frame,
   structure and beat triage in one LLM call. Storyline discovery is a missing responsibility of that
   stage, not a new stage before it — a fourth call adds ~$0.28, a new artefact, and a hand-off
   contract for a decision that stage already makes badly. Reordering the *fields* the LLM fills
   (structured output fills top-down) gets the ordering effect without a new call.
2. **Add free, deterministic beat clustering before the LLM call**, not just better prompting. The
   pipeline's own pattern (`vehicle_fit.py`, `win_anatomy.py`, `tournament_shape.py`) is: compute a
   candidate signal in Python, hand it to the editor as an advisory, let the editor decide. Subplot
   detection is the same shape of problem and belongs in the same layer, run before any prompt
   changes.

## Plan

### Phase 1 — thread detection (free, no LLM, no schema change)

New `teg_analysis/reporting/threads.py`. Cluster beats (from `assemble_bundle`'s `all_beats`) by
shared subject — player, hole/course, recurring failure mode — spanning 2+ rounds. Score each
cluster on round-span, summed entertainment, rarity, and *independence from the Trophy race* (a
cluster that's just the Trophy arc restated isn't a subplot). Emit `candidate_threads` into the
bundle, framed exactly like `vehicle_fit_hints`: a candidate list, not a verdict.

**Acceptance for Phase 1:** run it over all 17 TEGs, read the output, confirm it surfaces things a
human would call a subplot before writing a line of prompt or schema. No cost to iterate.

### Phase 2 — schema (`story_plan.py`)

Add to `StoryPlan`, positioned *before* `narrative_structure` and `rounds` (structured-output field
order matters — later fields can reference earlier ones):

- `storyline_candidates: list[Candidate]` — 6–8, cheap to generate, discarded downstream. Forces
  divergence before convergence and makes the cut auditable.
- `storylines: list[Storyline]` — **2–4 selected**, each: `subject`, `why_it_matters`, `shape`
  (setup → turn → resolution), `beat_ids`, `resolves_in`.
- Storyline 1 is always the lead and carries `why_the_champion_won` (unchanged, already works).
- `check_plan_consistency()` gains: at most one storyline per protagonist; at least one storyline not
  about the Trophy race.
- **`rounds[]` becomes optional**, populated only when `narrative_structure == "chronological"`
  (or when a storyline's `shape` genuinely needs round anchoring — the "unless it's clearly the best
  vehicle" case from the brief).

### Phase 3 — dry draft, split in two (`authoring.py`)

Section A: one block per storyline, hole-level evidence, in narrative order (setup → turn →
resolution) — not round order unless the storyline's shape is round order. Section B: a flat ledger
of every mandatory beat not consumed by a storyline. This preserves the dry draft's existing second
job — completeness and fact-checkability — which a pure storyline reorganisation would quietly lose,
weakening `verify.py`'s ability to check the finished prose against the facts.

### Phase 4 — writer (`authoring.py`, `render.py`)

Round-by-round becomes one structural option, not the chassis every draft defaults to. Add an
explicit word budget so storyline sections replace round sections rather than stack on them. Confirm
the consolidated "Standings by round" appendix (already built for non-`## Round N` reports) reads
well without round headings — TEG 16 is a free, existing test case for this, already in the corpus.

## How to know it worked

Every other dial in this pipeline (selection weights, humour, dry-draft detail level) was settled by
a blind A/B on a frozen upstream artefact, not by reading one report and deciding. Do the same here:
a short rubric (lead clarity, subplot presence and payoff, structure feels chosen not defaulted,
pace, factual integrity — the last one free, from `verify.py`) scored blind, old plan vs new plan, by
a fresh model with no memory of which is which.

**Test TEGs:**
- **14** — close finish, the hard rule fires, newest schema on disk already.
- **16** — already theme-led in production; the natural control, since it's the one existing report
  that didn't collapse into round-by-round.
- **18** — a procession, the longest report in the library (2,226 words) — the hardest case to make a
  storyline-first cut actually shorter.

## Explicitly out of scope for this proposal

- Round reports (`round_report.py` / `RoundStoryPlan`) — separate pipeline instance, not touched.
- Voice/register (`WRITER_VOICE`, humour dial) — already settled 2026-08-15, unrelated lever.
- Re-running the library regeneration — a separate outstanding item in `teg_analysis/TODOS.md`, not
  to be bundled with this until the storyline approach is validated on the 3 test TEGs above.
