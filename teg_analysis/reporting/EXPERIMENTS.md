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

#### (a) Testing impact on the final cut — free, no API calls — DONE 2026-08-11

`scripts/weight_profiler.py` sweeps the four candidate settings over cached
`build_notable_events()` output for TEGs 9–18 (computed once per TEG, reused
across settings) and profiles the top-20 by weighted total, plus mandatory
survival at the real production cut (`assemble_bundle`'s top_n=50 + force-add).
Run: `python scripts/weight_profiler.py`.

**Results — type mix of the top-20 (200 slots across 10 TEGs):**

| Setting | big_blowup | hot_stretch | disaster tone | achievement tone | mandatory survival | churn vs baseline |
|---|---|---|---|---|---|---|
| current (1,1,1) | 106 (53.0%) | 19 (9.5%) | 60.0% | 36.5% | 115/115 (100%) | — |
| importance-led (2.0,0.5,0.5) | 46 (23.0%) | **54 (27.0%)** | 34.0% | 54.5% | 115/115 (100%) | 66% mean overlap |
| fast (1.5,0.8,0.7) | 80 (40.0%) | 38 (19.0%) | 48.0% | 46.0% | 115/115 (100%) | 85% mean overlap |
| archive (1.0,1.3,1.3) | 107 (53.5%) | 16 (8.0%) | 60.5% | 36.0% | 115/115 (100%) | 98% mean overlap |

**Hypothesis confirmed.** At (2.0, 0.5, 0.5), `hot_stretch` (54, 27%) overtakes
`big_blowup` (46, 23%) on top-20 share, and the tone balance flips from
disaster-majority (60%) to achievement-majority (54.5%). `fast` (already
defined, never evaluated as a quality setting) is a genuine middle ground —
blow-up share drops 53%→40% without fully inverting the mix, and it's the
setting closest to current (85% churn overlap), which matters if regenerating
the whole library is the eventual step. `archive` does exactly what
EXPERIMENTS.md predicted — it *increases* the blow-up share slightly
(53.0%→53.5%) because rarity and entertainment are exactly the two axes a
blow-up already dominates on; cranking them further entrenches it rather than
diversifying it. `archive` is not a fix for the blow-up bias — it's the
opposite lever.

**Mandatory survival is 100% for every setting, but this is true by
construction, not something the sweep discovered.** `mandatory` (in
`assemble_bundle`) depends on event *type* and raw (unweighted) `rarity`, and
`assemble_bundle` force-adds every mandatory id regardless of what the top-N
cut contains. None of the four settings can violate it because none of them
touch the inputs the mandatory test reads. Worth confirming once (done), not
worth re-checking per setting going forward — it would only move if a future
change touched `MANDATORY_TYPES` or the force-add logic itself.

**Coverage doesn't discriminate between settings, for a structural reason:**
the player pool across TEGs 9–18 tops out at 6 distinct players (some TEGs
have only 4–5), and every setting's top-20 already covers all 6 and 39–40 of
the 40 possible (TEG, round) pairs. A 20-slot cut over a 6-player field
saturates coverage regardless of weighting — this metric would only bite in a
tournament with a much larger field.

**Recommendation:** `fast` (1.5, 0.8, 0.7) is the safer of the two non-trivial
settings to adopt as the new `balanced` default — it meaningfully rebalances
tone (60%→48% disaster) while staying closest to what's already been
validated across 17 published reports. `importance-led` (2.0, 0.5, 0.5) is
the stronger fix for the stated goal (competitive narrative over carnage) but
is a bigger jump (66% churn) and hasn't been read by a human yet. Per the H10
plan, the next rung is plan-only runs (`must_include_beat_ids` composition,
~$0.28/run) on the shortlist of `fast` and `importance-led` — not attempted
here, since it needs `ANTHROPIC_API_KEY` (see CONSTRAINTS).

#### Sub-finding, extended: the arc-payload audit — DONE 2026-08-11

Per Jon's request, audited every field `_arc_top`/`_arc_bottom` put into
`competition_arcs` (`events.py`), not just the `lead_changes` field the
original sub-finding named:

| Field | Bounded? | Verdict |
|---|---|---|
| `leader_by_round` / `bottom_by_round` | yes — one entry per round (≤4) | fine — this is the round-by-round skeleton the writer needs |
| `winner_trajectory` / `loser_trajectory` | yes — one entry per round (≤4) | fine, same reason |
| `decisive_takeover` / `decisive_drop` | single dict | fine — this **is** the weighted signal (last *outright* takeover by the eventual winner/loser), correctly the one moment worth flagging |
| `lead_changes` + `n_lead_changes` | **no — grows with event count** | the already-flagged bug: unweighted list + aggregate count, early-round jockeying reads the same as a late decisive swing |
| `bottom_changes` + `n_bottom_changes` | **no — grows with event count** | **same bug, not previously flagged.** Identical shape to `lead_changes`/`n_lead_changes` but for the Wooden Spoon race — early-tournament rotation through last place will read as "chaos" at the bottom the same way it does at the top |

**The `bottom_changes` version is actually worse.** `_arc_bottom` never
computes an outright/level distinction for spoon changes at all (unlike
`lead_changes`, whose entries at least carry an `outright: bool` the writer
*could* be told to filter on) — `_turning_points`'s spoon branch emits one
`spoon_change` type regardless of whether the new last-place player is
outright last or tied. So `bottom_changes` entries have no field a future fix
could even condition on without adding one.

**Conclusion:** the bounded-by-round fields (`leader_by_round`,
`winner_trajectory`, `decisive_takeover`, and their spoon equivalents) are
correctly exempt from selection weighting — they're small, fixed-size, and
already carry the "what actually decided it" signal. The only fields that
need a fix are the two growing lists/counts, and the fix should be applied to
**both** competitions, not just the Trophy/Jacket arcs the original
sub-finding covered.

#### Candidate fix 4 — long-held lead lost detector — BUILT 2026-08-11

Implemented as `events._lead_tenure_losses` / `events._lead_tenure_events`,
wired into `build_notable_events` alongside `_turning_points`. Walks the
hole-by-hole outright-leader sequence directly from `teg_df` (independent of
`events_log`): a tied ("level") hole doesn't break a leader's spell, it just
doesn't advance the tenure clock, so a leader who draws level and immediately
retakes it outright keeps their run intact. When a spell of at least 18 holes
(roughly a full round — the threshold that keeps this a rare, high-value beat
rather than duplicating every ordinary `lead_change`) ends in an outright
takeover by someone else, it emits a `long_lead_lost` beat for **both** the
Trophy and the Green Jacket, scored on tenure length, rounds spanned, and the
existing round-lateness signal — reusing the same "later matters more" logic
`_turning_points` already applies, on top of the new tenure dimension. This
sits *alongside* the regular `lead_change` beat for the same hole (which
still fires from the taker's perspective) rather than replacing it — the
report can now draw on both "X takes the lead" and "Y's grip at the top
ends" as distinct facts.

Tested across TEGs 9–18: **7 beats fire, 0–2 per TEG**, all substantial
(tenure 20–45 holes, i.e. more than a full round, several spanning 2–3
rounds), importance/rarity/entertainment scores land in the 6.6–10.0 range —
several exceed the `rarity >= 7` mandatory threshold automatically, with no
change needed to `MANDATORY_TYPES`. Example: *"Jon Baker loses the Trophy
(Stableford) lead to Alex Baker after 45 holes in front (R1 H4–R3 H13)"*
(TEG 11, imp=10.0, rar=8.6, ent=10.0). No TEG produces more than 2 — this is
not spam.

**Not built:** the Wooden-Spoon equivalent (a long-suffering last place
finally escaping). Out of scope — Jon's request was specifically about lead
changes — but the same walk-and-track pattern would generalise directly if
wanted later.

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

#### Sub-finding: competition arcs bypass the scoring layer

Raised by Jon 2026-08-11 — *"lead changes grow in importance through the tournament; an R1 lead
change isn't worth commenting on, an R4 one is a very big event. Some drafts call early-R1 lead
changes 'chaos', but it's just what happens at the start of every tournament."*

**The scoring already encodes exactly that** (`events.py:285`):

```python
base_imp = 2.0 + 2.2 * (rnd - 1) + (1.5 if late else 0) + 1.5 * w
if not outright: base_imp *= 0.6        # drawing level < taking outright
```

An R1 change scores ~2.6 importance; an R4 outright hits the 10 cap. The individual beats are
correctly downranked and usually trimmed.

**But `competition_arcs` are preserved in full regardless of trimming** (`assemble_bundle`), and the
arc carries an unweighted `lead_changes` list plus a headline `n_lead_changes` count:

| TEG | `n_lead_changes` | by round | outright |
|---|---|---|---|
| 11 | 7 | R1: 4, R3: 2, R4: 1 | 1/7 |
| 14 | 2 | R1: 2 | 1/2 |
| 18 | 3 | R1: 3 | 3/3 |

TEG 18's entire lead-change story is three R1 changes. The writer is shown the aggregate with no
indication that all of it is routine opening jockeying — so "chaos" is a reasonable inference from
what it was given. The `WRITER_SYSTEM` rule forbidding "chaos" is a prompt patch over a
data-shaping gap, the same pattern as principle 8 and the blow-up bias.

**This matters beyond lead changes: arcs are exempt from component A3 (selection/weighting)
entirely.** Anything the arc reports reaches the writer unweighted. **Audited on the same basis
2026-08-11 — see "Sub-finding, extended" above.** The bounded-by-round fields are fine; the growing
lists/counts are the bug, and it affects the Wooden Spoon arc too, not just Trophy/Jacket.

**Candidate fixes** (cheap, no LLM needed to evaluate):
1. Split the count — `n_lead_changes_late` / `n_lead_changes_early`, so the headline number reflects
   what mattered. *(Still open — applies to both `lead_changes` and `bottom_changes` now.)*
2. Annotate each entry with its computed significance, so the writer sees the weighting the scorer
   already did. *(Still open.)*
3. Suppress R1-only changes from the arc summary when nothing later happened, and let the
   round-by-round detail carry them. *(Still open.)*
4. Add the missing case Jon named: **a long-held lead being lost** is currently not a distinct
   signal — `lead_changes` records the takeover but not how long the previous leader had held it.
   That is arguably the most narratively significant lead-change variant and it isn't detected.
   **BUILT 2026-08-11 — see "Candidate fix 4" above.**

**All four are now done (2026-08-11).** Fix 4 was the genuine detection gap. Fixes 1–3 landed
together as `_change_significance` / `_summarise_changes` in `events.py`: every change carries a
`significance` of `routine` / `notable` / `decisive`, and each arc carries a summary with the
early/late split, the outright count and an `all_routine` flag. Applied to **both** competitions —
the Spoon arc also gained the `outright` distinction it never had (`_ranklast_counts`).
`WRITER_SYSTEM` now points at that data instead of merely asserting early changes are routine.
TEG 18, whose entire lead-change story is three R1 changes, now reports `all_routine: true`.

**If reweighting alone can't fix the mix**, the next lever is a structural one rather than a
numeric one: a per-type cap (no more than N blow-ups in the cut) or a guaranteed quota for
achievement beats. Not needed here — `importance-led` already flips the mix without one.

**Notes:**
- 2026-08-11: part (a) run — see results table above. Part (b) not attempted (no `ANTHROPIC_API_KEY`
  in this environment). Arc-payload audit done; `long_lead_lost` detector built and tested.

**ADOPTED 2026-08-11: `balanced` is now (1.5, 0.8, 0.7).** Set in `scoring.MODE_WEIGHTS`, which
every call site defaults to, so it applies to every future report. `fast` is retained as an alias.

Re-measured after the `long_lead_lost` detector landed (it takes ~7 top-20 slots, displacing
blow-ups), so the figures moved slightly from the table above:

| Setting | big_blowup | hot_stretch | disaster | achievement | churn vs old default |
|---|---|---|---|---|---|
| pre-2026-08-11 (1,1,1) | 100 (50.0%) | 18 (9.0%) | 57.0% | 36.0% | — |
| **live default (1.5,0.8,0.7)** | **77 (38.5%)** | **37 (18.5%)** | **45.5%** | **45.0%** | 85% overlap |
| importance-led (2.0,0.5,0.5) | 44 (22.0%) | 54 (27.0%) | 32.0% | 53.5% | 67% overlap |
| archive (1.0,1.3,1.3) | 102 (51.0%) | 16 (8.0%) | 58.0% | 35.5% | 98% overlap |

Tone is now essentially even (45.5% disaster / 45.0% achievement) against 57/36 before.
`importance-led` remains the next step if 38.5% blow-ups still reads as too much carnage — it is a
bigger jump (67% overlap) and has not been read in prose.

`scripts/weight_profiler.py` now reads the live default from `MODE_WEIGHTS`, so it can never
describe a setting the pipeline stopped using.

**Verdict:** _(part (a) **done and adopted**. The arc sub-finding is **closed** — all four candidate
fixes shipped. Part (b) — confirming the change survives the LLM's own second selection gate at the
plan stage — remains open and needs an API key.)_

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
- Nothing was published.
- **2026-08-11: the method is now a proper lever.** `authoring.restyle_voice(teg, voice_prompt,
  label)` replaces the one-off script; `scripts/humour_dial.py` is a thin parameterised wrapper
  holding the three registers (`--teg N --variant humour8b`). The `humour8bb` TEG 18 retry that died
  on a connection reset is a one-line re-run. Guardrails now come from the shared
  `WRITER_FAITHFULNESS` constant rather than being restated inline, and every variant is checked for
  faults the rewrite *introduced* (`new_findings`) — which is the specific risk that got the
  critique-revise variant rejected.
- Fold the winner into **`WRITER_VOICE`**, not `WRITER_SYSTEM` — voice and faithfulness are separate
  constants now, and only the voice half should move.
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
