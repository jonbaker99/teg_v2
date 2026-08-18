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

## Explicitly out of scope for this proposal

- Round reports (`round_report.py` / `RoundStoryPlan`) — separate pipeline instance, not touched.
- Voice/register (`WRITER_VOICE`, humour dial) — already settled 2026-08-15, unrelated lever.
- Re-running the library regeneration — a separate outstanding item in `teg_analysis/TODOS.md`, not
  to be bundled with this until the storyline approach is validated on the 3 test TEGs above.
