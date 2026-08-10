# Reporting Pipeline

**Starting a new chat session?** Read [ONBOARDING.md](ONBOARDING.md) first — it bootstraps context in one read.

LLM-generated, newspaper-style tournament reports for TEGs. UI-agnostic — lives in `teg_analysis/reporting/` and is consumed by both the FastAPI webapp (primary) and the legacy streamlit page.

Replaces the old `streamlit/commentary/` system. The old pipeline buried key events under rolling-window noise, lost hole-level colour in plumbing, had no editorial layer, and the prose model was reaching for the same dramatic words ("disaster", "meltdown", "catastrophe") report after report. The new pipeline foregrounds what mattered, retains specific hole detail, and has an explicit editorial stage between data and prose.

For the running ledger of what's done and what's deferred, see [STATUS.md](STATUS.md).

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
| `history_context.py` | `build_player_cross_teg_history(teg)` — career storyline phrases per player (Nth Trophy/Jacket/Spoon, back-to-back, first win in N years, defending champion, "first Trophy after 2 runner-up finishes"). Also `build_history_enrichment_context(teg)` and `build_win_counts(teg)` | Bundle's `player_history`; the deterministic at-a-glance win counts in `render` |
| `course_history.py` | `build_player_course_history(teg)` — first visit / Nth visit / personal best here / strokes vs last visit. `detect_course_records(teg)` — new course gross records (good or bad) | Bundle's `player_course_history`; new course records become **mandatory beats** |
| `tournament_shape.py` | `detect_close_finish(arcs, metric)` — deterministic close-finish signal. `recent_vehicle_choices(teg, n=3)` — what narrative vehicles the last few reports used | Bundle's `tournament_shape` (drives the close-finish **hard rule**) and `recent_vehicle_choices` (drives the anti-repetition **soft rule**) |

Verified `player_relationships` (from `teg_analysis.constants.PLAYER_RELATIONSHIPS`, filtered to players in this TEG) are also passed in the bundle. The writer is forbidden from inferring any relationship not listed there — shared surnames are not evidence.

### 3. Story plan — `story_plan.py`

The missing editorial layer. `build_story_plan(teg, mode=, tone=, dry_run=)`:

- Assembles the input bundle (scored beats + arcs + venue) and a token-lean JSON.
- Calls Claude Opus 4.7 with adaptive thinking, prompt caching on the (large, stable) system prompt, and structured Pydantic output.
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

#### Optional extra passes (built, not in the default chain)

Two further passes exist as separate levers. **Neither is called by `backfill.py`** — see [STATUS.md](STATUS.md) → Known issues before relying on them.

- **`tighten_prose(text)`** (`TIGHTEN_SYSTEM`) — sandpapers over-built constructions: em-dash ceiling of two per paragraph, subordinate-clause budget, no subject-burying preambles, punchline isolation, one dominant idea per paragraph. The same 11 rules are also baked into `WRITER_SYSTEM`'s ECONOMY block so the writer constructs tight on the first pass, which makes this pass largely a fix-up lever for older text.
- **`enrich_report_with_history(teg)`** (`ENRICH_SYSTEM`) — a targeted insert-only pass that weaves 3–7 pre-verified achievement phrases from `history_context.build_history_enrichment_context()` into an already-written report, without restructuring it.

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

## Artefacts (per TEG, under `data/commentary/`)

| File | Stage | Cost |
|---|---|---|
| `teg_N_notable_events.md` | 2 (inspection) | free |
| `teg_N_venue_context.md` | 2 (inspection) | free |
| `teg_N_story_plan_prompt.md` | 3 (dry-run input check) | free |
| `teg_N_story_plan.json` | 3 (live) | ~$0.28 |
| `teg_N_dry_draft.md` | 4a | ~$0.20 |
| `teg_N_report_A_around_draft.md` | 4b | ~$0.10 |
| `teg_N_report_final.md` | 4b + lint | ~$0.07 |
| `teg_N_report_styled.md` | 5 | free |
| **Total per report (Opus 4.7)** | | **~$0.65** |

Round artefacts follow the same names with a `round_{r}_` infix (`teg_N_round_2_story_plan.json`, `teg_N_round_2_report_styled.md`, …).

**Naming conventions for everything else in the folder.** `data/commentary/` also holds a lot of experiment output; the convention is worth knowing before you go looking for the live file:

| Pattern | Meaning |
|---|---|
| `teg_N_report_styled.md` | **the live report** — this is what the UI renders |
| `teg_N_report_{pre*}.md` | a snapshot of the report *before* a named prompt change (`prevehicles`, `prepayoff`, `preclose`, `pretighten`, `pre_detailed_baseline`, `pre_phaseA`) |
| `teg_N_report_{variant}.md` | an A/B variant (`humour6`, `humour8`, `humour8b`, `tightened`, `light`, `detailed`, `B_single_pass`, `C_critique_revise`) |
| `teg_N_{tournament_,}v0…v5_*.md` | the voice-ladder experiment (`existing`, `baseline`, `restraint`, `economy`, `observer`, `gravitas`) |
| `archive 2026 v1/`, `archive 2026 v2/` | full snapshots of two earlier generations of the whole library |
| `archive 2025/`, `drafts/`, `round_reports/` | the pre-pipeline 2025 system's output; still the webapp's fallback read paths |

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

- **Model**: default `claude-opus-4-7` (per-call override via `model=`).
- **API key**: `ANTHROPIC_API_KEY` env var, else `.streamlit/secrets.toml` at the repo root (gitignored — see `.streamlit/secrets.toml.template`).
- **Tone dial**: `tone=` input on `build_story_plan` (default `"house"` = Ronay/Peck). Plan echoes the resolved tone for the writer.
- **Mode**: `balanced` / `fast` / `archive` — controls scoring weights (fast leans on importance; archive cranks rarity + entertainment).

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
| `authoring.py` | Stage 4 + all writer/lint/tighten/enrich system prompts |
| `round_report.py` | The per-round pipeline and its prompts |
| `render.py` | Stage 5 — CSS hooks, standings, records block |
| `backfill.py` | Batch orchestration across TEGs |
| `llm.py` | Thin Anthropic wrapper (key resolution + prompt caching) |

Suggested reading order for a fresh session is in [ONBOARDING.md](ONBOARDING.md).

## Status

See [STATUS.md](STATUS.md) for the pick-up ledger: what's published, which reports are on which
pipeline vintage, the open decisions, and known issues. Running experiment log in
[EXPERIMENTS.md](EXPERIMENTS.md).
