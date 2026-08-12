# Reporting Pipeline

**Starting a new chat session?** Read [ONBOARDING.md](ONBOARDING.md) first — it bootstraps context in one read.

LLM-generated, newspaper-style tournament reports for TEGs. UI-agnostic — lives in `teg_analysis/reporting/` and is consumed by both the FastAPI webapp (primary) and the legacy streamlit page.

Replaces the old `streamlit/commentary/` system. The old pipeline buried key events under rolling-window noise, lost hole-level colour in plumbing, had no editorial layer, and the prose model was reaching for the same dramatic words ("disaster", "meltdown", "catastrophe") report after report. The new pipeline foregrounds what mattered, retains specific hole detail, and has an explicit editorial stage between data and prose.

For the running ledger of what's done and what's deferred, see [STATUS.md](STATUS.md).

**Lost in the filenames?** [ARTEFACTS.md](ARTEFACTS.md) is the lookup: what every file in
`data/commentary/` is, and which one to restart from for a given change (including the
~$0.17 voice loop).

## Components — what you can change independently

The five stages below describe how a report is *built*. This section describes what can be
*changed*, which is a different cut and the more useful one when planning work. Components are
grouped into five themes, A–E, that run in order: each theme consumes the previous theme's output.
Within a theme, rows are independently editable.

Two things this cut gives you that the stage list doesn't: **which loop you're in** (themes differ by
orders of magnitude in cost per try), and **how finished each part is** (maturity column — several
rows are load-bearing and unbuilt).

### Theme A — Source & selection
**In:** `data/*.parquet` · **Out:** the bundle (~26k tokens) · **Cost per try:** free to full chain

What the report is *allowed to know*. Everything downstream can only work with what survives here.

| # | Component | In → Out | Lives in | Restart from | Cost | Maturity |
|---|---|---|---|---|---|---|
| A1 | **Raw facts — tournament** (scorecards, results, streaks) | parquet → `NotableEvent[]` | `core/data_loader`, `events.py` detectors | the data | full chain | **Works.** Era leak fixed 2026-08-11 — `hole_evidence` is era-aware. New `long_lead_lost` detector added |
| A2 | **Raw facts — context** (cross-TEG, course, venue, era) | parquet → context dicts | `history_context`, `course_history`, `venue`, `era`, `tournament_shape` | the data | full chain | **Works.** The duplicate `enrich` path was deleted 2026-08-11 |
| A3 | **Selection / weighting** — *what is notable enough to make the cut* | `NotableEvent[]` → ranked, trimmed beats | `scoring.py` (axis weights), `events.py` (sub-scores), `top_n` trim | cached beats | **free** (pure Python) | **Tuned 2026-08-11** to (1.5, 0.8, 0.7) — blow-ups 53%→38.5%, tone near-even. Arcs still bypass this layer but are now weighted at source. Re-measure with `scripts/weight_profiler.py` |

### Theme B — Editorial plan
**In:** the bundle · **Out:** `teg_N_story_plan.json` · **Cost per try:** ~$0.28 (plan only) / ~$0.65 (chain)

What the report will *say*, and in what order. The steerable artefact — for archive mode a human can
edit the JSON before authoring runs.

| # | Component | In → Out | Lives in | Restart from | Cost | Maturity |
|---|---|---|---|---|---|---|
| B1 | **Narrative vehicle** — the frame | bundle → `narrative_vehicles`, `prominent_vehicle` | `story_plan.SYSTEM_PROMPT` menu, `StoryPlan` fields | bundle | ~$0.65 | **Works.** The close-finish hard rule can finally fire — see B3 |
| B2 | **Report structure** — round-by-round vs theme-led, closing section | bundle → `narrative_structure`, `rounds[]` | `narrative_structure`, `WRITER_SYSTEM` STRUCTURE | bundle | ~$0.65 | **Works** |
| B3 | **Plan schema & shared vocabulary** — the editor↔writer contract | *(constrains B1/B2 and all of C)* | `story_plan.NARRATIVE_VEHICLES` / `PALETTE_VEHICLES` / `NARRATIVE_STRUCTURES` (single source of truth) | bundle | ~$0.65 | **Fixed 2026-08-11.** `Literal` enums; both prompts' menus generated from the constants; `check_plan_consistency()` catches combination violations |

### Theme C — Prose generation
**In:** plan + bundle · **Out:** `teg_N_report_final.md` · **Cost per try:** ~$0.17–$0.37

Turning the plan into text. Two rungs, and the cheaper one is where most iteration should happen.

| # | Component | In → Out | Lives in | Restart from | Cost | Maturity |
|---|---|---|---|---|---|---|
| C1 | **Factual scaffold** — the dry draft's density and shape | plan + bundle → `dry_draft.md` | `DRY_DRAFT_SYSTEM_DETAILED` / `_LIGHT`, `dry_draft_style=` | frozen plan | ~$0.37 | **Works, A/B settled** (detailed wins). The contradicting dead alias was removed 2026-08-11 |
| C2 | **Writing style / voice** | dry draft → finished prose | **`WRITER_VOICE`** (own constant since 2026-08-11) | frozen dry draft + plan | ~$0.17 | **Works, validated across 17 reports — but the target level is an open decision** (humour dial, unsettled) |

