# Reporting — Experiment log

Running list. Each entry: what was tried, how it was tested, what the verdict was. Settled entries
are kept (briefly) so we don't re-run them; open entries are the live agenda.

**Regen anchor for style experiments: TEG 14.** Tight 2-point finish, multiple courses — the case
that most tempts the writer into fabrication, so regressions show there first. TEG 18 (blowout with
a Jacket-leader → Spoon-winner subplot) is the useful second read.

---

## OPEN

### H10. Selection weights — the untuned lever

**Goal:** the 3-axis scoring in `scoring.py` decides which beats the editor ever sees. The weights
have never been tuned. Establish what they're currently doing, and whether a different setting
produces better-balanced reports.

**Why this matters more than it looks.** Selection sits upstream of vehicle, structure and style —
it decides what there *is* to write about. It is also the cheapest component in the pipeline to
experiment on, because `build_notable_events()` is pure Python and never calls an LLM.

#### What the current weights actually do (measured 2026-08-10, TEGs 9–18, `balanced`)

**`big_blowup` takes 106 of 200 top-20 slots — 53%.** TEG 16 is 17/20; TEGs 11 and 15 are 14/20.
Over half of what the editor is shown as "most notable" is somebody having a disaster.

Mean sub-scores by type (TEGs 11, 14, 16, 18):

| type | n | importance | rarity | entertainment |
|---|---|---|---|---|
| trophy_win | 4 | 10.00 | 4.00 | 5.00 |
| jacket_win | 4 | 9.00 | 5.50 | 4.00 |
| hot_stretch | 34 | 6.04 | 2.65 | 3.27 |
| cold_stretch | 37 | 5.12 | 1.88 | 2.57 |
| **big_blowup** | **60** | **4.20** | **4.50** | **5.90** |
| lead_change | 34 | 3.44 | 2.00 | 2.12 |

A blow-up is the **second-least important** thing that happens. It dominates because it is the only
type scoring high on *both* rarity and entertainment, and because there are 15× more blow-ups than
spine events. Under `balanced` (1.0, 1.0, 1.0) those two axes jointly outvote importance.

**This is reweightable.** At roughly (2.0, 0.5, 0.5), `hot_stretch` overtakes `big_blowup` on
combined total. The knob works; it has simply never been turned.

**Related observation:** `WRITER_SYSTEM` principle 8 ("Achievements earn their moment too") is a
prompt patch for what is really a selection-layer bias. The writer is instructed to celebrate good
play while being handed a bundle that is half disasters. If reweighting fixes the mix, that
principle may become unnecessary — a good example of fixing a problem at the layer that causes it.

**Other measured facts:**
- The `top_n=50` trim **does** fire — 9 of 10 TEGs produce 57–105 beats. TEG 14 (43 beats) is the
  exception, which is awkward given it is the standing anchor case.
- The axes do not share a range. Importance spans 2–10; rarity never exceeds 7. So `balanced`
  (1,1,1) is not balanced in effect — importance has the widest range and rarity the narrowest.
- `mandatory` is partly `rarity >= 7`, and rarity rarely gets there: TEG 11 has **0** mandatory
  beats, TEG 10 has 16. That inconsistency is worth understanding before relying on the guarantee.

#### (a) Testing impact on the final cut — free, no API calls

Sweep weight vectors over the cached `build_notable_events()` output and profile the resulting cut.
Metrics that matter (order churn is the least informative):

| Metric | Why |
|---|---|
| **Type mix of the top-N** | The 53%-blowup figure is the headline number to move |
| **Tone balance** | disasters (blowup, collapse, cold) vs achievements (eagle, hot, PB, recovery) |
| **Coverage** | distinct players and rounds represented — does the cut describe the tournament, or one man's bad week? |
| **Mandatory survival** | must stay 100%. A setting that drops a TEG record is invalid regardless of how good the mix looks |
| **Churn vs baseline** | sensitivity — tells you whether a knob does anything at all |

Run it across all 10 TEGs at once. `build_notable_events()` is the slow part (~30s/TEG), so compute
once per TEG and re-score in memory.

#### (b) Testing impact on the actual reports — two complications

