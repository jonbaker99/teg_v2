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

## Phase 1 result (2026-08-18) — built, run over all 17 TEGs, verdict: not sufficient alone

`threads.py` built and wired into `assemble_bundle()` as `candidate_threads`. No schema or prompt
change; `check_plan_consistency`/`SYSTEM_PROMPT` untouched. 130 reporting tests still pass.

**What it does well.** The `course` cluster (fires only when a TEG repeats a course across rounds —
TEGs 12, 14, 17, 18) is a genuine find: it groups beats a human wouldn't otherwise connect, because
nothing else in the pipeline compares a player's two visits to the same course within one TEG. The
`failure_mode` cluster (a player's cold-stretch/collapse beats specifically, not their whole beat
list) is differentiated enough to read as a real recurring pattern rather than a beat dump.

**What it doesn't do.** The `player` cluster — by far the largest group, one per player per TEG — is
just "every notable beat this player had," which fires for nearly everyone in every TEG (6-8
candidates per TEG, most of them player clusters). That's not a subplot, it's an index. A human
reading the ranked list would reject most of the top entries as "that's just what happened to them,"
not "here's a thread." Confirms the doubt raised before this ran: **round-span + summed scores finds
volume, not narrative shape** — it can't tell "recurring pattern with a turn" from "player had a
below-average tournament with several bad holes," and most players have the latter.

**Consequence for Phase 2.** Ungate the schema/prompt work on this clustering being sufficient on its
own — it isn't. Two live options, not mutually exclusive:
1. Feed `candidate_threads` to the editor as a *trimmed* advisory (drop bare `player` clusters
   entirely, or require them to pass a shape test — e.g. contains a `long_lead_lost`/`recovery`
   pair, not just a volume of beats) and let the LLM pick from a shorter, more honest list.
2. Test the LLM's own subplot-finding ability directly — with and without the `candidate_threads`
   hint — against a rubric, the way the humour dial and vehicle-fit questions were settled (blind
   A/B, `EXPERIMENTS.md` pattern). This answers Jon's actual question (2026-08-18): can an LLM spot
   compelling storylines at all, hinted or cold, before spending more effort improving the
   deterministic signal that feeds it.

Not yet done: the A/B in option 2. That's the next step, not Phase 2's schema change.

## Detection fixes before the A/B (2026-08-18)

Jon's call: fix detection gaps first, so the A/B tests the LLM against a real candidate pool, not a
handicapped one.

1. **Stretch detectors simplified to one hot + one cold per metric.** See `events.py` /
   `STATUS.md` (2026-08-18 entry) for the change and the balance regression it caused and fixed.
2. **Round-by-round gap-to-leader for every player — built.** `_trajectory_beats` (`events.py`)
   emits `gap_closed` / `position_reversal` beats for every non-winning player, both Trophy and
   Green Jacket. Confirmed firing real material on TEGs 14/16/18 (e.g. TEG 14: Gregg Williams
   closing an 18-point Jacket deficit to 8; TEG 18: Alex Baker fading from 2nd to 5th in the
   Jacket after R1). Not yet re-run through `threads.py`'s scoring formula specifically for these
   types — they currently just add to whichever player cluster they belong to.

## A/B result (2026-08-18) — cold wins, 3 for 3; hints hurt grounding, not discovery