### Theme D — Assurance
**In:** finished prose + the source data · **Out:** a report you can trust · **Cost per try:** free to ~$0.17

Does the output match the data. **This is the least-built theme and the one carrying the most risk** —
the audience is the players themselves, who spot any factual error.

| # | Component | In → Out | Lives in | Restart from | Cost | Maturity |
|---|---|---|---|---|---|---|
| D1 | **Preventive rules** — instructions telling the writer not to fabricate | prompt → constrained prose | **`WRITER_FAITHFULNESS`** (own constant since 2026-08-11; 11 absolutes) | frozen dry draft + plan | ~$0.17 | **Built.** Still carries the 6 rules D3 now also checks — deliberate belt-and-braces; trim only once D3 has run on fresh generations |
| D2 | **Deterministic guarantees** — facts code emits so prose can't get them wrong | data → injected blocks | `render.py` standings / records / at-a-glance | `_report_final.md` | **free** | **Works well.** The strongest assurance mechanism in the pipeline |
| D3 | **Programmatic verification** — checking claims against the data after the fact | prose + data → findings | `verify.py` (7 checks), auto-run by `backfill.py` | `_report_final.md` | **free** | **Built 2026-08-11.** Independently re-found the TEG 10 R3 error and 41 reader-visible beat IDs in TEG 5 |

> **The determinism boundary is a policy, not a component.** For each class of fact, it decides
> whether code emits it (D2), the writer is trusted with it (D1), or the writer produces it and code
> checks it (D3). It used to be listed as its own row, which made it look editable; it isn't — it's
> the question you answer when deciding *which of D1–D3 a rule belongs in*.
>
> **Run it:** `python -m teg_analysis.reporting.verify --all --rounds`, or
> `verify_report(teg)` in code. `backfill.py` calls it after every generation, so a new report
> cannot ship with a mechanical fault unnoticed. Findings are reported, never raised — a flagged
> report is still written.

### Theme E — Presentation
**In:** `_report_final.md` · **Out:** what the reader sees · **Cost per try:** free

| # | Component | In → Out | Lives in | Restart from | Cost | Maturity |
|---|---|---|---|---|---|---|
| E1 | **Content injection** (which blocks, where) | final MD → styled MD | `render.py` | `_report_final.md` | **free** | **Works** |
| E2 | **Visual design** | styled MD → rendered page | `teg_reports.css` (×2 — see known issue 6) | `_styled.md` | **free** | **Works.** The two copies have drifted; `webapp/static/` is the live one. Resolves when `streamlit/` is deleted — editing it is forbidden by the project rules (known issue 6) |

### Cross-cutting — not components

The two rows that used to sit at the bottom of this table (scope, model config) were never components
in the same sense: they don't consume one theme's output and hand on to the next. They're listed
separately because that's what they are.

| Concern | What it actually is | Lives in | Maturity |
|---|---|---|---|
| **Scope — tournament vs round** | A **second instance of the whole A→E chain**, not a stage within one. `round_report.py` re-implements plan → draft → write → style for a single round. | `story_plan.py` vs `round_report.py` | **A generation behind at B1/B3** — `RoundStoryPlan` has no vehicles and no payoffs. Port before backfilling ~50 rounds |
| **Model & runtime config** | A **dial on every LLM row** (all of B, C, D1), not a step. Changing it re-prices whichever rows you're running. | `llm.DEFAULT_MODEL`, `output_config.effort` | **Pinned to `claude-opus-5`** (2026-08-11). `effort` is still never set anywhere, so every call runs at default `high` — untested lever (known issue 15) |

### What follows from this

- **Themes A, D2/D3 and E are free to iterate on.** Selection (A3) especially — `build_notable_events()`
  never calls an LLM, so the most powerful component in the pipeline can be tuned for nothing. See
  [EXPERIMENTS.md](EXPERIMENTS.md) → H10.
- **Never test a cheap-theme change by regenerating the expensive themes.** Changing voice (C2) means
  re-running Stage 4b against a *frozen* dry draft. Regenerating the plan as well changes two things
  at once and teaches you nothing.
- **D is deliberately separate from C, and now separate in the code too.** They have different
  failure modes (a factual error the players catch, vs a flat sentence) and different tests
  (mechanical verification, vs taste). Until 2026-08-11 that separation was conceptual only: voice
  and faithfulness lived in one 16k-character `WRITER_SYSTEM` literal, so every voice experiment
  edited the same string as the guardrails — one careless rewrite away from silently dropping a
  faithfulness rule. They are now `WRITER_VOICE` and `WRITER_FAITHFULNESS`, concatenated at import:

  ```python
  WRITER_SYSTEM = WRITER_VOICE + "\n" + WRITER_FAITHFULNESS + "\n" + WRITER_OUTPUT_RULE
  ```

  The composed string is byte-identical to the literal it replaced (asserted in tests), so nothing
  about generated output moved. Tune the humour dial by editing `WRITER_VOICE` alone.
