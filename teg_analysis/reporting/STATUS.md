# Reporting — Status & Next Steps

**Pick-up ledger.** Read this first when resuming work in a fresh session. The how-it-works architecture is in [README.md](README.md); **how to test and iterate on each element is in [ARTEFACTS.md](ARTEFACTS.md)**; the running experiment log is in [EXPERIMENTS.md](EXPERIMENTS.md).

> **Last verified against the codebase: 2026-08-17** — docs reconciled against the code, the artefacts
> on disk, a full test run and a full `verify --all --rounds` run. Everything below the START HERE
> block is the older ledger and had drifted; the corrections are in
> [Doc reconciliation](#doc-reconciliation-2026-08-17). Note that `data/commentary/` was only added to
> git in the June 2026 merge, so **git dates tell you nothing about when a report was generated**
> — use the story-plan schema fingerprint in
> [Report inventory](#report-inventory--what-actually-exists) instead.

---

## START HERE — picking this up in a new chat (2026-08-17)

### Doc reconciliation (2026-08-17)

No pipeline change. The reporting docs were checked against the code and the artefacts and corrected;
**four of the corrections change what you would do next**, so they are here rather than only in a diff:

- **The library is no longer three vintages, and no longer has fixture gaps.** All 17 TEGs have the
  complete artefact chain (plan, dry draft, final, styled) and all 17 carry `narrative_vehicles` +
  `payoffs`. The old "regenerate TEGs 2–8, 15, 16 and 9" item and known issue 14 (TEG 14's broken
  fixture chain) were both already done and are now closed.
- **D3 is clean on every tournament report.** `verify --all --rounds` reports **0 errors across all 17
  tournaments**; the 81-fault backlog (known issue 17) cleared on the 2026-08-13 regeneration. The
  only errors left are **4, all in round reports** (TEG 9 R1/R4, TEG 10 R4). The 566 warnings are all
  `no_em_dashes` and clear on regeneration.
- **The round pipeline is not "a generation behind" any more** — the *code* is level (schema ported
  2026-08-11, shared voice 2026-08-15). It is the 18 **published** round reports that are two
  generations behind, and none of the code changes has ever been run.
- **`TIGHTEN_SYSTEM` was missed by the em-dash decision** — new known issue 19. It still sets a
  two-per-paragraph em-dash ceiling and still licenses long sentences, the exact two contradictions
  removed from `_WRITER_ECONOMY`. Nothing calls it, so nothing is broken today.

⚠️ **And the one to act on: none of the regenerated prose has reached a reader.** `style=False` on the
2026-08-13 run was deliberate, but the consequence was never measured. Measured now: **16 of 17
`*_report_styled.md` files — everything except TEG 14 — do not match their own `report_final.md`.** The
titles alone give it away (TEG 17 final: *"Eighty-Six on Seve's Last Design"*; TEG 17 styled, which is
what the site serves: *"The Coronation at Óbidos"*). So the entire library regeneration, the era-leak
fix in TEGs 5–7, and the 81 cleared wording faults are all invisible on the site. `style_report(teg)` is
free, deterministic and idempotent — see [next steps](#next-steps--ranked-to-do-list) step 2 for why it
is bundled with the regeneration rather than run now.

Also corrected, without changing any decision: several files still described D3 as unbuilt, `verify.py`
was recorded as 7 checks in two places (it is 8), the `agent` provider was still called the default in
the skill doc and in `llm.get_provider`'s docstring, and the round-report count was 17 (it is 18).

Test suite at the time of writing: **520 passed, 20 skipped** (skip count is environment-dependent —
no API key and no network in this container).

---

### A second comic engine: the occasion device (2026-08-17)

**The problem.** The report's humour was almost entirely hole-level. A quintuple bogey is funny, but
a report built only from blow-ups has nothing to say about a tournament where nobody blew up, and
nothing that scales with the RESULT. Jon's example of the missing register, from darts: *"When
Alexander of Macedonia was 33, he cried salt tears because there were no more worlds to conquer.
Bristow's only 27."*

**`prompts.ELEVATION_DEVICE`** puts that engine in. Raise a frame far grander than the occasion
deserves, then let a plain fact land against it. Crucially the frame is **read off the data, not
guessed**: `win_anatomy` and `tournament_shape` already classify every result, and the block maps
each classification to an archetype.

| Signal | Archetype |
|---|---|
| `attribution: "built"`, wide margin | procession, conquest with nothing left to conquer |
| `attribution: "inherited"` | robbery, the rival who outplayed and lost |
| `attribution: "unopposed"` | walkover, an occasion staged for a foregone result |
| `biggest_lead_blown` present | collapse, a fall from a stated height at a named hole |
| `rival_could_have_flipped_it` | the haunting counterfactual |
| `close_finish` | trivial margin treated as dynastic |
| `shape: "volatile"` / `"consistent"` | carried by a machine he isn't operating / grinding inevitability |

**It is CONTRACT, not voice.** It specifies a rhetorical move and leaves the register of the frame
entirely to the voice: a deadpan voice states the grand parallel flatly, a vicious one reaches for
Bristow. Both execute the same move. What must not vary is that the opening establishes the scale.
`tournament_shape` joined `BUNDLE_CONTEXT_KEYS` so `close_finish` reaches the writer.

**This does change the house writer prompt** — it is the first content added to `WRITER_CONTRACT`
rather than moved within it. Nothing regenerates until a backfill runs.

Two tests guard it: every value `win_anatomy` can emit must have an archetype (this caught
`shape: "consistent"` being unaddressed on the first pass), and every field the block names must
exist and be in `BUNDLE_CONTEXT_KEYS`.

---

### The writer prompt now has a swappable VOICE slot (2026-08-16)

**Why:** trying a new register meant editing `WRITER_VOICE` in the source, running the writer, then
editing it back. Five registers meant five source edits. Meanwhile `restyle_voice` — which only
rewrites a *finished* report, the weaker test — took its voice as an argument. The ergonomics were
backwards: the path that proves the pipeline reaches a voice was the awkward one.

**What changed.** `WRITER_SYSTEM` went from two slots to three:

```python
build_writer_system(voice=None) -> WRITER_CONTRACT + (voice or WRITER_VOICE)
                                   + WRITER_FAITHFULNESS + WRITER_OUTPUT_RULE
```

`WRITER_CONTRACT` is new and holds everything that is true of the report **whatever register it is
written in**: the role, the winner's-story duty, the structure and palette, the scoring-redundancy
notation, the SI guidance. `WRITER_VOICE` keeps only the register: `VOICE_CORE`, the comic aim, the
named principles, the economy rules. A `voice=` argument **replaces** `WRITER_VOICE` — it is a
complete register description, not a delta — and cannot shed the contract or the guardrails.

**Two blocks were split to draw that line:**

- The old `_WRITER_AIM` interleaved the duty owed to the champion (voice-independent) with where the
  comedy points (voice-specific). Now `_WRITER_EDITORIAL` (contract) and `_WRITER_COMIC_AIM` (voice).
- `NAMED_PRINCIPLES` principle 5, scoring redundancy, moved out to
  `prompts.SCORING_REDUNDANCY_RULE`. It is a notation rule, not an aesthetic principle, and a
  swappable block is the wrong home for something that must survive the swap. The round writer
  carries it explicitly now.

**Same content, one reordering.** Every substantive sentence of the old prompt survives; the diff is
six deliberate rewordings (removing cross-references to the comic devices from blocks that are now
voice-neutral) plus **STRUCTURE and STROKE_INDEX moving before the voice instead of after**, so the
contract is contiguous and a swap is a single substitution. **The house prompt is therefore not
byte-identical to its predecessor** — the earlier `WRITER_VOICE`/`WRITER_FAITHFULNESS` split was.
Nothing regenerates until a backfill runs, so no report on disk or on the site has moved.

**The lever:** `write_from_dry(teg, voice, label, plan_scope=...)`. Thin wrapper over
`report_around_draft` — same function production calls, so an experiment cannot be true of the
trial and false of the pipeline. `plan_scope` is the second dial: `"none"` (dry draft alone,
isolating the voice), `"arc"` (default — narrative vehicles and story-arc fields only) or `"full"`
(production). `bundle_context=True` is the third: it appends the structured venue / career-history /
win-anatomy block, which is how a variant gets the full material without the plan's pre-written
phrasing — every plan field is editorial prose, the bundle keys are data. Recipe ⑥ in
[ARTEFACTS.md](ARTEFACTS.md) is the walkthrough.

**Not promoted, and not the default.** Nothing in the chain calls `write_from_dry`; it refuses to
write `report_final`, `report_styled` or `A_around_draft`. Promotion stays a deliberate act: paste
the winning voice into `WRITER_VOICE` and re-run the backfill.

**Open:** no voice has been trialled through it yet. The house voice still needs the from-scratch
validation the 2026-08-15 readability pass has been waiting on.

---

### Readability pass: em-dashes banned, humour dialled to 6, sentences capped (2026-08-15)

Jon's verdict on the current reports: **"80% good, lacking a bit in humour, and a bit hard to read.
Sentences run long and the constructs rapidly become hard work."** That settles the humour-dial
question that had been blocking regeneration since 2026-08-10.

**What changed in `VOICE_CORE`, so both pipelines get it:**

- **Em-dashes banned outright.** Not a ceiling of two per paragraph, zero. This was the specific
  construction Jon identified as driving the sprawl.
- **Comic density specified**: five to seven landed moments, not two or three. This is the
  `humour6` register from `scripts/humour_dial.py`, folded into the baseline voice.
- **Sentence discipline moved to the top of the voice block** and made concrete: average ~15
  words, hard stop around 25, one idea per sentence.

**Why the old 25-word cap never worked.** It was contradicted twice: `ECONOMY` licensed
*"long sentences that earn their length stay long"*, and the `ELEVATED (right)` exemplar — the
clearest picture of the target the writer gets — was a single 40-word sentence. Measured output
broke the cap 18–31% of the time. By contrast the em-dash *ceiling* (2/paragraph), which nothing
contradicted, had **zero** violations across all four recent reports. Same prompt, same model:
unambiguous rules are obeyed, contradicted ones are not. Both contradictions are now removed and
the exemplar rewritten as five short sentences.

**Enforcement, because a prompt rule alone was never going to hold it:** `verify.py` has a new
`check_no_em_dashes` (warning severity), auto-run by `backfill.py` after every generation.
`tests/test_reporting_prompts.py` asserts the style-setting blocks contain no em-dashes themselves,
and that the worked exemplar obeys the sentence cap it sits above.

**Scope call on the prompt's own punctuation:** `VOICE_CORE`, `NAMED_PRINCIPLES`, `_WRITER_AIM` and
`_WRITER_ECONOMY` are now em-dash free, so the blocks that teach register don't model the thing they
ban. The structural, palette and faithfulness blocks still contain them: they are procedural lists
rather than prose the model imitates for style, and one test locates a block by the literal
`"PALETTE —"`. Revisit if the ban doesn't hold in generated output.

⚠️ **All published reports predate this and trip the new check.** Measured across the whole library
2026-08-17: **566 `no_em_dashes` warnings**, every tournament and round report affected, 10 to 40 each
(TEG 14 is the worst at 40). That is the backlog clearing on regeneration, not a new defect — and it
doubles as the acceptance test for the regeneration, since a report generated under the ban should
report zero.

**Untested end-to-end.** The `humour6` outputs on disk were produced by `restyle_voice` rewriting a
*finished* report, not by generating cold with the dialled prompt — see `EXPERIMENTS.md` on what that
method does and does not prove. **Next step is one from-scratch generation (~$0.65) and a read.**

---

### Voice is now defined in ONE place — `prompts.py` (2026-08-15)

**The voice work of 11–14 Aug never reached three of the four prompts that carry it.** All three
voice commits (`ef67417` Herron, `ac55be8` the four humour mechanisms, `342db93` dropping the Peck
device) edited only `authoring.WRITER_VOICE`, because that is where the voice experiments ran. Both
editor prompts and the round writer kept their own copies and went on describing a Ronay/Peck
register — still naming Peck, whose device had been deliberately removed. The faithfulness rules had
drifted the same way: seven of them existed twice, in two files, edited independently.

**Fixed structurally, not by hand-syncing the copies.** `reporting/prompts.py` now holds
`VOICE_CORE`, `NAMED_PRINCIPLES`, `HOUSE_VOICE_SUMMARY`, `SHARED_FAITHFULNESS` and
`STROKE_INDEX_RULE`; all four prompts import them. `tests/test_reporting_prompts.py` (26 tests)
fails if a block is re-inlined, if any prompt stops naming the current voice, if Peck reappears, or
if the editor-facing summary drifts from the writer-facing voice.

**What changed in generated output:**

| Pipeline | Effect |
|---|---|
| Tournament writer | **None.** Content-identical — six faithfulness bullets moved earlier in the list; verified by diffing the composed prompt against the pre-refactor original |
| Tournament editor | Plans now aimed at the register the writer actually has |
| **Round writer** | **Real change** — adopts the four humour mechanisms in place of its pre-Herron formulation |
| Round editor | Same summary as the tournament editor |

⚠️ **The 18 published round reports are now doubly stale** — they were already pre-H1/H3 vintage, and
the round voice has now moved as well. Regenerating them is untouched and uncosted.

**One deliberate omission:** `NARRATIVE PULL` stays tournament-only. It is voice-adjacent craft
rather than voice, and sharing it would have widened the round-report change beyond the voice.

---

Two live workstreams. They are independent; either can be picked up first.

| | Workstream | State | Doc |
|---|---|---|---|
| **A** | **Report quality** — data, vehicles, voice | Reworked end to end; 4 test TEGs regenerated and read well; **full library regeneration outstanding** | this file + [README.md](README.md) |
| **B** | **Stop paying per API call** — run the same prompts through claude.ai plan usage instead of the Anthropic API | **Built 2026-08-15.** Provider switch + mailbox hand-off + variants. **The API remains the default**; plan usage is opt-in per run via `--plan`. See the note below on whether it has been run for real | [README.md](README.md) → *Who answers the prompts* |

### What workstream A was trying to achieve

Reports that are **entertaining, engaging and insightful**: they celebrate the winner (tongue-in-cheek,
and better for it), mock the losers where deserved, and are clear about **why the champion won**.
Course history, previous results and recent form are welcome texture.

### What was wrong, and what we did about it

Three root causes, all in the data layer rather than the prompts — which is why earlier prompt-only
attempts had not fixed them:

1. **`importance` did not measure what it claimed.** Its docstring said "contribution to the result";
   it was a hand-tuned function of shot-cost, round and standing that never consulted the result. On
   TEG 18 the champion won by 8 Stableford points and none of his eight worst holes could have cost
   him more than 2.3, yet they scored 5.0–6.5 and made up half the champion-negative material.
   → **`impact.py`**: importance is now the counterfactual — *if this player had scored their own
   average over these holes, would the competition have finished differently?* Measured in each
   competition's own metric, discounted by how much time remained to recover.
2. **Detection was lopsided 2.6:1 against the champion's dignity.** Bad things were detected on
   *gross*, good things on *net*, so a high-handicap player in contention was the maximum-negative
   configuration — champion's handicap literally predicted how negative the report was about them
   (handicap 16 → 0 negative beats; handicap 36 → 10). → **`cold_stretch_net` + `steady_stretch`**,
   ratio now 1.52:1.
3. **Nothing computed WHY the champion won.** `competition_arcs` gave the *what*; causation was left
   to inference over a pile of beats, which is exactly where "the champion was rubbish" comes from.
   → **`win_anatomy.py`** + a required `why_the_champion_won` plan field.

Then the voice: a storyline hierarchy (winner's story leads, departures recorded), mockery calibrated
by target, and the champion register — hard on the golf, never on the achievement, **elevated
delivery**, proportion capped. See [README.md](README.md#the-storyline-hierarchy-and-the-champion-register)
for the three failed attempts at that last rule and why each failed.

### Measured effect (TEGs 2–18, deterministic, no LLM)

| | Before | After |
|---|---|---|
| Champion's share of negative beats | 20% | **14%** |
| Overall negative share of the cut | 41% | **39%** |
| Detection ratio (negative:positive) | 2.59:1 | **1.52:1** |

### Two mistakes worth not repeating

- **I optimised the wrong objective twice.** First minimising the cut's overall negative share, then
  minimising the champion's share of negatives. Negative material *is* the comic material, and
  champion-negative *volume* was never the real problem — the **framing** was. Both metrics are
  useful diagnostics; neither is the target. The prose is the only real test.
- **Every string in `win_anatomy` is copied into prose.** Statistical phrasing anywhere in that
  module ships to the reader ("a round-to-round spread of 5 against a field median of 8"). Plain
  English only — there is a test enforcing it.

### Where workstream A got to

- Pipeline reworked and green: **518 passed** as of 2026-08-17.
- **TEGs 4, 8, 12, 14 and 18 regenerated** under the rework and all read well. TEG 4's report is now
  framed on the seven-shot lead Baker threw away; TEG 18 leads on the champion's gross 10 and elevates
  it. Fingerprint for "has the rework": `why_the_champion_won` present in the story plan — those five
  TEGs have it, the other twelve don't.
- **Outstanding: regenerate the full library (2–18).** ~90 min. Jon's call was "a few tests first,
  then everything" — the tests are done. Note the five test reports **also predate the em-dash ban and
  the humour dial** (both landed later on 2026-08-15), so the cold-generation validation still comes
  first.
- Two late fixes (plain-English round labels, inverted Spoon phrasing) **postdate the four test
  reports**, so those flaws are still visible on disk in the Spoon sections of TEGs 4 and 18. They
  clear on the full run.
- **Nothing is user-visible yet, and this was verified 2026-08-17: 16 of 17 styled reports are out of
  sync with their finals.** All regeneration ran `style=False`, so `*_report_styled.md` — what the site
  serves — still holds pre-2026-08-13 prose. A styling pass is free, deterministic and idempotent.
- Round reports (49 outstanding) were not touched. The round *code* is level with the tournament
  pipeline; the published round reports are two generations behind it.

### Where workstream B got to (2026-08-15)

Built and tested. Full detail in [README.md](README.md) → *Who answers the prompts*.

> **"Not yet run on a real report" is out of date — but nobody wrote up the run.** Three pieces of
> evidence on disk say the hand-off has produced whole reports:
>
> - **`reply.txt` at the repo root** is a complete, unpublished TEG 17 tournament report
>   (*"Order Restored on the Silver Coast"*). That filename is the scratch file from the documented
>   manual command, `mailbox answer <dir> --file reply.txt`. It was committed by accident in `aafad8b`
>   and is **still tracked** — see known issue 20.
> - **TEG 14 was regenerated in `aafad8b`** (Jon's own commit, same day): tournament + R1 + R2 rewritten,
>   R2 and R3 story plans added, R3 left plan-only. A `--plan` run at `scope="both"` interrupted during
>   round 3 produces exactly that footprint.
> - **`4a78bb9` quotes per-call token counts "measured on TEG 17"** across all four calls, which needs a
>   real run to obtain.
>
> **What is genuinely still open is the quality comparison**, which was always the point: nobody has
> read a plan-usage report against an API report of the same TEG and recorded a verdict. Treat the
> mechanism as proven and the equivalence as unmeasured.

- **`TEG_LLM_PROVIDER=api|agent` in `llm.py`, defaulting to `api`.** Plan usage is opt-in per run
  (`--plan`), because it is the one mode that needs a responder present. Nothing else in the
  pipeline changed: `backfill_all` and the four-call chain keep one implementation, which was the
  main constraint on the design.
- **`--paste NAME`** — one flag for the cross-model workflow: hand-off, variant directory, and the
  run marked `manual` so the skill cannot answer prompts intended for ChatGPT or Gemini.
- **Concurrent runs supported.** Runs are found by scanning `data/llm_mailbox/` (live PID, no
  `FINISHED` marker) rather than a single `CURRENT` pointer, which a second run used to clobber.
  Ambiguity is an error listing `--run <id>` options, never a guess.
- **`mailbox.py`** — the file hand-off. The pipeline writes `request.md` and blocks; a Claude Code
  skill (`.claude/skills/teg-report-respond/`) or a human answers it. `request.md` is
  self-contained, so the same file pastes into ChatGPT or Gemini.
- **Structured output survives without `messages.parse`**: the JSON Schema travels in the prompt,
  Pydantic validates on the way back, and a failure is re-asked with the error attached (3
  attempts). This is a net gain — the API path has no retry.
- **`paths.py`** — `TEG_REPORT_VARIANT` redirects artefacts to `variants/<name>/` for model
  comparisons, with `promote_variant` to pick a winner.
- **CLI**: `python -m teg_analysis.reporting.backfill --tegs 2-18 [--provider api] [--variant gpt5]`.
- 34 new tests; full suite **518 passed** as of 2026-08-17.

**Open**: whether plan-usage output matches API output in quality. Run one report each way on the
same TEG before committing the full 2–18 regeneration to either. `reply.txt` is half of that comparison
already — it is a plan-usage TEG 17 against a published API TEG 17.

---

## TL;DR — the older ledger

The pipeline is **built, working and well past what the old docs described**. Three things are true:

1. **Tournament coverage is complete.** Every TEG has a published tournament report and the webapp
   renders them. (TEG 1 predates the data — it isn't in `completed_tegs.csv` or `all-data.parquet`,
   so TEGs 2–18 *is* the full set. TEG 2 has 3 rounds; every other TEG has 4.)
2. **The pipeline kept evolving after the last backfill run.** As of 2026-08-13 every *tournament*
   report was regenerated on one vintage, so this no longer applies to them — but round reports
   still span several.
3. ~~**Work stopped mid-experiment.**~~ **Settled 2026-08-15.** The "humour dial" A/B (3 → 6 → 8 → 8b)
   on TEGs 14 and 18 got its verdict: `humour6`, folded into `prompts.VOICE_CORE` with the em-dash ban
   and the sentence cap. The variant files are still on disk as history. See
   [the humour dial](#where-work-stopped--the-humour-dial-settled-2026-08-15).

**Suggested pick-up order** is in [Next steps](#next-steps--ranked-to-do-list).

**2026-08-11 — H10(a) run + a new detector landed.** The selection-weight profiler
(`scripts/weight_profiler.py`) swept the four candidate weight settings over cached beats for TEGs
9–18: confirmed the (2.0, 0.5, 0.5) hypothesis (`hot_stretch` overtakes `big_blowup`), and found
`fast` (1.5, 0.8, 0.7) is a safer middle-ground fix. Separately, `events.py` gained a new
`long_lead_lost` detector — a genuinely missing signal (a long-held lead being lost), not a
re-weighting — which fires 7 times across TEGs 9–18 and is wired into `build_notable_events` for
every future report. No report was regenerated and no weight setting was adopted yet; both are
judgment calls for a session with `ANTHROPIC_API_KEY`. Full detail in
[EXPERIMENTS.md](EXPERIMENTS.md) → H10.

**2026-08-11 (later) — the defect backlog was cleared.** Ten of the register's issues are fixed,
including all three P1s. The two that matter most:

- **D3 exists.** `verify.py` checks a finished report against the data — the assurance mechanism the
  pipeline never had. Run it with `python -m teg_analysis.reporting.verify --all --rounds`. It
  independently re-found the TEG 10 R3 arithmetic error and turned up **41 raw beat IDs sitting in
  TEG 5's published report**, which nobody knew about. Both are now fixed.
- **The close-finish hard rule can finally fire.** `prominent_vehicle` was specified with two
  different vocabularies in two prompts; the vocabulary now lives in one place, the prompt menus are
  generated from it, and the schema enforces it. The exact value that shipped for four TEGs is now a
  validation error.

**2026-08-13 — vehicle-fit scoring measured across all 17 TEGs; hints cleaned up; the advisory made
accountable.** `vehicle_fit.py` (added on the preceding branch) scores each narrative vehicle
against a TEG's actual facts for free — no LLM call — and z-scores it against the checked-in
17-TEG baseline. Scored across TEGs 2–18, **the normalization works**: raw scores put `tragic_arc`
or `redemption_arc` top in all 17 TEGs, normalized scores give 10 different winners with none
appearing more than twice. Two changes came out of that run:

- **Four vehicles were polluting the hint list.** `motif`, `bookends`, `ensemble` and
  `theme_led_body` have no detector at all, so their baseline is mean 0 / std 0 and
  `normalize_vehicle_fit` scored them z = 0.00 — which sorted them *above* every genuinely detected
  vehicle that came in below its average. They occupied 26 of the 85 hint slots the editor sees
  (TEG 2's list was 1 real hint and 4 of these), and `motif` was the joint-most-frequent top-3 hint
  despite never having been measured for anything. They are now excluded from the ranking, and the
  editor prompt names them and asks for them to be judged on their own merits — their absence is
  not evidence against them.
- **The advisory is now accountable, not binding.** Decision (Jon, 2026-08-13): do *not* require the
  editor to justify diverging from the top hint. That pressure would fall hardest on precisely the
  vehicles that can never be top-scored, defeating the variety the scorer exists to serve. Instead
  the new required `vehicle_fit_response` field records the top hint, whether it was adopted, and
  one line of reasoning; `check_plan_consistency` verifies the record is *truthful* and never warns
  on divergence itself. `test_diverging_from_the_top_hint_is_not_a_warning` guards that boundary.

**2026-08-13 (later) — closing section renamed, and a prose-only backfill switch.** The closing
player summary heading is now prescribed **exactly** as `## Player-by-player summary` in
`authoring.py` (it was `## The men, in brief` "or similar", so published reports vary). Nothing
matches on the heading in code — `verify.check_only_participants` only mentions it in a docstring —
so this is a pure guidance change; existing reports keep their old heading until regenerated.
`backfill_teg` / `backfill_all` gained `style=False`, which stops at `teg_N_report_final.md` and
skips the injection of standings, the at-a-glance box and the records appendix.

**2026-08-13 — the whole library regenerated (TEGs 2–18), and two silent bugs found by doing it.**
Every TEG now has a tournament report from the current pipeline, prose only
(`force=True, scope="tournament", style=False`), so `*_report_styled.md` — what the site serves —
is deliberately untouched and still carries the old reports until a styling pass is run. The key is
read from `TEG_ANTHROPIC_API_KEY`, now accepted as an alias in `llm.get_api_key()`.

Both bugs are the same shape: **a value computed one way in the live path and another way in the
reference path.** Neither could ever fail loudly.

1. **Vehicle fit was scored on trimmed beats.** `assemble_bundle` scored against the `top_n=50`
   beat list — a token budget for the LLM call — while the checked-in baseline is generated with
   `top_n=None`. So live z-scores compared a trimmed raw score against an untrimmed population
   mean, deflating every vehicle that scores as a *sum over beats* (`tragic_arc`,
   `redemption_arc`, `catalogue`) while leaving arc- and milestone-derived ones untouched. On TEG
   6, `tragic_arc` went from raw 79.5 / z +2.70 to raw 32.7 / z +0.06 — rank 1 to rank 5. Fixed to
   score on `all_beats`; `test_vehicle_hints_do_not_depend_on_the_beat_trim` locks it. Measured
   impact: the top hint changed on only **2 of 12** already-generated TEGs (6 and 15), both
   re-run.
2. **`restyle_voice` blamed inherited faults on the restyle pass.** The `new_findings` split
   exists to catch a prose pass fabricating a detail; it compared source to output on `str(f)`,
   which embeds the excerpt. A restyle rewrites the prose around a fault by definition, so the
   excerpt shifts and an inherited fault reads as newly introduced — inverting the mechanism in
   the normal case. Now keyed on `(rule, detail)` via a `Counter`.

**What seventeen recorded `vehicle_fit_response` rationales show.** The scorer reliably detects
local texture and reliably mis-weights it against tournament-level meaning. Every rejection traces
to that one cause: `redemption_arc` sums hole-level recovery beats (rejected as "small change" on
TEGs 9 and 18); `inevitability` fires on a structural fact (declined as "texture, not the frame" on
15, 2, 3, 8); `dual_narrative` counts lead changes without knowing whether they were contested
(TEG 5 — "Mullin faded rather than duelling"). Adopted hints skew to career milestones and genuine
inventories (`origin`, `comeback`, `underdog`, `catalogue`).

**Candidate fix, not yet done:** weight beat-derived vehicles by whether their beats belong to the
decisive competition and rounds, rather than summing across the tournament. It changes scoring, so
it needs a baseline regeneration — a judgement call for Jon.

**The advisory decision looks right in practice.** Three of the four unscoreable vehicles were
chosen on the editor's own reading (`motif` ×6, `ensemble`, `bookends`), and on TEG 8 `ensemble`
was the *primary frame* — a frame the scorer cannot nominate under any circumstances. A
binding-on-divergence rule would have suppressed all of it.

Residual, not fixed: a detectable-but-unfired vehicle (raw 0, negative z) can still reach the top 5
on a quiet TEG — ~14 of 85 slots. Less misleading than the removed cases, since the editor sees
`raw: 0.0` and an empty `reasons` list, and a genuine 0 for a vehicle that *does* have a detector is
real evidence of absence. Left as-is deliberately.

*(As written on 2026-08-13, the humour dial and the 81 prose-wording faults were the two open items.
Both are now closed — the dial on 2026-08-15, the faults by the regeneration described above. Test
suite was 422 passed at the time; it is 518 as of 2026-08-17.)*

---

## Architecture status — all stages built

| | Stage | Module / function |
|---|---|---|
| ✅ | 1 — record | reuses `teg_analysis.core.data_loader.load_all_data` |
| ✅ | 2 — notable-event detection + 3-axis scoring | `events.py`, `scoring.py` |
| ✅ | 2 — competition arcs (Trophy / Jacket / Spoon) | `events._competition_arcs` |
| ✅ | 2 — venue context | `venue.py` + `data/course_info.csv` |
| ✅ | 2 — cross-TEG player history + milestones | `history_context.py` |
| ✅ | 2 — per-course player history + course records | `course_history.py` |
| ✅ | 2 — tournament shape signals + anti-repetition | `tournament_shape.py` |
| ✅ | 2 — era resolution (Trophy metric by TEG) | `era.py` |
| ✅ | 3 — story plan (LLM, structured) | `story_plan.py`, `llm.py` |
| ✅ | 4a — dry storyline draft | `authoring.generate_dry_draft` |
| ✅ | 4b — entertaining report (around-draft) | `authoring.report_around_draft` |
| ✅ | 4b — repetition lint | `authoring.repetition_lint` |
| ⚠️ | 4c — tighten pass | `authoring.tighten_prose` — **built, not wired into `backfill.py`** (deliberate lever) |
| ✅ | voice A/B lever (rewrite) | `authoring.restyle_voice` — rewrites a finished report's voice only; **not** in the default chain |
| ✅ | voice A/B lever (from scratch) | `authoring.write_from_dry` — runs the real writer over the frozen dry draft in a supplied voice; **not** in the default chain |
| 🗑️ | 4d — history enrichment pass | **deleted 2026-08-11** — zero callers, duplicated `history_context` |
| ✅ | D3 — programmatic verification | `verify.py` — **8** mechanical checks, auto-run by `backfill.py` (8th = `no_em_dashes`, added 2026-08-15) |
| ✅ | shared prompt blocks | `prompts.py` — `VOICE_CORE`, `NAMED_PRINCIPLES`, `HOUSE_VOICE_SUMMARY`, `SHARED_FAITHFULNESS`, `STROKE_INDEX_RULE`, `OUTPUT_RULE`; imported by all four prompts |
| ✅ | provider switch (API / plan usage) | `llm.py` + `mailbox.py` + `paths.py` — API is the default |
| ✅ | 5 — CSS-class styling renderer | `render.apply_styling` / `render.style_report` |
| ✅ | round-level pipeline | `round_report.py` |
| ✅ | batch orchestration | `backfill.py` |

### Phases A–G (the original agenda) — all closed

| Phase | What | Status |
|---|---|---|
| **A. Easy cost levers** | Haiku 4.5 lint; bundle trim to top-N=50 (preserves mandatory beats). | DONE |
| **B. Per-round standings + player closing** | Deterministic `build_round_standings` injection; non-negotiable closing rule. | DONE |
| **C. Round-report prototype** | `round_report.py` pipeline (RoundStoryPlan, ROUND_* prompts, single-round bundle). | DONE |
| **D. Pre-Phase-F shape fixes** | Folded into Phase E. | DONE |
| **E. Round-report shape fixes (E1–E5)** | Round-scores block at top; auto-injected standings; anti-countback rule; arithmetic-faithfulness rule; mandatory-beats coverage; deterministic "PBs and TEG records" appendix. | DONE |
| **F. Backfill TEGs 8–18** | DONE at tournament level (8–18 all published). **Round level still partial** — see inventory. |
| **G. Pre-TEG-8 era-aware Trophy + backfill** | Code DONE. Backfill DONE for TEGs 2–7 — **but run on an old pipeline vintage and with a known era leak** (see [Known issues](#known-issues)). |

### Phase H — editorial depth & voice (post-June, was never logged until now)

This block of work landed after the last STATUS update and is the reason the current code is ahead
of most published reports. Reconstructed from the code and the `*_pre*` snapshot files on disk
(the naming convention is "the report as it was **before** change X"):

| # | What | Where | Snapshot marker |
|---|---|---|---|
| **H1** | **Narrative vehicles.** The editor picks 1–3 named storytelling frames from a menu (`bookends`, `motif`, `hero_arc`, `inversion`, `counterfactual`, `dual_narrative`, `three_act`, `theme_led_body`, …) and the writer is required to honour them. | `story_plan.SYSTEM_PROMPT` vehicle menu; `StoryPlan.narrative_vehicles` / `.prominent_vehicle`; WRITER_SYSTEM STRUCTURE rule | `*_report_prevehicles.md` |
| **H2** | **Anti-repetition across reports.** `recent_vehicle_choices(teg)` feeds the last few TEGs' vehicle picks into the bundle as a SOFT RULE so consecutive reports don't default to the same frame. | `tournament_shape.recent_vehicle_choices` | `*_report_prevehicles.md` |
| **H3** | **Explicit setup→payoff pairs.** `foreshadow[]` seeds without payoffs was the single most common thinness. `Payoff` model + a non-negotiable writer rule now pairs each seed with the section that resolves it. | `story_plan.Payoff`, `StoryPlan.payoffs` | `*_report_prepayoff.md` |
| **H4** | **Close-finish hard rule.** `detect_close_finish()` computes deterministically from the Trophy arc whether the finish was close; when true, `prominent_vehicle` MUST be `counterfactual`/`dual_narrative` and the close finish leads. Overrides H2. **Never fired correctly until the 2026-08-11 schema fix** — see known issue 8. | `tournament_shape.detect_close_finish` | `*_report_preclose.md` |
| **H5** | **Economy / tightening.** An 11-rule ECONOMY block (subordinate-clause budget, no subject-burying preambles, punchline isolation, …) baked into `WRITER_SYSTEM`, **plus** a standalone `TIGHTEN_SYSTEM` / `tighten_prose()` pass. The economy rules were baked into the writer so tightening happens on the first pass; `tighten_prose` remains as a separate lever. ⚠️ **Two of the original 11 were superseded on 2026-08-15** — the em-dash *ceiling* became an outright ban and the "long sentences that earn their length" licence was withdrawn. `_WRITER_ECONOMY` was updated; `TIGHTEN_SYSTEM` was not (known issue 19). | `authoring.WRITER_SYSTEM` ECONOMY; `authoring.tighten_prose` | `*_report_pretighten.md`, `*_report_tightened.md` |
| **H6** | **Cross-TEG + per-course context.** Career storylines (Nth Trophy, back-to-back, first win in N years, defending champion), per-course player history, new course records (mandatory beats), and win counts in the at-a-glance box. Plus a standalone `ENRICH_SYSTEM` / `enrich_report_with_history()` insert pass. | `history_context.py`, `course_history.py`, `render._build_at_a_glance` | — |
| **H7** | **Faithfulness hardening.** New non-negotiable writer rules: verified `player_relationships` only (no inferring siblings from surnames); verbatim `weekday` use, and never call a 4-day TEG "a week"; only players who actually played this TEG; strip internal beat IDs from prose; exact arithmetic. | `authoring.WRITER_SYSTEM` FAITHFULNESS; `constants.PLAYER_RELATIONSHIPS` | — |

**Important consequence, as it stood:** `RoundStoryPlan` (`round_report.py`) did **not** get H1/H3 — no
`narrative_vehicles`, no `payoffs`, no storyline bullets.

> **Closed 2026-08-11**, and the wording above is kept only because it explains the vintage of the
> published round reports. `RoundStoryPlan` now carries `narrative_vehicles`, `prominent_vehicle`,
> `prominent_palette` and `payoffs` from the same shared enums as the tournament plan, and since
> 2026-08-15 `ROUND_WRITER_SYSTEM` composes the same `prompts.VOICE_CORE` blocks. **The code is level;
> the 18 published round reports are two generations behind it, and neither change has been run.**

---

## Report inventory — what actually exists

Live files are at `data/commentary/` top level. Two full prior snapshots are preserved at
`data/commentary/archive 2026 v1/` and `archive 2026 v2/`; the pre-pipeline 2025 system's output is
at `archive 2025/`, `drafts/` and `round_reports/` (these are also the webapp's fallback paths).

### Tournament reports

Vintage is fingerprinted from `teg_N_story_plan.json`, in two tiers:

- `narrative_vehicles` + `payoffs` populated ⇒ **Phase H or later**
- `why_the_champion_won` present ⇒ **the 2026-08-14 A–D rework** (counterfactual importance,
  `win_anatomy`, storyline hierarchy, champion register)

TEGs 2–18 is the complete set — there is no TEG 1 in the data.

**Verified on disk 2026-08-17:**

| TEG | Published | Artefact chain | Story-plan vintage |
|---|---|---|---|
| 4, 8, 12, 14, 18 | ✅ | complete | **A–D rework** (2026-08-14/15) — the five test reports |
| 2, 3, 5, 6, 7, 9, 10, 11, 13, 15, 16, 17 | ✅ | complete | **Phase H** (regenerated 2026-08-13) |

Two things this replaces. The old three-vintage split (**pre-H1 for 2–8, 15, 16; partial for 9**) is
gone — the 2026-08-13 run regenerated every tournament report on one vintage, so the pre-TEG-8 era
leak and the "reads inconsistently" problem are no longer in the published prose. And every TEG now has
**all four artefacts** (plan, dry draft, final, styled), so there are no fixture gaps anywhere.

**What is still uniform-and-stale:** all 17 predate the 2026-08-15 readability decision (em-dash ban,
`humour6`, sentence cap), which is what the outstanding regeneration is for. D3 reports **0 errors**
across all 17 and 566 em-dash warnings library-wide.

### Round reports

Verified on disk 2026-08-17:

| TEG | Rounds published |
|---|---|
| 8, 9, 10 | 1, 2, 3, 4 ✅ complete |
| 11 | 1, 2 (R3 has a story plan but no report — an interrupted run; R4 missing) |
| 14 | 1, 2, 4 (R3 plan-only — the 2026-08-15 hand-off run stopped there) |
| 18 | 3 |
| 2–7, 12, 13, 15, 16, 17 | none |

Full coverage is 67 rounds (TEG 2 has 3, the rest 4); **18 are published, so 49 outstanding** (~$32).

**All 18 are two generations behind the round code**, which is the thing to know before backfilling:
they predate both the `RoundStoryPlan` schema port (2026-08-11) *and* the shared-voice change
(2026-08-15) that moved the round writer off its pre-Herron register. Neither has been run on real
round output. **Generate one round and read it before spending on the other 49.**

The 4 remaining D3 errors in the whole library are all here — TEG 9 R1 (`weekdays`), TEG 9 R4
(`weekdays`, `not_a_week`), TEG 10 R4 (`not_a_week`). Regeneration clears them; hand-editing them would
be editing the writer's voice.

---

## Where work stopped — the humour dial (SETTLED 2026-08-15)

> **Resolved.** Jon's verdict on the published reports: *"80% good, lacking a bit in humour, and a bit
> hard to read."* **`humour6` won** and is folded into `prompts.VOICE_CORE` as the baseline — 5–7 landed
> comic moments per report, not the 2–3 the old baseline produced — alongside the em-dash ban and the
> ~15-word sentence average. Recorded in [EXPERIMENTS.md](EXPERIMENTS.md) → H8.
>
> **What is left is validation, not the decision:** every variant on disk was `restyle_voice` rewriting
> a *finished* report, which proves a register is reachable but not that the writer hits it cold from
> the bundle. One from-scratch generation (~$0.65) closes it.

The historical record, kept because the variant files are still on disk.
`scripts/humour_dial.py` takes a finished report and rewrites it at a
higher humour level, adding influences on top of the baseline Herron/Ronay/Armstrong/Iannucci register.

> Its baseline description was stale too (named Peck, no Herron) and was corrected 2026-08-15. The
> variant outputs on disk were generated against the old description, so they are not exactly
> reproducible from the current script — that affects reproduction, not the taste call below.

| Variant | Register added | Outputs on disk |
|---|---|---|
| baseline (≈3/10) | Herron / Ronay / Armstrong / Iannucci | **this is what the site currently shows** |
| `humour6` | dialled to ≈6/10 | TEG 14, TEG 18 |
| `humour8` | dialled to ≈8/10 | TEG 14, TEG 18 |
| `humour8b` | ≈8/10, **Brooker-only** — drops Clive James and the literary-comparison register, adds Marina Hyde; physical/contemporary comparisons, short sentences, punch-not-flourish | TEG 14 only |
| `humour8bb` | intended Brooker-only retry on TEG 18 | **never produced** — the script header records a connection reset |

**None of the variants was ever published**, and `scripts/humour_dial.py` is still pointed at
`TEGS = [18]` mid-retry. The verdict came from reading them, not from promoting one — the winning
register was folded into the writer prompt instead, which is the durable form of the decision.

---

## Known issues

**Register — everything open, ranked by severity.** Detail sections follow in ID order (IDs are
stable and referenced from README.md and EXPERIMENTS.md; new issues get the next free number rather
than a renumber). Verified against the code, the artefacts on disk and a full `verify --all --rounds`
run on **2026-08-17**.

Severity is *impact if left alone*, not effort:

- **P1** — wrong output reaches readers, or silently corrupts every future report. Fix before any regeneration.
- **P2** — real defect or missing capability, contained or not yet shipped.
- **P3** — tidiness, dead code, cosmetic. Costs the next session time, not correctness.

| ID | Issue | Sev | Effort | Blocks regen? | Status |
|---|---|---|---|---|---|
| 10 | **No programmatic verification (D3) exists** | **P1** | L | — | ✅ **FIXED 2026-08-11** — `verify.py`, now 8 checks, auto-run by `backfill.py` |
| 8 | **Editor↔writer vocabulary defined twice, unenforced** | **P1** | S–M | yes | ✅ **FIXED** — single source of truth + `Literal` enums; collision is now a validation error |
| 1 | **Pre-TEG-8 era leak** | **P1** | S | yes | ✅ **FIXED** — `hole_evidence` is era-aware; pre-8 beats carry `netvp`, never `stableford` |
| 3 | **Round pipeline a generation behind** | P2 | M | round regen | ✅ **FIXED** — `RoundStoryPlan` has vehicles, payoffs and the shared enums |
| 4 | **TEG 10 R3 arithmetic error** | P2 | S | no | ✅ **FIXED** — "fourteen-point swing" → sixteen; D3 regression-tests it |
| 16 | **TEG 5 shipped 41 beat IDs to readers** | P2 | S | no | ✅ **FIXED** — found by D3, stripped from final + styled |
| 18 | **Writer prompt read the wrong prominence field** (self-inflicted by the issue-8 fix; caught pre-generation) | P2 | XS | no | ✅ **FIXED 2026-08-11** — PALETTE block now names `prominent_palette`; regression test added |
| 12 | **Arc payload reaches the writer unweighted** | P2 | S–M | no | ✅ **FIXED** — per-entry `significance`, early/late summaries, and the Spoon arc finally has an `outright` flag |
| 11a | **`DEFAULT_MODEL` still `claude-opus-4-7`** | P2 | XS | no | ✅ **FIXED** — pinned to `claude-opus-5` |
| 2 | **`enrich_report_with_history()` has zero callers** | P3 | XS | no | ✅ **FIXED** — deleted, with `ENRICH_SYSTEM` and `build_history_enrichment_context` |
| 11b | **Dead `DRY_DRAFT_SYSTEM = ..._LIGHT` alias** | P3 | XS | no | ✅ **FIXED** — deleted |
| 17 | **81 prose-wording faults across older reports** ("the week" ×71, invented weekdays ×10) | P2 | — | **cleared BY regen** | ✅ **FIXED by the 2026-08-13 regeneration** — verified 2026-08-17: **0 errors across all 17 tournament reports.** Rescoped as issue 21 for the 4 that remain in round reports |
| 13 | **Selection weights untuned** | P2 | S | no | ✅ **FIXED 2026-08-11** — `balanced` set to (1.5, 0.8, 0.7); blow-ups 53%→38.5%, tone near-even |
| — | **Humour dial unsettled** | **P1** | — | yes | ✅ **SETTLED 2026-08-15** — `humour6` + em-dash ban + ~15-word sentences, in `prompts.VOICE_CORE`. One cold generation still owed as validation |
| 19 | **`TIGHTEN_SYSTEM` contradicts the em-dash ban and the sentence cap** | P3 | XS | no | ⏳ **Open (new 2026-08-17)** — dormant; nothing calls the pass |
| 20 | **`reply.txt` tracked at the repo root** — a complete unpublished TEG 17 report | P3 | XS | no | ⏳ **Open (new 2026-08-17)** — needs a keep-or-delete call from Jon |
| 21 | **4 D3 errors in round reports** (TEG 9 R1/R4, 10 R4) | P2 | — | cleared by round regen | ⏳ **Open** — the residue of issue 17 |
| 22 | **Raw `SI n` leaks into published prose** | P2 | S | no | ⏳ **Open** — TEG 8 does it 8 times; candidate 9th D3 check |
| 9 | **Prompt density past the useful point** | P2 | M | no | ⏳ **Partly addressed** — voice and faithfulness split into `WRITER_VOICE` / `WRITER_FAITHFULNESS` (byte-identical composition), and the shared blocks now live once in `prompts.py`. Trimming the 6 rules D3 duplicates is still open; do it on evidence from fresh generations |
| 14 | **TEG 14 fixture chain broken** | P2 | S (~$0.65) | no | ✅ **FIXED 2026-08-15** — rebuilt by the TEG 14 regeneration; all four artefacts present |
| 5 | **Remote (webapp) report generation not built** | P2 | L | no | ⏳ **Open** — `webapp/TODOS.md` |
| 15 | **`output_config.effort` never set** | P3 | S | no | ⏳ **Open** — needs a key (H9) |
| 6 | **`teg_reports.css` duplicated and drifted** | P3 | XS | no | ⏳ **Open — deliberately not fixed**, see below |
| 7 | **Python 3.14 venv jinja2 bug** | P3 | — | no | ⏳ **Open** — use 3.12/3.13 |

**Issue 6 — why it was left alone.** The obvious fix (delete `streamlit/styles/teg_reports.css`,
keeping the live `webapp/static/` copy) requires editing `streamlit/`, which the project rules
forbid outright. The duplication is also harmless in practice: the webapp copy is the live one and
is already ahead, and nobody is permitted to edit the streamlit copy anyway. It resolves itself when
`streamlit/` is deleted — which is a scoped decision of its own, not something to slip into an
unrelated change.

**What D3 found that nobody knew about — and how it ended.** Running the new checks over the library on
2026-08-11 turned up **123 errors across 14 reports**. Two classes were fixed by hand: TEG 5's 41
reader-visible beat IDs, and the TEG 10 R3 arithmetic error. The remaining **81 were prose wording** —
71 uses of "the week" (a TEG is 3–4 consecutive days) and 10 invented weekday names (TEG 2 names a
Tuesday; it ran Saturday–Monday) — and were left for regeneration rather than hand-edited, on the
grounds that rewording them is editing the writer's voice.

**That worked.** Re-run on 2026-08-17, after the 2026-08-13 regeneration:

| | 2026-08-11 | 2026-08-17 |
|---|---|---|
| Errors, tournament reports | ~119 | **0** |
| Errors, round reports | 4 | **4** (untouched — rounds were never regenerated) |
| Warnings | — | 566, all `no_em_dashes` (the check did not exist in August 11) |

The prediction and the mechanism both held: D3 turned "reads inconsistently" into a number, and the
number went to zero for exactly the reports that were regenerated. That is the strongest evidence to
date for regenerating rather than patching.

**Recommended order for what remains:**

1. **One cold generation** under the settled voice (~$0.65) — validates `humour6` and the em-dash ban
   from scratch rather than by rewrite. The last thing blocking the library regeneration.
2. **Regenerate the library** — clears the 566 em-dash warnings. Run `verify --all` after; the error
   count stays 0 and the warning count should collapse.
3. **Rounds** — one round report read first (the voice change is untested there), then the scope call on
   the other 49. Clears issue 21.
4. **9** — trim D1 only after D3 has proven itself on fresh generations.
5. **19**, **20**, **22** — small and independent; **5**, **15**, **6**, **7** — schedule separately.

### 1. Pre-TEG-8 era leak — FIXED 2026-08-11

> **FIXED.** `hole_evidence(row, metric)` is era-aware: `net_vs_par` eras carry `netvp` per hole
> and never `stableford`. `_fmt_evidence` reads whichever is present, and the `hot_stretch`
> headline reports "shots to par" rather than "points" pre-TEG-8. The published TEG 5/6/7 prose
> still contains the old framing — that clears on regeneration.


TEGs 1–7 decided the Trophy on **net vs par**, not Stableford. `era.trophy_metric()` handles this and
the prompts reference it — but `events.hole_evidence()` **unconditionally** puts a `stableford` value
on every hole of evidence regardless of era, so the writer sees Stableford points and uses them.

Confirmed in the published reports:

- `teg_5_report_styled.md` — *"a par at the par-5 3rd for four Stableford points … moved into outright lead"*
- `teg_6_report_styled.md` — *"in the chilly idiom of Stableford, that reads 3-5-4-3, which is fifteen points"*
- `teg_7_report_styled.md` — *"Across holes three to nine Meller gained twenty-three Stableford points"*

TEGs 3 and 4 read clean (TEG 3 was the Phase-G smoke test). The webapp already ships a caption
admitting the problem (`_PRE_TEG8_CAPTION` in `webapp/routes/reports.py`: *"the report here is
written based on Stableford so finishing positions may be inaccurate"*) — that caption was inherited
from the legacy 2025 reports and is still accurate for TEGs 5–7 today.

**Fix**: make `hole_evidence()` era-aware (omit or relabel `stableford` when
`trophy_metric(teg) == "net_vs_par"`), then regenerate TEGs 1–7. Also audit `_fmt_evidence()`
(`events.py:859`), which renders `{stableford}pt` into the inspection artefact unconditionally.

### 2. `backfill.py` was a generation behind the authoring module — RESOLVED

`backfill_teg()` runs `plan → dry → around → lint → style`. It did not call `tighten_prose()` or
`enrich_report_with_history()`.

**Resolved 2026-08-11 by deleting the enrich path** (`enrich_report_with_history`, `ENRICH_SYSTEM`,
`build_history_enrichment_context`). It had zero callers and computed the same class of fact the
bundle already feeds the writer through `player_history` → `WRITER_SYSTEM` palette item (a) —
duplication, not a gap. `tighten_prose()` is kept as a deliberate standalone lever; H5's economy
rules are baked into `WRITER_SYSTEM` so the writer constructs tight on the first pass.

`backfill_teg()` now also runs **D3 verification** after each report and reports any findings.

The uneven history coverage that prompted the original question stands as an argument for tightening
palette item (a), not for reviving a second pass:

| TEG | 10 | 11 | 12 | 13 | 14 | 17 | 18 |
|---|---|---|---|---|---|---|---|
| history phrases in prose | 9 | 6 | **1** | 2 | 5 | 9 | 4 |
| ordinal wins in prose | 3 | **0** | **0** | 5 | 4 | 3 | **0** |

### 8. Shared editor↔writer vocabulary defined twice — FIXED 2026-08-11

> **FIXED.** The vocabulary now lives once, in `story_plan.py`'s `NARRATIVE_STRUCTURES` /
> `NARRATIVE_VEHICLES` / `PALETTE_VEHICLES`; both prompts' menus are *generated* from those
> constants, and the schema types are `Literal`s built from the same source. The collided field was
> split into `prominent_vehicle` (the frame) and `prominent_palette` (the context material), both
> required. `check_plan_consistency()` additionally catches combination-level violations the schema
> can't express — the close-finish rule, mandatory-beat coverage — and `build_story_plan` prints
> them. Cost: the editor can no longer invent an unlisted vehicle name; that freedom is what
> allowed the drift.


`prominent_vehicle` is specified in two places with two different vocabularies:

- `story_plan.py:245` — *"Pick the **palette** vehicle the writer should foreground"* (the
  WRITER_SYSTEM palette (a)–(g): `cross_teg_career`, `decisive_moment`, `records`, …)
- `story_plan.py:202` — the close-finish **HARD RULE** requires `counterfactual` or
  `dual_narrative`, which are from the **`narrative_vehicles` menu**, a different list

The editor resolves the ambiguity in favour of the field's own spec every time, so the hard rule has
**never once fired correctly**. It applies to exactly two TEGs and was violated on both:

| TEG | close_finish | margin | `prominent_vehicle` | expected |
|---|---|---|---|---|
| 11 | true | 6 | `decisive_moment` | `counterfactual` / `dual_narrative` |
| 14 | true | **2** | `decisive_moment` | `counterfactual` / `dual_narrative` |

TEG 14 is the tightest finish in the library — the case the rule exists for. Both plans *do* carry
`counterfactual` / `dual_narrative` in their `narrative_vehicles` list, so the editor understood the
close finish correctly and simply put the answer in the field the other rule wasn't reading. This is
a spec bug, not a disobedient model.

**It is one instance of a general class.** Nine terms (`prominent_vehicle`, `narrative_vehicles`,
`narrative_structure`, `payoffs`, `foreshadow`, `decisive_moment`, `counterfactual`,
`in_medias_res`, `theme_led`) are defined independently in two ~15k-character prose prompts with no
single source of truth. Every one of them is a place the two prompts can drift apart, silently.

**Fix: move the shared vocabulary into the schema.** `prominent_vehicle: str = ""` and
`narrative_vehicles: list[str]` are free strings; as `Literal[...]` enums the collision would have
been a structured-output validation error at generation time instead of a silent 4-of-7 collapse.
Related symptoms the same fix addresses: `narrative_structure` sometimes returns a whole sentence
instead of an enum value (TEGs 11 and 14), and `in_medias_res` appears as both a *structure* and a
*vehicle* (TEG 12).

**Also symptomatic — the soft anti-repetition rule is leaking.** TEGs 17 and 18, generated
adjacently, open with the same construction ("Picture Jon Baker walking off the 16th…" / "Picture
Alex Baker, on the 18th tee…") despite `recent_vehicle_choices` being in the bundle.

### 9. Prompt density is past the point where emphasis carries information

`WRITER_SYSTEM` is ~16k characters with **38 bolded directives and 11 MUST/NEVER/NON-NEGOTIABLE
absolutes**; `story_plan.SYSTEM_PROMPT` is ~14k with 19 and 10. When most instructions are marked
critical, the marking stops distinguishing anything.

**Recommendation: targeted fix + audit, not a rewrite.** These prompts have been validated across 17
published reports, and most of the absolutes trace to a specific observed failure that was expensive
to find — the countback fabrication, the cross-course "same hole" rhyme, the invented sibling
relationships, the invented weekdays. A clean-sheet rewrite would discard that hard-won ballast and
risk reintroducing bugs already paid for. The order that preserves it:

1. **Schema-enforce the shared vocabulary** (issue 8) — fixes a whole class of drift permanently.
2. **Run a structured prompt audit** over `story_plan.SYSTEM_PROMPT`, `WRITER_SYSTEM`,
   `DRY_DRAFT_SYSTEM_*`, `ROUND_*`, `TIGHTEN_SYSTEM`, `ENRICH_SYSTEM` — separating instructions that
   still prevent a live failure from scaffolding written for an earlier model or superseded by a
   later phase. (`/claude-api prompt-audit` does exactly this and produces a report plus a proposed
   diff.)
3. **Keep every faithfulness rule that traces to a real incident**, however shouty. Those are the
   ones the insider audience notices.

### 10. No programmatic verification (D3) — FIXED 2026-08-11

> **FIXED.** `teg_analysis/reporting/verify.py` implements seven mechanical checks (beat IDs,
> invented mechanisms, "a week", non-participants, invented weekdays, impossible over/under-par
> totals, and mis-stated swings). `backfill.py` runs it after every generation. Findings are
> reported, never raised.
>
> On first run over the whole library it produced **123 errors across 14 reports** — including the
> TEG 10 R3 arithmetic error it was designed to catch, and 41 beat IDs visible in TEG 5's published
> report that nobody had noticed. See the register above for what was fixed and what waits on
> regeneration.


Surfaced by the 2026-08-11 component-model rework (README → Theme D). Confirmed by grep: **nothing in
`teg_analysis/reporting/` checks a prose claim against the source data.** Every faithfulness
mechanism is either a prompt instruction (D1) or a deterministic block that sidesteps the writer
entirely (D2). There is no third mechanism.

That is why the three recorded drift incidents (fabricated "countback", fabricated cross-course
"same hole", the TEG 10 R3 arithmetic error) reached published reports — **the arithmetic rule was
already in the prompt when the TEG 10 error was written.** A rule the model is asked to follow and a
check that fails the build are not the same guarantee.

Roughly **6 of the 11 `WRITER_SYSTEM` faithfulness absolutes are mechanically checkable** (beat IDs,
countback vocabulary, "a week", roster membership, weekday-verbatim, arithmetic) — see the table in
README → "Why D3 would reduce the burden on D1". Building D3 for those six would also let D1 shrink
to the genuinely semantic rules, which is the targeted version of the known-issue-9 prompt-density
fix. Note the manual version already exists: the sanity grep in
[Historical verification record](#historical-verification-record) is D3 done by hand, once.

Tracked as **Deferred → Faithfulness-check pass** below; this entry records *why* it has been
promoted from "nice to have" to the largest structural gap in the pipeline.

### 11. Two small code/doc contradictions — FIXED 2026-08-11

> **FIXED.** `llm.DEFAULT_MODEL` is now `claude-opus-5`, and the dead
> `DRY_DRAFT_SYSTEM = DRY_DRAFT_SYSTEM_LIGHT` alias is deleted (`generate_dry_draft` already
> defaulted to `detailed`, the settled winner).


Both are live, both are cheap:

- **`llm.DEFAULT_MODEL` is still `claude-opus-4-7`.** Next-steps item 4 (pin to `claude-opus-5`)
  has not been done. Same price for a better model — see that item.
- **`authoring.py:143` has `DRY_DRAFT_SYSTEM = DRY_DRAFT_SYSTEM_LIGHT`**, a module-level alias whose
  comment claims light is "current behaviour". It isn't: `generate_dry_draft` defaults to
  `dry_draft_style="detailed"`, and EXPERIMENTS.md records **detailed** as the settled winner. The
  alias has no remaining callers — it's dead, but it reads as a contradicting default. Delete it.

### 3. Round pipeline behind the tournament pipeline — FIXED 2026-08-11

> **FIXED.** `RoundStoryPlan` gained `narrative_vehicles`, `prominent_vehicle`,
> `prominent_palette` and `payoffs`, all on the same shared enums as the tournament plan, and
> `ROUND_PLAN_SYSTEM`'s menus are generated from the same constants. The two pipelines can no
> longer drift apart. Round *reports* are still unwritten for most rounds — that's coverage, a
> separate decision.


`RoundStoryPlan` has no `narrative_vehicles`, no `payoffs`, no storyline bullets. If round reports
matter, H1/H3 need porting to `round_report.py` before the ~45 outstanding round reports are
generated — otherwise the backfill bakes in the older editorial model.

### 4. `teg_10_round_3` arithmetic error — FIXED 2026-08-11

> **FIXED.** Corrected to "sixteen-point swing" in `_final`, `_styled` and `_A_around_draft`
> (verified against the data: Mullin 91, 5 clear after R2 → 122, 11 adrift after R3). D3's
> `check_swing_claims` now regression-tests this exact shape.


Opening para claims "a fourteen-point swing" (Mullin: 5 clear → 11 adrift). Correct figure is
sixteen. The dry draft has the right raw numbers; the writer miscalculated the summary. Fix on re-gen.

### 5. Remote (webapp) report *generation* not built

Viewing was fixed 2026-07-12 (all reads go through `teg_analysis.io.read_text_file`, discovery via
`data/completed_tegs.csv`, and `/admin/volume-sync` has a "Sync all reports from GitHub" button).
**Generating** a report from the webapp is still not possible — it's a local script/notebook job
with `ANTHROPIC_API_KEY`, then a sync. Tracked in `webapp/TODOS.md`.

### 6. `teg_reports.css` is duplicated — and the two copies have now drifted

Lives in both `streamlit/styles/` and `webapp/static/`. **Verified 2026-08-11: they are no longer
identical.** The webapp copy carries a paragraph-spacing rule the streamlit copy lacks:

```css
/* Tailwind's preflight zeroes <p> margins, so set our own */
.teg-report p { margin: 0 0 1.1em 0; }
```

So the "keep both in sync" instruction has already failed once in practice. Since `streamlit/` is
frozen dead code slated for deletion and nothing depends on it, **the fix is to delete the streamlit
copy, not to re-sync them** — the webapp copy is the live one and is ahead. Deleting it also removes
the only reason anyone would edit a file under `streamlit/`, which the project rules forbid anyway.

### 7. Python 3.14 venv / jinja2 template-cache bug

The isolated `venv/` (Python 3.14) hits `TypeError: cannot use 'tuple' as a dict key` on every
templated route. Visual webapp verification needs Python 3.12/3.13.

### 18. Writer prompt read the wrong prominence field — FIXED 2026-08-11 (self-inflicted)

Introduced by the issue-8 fix and caught before any report was generated. Splitting
`prominent_vehicle` into a frame field and a `prominent_palette` context field left
`WRITER_VOICE`'s PALETTE block still saying *"informed by the plan's `prominent_vehicle`"* — so the
writer would have been told to choose a palette item (a)–(g) on the basis of a field now holding a
frame value like `counterfactual`, which is not in that list.

**Exactly the same failure mode as issue 8, reintroduced in the other prompt** — which is the
argument for the schema-and-generated-menus approach rather than prose cross-references. The prompt
now names `prominent_palette` with an explicit note that the two fields are different vocabularies,
and a regression test asserts the PALETTE block never references `prominent_vehicle` outside that
disambiguation.

No cost: no report has been generated since the split.

### 12. Competition arcs reach the writer unweighted — FIXED 2026-08-11

> **FIXED.** Every lead/bottom change now carries a `significance` of `routine` / `notable` /
> `decisive`, and each arc carries a `lead_change_summary` / `bottom_change_summary` with the
> early/late split, the outright count and an `all_routine` flag. The Spoon arc gained the
> `outright` distinction it never had (`_ranklast_counts`). `WRITER_SYSTEM` now points at this data
> instead of merely asserting that early changes are routine. TEG 18 — whose entire lead-change
> story is three R1 changes — now reports `all_routine: true`.


Arcs bypass the selection layer entirely (README → component A3), so anything they carry arrives
unfiltered. Audited the full payload 2026-08-11: the round-bounded fields are fine, but **two fields
grow with event count and are handed over raw** — `lead_changes`/`n_lead_changes` (Trophy, Jacket)
and `bottom_changes`/`n_bottom_changes` (Spoon). The spoon version is worse: spoon changes carry no
`outright`/`level` flag at all, so there is no field a fix could even condition on without adding one.

This is the root of the "chaos" framing on routine opening jockeying — the beats *were* correctly
downranked by the scorer; the arc handed over an aggregate count anyway.

**Partly fixed 2026-08-11:** the missing *long-held-lead-lost* signal is now detected
(`events._lead_tenure_events`). **Still open:** splitting early/late counts, annotating entries with
their computed significance, or suppressing R1-only changes from the summary — see EXPERIMENTS.md →
H10 candidate fixes 1–3. All are cheap and need no LLM to evaluate.

### 13. Selection weights — TUNED 2026-08-11

The three scoring axes have never been tuned; `balanced` (1,1,1) shows the editor a cut that is
53% blow-ups and 60% disaster-toned. Measured across TEGs 9–18 on 2026-08-11 via
`scripts/weight_profiler.py` — full results in EXPERIMENTS.md → H10(a).

**Resolved:** `balanced` — the mode every call site defaults to — is now **(1.5, 0.8, 0.7)**.
Measured effect across TEGs 9–18: blow-ups 50%→38.5% of top-20 slots, tone from 57/36
disaster/achievement to an even 45.5/45.0, with 85% top-20 overlap against the old default.

`importance-led` (2.0, 0.5, 0.5) remains the next step if 38.5% still reads as too much carnage —
a bigger jump (67% overlap), not yet read in prose. **Still worth doing when a key is available:**
a plan-only run to confirm the change survives the LLM's own second selection gate at the plan
stage (H10 part b). The code change stands on the free profiling either way.

### 14. TEG 14's fixture chain is broken — FIXED 2026-08-15

> **FIXED.** The TEG 14 regeneration on 2026-08-15 rebuilt the chain. All four artefacts are present
> (verified 2026-08-17), so the two cheapest iteration loops work on the anchor case again — and since
> every other TEG also has a complete chain, there is no fixture gap anywhere in the library.

TEG 14 is the designated regression anchor (tight 2-point finish, multiple courses) and had been
**missing `dry_draft.md` and `report_final.md`** — the humour and tighten experiments consumed them into
variant filenames, breaking the cheap loops on the very case chosen for being hardest.

### 15. `output_config.effort` is never set anywhere

Every LLM call runs at the default (`high`). Not a defect — an untested cost/latency lever on the
most expensive stage. Tracked as EXPERIMENTS.md → H9; needs an API key.

### 19. `TIGHTEN_SYSTEM` contradicts the settled readability rules — new 2026-08-17

The 2026-08-15 decision removed two clauses from `_WRITER_ECONOMY` because they *contradicted* the
em-dash ban and the sentence cap, and a contradicted rule gets ignored. `TIGHTEN_SYSTEM` still carries
both:

| `TIGHTEN_SYSTEM` says | The settled rule |
|---|---|
| *"Two [em-dashes] per paragraph is the ceiling"* (rule 1) | Zero. Banned outright |
| *"Bathos: long sentences that are funny BECAUSE they are long stay long"* (PRESERVE ALWAYS) | ~15-word average, hard stop ~25, no earned-length exemption |
| *"long sentence contains two equal-weight beats joined by `—`"* (rule 8) | The construction it describes cannot occur |

**Nothing is broken today** — `tighten_prose()` has no callers and `backfill.py` does not run it, which
is exactly why the em-dash commit missed it. But it is a live lever documented for fixing up older text,
and running it on a report would reintroduce both faults. Fix when the pass is next wanted, or delete
the pass: it duplicates rules the writer now applies on the first pass.

### 20. `reply.txt` is tracked at the repo root — new 2026-08-17

A complete, styled, unpublished **TEG 17 tournament report** (*"Order Restored on the Silver Coast:
Baker Leaves the Mid-Pack Behind"*, 6.9 KB), committed by accident in `aafad8b` alongside the TEG 14
regeneration. The filename comes from the documented manual mailbox command,
`mailbox answer <dir> --file reply.txt`, so this is very likely the plan-usage TEG 17 output.

**Needs a decision, not a cleanup.** It is either (a) the missing half of the plan-usage-vs-API quality
comparison, in which case it belongs in `data/commentary/variants/` with a manifest, or (b) scratch, in
which case delete it. Deleting it blind would throw away a generated report; leaving it tracked at the
repo root implies it is a project file.

### 21. Four D3 errors remain in round reports

The residue of issue 17, in the three round reports that were never regenerated: TEG 9 R1
(`weekdays`), TEG 9 R4 (`weekdays` + `not_a_week`), TEG 10 R4 (`not_a_week`). Same class as the 81 that
cleared, same fix — regeneration, not hand-editing. Blocked behind the round-report scope decision.

### 22. Raw `SI n` leaks into published prose

`prompts.STROKE_INDEX_RULE` tells both writers to translate stroke index into English ("the hardest hole
on the course"). **TEG 8's published report does both**: correct translations in some places, raw
`"the SI 2 last"` / `"the SI 1 8th"` in eight others. TEGs 4, 12 and 18 have zero, so the rule works and
is obeyed unreliably — per-run variance, not a dead rule. Reads as machine output to the audience least
likely to forgive it.

**Mechanical and unambiguous, so it belongs in D3** as a 9th check rather than as more prompt emphasis —
the same argument that moved the other six.

---

## Deferred (deliberate, not forgotten)

| Item | Notes |
|---|---|
| **5b — strict round-by-round tournament variant** | A *tournament* report rendered strictly chronologically, as an alternative format from the same story plan. |
| **5c — modes (fast vs archive)** | `mode='fast'` skips the dry draft and uses single-pass authoring — cheaper for post-round write-ups. `mode='archive'` = current full chain. Add as a `mode=` arg to a top-level orchestrator. |
| **5d — Batch API wrapper** | Anthropic's Batch API (50% off, 24h SLA, identical output) for archive runs. Bigger saver than the easy levers but ~1–2h of staged-batch wrapper code. |
| **Faithfulness-check pass** (component **D3**) | A programmatic verifier of prose claims against the data. Three writer-drift incidents to date (fabricated "countback"; fabricated "same hole across courses"; the TEG 10 R3 arithmetic error). **Promoted 2026-08-11 from "deferred nicety" to the pipeline's largest structural gap — see known issue 10.** The framing that kept it deferred ("prompt rules block the first two classes") is weaker than it looks: the arithmetic rule was already in the prompt when the TEG 10 error was written. ~6 of 11 faithfulness absolutes are mechanically checkable and would move out of the prompt entirely. |
| **Embed scorecards in reports** | EXPERIMENTS.md item 2b — never built. |

---

## Next steps — ranked to-do list

> **Rewritten 2026-08-17.** Both judgement calls that used to head this list are settled — the humour
> dial on 2026-08-15, the weights on 2026-08-11 — and three of the "then, in order" items turned out to
> be already done (TEG 14's fixtures, the stale-report regeneration, issue 17). What is left is one
> cheap validation step and then spending.

**The organising principle is unchanged.** Regenerating the library is the expensive, effectively
one-way step: it sets the published voice and bakes in whatever state the pipeline is in. Everything
that changes *what a report is* lands before it.

**What changed is where the bottleneck sits.** It is no longer a decision, and no longer code. It is one
generation nobody has paid for yet.

```
  1 cold generation (~$0.65) ──► 2 regenerate 2-18 ──► 3 verify --all
     validates humour6 +              (~$11)              warnings → 0, errors stay 0
     the em-dash ban cold

  rounds, gated on a scope call:  4 read one round report ──► 5 backfill 49 (~$32) ──► clears issue 21

  independent, any time:  6 effort experiment · 7 prompt trim · 8 remote generation · 19/20/22 small fixes
```

---

### 1. The one thing blocking regeneration

**Generate one TEG cold and read it** (~$0.65). Every variant behind the `humour6` verdict was
`restyle_voice` rewriting a *finished* report; that proves the register is reachable, not that the
writer reaches it from the bundle. The em-dash ban and the sentence cap have never been exercised on a
cold generation at all.

Use **TEG 14** (the anchor: 2-point finish, multiple courses) or **TEG 17**. Acceptance test is
mechanical for once: `verify` should report **0 em-dash warnings**, against 10–40 on every report
currently on disk.

*Both former blockers, for the record:* the humour dial is settled (`humour6`, in
`prompts.VOICE_CORE`); `balanced` weights are (1.5, 0.8, 0.7). The optional weight follow-up still
stands — a plan-only run (~$0.28) to confirm the change survives the plan-stage selection gate, and a
look at `importance-led` if 38.5% blow-ups still reads as too much carnage.

---

### Then, in order

**2. Regenerate the library** — all of 2–18, ~$11 at ~$0.65 each. Not "the stale ones": every report on
disk predates the readability decision, so this is a full pass. It is also the point at which
`style=True` should run — the 2026-08-13 regeneration used `style=False`, so **`*_report_styled.md`,
which is what the site actually serves, still holds pre-2026-08-13 prose.** Styling is free and
deterministic; it just has to be remembered.

**3. Verify.** `python -m teg_analysis.reporting.verify --all --rounds`. Errors should stay at 0 and the
566 em-dash warnings should collapse to near zero. Anything else is a genuine new finding.

**4–5. Rounds, if wanted.** Generate and read **one** round report first: the round writer's voice
changed on 2026-08-15 and has never been run. Then the scope call on the remaining 49 (~$32), which
also clears issue 21.

---

### Independent — schedule whenever

**6. Effort + cheap-model experiment** (EXPERIMENTS.md → H9), ~$1.25. `output_config.effort` is never
set, so every call runs at default `high`. Needs a key. Do it after the humour dial or the results
can't be attributed.

**7. Trim `WRITER_SYSTEM`'s faithfulness block** (known issue 9). D3 now independently checks six of
the eleven absolutes, so they *could* leave the prompt. **Do this on evidence, not speculatively:**
run a few fresh generations first and check D3 stays quiet with the rules still in place. Belt and
braces costs nothing; removing a rule that was doing real work is expensive to discover.

**8. Decide whether round reports are wanted** — 49 outstanding, ~$32. `RoundStoryPlan` is no longer
the blocker (it was ported on 2026-08-11); this is now purely a scope-and-cost call.

**9. Remote (webapp) report generation** (known issue 5) — tracked in `webapp/TODOS.md`.

**10. Whenever:** TEG 11's at-a-glance box renders differently from every other report, suggesting
`build_win_counts` returned nothing for that TEG. Cosmetic and self-contained.

---

**Not on this list, deliberately:** a full evaluation/regression harness. D3 is the proportionate
version and now exists; revisit a fuller harness only if D3's mechanical checks prove insufficient
in practice.

Cost reference: **~$0.65 per report** on Opus-tier. Total for the plan above: ~**$8** without round
reports, ~**$40** with.

---

## How to pick up in a clean session

1. Read this file top to bottom — five minutes.
2. Skim [README.md](README.md) for the architecture refresher — five more.
3. Start at [Next steps](#next-steps--ranked-to-do-list).
4. **Sanity-test any change by regenerating TEG 14** — it's the trickiest validated case (tight
   finish, multiple courses, the kind of pattern the writer wants to fabricate into a "rhyme") and
   any regression shows there first. Its fixture chain is complete again as of 2026-08-15. Baselines
   preserved at `teg_14_report_baseline.md` (pre-Step-1 chronological), `teg_14_report_step1.md`,
   `teg_14_report_pretighten.md` and `teg_14_report_prepayoff.md`.
5. Environment: `ANTHROPIC_API_KEY` (or `TEG_ANTHROPIC_API_KEY`) in the environment, else a gitignored
   `secrets.toml` at the repo root. `.streamlit/secrets.toml` still works but is **deprecated** —
   don't use it for new setups. Run with `venv/bin/python` from the repo root.
   **Or skip the key entirely:** `--plan` hands the prompts to a Claude Code session instead
   ([README.md](README.md) → *Who answers the prompts*).

## Historical verification record

**Phase F partial verification (2026-06-02)** — reports checked: TEGs 8, 9, 10 (tournament + all
rounds), TEG 11 (tournament + R1/R2), plus anchors TEG 14 (tournament + R1/R4) and TEG 18
(tournament + R3).

- **Sanity grep** — no hits in any `_final` report for `schizophrenic`, `unique double`,
  `countback`, `tiebreak`, `playoff`. All "same hole" references are within-round. ✅
- **Spot-reads** — TEG 8, 9, 10, 11 tournaments; TEG 14 R4; TEG 18 tournament: all faithful,
  correct arithmetic, correct framing. ✅ (One exception: the TEG 10 R3 error above.)
- **Structure** — all round styled reports carry the round-scores block, end-of-round standings and
  records block; all tournament styled reports carry final standings and a `class="records"` block. ✅

**A/B decision (TEG-9 prototype)** — chose **A: around-draft + repetition lint**. Most faithful
(bounded by the validated dry draft), still reads well. Rejected: *single-pass (B)* — good but more
freewheeling, loses the QA scaffold; *critique-revise (C)* — best polish, but the extra pass
fabricated a "countback" detail. Too risky for an insider audience.

**Dry-draft density A/B** — tested `detailed` vs `light` across TEGs 9, 14, 18. Verdict:
**detailed wins** — it floors the worst case (TEG 14 light was materially drier); light occasionally
edges on voice but loses hole-level specificity the insider audience wants. `dry_draft_style="detailed"`
is the default in `generate_dry_draft`; `light` remains available as a kwarg (useful for a future
fast/post-round mode).