**1. There are two selection gates, not one.** Code picks the top 50; then the *LLM* picks 6–10
`must_include_beat_ids` from those. Changing weights changes what the editor can choose from, not
directly what it chooses — a weight change can wash out entirely at the plan stage. Measure at both
points, or you will attribute a null result to the wrong layer.

**2. You need a noise floor before you can read any result.** LLM output varies run-to-run on
identical input. Generate the same TEG **twice with unchanged weights** and measure how much the two
plans differ; that is the baseline. Only differences larger than it are attributable to the weights.
Skipping this is how a weight change gets credited with what is actually variance. ~$0.56, once.

**Then use plan-only runs as the cheap middle rung.** Stop at Stage 3 (~$0.28 vs $0.65 for the full
chain) and compare `must_include_beat_ids` composition across settings. Only generate full prose for
the one or two settings that survive.

**Cost ladder:** free profiling (all TEGs, all settings) → $0.28/run plan-only for the shortlist →
$0.65 full generation for the winner. Establishing the noise floor is the only fixed cost.

#### Candidate settings to try

| Setting | Weights | Hypothesis |
|---|---|---|
| current | 1.0 / 1.0 / 1.0 | baseline — 53% blow-ups |
| importance-led | 2.0 / 0.5 / 0.5 | competitive narrative over carnage; predicted to flip hot_stretch above big_blowup |
| existing `fast` | 1.5 / 0.8 / 0.7 | already defined, never evaluated as a quality setting |
| existing `archive` | 1.0 / 1.3 / 1.3 | already defined; predicted to *increase* the blow-up share |

**If reweighting alone can't fix the mix**, the next lever is a structural one rather than a
numeric one: a per-type cap (no more than N blow-ups in the cut) or a guaranteed quota for
achievement beats. Try the weights first — they're free.

**Notes:**
- _(empty — to fill in as we run)_

**Verdict:** _(open)_

---

### H9. Effort levels and cheaper models — how to test this without wasting money

**Goal:** find out whether `output_config.effort` (never set — every call runs at the
default `high`) and a cheaper model can cut cost without costing quality.

**First, the trap.** The instinct is to test on a short section of prose. Don't —
it will tell you nothing and the nothing will be misleading. `effort` controls how
much the model *reasons* before answering. On a short rewrite where the facts,
structure and voice are all fixed by the input, there is very little to reason about,
so low and high effort land in roughly the same place. You would conclude "effort
doesn't matter" and switch it off everywhere, including the one stage where it does.

**Test each lever at the stage where it actually bites:**

| Lever | Test at | Why there | How to score it |
|---|---|---|---|
| **`effort`** | **Stage 3 (story plan)** | This is the only stage doing real reasoning — ranking beats, picking vehicles, building setup→payoff pairs. It is also the single most expensive stage (~43% of report cost). | **Machine-checkable.** The plan is JSON. No reading required — see the rubric below. |
| **Cheap model** | **Stage 4a (dry draft)** | It re-sends the same ~26k bundle as Stage 3 (~31% of report cost) but its job is explicitly faithful, colourless transcription — the least quality-sensitive stage in the pipeline. | Factual check: does the cheap model keep the arithmetic, holes, scores and courses right? |
| **Cheap model** | Stage 4b (the writing) | Only *after* the humour dial is settled — otherwise you are moving voice and model at once and can't attribute the result. | Taste. Expensive to evaluate; do it last, or not at all. |

Stage 4b is already the cheapest stage (~15%). Cheapening the writing is the
intuitive move and close to the worst one available: most quality risk, least saving.

**The Stage 3 rubric — score without reading anything.** Regenerate the plan at
`low` / `medium` / `high` and diff the JSON:

- Does it honour the close-finish hard rule when `tournament_shape.close_finish` is true?
- Does every beat marked `"mandatory": true` appear in `must_include_beat_ids`, and none in `cuts`?
- Is there a `payoffs[]` entry for each `foreshadow[]` seed?
- How many vehicles overlap with the previous 3 TEGs' picks?
- Beat overlap between effort levels — if `low` picks the same spine as `high`, that is the finding.

**Anchor TEG: 14.** Close finish (exercises the hard rule), 2-point margin (arithmetic
risk), multiple courses (the cross-course fabrication trap). If a cheaper setting
breaks anything, it breaks here first.