- **Where the work is.** As of 2026-08-11 **D3, B3, A1's era leak and the model pin are all fixed**;
  see [STATUS.md](STATUS.md) → Known issues for the register. What remains is **A3** (weights
  measured, setting undecided) and **C2** (the humour dial) — both judgement calls, not defects —
  plus the 81 prose-wording faults D3 now reports across the older reports, which regeneration
  clears.

#### Why D3 would reduce the burden on D1

An open thought, assessed against the actual prompt: roughly **half of `WRITER_SYSTEM`'s 11
faithfulness absolutes are mechanically checkable**, and are currently enforced only by asking the
model nicely.

| Rule | Checkable? | How |
|---|---|---|
| No beat IDs in prose (`b07`, `cr01`) | **yes, trivially** | regex |
| No countback / tiebreaker / playoff | **yes, trivially** | vocabulary blocklist |
| Never call a 4-day TEG "a week" | **yes, trivially** | vocabulary blocklist |
| Only players who played this TEG | **yes** | extract names, diff against the roster |
| Weekdays verbatim from `venue.rounds[i].weekday` | **yes** | compare any weekday token against the venue record for that section |
| Arithmetic must be exact | **yes, with parsing** | sum the per-hole evidence behind each asserted total |
| `must_include_beat_ids` all covered | partially | needs semantic matching |
| Same hole number ≠ same hole across rounds | no | semantic |
| Stableford vs Gross is not a paradox | no | semantic |
| Relationships only from `player_relationships` | partially | relationship vocabulary near name pairs |
| Early lead changes aren't "chaos" | no | semantic — but **A3 is the real fix**, not a rule |

The six mechanical rules are the ones that trace to real incidents, and they're exactly the ones a
post-hoc check would catch *more* reliably than a prompt absolute — the TEG 10 R3 arithmetic error
happened with the rule already in the prompt. Moving them to D3 would let D1 shrink to the semantic
rules that genuinely need a model's judgement, which is also the targeted version of the known-issue-9
prompt-density fix.

Note this is already being done, just by hand and unrepeatably: STATUS.md's verification record
describes a **manual sanity grep** for `countback` / `tiebreak` / `playoff` / `unique double`. D3 is
mostly the job of turning that grep into code and running it on every generation.

### The plumbing — where each component sits and what it hands on

Every arrow is a place you can stop, freeze the artefact, and restart from later. That is what makes
the cheap loops cheap.

```
  data/*.parquet
        │  load_all_data()
        ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │ build_notable_events(teg)          ── detectors ──►  43–105 raw │  A1
  │ scoring.finalise(events, mode)     ── axis weights ─► ranked    │  A3  ← FREE loop
  └─────────────────────────────────────────────────────────────────┘
        │
        │   venue / history_context / course_history / era / tournament_shape   A2
        │   competition_arcs  ⚠ never trimmed — bypasses A3 entirely
        ▼
  assemble_bundle(teg, top_n=50)  ──────────────────────►  BUNDLE (~26k tok)  A3 (trim)
        │
        ▼
  build_story_plan(teg)            ─write─►  teg_N_story_plan.json    B1,B2,B3 ~$0.28
        │                                    ▲ restart point
        ▼
  generate_dry_draft(teg, plan)    ─write─►  teg_N_dry_draft.md       C1  (bundle re-sent) ~$0.20
        │                                    ▲ restart point
        ▼
  report_around_draft(teg, plan, dry) ─write─► teg_N_report_A_around_draft.md  C2, D1  ~$0.10
        │
        ▼
  repetition_lint(text)            ─write─►  teg_N_report_final.md    ~$0.07
        │                                    ▲ restart point ← the cheap-loop workhorse
        │
        │   ⚠ D3 (verification) would sit HERE — nothing runs at this point today
        ▼
  style_report(teg)                ─write─►  teg_N_report_styled.md   D2, E1   FREE
        │
        ▼
  webapp / streamlit  +  teg_reports.css                              E2       FREE
```

**Two structural facts the diagram makes visible:**

**1. `competition_arcs` skip the weighting step.**

Beats go through selection (A3): they get scored, ranked, and the bundle keeps roughly the top 50.
Arcs don't. They are attached to the bundle whole, whatever `top_n` says.

That matters because an arc and a beat can describe *the same event* — and disagree about how much
it mattered. A first-round lead change scores about 2.6/10 on importance, so as a beat it gets
downranked and usually trimmed out. But the arc still lists it, and still adds it to a headline
count like `n_lead_changes: 3`.

So the writer was shown "3 lead changes" with nothing to indicate all three were opening-morning
jockeying. Calling that "chaos" was a reasonable reading of what it had been given. **The prompt
rule forbidding the word "chaos" was patching a data problem** — the scorer already knew those
changes were routine; that judgement just never reached the writer.

Auditing the rest of the arc payload found the same shape in one more place, and cleared everything
else:

| Arc field | Verdict |
|---|---|
| `leader_by_round`, `winner_trajectory`, `decisive_takeover` (+ spoon equivalents) | **Fine.** Fixed size — one entry per round — and `decisive_takeover` *is* a weighted signal already: it names the single moment that settled it. |
| `lead_changes` / `n_lead_changes` | **The bug.** Grows with event count; every entry looked equally significant. |
| `bottom_changes` / `n_bottom_changes` | **The same bug, in the Wooden Spoon arc** — and worse, because spoon changes carried no outright/level flag at all, so there was nothing to filter on even if you wanted to. |

**Fixed 2026-08-11.** Every change now carries a `significance` (`routine` / `notable` /
`decisive`), each arc carries a summary with the early/late split and an `all_routine` flag, and the
Spoon arc has the outright distinction it was missing. TEG 18 — whose entire lead-change story is
three R1 changes — now reports `all_routine: true` explicitly. Detail in
[EXPERIMENTS.md](EXPERIMENTS.md) → H10 sub-finding.

**2. Stage 4a pays full price for a bundle Stage 3 already sent.**

Prompt caching only helps when the *cached prefix* is reused. The cache is on the system prompt, and
the ~26k-token bundle travels in the user message — so it isn't cached in the first place.

Stage 3 (story plan) and Stage 4a (dry draft) both send that bundle, under different system prompts.
Two different prefixes, no reuse: the bundle is paid for twice, at full rate.

That is why those two stages are **~74% of a report's cost** ($0.28 + $0.20 of $0.65) despite Stage
4b doing the actual writing. It also explains the cost ladder in the restart recipes: freezing the
plan and re-running from 4a costs ~$0.37, while freezing the dry draft too costs ~$0.17 — the
difference is almost entirely whether you re-send the bundle.

### Restart recipes

`authoring.load_story_plan()` and `authoring.load_dry_draft()` exist precisely so you can re-enter
mid-chain. Use them — don't regenerate what you aren't testing.

```python
# A3 — SELECTION. Free, no LLM. Compute beats once, re-score in memory.
from teg_analysis.reporting.events import build_notable_events
from teg_analysis.reporting import scoring
raw = build_notable_events(14)                      # slow (~30s), do once
ranked = scoring.finalise(list(raw), mode="fast")   # instant, repeat freely
# Sweep all four candidate weight settings at once: python scripts/weight_profiler.py

# B1/B2/B3 — PLAN. Needs the full chain from the plan down.
from teg_analysis.reporting import build_story_plan
plan = build_story_plan(14)["plan"]                 # ~$0.28
# …then dry draft → around draft → lint → style

# C1 — FACTUAL SCAFFOLD. Freeze the plan; re-run 4a onwards.
from teg_analysis.reporting.authoring import load_story_plan, generate_dry_draft
plan = load_story_plan(17)                          # frozen fixture
dry  = generate_dry_draft(17, plan, dry_draft_style="detailed")   # ~$0.20
# …then around draft → lint  (~$0.37 total)

# C2/D1 — VOICE + PREVENTIVE RULES. Freeze plan AND dry draft; re-run 4b only.
from teg_analysis.reporting.authoring import (
    load_story_plan, load_dry_draft, report_around_draft, repetition_lint)
plan = load_story_plan(17)                          # frozen fixture
dry  = load_dry_draft(17)                           # frozen fixture
rpt  = report_around_draft(17, plan, dry)           # ~$0.10
linted, _ = repetition_lint(rpt["text"])            # ~$0.07
# total ~$0.17 — no story plan regenerated, so voice is the only variable

# D2/E1 — DETERMINISTIC BLOCKS + INJECTION. Free; reads _report_final.md.
from teg_analysis.reporting.render import style_report
style_report(17)

# D3 — VERIFICATION. Nothing to run: not built.

# E2 — VISUAL. No Python at all: edit teg_reports.css and reload.

# Inspect the Stage-3 input without spending anything:
build_story_plan(14, dry_run=True)                  # writes teg_14_story_plan_prompt.md
```

### Fixture set

Iterating on themes C, D and E needs a frozen artefact chain to restart from — specifically
`story_plan.json` **and** `dry_draft.md`. **11 of 17 TEGs have both**; the current list, and which
files each TEG is missing, is in [ARTEFACTS.md](ARTEFACTS.md) → "Which TEGs can I iterate voice on?".

> ⚠️ **TEG 14 — the standing stress-test anchor — is missing `dry_draft.md` and `report_final.md`.**
> The humour and tighten experiments consumed them into variant filenames, so the two cheapest
> iteration loops are broken on the very case chosen for being hardest. Rebuilding costs one full
> generation (~$0.65). Use **TEG 17 or 12** meanwhile — both current-vintage with complete chains.

## The five stages

```
                                                          (LLM ────────────┐
       (code) ──────────────────────────────►    (LLM)                     ▼
data ──► 1. Stage 1: The Record  ──┐          ┌─► 3. Story plan ──► 4a. Dry draft ──► 4b. Report ──► lint ──► 5. Styled MD
         2. Stage 2: scored beats ──┤         │                                                                  │
            + competition arcs      │   bundle│                                                                  ▼
            + venue context  ───────┘ ────────┘                                                              UI render
                                                                                                   (webapp + streamlit)
```