Built `scripts/storyline_experiment.py`: three arms (`cold` = raw beats + arcs only; `hinted` = cold
+ `win_anatomy` + `candidate_threads`; `fallback` = hinted + an explicit "zero discovered storylines
is fine" instruction), each producing a mandatory trophy/jacket/spoon storyline plus 1–3
independently-discovered ones, judged blind by a fourth call against lead clarity, subplot quality,
"chosen not defaulted", and factual integrity (checked against the raw beats, not taken on trust).
Run on TEGs 14, 16, 18 — one run per arm, so directional, but consistent all three times:

| TEG | Ranking | Cold factual score | Hinted / fallback factual score |
|---|---|---|---|
| 14 | cold > hinted > fallback | 8 | 5, 4 |
| 16 | cold > fallback > hinted | 8 | 5, 5 |
| 18 | cold > fallback > hinted | 8 | 5, 6 |

**Discovery, not grounding, was never the problem.** All three arms independently converged on the
same core storylines every TEG — the champion's story, a redemption/collapse subplot, a
course-record collision, a quiet-achiever thread. `candidate_threads` and `win_anatomy` added no
storylines the cold model didn't already find on its own.

**What the hints actually did was degrade factual grounding.** Hinted/fallback consistently invented
specifics the beats don't support — head-to-head round records, precise gaps, course-visit counts,
"best in the field" claims — that cold didn't. The mechanism the judge kept naming: more material in
context gives the model more surface to *compute* a plausible-sounding derived number from, rather
than citing a fact that's actually in the data. Hinted/fallback's `discovered_storylines` also
repeatedly just re-described the guaranteed Jacket/Spoon story instead of finding something distinct
— padding, not real discovery. Cold was the only arm to consistently surface a genuinely separate
angle each time (Prince's two decisive holes as protagonists, a brothers' mid-tournament reversal).

**Verdict: drop the hint-feeding approach.** `candidate_threads`/`win_anatomy` don't belong in the
storyline-*discovery* prompt. (Whether they have a role as a post-hoc fact-checking pass is a
separate, unexplored question — not tested here.) The guaranteed trophy/jacket/spoon + discovered
structure worked as designed: solid baseline material every time, and the self-rated
`compelling_score` tracked something real (Jacket scored 6, the weakest story, in 2 of 3 TEGs).

## Phase 2, revised (2026-08-18) — cold discovery, then a separate per-storyline telling pass

Two things the A/B didn't yet solve, both raised by Jon: (a) finding a storyline isn't the same as
telling it well — the plan needs to hand the writer more than `subject`/`shape`, and (b) even cold's
factual score was 8, not 10 — some invention (a fabricated weekday, a misattributed hole) survived
even without hints. Revises the original schema-only Phase 2 sketch above with what the A/B actually
learned.

### 2a. Discovery call — cold bundle, StoryPlan schema gains the experiment's shape

Replace `story_plan.py`'s current per-round outline with the A/B's schema: mandatory
`trophy_storyline` / `jacket_storyline` / `spoon_storyline` + `discovered_storylines` (1–3, can be
zero). **Bundle for this call stays cold** — beats + arcs only. Drop `candidate_threads` and
`win_anatomy` from what reaches it; the measured result is they don't help this step and do harm.
(`vehicle_fit_hints` is a different axis — frame choice, not subject discovery — untested here,
leave as is pending its own check.)

### 2b. Telling call — separate, per storyline, narrow context

Jon's ask: the LLM that finds a storyline should also work out the compelling *bullet-point* version
of telling it — an outline the writer follows, not just a subject line. Building this as a **second,
per-storyline call** rather than folding it into 2a, on direct evidence from the A/B: the hallucination
this run measured scaled with how much context the model had to reach into for a claim. A telling call
that sees *only* the hole-level evidence for that storyline's own `beat_ids` (not the whole bundle,
not other storylines) has no material available to invent a head-to-head record from — it can only
restate what's actually in the beats it was handed. This mirrors the pattern that already works
elsewhere in the pipeline (the dry draft's hole-level-evidence-only citation rule).

Output: `telling: list[str]` — ordered bullets (setup → turn → resolution beats, what to emphasise,
where the punch line lands), each anchored to a specific `beat_id` already in the storyline. A rule
in the same prompt: **no comparative or aggregate claim** ("beat X in N of M rounds", "Nth visit to
this course") **unless the literal number is present in the evidence handed to this call** — the
exact failure mode the A/B measured, named explicitly rather than left implicit.

Costs 4–6 more calls per TEG (one per storyline) instead of folding into 2a's single call — the
tradeoff against Jon's simpler one-call framing, made deliberately on the A/B's evidence rather than
by default. Worth re-testing whether 2a+2b combined into one call reproduces the same grounding once
2a's bundle is cold — possible, since context breadth (not call count) was the measured variable —
but split-and-narrow is the safer default until that's checked.

### 2c. Grounding guardrails (free, deterministic, do these regardless of 2a/2b's outcome)

1. **`beat_ids` existence check.** Add to `check_plan_consistency`: every `beat_id` cited anywhere in
   the plan must exist in the bundle handed to that call. Catches a hallucinated citation for free,
   before any prose is written on top of it — cold's residual errors (misattributed hole, invented
   weekday) were exactly this class of thing.
2. **A named faithfulness rule** for the writer stage: comparative/aggregate claims (head-to-head
   records, "Nth visit", "best in the field in round N") must trace to a bundle field, never be
   computed from memory of individual beats. Same rule 2b's telling-call prompt carries, promoted to
   `WRITER_FAITHFULNESS` so it also guards prose written *outside* this pipeline's own tellings.
3. **Stretch, not required for Phase 2**: extend `verify.py` (D3) to parse numeric claims in finished
   prose near a cited beat and check them against that beat's own evidence fields. Harder to build
   reliably (free-text parsing) — worth doing once 2a/2b are live and there's real prose to check it
   against.

### Phase 3 / 4 (dry draft, writer) — unchanged in shape from the original sketch above, now consume
2a's storylines + 2b's tellings instead of round outlines. Not re-detailed here; revisit once 2a/2b
are built and read.

### 2a/2c built and validated (2026-08-18)

Built on a new branch (`claude/storyline-first-reports`). Landed the `DraftedStoryline` model and
`trophy_storyline` / `jacket_storyline` / `spoon_storyline` / `discovered_storylines` on `StoryPlan`,
replacing `competition_storyline_bullets` / `player_storyline_bullets` / `decisive_moments` — found to
be **dead code** in the process (zero downstream readers anywhere in the codebase; a prior unfinished
attempt at the same idea). Added the `beat_ids`-exist grounding check to `check_plan_consistency`.

**Hit the API's structured-output size limit** adding the new fields on top of the existing schema
("compiled grammar is too large"). Fixed by trimming `Competition.how` / `Competition.key_beat_ids` —
also unused downstream (`render.py`'s at-a-glance box only reads `name`/`winner_or_loser`) and now
duplicated by the new storylines' `shape`/`beat_ids` anyway, so this was a second dead/redundant
pocket found by the same change, not a workaround.

**Validated the same way Phase 1 was** — real `build_story_plan()` runs (not the standalone
experiment script) on all 3 test TEGs, live API calls, checked against `check_plan_consistency`:

| TEG | Grounding warnings | Discovered storylines |
|---|---|---|
| 14 | 0 | Alex Baker's runner-up "ledger of catastrophes"; Gregg Williams's unrewarded personal best |
| 16 | 0 | "The twelfth hole" (3 separate blow-ups at the same hole number); Mullin's Penha Longa→Estoril reversal |
| 18 | 0 | The Stadium course record rendered pointless; the Baker brothers at opposite ends of the tournament; Camiral's catalogue of catastrophe |

Zero grounding warnings across all three, and every discovered storyline reads as genuinely distinct
from its TEG's trophy/jacket/spoon story — matches or beats the standalone experiment's cold-arm
quality, produced from the full production bundle (not the experiment's stripped-down cold context),
confirming prompt-level discipline ("don't use `win_anatomy`/`candidate_threads` to find the subject")
holds even with those still present in context for other schema fields.

### 2b A/B result (2026-08-18) — no measurable effect; found a bigger leak instead

Built `scripts/storyline_telling_experiment.py`: for TEG 14's 5 storylines (trophy/jacket/spoon + top
2 discovered), ran 2b's telling call (narrow context — only that storyline's own cited beat evidence)
into a minimal writer, against the same writer given no telling. Blind judge, A/B order randomised
per storyline, scored on compellingness/clarity/factual_grounding/reads-as-story.

**Result: a wash.** 3 storylines favoured `with_telling`, 2 favoured `without_telling`; averaged
scores across all 4 axes differ by 0.0–0.4 points, well inside noise for one TEG. 2b is not earning
its extra call on this evidence.

**What the judge actually flagged is more important than the with/without question.** In every one of
the 5 pairs, **both** arms — with telling and without — asserted specific facts absent from the
narrow evidence handed to the writer: "87 at Deal / 85 at Littlestone", "beat Baker head-to-head in 3
of the 4 rounds", "the fourth hole", a "Trophy" reference inside the Jacket storyline, a day name
("on Saturday") nowhere in any evidence. Same fabrications, same rate, in both arms — because **both
writer calls also receive the storyline's own `why_it_matters` and `shape` text**, generated by 2a
from the FULL bundle, and those free-text fields are where the invented specifics actually live. 2b's
narrow-context isolation only applies to the *telling* step; the *writer* step still reads
un-isolated prose from 2a, so nothing about 2b prevents the leak it was designed to guard against.

**This means 2c's grounding check has a real gap.** `check_plan_consistency`'s `beat_ids`-exist check
(built this session) passed with 0 warnings on TEGs 14/16/18 — but that only verifies the *citations*
exist, not that the *prose* in `why_it_matters`/`shape` is itself traceable to them. TEG 14's
`jacket_storyline.why_it_matters` — "Mullin beat Jon Baker head-to-head in 3 of the 4 rounds" — is
exactly the comparative-claim failure mode the 2a prompt explicitly forbids, and it passed every
check built so far. The "0 grounding warnings" reported earlier in this doc is real but narrower than
it read at the time: beat_id citations are clean, free-text prose is not verified at all.

**Recommendation, not yet built:** the fix is upstream of 2b, not inside it — either (a) strip
`why_it_matters`/`shape` from what the writer/telling steps receive, forcing every downstream claim
to be reconstructed from `beat_ids`' own evidence only (cheap, testable), or (b) extend 2c to check
numeric/comparative claims in the free-text fields against the bundle, not just that citations exist
(harder — free-text parsing). (a) is the natural next experiment: same harness, same TEG, one more
arm.

### Round 2 (2026-08-18) — confirmed: the fix is fact isolation, not 2b itself

Re-ran the same 5 storylines with the writer stripped of `why_it_matters`/`shape` in BOTH arms —
only `subject` (a label) + `evidence` (+ `telling` for the with-telling arm) reach the writer now.
Jon's framing (same session): discovery (i) and arcs (ii) can use full context to judge what's
compelling, but the writer (iv) must only ever quote facts from the evidence bundle (iii), never
from i/ii's own prose.

**Grounding jumped in both arms**, confirming the leak was exactly what round 1 identified:

| | Round 1 (shape/why_it_matters visible to writer) | Round 2 (stripped) |
|---|---|---|
| `with_telling` factual_grounding | 6.2 | **8.4** |
| `without_telling` factual_grounding | 6.0 | **7.4** |

Remaining errors dropped from invented head-to-head records and scores from nowhere to minor
phrasing stretches ("16th-best winning total" for an `all_time_rank: 16` field, one hole's stroke
index called "gentlest" rather than precisely "second-easiest") — real but much lower-stakes.

**2b (telling) itself: still a wash**, now cleanly isolated. 3-2 `without_telling` this round (3-2
`with_telling` last round) — noise, not signal, both times. `compellingness`/`reads_as_story`
slightly favoured `without_telling` this round, `factual_grounding` favoured `with_telling`. Sample
too small (5 storylines, 1 TEG) to call either way, and the effect size either way is smaller than
the fact-isolation effect by an order of magnitude.

**Conclusion — validates Jon's ordering with one correction:** i (discover, full context) → ii
(optional telling, narrow context) → iii (facts) → iv (write, facts-only). The load-bearing fix is
**iv never seeing i's free-text prose**, not whether ii runs. 2b can be added later purely as a
polish lever (it's free to build, already works, just not proven to matter yet) — it is not a
prerequisite for the grounding fix, which is cheaper: strip `why_it_matters`/`shape` from any writer
context.

### 2b verdict, 3 TEGs (2026-08-18) — drop it. `without_telling` wins, consistently

Re-ran the fact-isolated harness (writer sees only `subject` + raw evidence, `telling` only in that
arm) on TEGs 16 and 18, adding to TEG 14's round 2 — 15 storylines total, same methodology
throughout.

**`without_telling` won 10 of 15 pairs** (TEG 14: 3-2, TEG 16: 3-2, TEG 18: 4-1) — consistent
direction across all three TEGs, not noise. Averaged scores:

| axis | with_telling | without_telling |
|---|---|---|
| compellingness | 7.4 | **8.0** |
| clarity | 7.87 | **8.0** |
| factual_grounding | **8.07** | 7.6 |
| reads_as_story_not_list | 7.07 | **8.27** |

**Mechanism, from the judge notes:** `without_telling` compresses the same evidence into a
"characterised sequence" or a deliberate three-beat structure the writer builds itself; `with_telling`
tends to work through the telling's own bullet order fact-by-fact, which reads closer to a list even
when instructed not to. `with_telling` keeps a real edge on `factual_grounding` — the telling step's
narrow, evidence-anchored bullets are genuinely precise (stroke indexes, exact point tallies) and the
writer inherits that precision — but it costs narrative flow, and by a bigger margin than it gains on
accuracy.

**Verdict: skip 2b.** The fact-isolation fix (this doc, round 2) already delivers most of the
grounding gain on its own, for free — no extra call. 2b adds a call, adds precision, and *reduces*
how much a storyline reads as a story, which is the opposite of Phase 2's actual goal. Not
worth building into the pipeline on this evidence. If grounding regresses once this runs through the
real writer (richer voice constraints, longer prose, more storylines at once), 2b is the documented
fallback — the code exists (`scripts/storyline_telling_experiment.py`), it's just not the default.

**Not yet done:** wiring the fact-isolation fix into `check_plan_consistency` / the real
dry-draft-and-writer pipeline (Phase 3/4) — the three-TEG experiment above used a standalone minimal
writer, not the production `authoring.py` writer, and `rounds[]` still drives report structure today.

## Full-report proof + user's 3-point punch list (2026-08-19)

`scripts/storyline_full_report_experiment.py` proved the pipeline end-to-end (structural draft →
`authoring.restyle_voice`) on TEG 14, and the plain "straight" draft (no voice pass, `--no-voice`)
read strong on TEGs 16/18 too — "The twelfth hole" (TEG 16, both Baker brothers blowing up the same
hole on two different courses) and "The brothers Baker at opposite ends of the same tournament"
(TEG 18) are storylines a round-by-round report would never surface. Full detail and read of all
three drafts: see the STATUS.md entry dated 2026-08-19.

Reviewing that output, Jon raised three points, tackled in order:

**1. Records/streaks weren't guaranteed to reach the beat layer — closed.** Course records were
already wired into `beats` as mandatory (`course_history.py`). All-time streak records
(`analysis/streaks.py`) and TEG-total score-count records (`analysis/records.py`) — both already
computed for the webapp Records page — were not. New `milestone_records.py` wraps both as `sr*`/`sc*`
mandatory beats, same wiring pattern as `course_history.py`. This guarantees these facts are
*mentioned*; it does not yet guarantee they *drive* a storyline — that's addressed by the "records
are legitimate storyline subjects" guidance added in point 2 below (SYSTEM_PROMPT), not by new code.

**2. Storyline quality bar + fallback ladder — added to `story_plan.py`'s `SYSTEM_PROMPT` and
schema.** Jon's framing: "how each trophy was won" (`trophy_storyline`/`jacket_storyline`/
`spoon_storyline`, always populated) always leads; `discovered_storylines` is the default
enrichment; `player_by_player`/`round_by_round` are fallbacks that sit at the SAME tier as each
other and BELOW discovered-storylines — used only when nothing clears the bar, never above it.

- `DraftedStoryline` gained `humour_score` (1-10, self-rated like `compelling_score`). SYSTEM_PROMPT
  requires at least one storyline in the report to score `humour_score >= 7`; `check_plan_consistency`
  surfaces a warning (not a hard failure — some tournaments genuinely have no funny material) when
  none does.
- SYSTEM_PROMPT now states the quality bar explicitly: "spans 2+ rounds and has beats" is the
  eligibility floor, not the bar — a storyline must deliver humour, intrigue, drama, or importance to
  be included, and a technically-grounded-but-flat storyline should be left out even if it's the only
  candidate.
- New `sr*`/`sc*`/`cr*` mandatory beats (records) are explicitly called out as legitimate storyline
  SUBJECTS ("Anatomy of a TEG record"), not just facts that need a mention.
- New `StoryPlan.body_fallback: Literal["none", "player_by_player", "round_by_round"] = "none"`.
  `check_plan_consistency` warns if a fallback is chosen while `discovered_storylines` already has
  2+ entries (contradicts the tiering). Wired into `scripts/storyline_full_report_experiment.py`'s
  `_fallback_sections()`: when the editor sets a non-`"none"` fallback, sections are built
  **deterministically** from grouped raw beats (by player, or by round) — same fact-isolation
  principle as everywhere else in this pipeline; the editor's job is the structural call, not
  authoring a second unverified "shape" for the fallback content.

**Bug found and fixed live on TEG 14 (2026-08-19): `candidate_threads` leaked beat IDs outside the
trimmed bundle.** `candidate_threads` (`threads.py`) is deliberately scored from `all_beats`
(untrimmed) — same reasoning as `vehicle_fit_hints` — but its `beat_ids` were never filtered back down
to the trimmed `beats` actually sent to the model. On TEG 14 the editor read beat IDs straight out of
`candidate_threads` and cited them in four different storylines' own `beat_ids`; none of those IDs
existed in the bundle the model was given. `check_plan_consistency`'s grounding check caught it
correctly ("cites unknown beat_ids") — the bundle handed the model phantom IDs to begin with, not a
new failure of the check. Fixed in `assemble_bundle`: threads now get their `beat_ids` filtered to the
in-bundle set immediately after `detect_threads` runs, and any thread left with zero beats is dropped.
Regression test: `test_candidate_threads_never_cite_beats_outside_the_bundle`
(`tests/test_reporting_schema_and_era.py`). Re-ran TEG 14 live after the fix: zero grounding warnings.
Pre-existing bug, not introduced by the Call A/B split — `candidate_threads` has worked this way since
Phase 1; it simply hadn't been exercised enough times to surface until now.

**Validated live on TEGs 14 and 16.** First call truncated: the new `humour_score`/`body_fallback`
fields pushed StoryPlan's structured-output length over `generate_structured`'s default
`max_tokens=16000` (a `pydantic.ValidationError: EOF while parsing a string` — the JSON was cut off
mid-string, not a schema-shape problem). Fixed by raising the `build_story_plan` call site to
`max_tokens=20000` (tested 24000 first — the Anthropic SDK requires streaming above some threshold
and threw before the request was even sent, so 20000 is the safe number, not an arbitrary one).

Both TEGs then came back with zero `check_plan_consistency` warnings. Humour requirement: real spread,
not every storyline padded to a high score (TEG 14: 3, 4, 5, 8, 8; TEG 16: 4, 5, 5, 8, 9) — both
tournaments' Wooden Spoon storyline scored highest, matching the SYSTEM_PROMPT's own prediction that
disaster is usually the funny one. `body_fallback` was `"none"` both times (discovered_storylines
cleared the bar on its own) — the fallback path itself is still unexercised on real output; worth
checking on a TEG where discovery genuinely comes up empty before calling it proven.

**The actual payoff, unprompted:** TEG 16's `discovered_storylines` included *"Anatomy of an 80:
Mullin's Estoril course record, two days after Penha Longa took him apart"* — built from the `cr*`
course-record beat this session wired in under point 1, exactly the "records driving a storyline"
outcome Jon asked for, without any code beyond the SYSTEM_PROMPT guidance above.

**3. Interweaving storylines instead of running them as separate sections — not started.** Flagged
by Jon as worth trying despite the added complexity risk (clarity vs. richness trade-off). Deferred
to its own fresh-context chat per the session's own advice (see chat history) — it's a different kind
of problem (narrative ordering, not fact-grounding or discovery) and the most exploratory of the
three, so cleanest to explore once 1 and 2 have landed as the new baseline to interweave *from*.

## Call A / Call B split, and the writer-richness gap (2026-08-19)

Two follow-ups from reading the TEG 14/16/18 output: Jon noticed the `max_tokens` fix (16000 →
20000, previous section) was patching a symptom, and separately asked whether the storyline-first
writer has access to the same richness of context the legacy pipeline's writer does.

**Diagnosis, not assumption — checked against the code.** `StoryPlan` carries every field the
LEGACY round-by-round pipeline needs (`rounds[]`, `players[]`, `must_include_beat_ids`, `cuts`,
`venue_notes`, `course_history_notes`, `foreshadow`, `payoffs`, `narrative_structure`) even though
`scripts/storyline_full_report_experiment.py` reads none of them — only
`trophy_storyline`/`jacket_storyline`/`spoon_storyline`/`discovered_storylines`/`body_fallback`. That
dead weight, not the humour/fallback additions alone, is most of what pushed the call over budget.

**The split ("Call A" / "Call B").** New `StorylinePlan` (in `story_plan.py`, right after
`check_plan_consistency`) is the same underlying bundle/beats as `StoryPlan` — an OUTPUT-schema split,
not an input split; both would see identical `beats`/`player_course_history`/`win_anatomy`/etc. Only
what each is *asked to produce* differs. `StorylinePlan` keeps: title/theme/tone, `opening_hook`,
`narrative_vehicles`, `competitions` (name/winner only), the three anatomy storylines,
`discovered_storylines`, `body_fallback`, `prominent_vehicle`/`prominent_palette`/
`vehicle_fit_response`, `why_the_champion_won`, `storyline_note`. A trimmed `STORYLINE_SYSTEM_PROMPT`
drops the round-plan/must-include/venue-notes/payoffs instructions and adds an explicit **MANDATORY
BEAT COVERAGE** rule in their place: every `mandatory: true` beat must appear in *some* storyline's
`beat_ids`, checked by new `check_storyline_plan_consistency` (replaces the `must_include_beat_ids`/
`cuts` check, which doesn't apply to this schema). New `build_storyline_plan()` writes
`teg_{n}_storyline_plan.json` — a distinct filename from `build_story_plan`'s
`teg_{n}_story_plan.json`, so this doesn't clobber the file the legacy pipeline reads.
`storyline_full_report_experiment.py` now calls `build_storyline_plan` directly (Call A only) instead
of reading a pre-generated `StoryPlan` off disk — **`StoryPlan`/`SYSTEM_PROMPT`/`build_story_plan` are
untouched**, still serving the legacy pipeline, and this prototype never calls them.

Validated: imports cleanly, `dry_run=True` assembles the prompt+bundle without an API call (TEG 16:
53 beats, 94183 user-message chars), 53/53 unit tests still pass. **Not yet validated with a live
call** — the Anthropic API usage limit was hit immediately after this landed (`account has reached
its specified API usage limits, resets 2026-09-01`). Blocked until then, or until run through
`--plan`/`--paste` mailbox mode instead of the direct API.

**The writer-richness gap (raised by Jon, not yet addressed by code).** Separate from the plan split:
the LEGACY writer (`authoring.py`) re-injects raw bundle context — `venue`, `player_history`,
`player_course_history`, `player_relationships`, `win_anatomy`, `tournament_shape`
(`BUNDLE_CONTEXT_KEYS`, `authoring.py:168`) — directly into the prose prompt, on top of the plan. The
storyline-first `draft_section()` writer gets none of that: only `evidence`, the beats a storyline's
`beat_ids` cited. Deliberate (the 2b fact-isolation fix), but a real narrowing — course-history colour
that never became a beat (ordinary Nth-visit notes, non-record deltas) cannot reach the page, only
`cr*`/`sr*`/`sc*` records can. Proposed next step: a fourth writer variant that gives `draft_section`
read-only access to the same *structured, numbers-only* context `authoring.py`'s `bundle_context="data"`
style already produces (stripped of derived prose), A/B'd against the current evidence-only writer on
factual_grounding / richness / reads-as-story, same judge methodology as the 2b experiment. Not started
— blocked on the same API limit.

## Writer-richness A/B result (2026-08-19) — adopt `with_context`, clean win

`scripts/storyline_context_experiment.py` tested the open question from the previous section:
`without_context` (current production — `subject` + `evidence` only) vs `with_context` (the same,
plus `context`: `venue` + this storyline's own players' `player_history`/`player_course_history`,
scoped to the players actually in the storyline and stripped of derived prose via
`authoring._strip_derived_prose` — numbers and names only, no summary sentences to lift). Same blind
judge methodology as 2b, order randomised per storyline, scored on compellingness, factual_grounding,
richness (genuine colour vs. padding), and reads-as-story.

**Result: `with_context` won 10/10 storylines across TEG 14 and TEG 16.** Averaged scores:

| axis | without_context | with_context |
|---|---|---|
| compellingness | 6.10 | **7.80** |
| factual_grounding | 7.70 | **8.20** |
| richness | 5.70 | **8.10** |
| reads_as_story_not_list | 6.30 | **7.70** |

**The key result is factual_grounding going UP, not down** — the opposite of what 2b found when the
writer got a second free-text channel. This confirms the hypothesis: 2b's fabrication risk came from
handing the writer an editor's own UNVERIFIED PROSE summary (why_it_matters/shape) that competed with
the evidence channel. Raw structured data — numbers/names, no sentences — doesn't carry that risk; it
gives the writer real material without giving it something to copy uncritically.

**Adopted as the default**, not left as an experiment. `storyline_full_report_experiment.py`'s
`draft_section()` now takes `context` as a required argument, built by `_context_for()` (same scoping
and stripping as the experiment script) and passed for every section. `DRAFT_WRITER_SYSTEM` updated
with the same anti-fabrication clause used in the A/B's `with_context` arm. Regenerated TEG 14/16/18
in full (fresh plan → context-aware draft → voice pass) to reflect it.

## Explicitly out of scope for this proposal

- Round reports (`round_report.py` / `RoundStoryPlan`) — separate pipeline instance, not touched.
- Voice/register (`WRITER_VOICE`, humour dial) — already settled 2026-08-15, unrelated lever.
- Re-running the library regeneration — a separate outstanding item in `teg_analysis/TODOS.md`, not
  to be bundled with this until the storyline approach is validated on the 3 test TEGs above.