**Cost:** a 3-level effort sweep at Stage 3 is ~3 × $0.28 ≈ **$0.85**; three model
variants at Stage 4a ~**$0.40**. The whole experiment is a couple of dollars — the
expensive part is evaluation time, which is exactly why the machine-checkable rubric
above matters more than the run itself.

**Sequencing note:** settle H8 (the humour dial) first. Voice and model are separate
variables and testing them together wastes both runs.

**Notes:**
- _(empty — to fill in as we run)_

**Verdict:** _(open)_

---

### H8. Humour dial — 3 vs 6 vs 8 vs 8b *(the live decision)*

**Goal:** the published reports sit at roughly 3/10 humour — deadpan gravitas, very dry. Test whether
dialling up lands better with the insider audience, and which added register works.

**What was run** (`scripts/humour_dial.py` — takes a finished report and rewrites at a higher level):

| Variant | Register added on top of the Ronay/Peck/Armstrong/Iannucci baseline | Outputs |
|---|---|---|
| baseline ≈3/10 | — | `teg_{14,18}_report_styled.md` (**what the site shows today**) |
| `humour6` | ≈6/10 | TEG 14, TEG 18 |
| `humour8` | ≈8/10 | TEG 14, TEG 18 |
| `humour8b` | ≈8/10 **Brooker-only** — drops Clive James and the literary-comparison register, adds Marina Hyde. Physical/contemporary comparisons (broken household objects, malfunctioning tech, bodily indignity) instead of literary ones; short sentences; running jokes that accumulate; punch not flourish | TEG 14 only |
| `humour8bb` | Brooker-only retry on TEG 18 | **never produced** — connection reset mid-run |

**How the test worked** (`scripts/humour_dial.py`) — worth knowing before resuming, because the
method is a good one and cheap to re-run at another dial setting:

1. It takes an **already-finished report** (`teg_N_report_final.md`) as the user message — it does
   **not** regenerate from the bundle.
2. A `HUMOUR_DIAL_SYSTEM` prompt rewrites it at the target level. That prompt is structured as:
   named influences → what to aim for → an explicit **failure-mode list** (the `❌` block: no
   literary register, no sustained metaphor, no setup-punchline, no flourish bolted onto sentences
   that already work) → the ECONOMY rules restated → the faithfulness rules restated.
3. The output is pushed back through the **same render pipeline** as a normal report
   (`apply_styling` + standings + records block), so `teg_N_report_humourX_styled.md` is directly
   comparable, line for line, with `teg_N_report_styled.md`.

Because it rewrites a finished report, **every variable except voice is held constant** — same
facts, structure, headings and records block. That is what makes the comparison clean, and it costs
one API call per variant instead of a full regeneration.

**What the method does not prove:** it shows the target voice is *reachable by rewriting*, not that
the writer will *hit it first time* from the bundle. Whatever wins must be folded into
`WRITER_SYSTEM` and validated with a from-scratch generation before it is trusted for a backfill.

**How to settle it:** read `teg_14_report_styled.md` against the three TEG 14 variants side by side,
then the TEG 18 pair. Score on: does it still read as faithful; does the added humour land or strain;
would the players enjoy it more. Then fold the winning register into `WRITER_SYSTEM`, regenerate
TEG 14 from scratch to confirm it lands, and record the verdict here.

**Notes:**
- Nothing was published. `scripts/humour_dial.py` is still pointed at `TEGS = [18]` mid-retry.
- This blocks the regeneration work — don't regenerate the stale reports until the voice is locked.

**Verdict:** _(open)_

---

### 2b. Embed actual scorecards (HTML) inside reports

**Goal:** if a scorecard is visible inline, the writer can stop spelling out per-hole sequences and
focus on what those sequences *mean*. Heavy lifting moves to a deterministic block; prose carries
interpretation.