### 1. The Record (code, reference)

Full hole-by-hole data. Treated as a lookup, not writer input — the old pipeline force-fed everything; the new pipeline only surfaces what's been scored as notable.

Reuses `teg_analysis.core.data_loader.load_all_data()`.

### 2. Notable-event detection + 3-axis scoring (code) — `events.py` / `scoring.py`

`build_notable_events(teg, mode=)` returns a ranked list of `NotableEvent` objects. Detectors:

- Lead/spoon changes (with `outright` vs `level` flag from per-hole rank-1 counts)
- Long-held leads lost (`_lead_tenure_events`) — a companion to lead changes: walks the hole-by-hole
  outright-leader sequence and flags spells of 18+ holes (roughly a full round) that end in an
  outright takeover by someone else, for both Trophy and Green Jacket. Distinct from an ordinary
  lead-change beat because it scores on tenure length and rounds spanned, not just round-lateness.
- Maximal cold/hot stretches (no overlapping-window spam)
- Recoveries (birdie ending a bogey run) / collapses (blow-up ending a steady run)
- Standout single holes (eagles / HIO / big blow-ups)
- Per-round and tournament beats (round shapes, winners, margins)

Each beat carries:

- Its **hole-by-hole evidence** — `[{hole, par, sc, grossvp, stableford, result}]` — so the writer can render specifics like "a double at the par-4 10th and a 10 at the short 17th", never vague abstractions.
- Its **course** (the round it was played in) — so the same hole *number* in different rounds is never mistaken for "the same hole".
- Three scores on a 0–10 scale: **importance** (contribution to the result, scored at top *and* bottom of the board), **rarity** (vs TEG history — PBs, records, records-to-date), **entertainment** (colour independent of result — non-contender brilliance/disaster).

Weights per axis are a dial per mode (`balanced` / `fast` / `archive`).

`events.py` also assembles a **competition arc** for each of Trophy / Green Jacket / Wooden Spoon — leader-by-round, winner-or-loser trajectory, lead changes (with outright/level flags), the decisive moment. These arcs are the report's spine.

### Venue context — `venue.py`

`build_venue_context(teg)` returns the area, year, area-visit count, and per-round course metadata (full name, location, type, designer, one-line description, visit number, visit_str like *"the 3rd TEG round at this venue"*, and a verified `weekday`).

Sourced from `data/round_info.csv` + `data/course_info.csv` (the latter relocated from `streamlit/commentary/course_info.py` so `teg_analysis` stays UI-agnostic).

### Context modules feeding the bundle

Four further code-only modules assemble context alongside the beats. All are pure Python — no LLM, no cost.

| Module | Provides | Used for |
|---|---|---|
| `era.py` | `trophy_metric(teg)` → `"stableford"` (TEG 8+) or `"net_vs_par"` (TEGs 1–7) | Every era-sensitive branch in `events`, `story_plan`, `authoring`, `round_report`, `render` |
| `history_context.py` | `build_player_cross_teg_history(teg)` — career storyline phrases per player (Nth Trophy/Jacket/Spoon, back-to-back, first win in N years, defending champion, "first Trophy after 2 runner-up finishes"). Also `build_win_counts(teg)` | Bundle's `player_history`; the deterministic at-a-glance win counts in `render` |
| `course_history.py` | `build_player_course_history(teg)` — first visit / Nth visit / personal best here / strokes vs last visit. `detect_course_records(teg)` — new course gross records (good or bad) | Bundle's `player_course_history`; new course records become **mandatory beats** |
| `tournament_shape.py` | `detect_close_finish(arcs, metric)` — deterministic close-finish signal. `recent_vehicle_choices(teg, n=3)` — what narrative vehicles the last few reports used | Bundle's `tournament_shape` (drives the close-finish **hard rule**) and `recent_vehicle_choices` (drives the anti-repetition **soft rule**) |

Verified `player_relationships` (from `teg_analysis.constants.PLAYER_RELATIONSHIPS`, filtered to players in this TEG) are also passed in the bundle. The writer is forbidden from inferring any relationship not listed there — shared surnames are not evidence.

### 3. Story plan — `story_plan.py`

The missing editorial layer. `build_story_plan(teg, mode=, tone=, dry_run=)`:

- Assembles the input bundle (scored beats + arcs + venue) and a token-lean JSON.
- Calls the model pinned in `llm.DEFAULT_MODEL` with adaptive thinking, prompt caching on the (large, stable) system prompt, and structured Pydantic output.
- Returns a validated `StoryPlan` and writes `data/commentary/teg_N_story_plan.json`.

Schema:

```
title, title_candidates[], theme, tone,
narrative_structure,                  # chronological | in_medias_res | theme_led | free-form
opening_hook,
narrative_vehicles[],                 # 1-3 named storytelling frames (see menu below)
prominent_vehicle,                    # the one being foregrounded
foreshadow[],                         # hooks to plant early that pay off later
payoffs[]:                            # one per foreshadow seed where possible
  { seed, resolves_in, payoff }
competitions[]:                       # Trophy → Jacket → Spoon (priority order)
  { name, winner_or_loser, how, key_beat_ids[] }
rounds[]:
  { round, headline_candidates[], chosen_headline, angle, beat_ids[] }
players[]: { player, arc }
must_include_beat_ids[], cuts[],
venue_notes,
# thread-organised extras (optional; empty unless the data supports them)
competition_storyline_bullets{}, player_storyline_bullets{},
course_history_notes[], decisive_moments[]
```

**Narrative vehicles** are a shared vocabulary between the editor and the writer, so the editor's
structural choice actually binds the prose. The menu spans structural frames (`bookends`, `motif`,
`dual_narrative`, `counterfactual`, `catalogue`, `inevitability`), historical-context frames
(`hero_arc`, `comeback`, `inversion`, `origin`, `underdog`) and stylistic ones (`chronological`,
`in_medias_res`, `reverse_chronology`, `three_act`, `theme_led_body`). Two rules govern selection:

- **Hard rule — close finish wins.** When `tournament_shape.close_finish` is true, `prominent_vehicle`
  MUST be `counterfactual` (or `dual_narrative` if two players carried the finish). The close finish
  *is* the story; historical framing can ride alongside but cannot displace it.
- **Soft rule — vary against recent picks.** `recent_vehicle_choices` shows the last few TEGs'
  selections; when the data is ambiguous, prefer a different combination. The hard rule supersedes.

`payoffs[]` exists because foreshadow-without-payoff was the most common thinness in earlier reports:
every seed planted in the opener must be named against the section that resolves it.

This is the steerable artefact — for `archive` mode a human can edit the JSON before authoring runs.

`dry_run=True` writes the assembled prompt + bundle to disk without calling the API — useful for inspecting inputs with no key.

### 4. Authoring — `authoring.py`

**4a. Dry storyline draft** — `generate_dry_draft(teg, plan)`. A plain, factual narrative spelled out from the plan + hole evidence, no colour. Two purposes:

- *Sense-check*: validates Stages 2–3 in prose form before any styling effort.
- *Scaffold*: the entertaining report (4b) is built around it, which bounds drift.

**4b. Entertaining report** — `report_around_draft(teg, plan, dry_text)`. Rewrites the dry draft into the finished report in the house voice (Ronay/Peck). Because it can only use facts already in the validated draft, it stays faithfully grounded.

(Two alternates exist for comparison — `report_single_pass` and `report_critique_revise` — see [STATUS.md](STATUS.md) for why they were rejected.)

**Repetition lint** — `repetition_lint(text)`. A narrow final pass whose only job is replacing repeated/over-used words. Doesn't change facts or structure. Runs on Haiku 4.5.

#### Optional extra pass (built, not in the default chain)

- **`tighten_prose(text)`** (`TIGHTEN_SYSTEM`) — sandpapers over-built constructions: em-dash ceiling
  of two per paragraph, subordinate-clause budget, no subject-burying preambles, punchline isolation,
  one dominant idea per paragraph. The same 11 rules are also baked into `WRITER_SYSTEM`'s ECONOMY
  block so the writer constructs tight on the first pass, which makes this pass largely a fix-up
  lever for older text. Not called by `backfill.py`.

> `enrich_report_with_history()` / `ENRICH_SYSTEM` / `build_history_enrichment_context()` were
> **deleted on 2026-08-11**. They had zero callers and computed the same class of fact the bundle
> already feeds the writer via `player_history`. Recoverable from git if that call was wrong.

### 5. Styling — `render.py`

`style_report(teg)` reads `teg_N_report_final.md` and adds the CSS-class hooks the UI needs:

- `{.report-title}` on the H1
- `<p class="dateline">TEG N | {area} | {year}</p>` after the title
- `<section class="callout at-a-glance-box">` with Trophy/Jacket/Spoon winners (from the plan)
- `{.roundN .round}` on each `## Round N` heading

Stage 5 also injects **deterministic data blocks** — the safety net that means the facts ship even if the prose skips them:

- **Standings.** `build_round_standings(teg)` computes end-of-round standings; they are injected under each `## Round N` heading. If the writer took a theme-led route with no round headings, a consolidated "Standings by round" appendix is inserted before the player closing instead.
- **Records appendix.** `build_records_block(teg, round=None)` appends a `class="records"` inventory of every personal best, TEG record, nine-hole record and rare feat, de-duplicated across rounds.
- **At-a-glance.** The `callout at-a-glance-box` names Trophy/Jacket/Spoon winners and annotates each with its ordinal win count from `history_context.build_win_counts()` (e.g. "his 3rd Trophy").

Writes `teg_N_report_styled.md`. Idempotent. The styled MD plus `teg_reports.css` (in `streamlit/styles/` and `webapp/static/`) produces the visual styling; same file serves both UIs.

## Round reports — `round_report.py`

