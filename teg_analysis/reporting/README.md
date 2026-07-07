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

`build_venue_context(teg)` returns the area, year, area-visit count, and per-round course metadata (full name, location, type, designer, one-line description, visit number, visit_str like *"the 3rd TEG round at this venue"*).

Sourced from `data/round_info.csv` + `data/course_info.csv` (the latter relocated from `streamlit/commentary/course_info.py` so `teg_analysis` stays UI-agnostic).

### 3. Story plan — `story_plan.py`

The missing editorial layer. `build_story_plan(teg, mode=, tone=, dry_run=)`:

- Assembles the input bundle (scored beats + arcs + venue) and a token-lean JSON.
- Calls Claude Opus 4.7 with adaptive thinking, prompt caching on the (large, stable) system prompt, and structured Pydantic output.
- Returns a validated `StoryPlan` and writes `data/commentary/teg_N_story_plan.json`.

Schema:

```
title, title_candidates[], theme, tone,
foreshadow[],                         # hooks to plant early that pay off later
competitions[]:                       # Trophy → Jacket → Spoon (priority order)
  { name, winner_or_loser, how, key_beat_ids[] }
rounds[]:
  { round, headline_candidates[], chosen_headline, angle, beat_ids[] }
players[]: { player, arc }
must_include_beat_ids[], cuts[],
venue_notes
```

This is the steerable artefact — for `archive` mode a human can edit the JSON before authoring runs.

`dry_run=True` writes the assembled prompt + bundle to disk without calling the API — useful for inspecting inputs with no key.

### 4. Authoring — `authoring.py`

**4a. Dry storyline draft** — `generate_dry_draft(teg, plan)`. A plain, factual narrative spelled out from the plan + hole evidence, no colour. Two purposes:

- *Sense-check*: validates Stages 2–3 in prose form before any styling effort.
- *Scaffold*: the entertaining report (4b) is built around it, which bounds drift.

**4b. Entertaining report** — `report_around_draft(teg, plan, dry_text)`. Rewrites the dry draft into the finished report in the house voice (Ronay/Peck). Because it can only use facts already in the validated draft, it stays faithfully grounded.

(Two alternates exist for comparison — `report_single_pass` and `report_critique_revise` — see [STATUS.md](STATUS.md) for why they were rejected.)

**Repetition lint** — `repetition_lint(text)`. A narrow final pass whose only job is replacing repeated/over-used words. Doesn't change facts or structure.

### 5. Styling — `render.py`

`style_report(teg)` reads `teg_N_report_final.md` and adds the CSS-class hooks the UI needs:

- `{.report-title}` on the H1
- `<p class="dateline">TEG N | {area} | {year}</p>` after the title
- `<section class="callout at-a-glance-box">` with Trophy/Jacket/Spoon winners (from the plan)
- `{.roundN .round}` on each `## Round N` heading

Writes `teg_N_report_styled.md`. Idempotent. The styled MD plus `teg_reports.css` (in `streamlit/styles/` and `webapp/static/`) produces the visual styling; same file serves both UIs.

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
- **Voice**: Barney Ronay (Guardian) / Tom Peck (Times political sketches). Witty, characterful, anchored. Never zany or over the top.
- **Spine**: Trophy (Stableford) → Green Jacket (Gross) → Wooden Spoon, with explicit "how each was won/lost" drawn from the competition arcs.
- **Structure**: story-led, with rounds as natural blocks. Each round gets a chosen witty headline plus 2 alternate candidates for the archive editor.
- **Faithfulness rules** (enforced in scoring AND in prompts):
  - Use only supplied data; never invent.
  - Honour `outright` vs `level` lead changes — drawing level is not a takeover.
  - The same hole *number* in different rounds is a different hole (almost always on a different course) — never "the same hole" / "same-hole rhyme".
  - Early-round lead changes (field still bunched) are routine, not "chaos" or drama.
  - Player names proper-cased at source (no all-caps surnames in prose).

## Where to read

- `events.py` — Stage 2 (detectors, arcs, 3-axis scoring)
- `scoring.py` — 3-axis combination + mode weights
- `venue.py` — venue context
- `story_plan.py` — Stage 3 + the editor system prompt
- `authoring.py` — Stage 4 + the writer/lint system prompts
- `render.py` — Stage 5 (CSS-class hooks)
- `llm.py` — thin Anthropic wrapper (key resolution + prompt caching)

## Status

See [STATUS.md](STATUS.md) for the running ledger of what's done and what's deferred (the round-by-round variant, fast/archive modes, batch-scale, the pre-TEG-8 backfill run, optional faithfulness-check pass).