**How to test:** build a `build_round_scorecard_html(teg, round)` helper emitting a styled HTML table
(hole / par / each player's gross). Inject it into the report. Regen one round under a writer prompt
told "the scorecard is rendered inline, do NOT enumerate; reference holes by number, comment on what
the score means."

**Notes:**
- **Not built.** No `build_round_scorecard_html` exists.
- Partially superseded: `render.build_round_scores()` already puts a deterministic round-scores block
  at the top of every round report, and the records appendix covers PBs/records. The open part is the
  *hole-by-hole* table.
- Open question: at top of report (with the round-scores block), or after the prose as a data appendix?
- Open question: does the styled output need CSS additions to render the table on both surfaces?

**Verdict:** _(open — lower priority than H8)_

---

## SETTLED

### 1. Style principles for the dry / satirical / humorous voice → **LANDED**

**Was:** make the voice deliberate rather than accidental — build a named list of principles and test
which combinations produce the voice we want.

**Outcome:** landed as the **"Named principles"** block in `WRITER_SYSTEM` (and mirrored in
`ROUND_WRITER_SYSTEM` and `ENRICH_SYSTEM`). Eight principles, built on an explicit core mechanism —
**subverted gravitas**: treat trivial stakes with the solemnity of a geopolitical crisis; the humour
lives in the gap; never wink at the camera. The principles cover: doomed seriousness rendered
honestly; bathos as the engine; trust the reader; balance ledger against emotional landscape; no
scoring redundancy; precise and earned over generic; trace the player arc within the round;
achievements get the same solemnity as disasters.

A separate voice-ladder A/B (`v0_existing` → `v1_baseline` → `v2_restraint` → `v3_economy` →
`v4_observer` → `v5_gravitas`, run on TEG 10 tournament + R2) fed this. *Inferred, not recorded:*
the ladder's final rung is `gravitas` and "subverted gravitas" is what ended up in `WRITER_SYSTEM`,
so gravitas appears to have won — but no verdict was written down at the time. The six variants are
still on disk at `teg_10_tournament_v{0..5}_*.md` and `teg_10_round_2_v{0..5}_*.md` if the comparison
needs redoing.

### 2. Writing must add value beyond the scorecard → **LANDED**

**Was:** the deterministic blocks already show what each player shot; the prose should do what a
scorecard can't — tournament context, historical context, PB flagging, cross-round threads,
cross-player comparisons, venue context, causal explanation.

**Outcome:** landed as the **PALETTE** block in `WRITER_SYSTEM` — seven named context vehicles, with
a hard rule that **at least one must be prominent** (featured in the opener *and* threaded through
the body):

(a) cross-TEG career storylines · (b) per-course player history · (c) course/venue character ·
(d) decisive-moment framing + counterfactual · (e) player-thread continuity within the tournament ·
(f) records and rare feats woven into prose · (g) foreshadow/payoff threads

Backed by real code, not just prompt exhortation: `history_context.py` (career storylines),
`course_history.py` (per-course history + new course records, which become mandatory beats),
`tournament_shape.py` (decisive/close-finish signal), and `StoryPlan.payoffs[]` (every foreshadow
seed must be paid off in a named section — this was the single most common thinness).

### 3. Verbal succinctness → **LANDED**

**Was:** strip redundancy. "A quintuple bogey 10 on the par-5 12th" carries the same number three
times — only two of {result name, raw score, par} are needed.

**Outcome:** landed twice over —

1. **Principle 5** in `WRITER_SYSTEM`: never use gross score, relation to par, and par of the hole
   all at once. Two is enough.
2. The **ECONOMY** block — 11 construction rules: em-dash ceiling of two per paragraph;
   subordinate-clause budget; no "particular kind of X" preambles; no subject-burying preambles;
   plain word over inflated phrasing; split run-on factual lists; two equal facts = two sentences;
   one aside form per sentence; compressed rhythmic lists and bogey shorthand ("quad, triple, double");
   punchline isolation; one dominant idea per paragraph.

**Design decision:** these were deliberately baked into `WRITER_SYSTEM` so the writer constructs tight
on the *first* pass, rather than relying on a fix-up pass. The standalone `tighten_prose()` /
`TIGHTEN_SYSTEM` lever still exists (same 11 rules) and was used to produce the `*_report_tightened.md`
references, but is **not** in the default chain. Snapshots before/after are at
`teg_{9,10,11,13,14,18}_report_pretighten.md`.

The lint pass (Haiku) stayed narrow — repeated/over-used words only. It does not collapse the
redundant-trio pattern; that is the writer's job.