A parallel, single-round pipeline with the same shape: `assemble_round_bundle` → `build_round_story_plan` (`ROUND_PLAN_SYSTEM`, `RoundStoryPlan`) → `generate_round_dry_draft` → `report_round_around_draft` → lint → `render.style_round_report`. `generate_round_report(teg, round)` runs the lot.

Differences from the tournament pipeline: the bundle carries prior-round context and the competition state at the end of the round, not the whole tournament arc; `render.build_round_scores(teg, round)` puts a deterministic round-scores block at the top; there is no "men in brief" closing; the default structure is chronological/player-by-player; and the final round gets coronation-aware framing.

> **Currently a generation behind.** `RoundStoryPlan` has no `narrative_vehicles` and no `payoffs` — the vehicle and setup→payoff machinery was only added to the tournament plan. See [STATUS.md](STATUS.md).

## Batch generation — `backfill.py`

`backfill_all(teg_nums, scope="both"|"tournament"|"rounds", force=False)` generates the canonical set for a list of TEGs. `build_notable_events` and `build_venue_context` are computed once per TEG and reused across the tournament and round runs — that's the heaviest pure-Python step. Idempotent: skips a report whose `_final.md` already exists unless `force=True`.

```python
from teg_analysis.reporting.backfill import backfill_all
backfill_all(range(8, 19))                                # TEGs 8-18, tournament + rounds
backfill_all([8, 9, 10], scope="tournament", force=True)  # re-run tournaments only
```

## Artefacts

**Full reference: [ARTEFACTS.md](ARTEFACTS.md)** — what every file in `data/commentary/` is, which
one to restart from for a given change, and a decoder for the experiment/snapshot filenames.

The short version: five files make up the live chain, in order —

| File | What it is | Cost to produce |
|---|---|---|
| `teg_N_story_plan.json` | the editorial plan (no prose) | ~$0.28 |
| `teg_N_dry_draft.md` | the facts, plainly stated | ~$0.20 |
| `teg_N_report_A_around_draft.md` | first pass with the voice on | ~$0.10 |
| `teg_N_report_final.md` | **the canonical text** (post word-lint) | ~$0.07 |
| `teg_N_report_styled.md` | **what the site serves** (+ tables, CSS hooks) | free |
| **Total** | | **~$0.65** |

Round artefacts use the same names with a `round_R_` infix. Note the **bundle is not a file** — it's
assembled in memory each run; dump it with `build_story_plan(teg, dry_run=True)`.

## End-to-end (archive mode, one TEG)

```python
from teg_analysis.reporting import build_story_plan, generate_dry_draft, style_report
from teg_analysis.reporting.authoring import report_around_draft, repetition_lint

teg = 9
plan = build_story_plan(teg)["plan"]
dry  = generate_dry_draft(teg, plan)
rpt  = report_around_draft(teg, plan, dry["text"])
linted, _ = repetition_lint(rpt["text"])
open(f"data/commentary/teg_{teg}_report_final.md", "w").write(linted)
style_report(teg)  # → teg_N_report_styled.md, ready for the UI
```

## Configuration

- **Tone dial**: `tone=` input on `build_story_plan` (default `"house"` = Ronay/Peck). Plan echoes the resolved tone for the writer.
- **Mode**: `balanced` / `fast` / `archive` — controls scoring weights (fast leans on importance; archive cranks rarity + entertainment).

### API key

`ANTHROPIC_API_KEY` from the environment is the supported route; a gitignored
`secrets.toml` at the repo root is the fallback. Resolution order is in
`llm.get_api_key()`.

> **`.streamlit/secrets.toml` is deprecated as a key location.** It still works so
> existing local checkouts don't break, but it is streamlit legacy and should not be
> used for new setups — put the key in the environment, or in a root `secrets.toml`
> (both are covered by the `**/secrets.toml` gitignore rule). Nothing in
> `teg_analysis` imports streamlit.

| Where you're running | How to set it |
|---|---|
| Local shell | `export ANTHROPIC_API_KEY=sk-ant-…` (add to your shell profile to persist) |
| Local, persisted to the repo | `secrets.toml` at the repo root: `ANTHROPIC_API_KEY = "sk-ant-…"` |
| Railway (webapp) | Service → Variables → add `ANTHROPIC_API_KEY` |
| Claude Code on the web | The session container gets its variables from the **environment** config, not from this repo. Add `ANTHROPIC_API_KEY` to the environment's variables so it's present in every session; a key pasted into a chat only lasts that session and ends up in the transcript. |

Report generation needs the key. Everything upstream of Stage 3 (beats, arcs, venue,
history, records, rendering) is pure Python and runs without one — including
`build_story_plan(teg, dry_run=True)`, which writes the assembled prompt to disk for
inspection with no API call.

### Model selection

`llm.DEFAULT_MODEL` is the single place the model is pinned; every stage accepts a
`model=` override, so per-stage selection needs no refactor.

**There is no floating "latest" alias.** `claude-opus-5` / `claude-sonnet-5` *are*
the aliases — they carry no date suffix and never need one — but they pin a
**generation**, and a new generation does not roll in automatically. Nor should it:
a silent model change under a fixed prompt is exactly the kind of thing that would
quietly alter every report's voice.

So the protection against running stale is procedural, not automatic:

1. Keep the pin in `DEFAULT_MODEL` only — never hardcode a model at a call site.
2. Re-check at each Claude release. Within a tier the newer generation is usually
   the **same price** (Opus 4.7 → Opus 5 is $5/$25 per MTok either way), so staying
   on an old generation isn't cheaper — it's the same spend for less capability.
3. `client.models.list()` / `.retrieve(id)` returns live context windows, output
   caps and capability flags if you want to check what's current from code.

`output_config.effort` is **not currently set anywhere**, so every call runs at the
default (`high`). It is the primary cost/latency lever and is untested here — see
[EXPERIMENTS.md](EXPERIMENTS.md).

## UI surfaces

- **Webapp (primary)** — `/teg-reports` page (see `webapp/routes/reports.py` + `webapp/templates/teg_reports.html`) and the Report tab on `/results` (see `webapp/routes/history.py` `_results_context()` `tab == "report"` branch).
- **Streamlit (legacy, still wired)** — `streamlit/teg_reports.py` prefers the new styled MD, falls back to the legacy `teg_N_main_report.md`.

Both render via the `markdown` library with the `extra`/`sane_lists`/`smarty`/`toc` extensions; same CSS file in both static dirs.

## Design rules (locked decisions)

- **Audience**: the players themselves — insiders who spot any factual error and want to relive the tournament being gently ribbed. Favour faithfulness over flair.
- **Voice**: Barney Ronay (Guardian) / Tom Peck (Times political sketches), with Jesse Armstrong (Succession) and Armando Iannucci (The Thick of It). British English, no exclamation marks, no obvious puns. The core mechanism is **subverted gravitas** — treat trivial stakes with the solemnity of a geopolitical crisis; the humour lives in the gap. Never wink at the camera.
- **Spine**: Trophy → Green Jacket (Gross) → Wooden Spoon, with explicit "how each was won/lost" drawn from the competition arcs. The Trophy metric is era-dependent: Stableford for TEG 8+, net-vs-par for TEGs 1–7.
- **Structure**: story-led, with rounds as natural blocks. Each round gets a chosen witty headline plus 2 alternate candidates for the archive editor. Chronology is a scaffold, not a constraint — the editor's `narrative_structure` and `narrative_vehicles` set the shape.
- **Economy**: 11 construction rules in `WRITER_SYSTEM` (two em-dashes per paragraph max; no subject-burying preambles; two equal facts = two sentences; punchline isolation; one dominant idea per paragraph). Length must be earned by facts or images.
- **Faithfulness rules** (enforced in scoring AND in prompts):
  - Use only supplied data; never invent.
  - Honour `outright` vs `level` lead changes — drawing level is not a takeover.
  - The same hole *number* in different rounds is a different hole (almost always on a different course) — never "the same hole" / "same-hole rhyme".
  - Early-round lead changes (field still bunched) are routine, not "chaos" or drama.
  - Player names proper-cased at source (no all-caps surnames in prose).
  - **No countback, tiebreaker or playoff** — those mechanisms do not exist in TEG.
  - **Stableford and Gross measure different things.** A split between the two is ordinary handicapping, never a paradox or a "unique double".
  - **Relationships only from `player_relationships`.** Shared surnames are not evidence of anything.
  - **Weekdays only from `venue.rounds[i].weekday`, verbatim, and only in that round's opener.** Everywhere else use round numbers. A TEG is four consecutive days — never "a week".
  - **Only players who actually played this TEG** appear in the prose.
  - **Arithmetic must be exact** — any stated total must equal the sum of the per-hole evidence.
  - **No beat IDs in the prose** (`b07`, `cr01`) — they are internal identifiers.

## Where to read

| File | What |
|---|---|
| `events.py` | Stage 2 — detectors, competition arcs, 3-axis scoring |
| `scoring.py` | 3-axis combination + mode weights |
| `venue.py` | Venue / course context |
| `era.py` | Trophy metric by TEG (the pre/post-8 switch) |
| `history_context.py` | Cross-TEG career storylines, milestones, win counts |
| `course_history.py` | Per-course player history + course-record detection |
| `tournament_shape.py` | Close-finish signal + recent-vehicle anti-repetition |
| `story_plan.py` | Stage 3 + the editor system prompt (incl. the vehicle menu) |
| `authoring.py` | Stage 4 + all writer/lint/tighten system prompts |
| `round_report.py` | The per-round pipeline and its prompts |
| `render.py` | Stage 5 — CSS hooks, standings, records block |
| `verify.py` | **D3** — mechanical verification of a finished report against the data |
| `backfill.py` | Batch orchestration across TEGs |
| `llm.py` | Thin Anthropic wrapper (key resolution + prompt caching) |

Suggested reading order for a fresh session is in [ONBOARDING.md](ONBOARDING.md).

## Status

See [STATUS.md](STATUS.md) for the pick-up ledger: what's published, which reports are on which
pipeline vintage, the open decisions, and known issues. Running experiment log in
[EXPERIMENTS.md](EXPERIMENTS.md).
