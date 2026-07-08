# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## General Claude Rules
1. Ask, don't assume. If something is unclear, ask before writing a single line. Never make silent assumptions about intent, architecture, or requirements. When running unattended, pick the most reasonable interpretation, proceed, and record the assumption rather than blocking.

2. Implement the simplest solution for simple problems, better solutions for harder problems. Do not over-engineer or add flexibility that isn't needed yet. 

3. Don't touch unrelated code but please do surface bad code or design smells you discover with me so we can address them as a separate issue.

4. Flag uncertainty explicitly. If you're unsure about something, see point 1 above. If it makes sense to do so, conduct a small, localised and low-risk experiment and bring the hypothesis and results to me to discuss. Confidence without certainty causes more damage than admitting a gap.

5. I'm always open to ideas on better ways to do things. Please don't hesitate to suggest a better way, or one that has long lasting impact over a tactical change. (as a few examples)


## Project Overview

TEG v2 is a golf tournament analysis project. It has two architectural layers: a legacy, self-contained Streamlit app (kept as a stable reference) and a newer decoupled architecture — a UI-agnostic `teg_analysis/` Python package plus a `webapp/` FastAPI frontend, which is **now the site deployed on Railway from `main`** (it replaced the Streamlit app). All new analytical work belongs in `teg_analysis/`.

## Domain knowledge

- A **TEG** is an annual golf tournament. Each TEG consists of several rounds (usually 4), each of 18 holes split into a front 9 (holes 1–9) and back 9 (holes 10–18).
- There are two competitions per TEG: **gross** and **net**. Up to TEG 7, net was total net vs par; from TEG 8 onwards it is total Stableford points.

## To-dos

**[TODOS.md](TODOS.md)** is the central to-do index. Each area (`webapp/`, `streamlit/`, `teg_analysis/`) has its own `TODOS.md`; the root file links to all of them and holds cross-cutting items (data updates). When a to-do surfaces mid-conversation, add it to the right area's `TODOS.md` before ending the session.

## Note on documentation

Do not read or reference `to_do_jon.md` unless the user explicitly asks you to. It is a personal draft notes file, not project documentation.

## Development Commands

```bash
# View outstanding to-dos across the project
python todos.py          # outstanding items only
python todos.py --all    # include completed items

# Run the webapp (active development)
uvicorn webapp.app:app --reload

# Run the Streamlit app (production app — see streamlit/README.md)
streamlit run streamlit/nav.py

# Install dependencies
pip install -r requirements.txt
```

## Current state & next steps

### What's done
- **teg_analysis package**: Phases 1–7 cleanup complete (all Streamlit imports removed, aggregation/streaks/scoring refactored, dead code removed). Merged to `main`. Ready to be the canonical analysis layer.
- **Webapp**: Full Streamlit page set replicated. Data-admin is now ported behind cookie auth — **add a round**, **delete rounds / whole TEGs**, **edit metadata CSVs**, **selective GitHub↔store file sync** (with pre-action preview + text diff and file-definition info icons), a **volume browser** (browse the store tree; per-file edit/sync/download/delete-with-backup), a **backups** browser (restore any backup; restores back up the replaced copy first), and a **file guide** (catalog of every data file by importance, `teg_analysis/io/file_catalog.py`) — all in `webapp/routes/admin.py`, driven by headless `teg_analysis/analysis/data_update.py` + `teg_analysis/io/sync.py`; report generation remains out of scope. Nav mirrors Streamlit's sections/titles/ordering via a single source of truth, `webapp/nav.py` (`NAV_SECTIONS`), injected into templates and looped in `base.html`; `/` lands on the new **Contents** site map. Newly added: **Contents** (`/contents`) and **Eclectic Records** (`/eclectic-records`, backed by new helpers in `teg_analysis/analysis/eclectic.py`). All functional. TEG Reports page at `/teg-reports` and the Report tab on `/results` render the new commentary reports.
  - **Feature-parity audit complete.** All functional gaps (controls/views/measures/charts) have been closed across every page, including the deep/conditional ports; all webapp endpoints render their Streamlit-equivalent content. New analysis modules: `teg_analysis/analysis/player_rankings.py` (ranking tables + summaries), `teg_analysis/analysis/handicaps.py` (handicap recalc + in-progress status), `teg_analysis/display/scorecards.py` (scorecard HTML builders), plus `pivot_window_streaks` in `analysis/streaks.py`. Highlights: Player Rankings (both competitions + dimension selectors), Scorecard (3 views), Leaderboard & Results race charts (Standard/Adjusted/Ranking) + inline scorecards, full Scoring-section controls, Latest pages (metric sub-tabs + per-metric chart, streak-type pivot, full records-completeness, report tabs, Stableford toggles, inline scorecards), Handicaps draft section, Eclectic filters, TEG Reports satire/fallbacks. Remaining items are **cosmetic only** plus the WIP heatmap — tracked in `webapp/PARITY_AUDIT.md`.
- **Architecture**: Decoupled design documented and validated. `teg_analysis` is fully UI-agnostic.
- **Commentary / report pipeline** (`teg_analysis/reporting/`): new LLM-powered tournament reports built around a 5-stage pipeline — scored evidence-carrying beats + competition arcs (code) → structured story plan (LLM) → dry draft as QA scaffold + entertaining write-up + repetition lint (LLM) → CSS-class styled markdown. Three production reports validated (TEGs 9, 14, 18); cost ~$0.65 each on Opus 4.7. **How it works**: `teg_analysis/reporting/README.md`. **Done / next**: `teg_analysis/reporting/STATUS.md`.
- **Player profile overhaul** (`webapp/routes/player.py`, `webapp/templates/partials/player_overview.html`, `webapp/templates/player_index.html`): major rework of `/player` and `/player/{code}`. Key changes: pill-driven roster landing with player cards (avatar, trophy/jacket stars, TEG count, avg stats); profile overview rebuilt with 11 ranked metric cards, trophy cabinet with ordinal ranks, career highlights (best/worst course, best round/TEG), full records and worsts sections (TEG/round/9-hole level, streaks, score counts) using natural language labels ("Best gross TEG", "Longest birdies streak", "Most birdies in a round"); career trend bar charts (single colour per metric, "TEG N" x-axis labels, rank annotations). Functionality complete; **UI design pass still needed** — tracked in `webapp/TODOS.md`.
- **Data storage hardening + native round entry** (`teg_analysis/analysis/round_setup.py`, `teg_setup.py`, `live_round.py`; `webapp/routes/admin_round_setup.py`, `admin_teg_setup.py`, `admin_live_round.py`, `live_round.py`): kept the Railway-volume-+-GitHub storage foundation, hardened the write path (backups on add, concurrency lock, retired dead CSV mirrors), and replaced the Google Sheets score-capture flow with a native mobile-first one. **Pre-round setup** (`/admin/round-setup`) confirms Par/SI before a round is played (`round_pars.csv`, course-level defaults from `course_pars.csv`); **TEG setup** (`/admin/teg-setup`) confirms the roster + handicaps before a TEG starts (not every player plays every TEG). **Live round entry** (`/admin/live-round` to start/review/finalize, `/live-round/{token}` — no login, the link is the access control — for players to enter scores from their own phones as a round is played): a fixed/relative keypad toggle, a player-group chip picker (show just your foursome), and voice entry (OS dictation, not Web Speech API) on a sticky-keypad grid; the server (never a client clock) assigns write order, so concurrent devices editing the same cell get flagged for admin review rather than silently resolved, and "Finalize" runs the reviewed scores through the existing `execute_data_update` pipeline — one GitHub commit, same as any other round addition. Design details (conflict model, polling, device identity) live in code comments/docstrings in `teg_analysis/analysis/live_round.py` and `webapp/README.md`'s "Live round entry" section — the planning doc itself was deleted once its outcome was folded in here (per CLAUDE.md's own rule on temporary working documents).
  - **Live-round feedback round (post-launch):** four gaps closed. (1) **Finishing/leaderboard** — a read-only **live leaderboard** (`/live-round/{token}/leaderboard`, `get_live_leaderboard` computing gross + net/Stableford straight from staging via `process_round_for_all_scores`), a "View leaderboard" done banner once a player's group has all 18 holes in (soft done — the admin still finalizes), and a toolbar Leaderboard button; the board shows "scoring in progress" until every player is thru 18 and reads only staging (a live round isn't on the main site until finalized). (2) **Central admin review/edit** — the review page now renders the full staged scorecard as an **editable grid**; `apply_admin_edits` is the authoritative bulk-edit primitive (overwrites player entries, clears conflicts, writes only changed cells) and `resolve_conflict` now wraps it. (3) **Scores >12** and (4) **direct text entry** — one fix: physical-keyboard entry on the active cell (digits, Enter/Tab, arrows, Backspace) plus an "Other" keypad field, with the ceiling raised from 12 to `MAX_SCORE=20` across keypad/voice/admin inputs. Covered by `tests/test_live_round_e2e.py::test_live_leaderboard_out_of_range_and_admin_edit`.
- **Guided "New round" setup wizard** (`teg_analysis/analysis/round_wizard.py`, `webapp/routes/admin_new_round.py`, templates `admin_new_round.html` / `admin_new_round_wizard.html`): a single "start here" admin entry point (`/admin/new-round`, first in the admin sub-nav) that orchestrates the four previously-separate setup steps — round metadata → roster+handicaps → Par/SI → go live — into one linear stepper. It's **stateless/resumable**: each step saves immediately via the existing tested `teg_setup`/`round_setup`/`live_round` functions, and the "current" step is recomputed from the data on every visit (`get_wizard_status`), so a new round 2/3/4 auto-skips the already-confirmed roster and a half-finished setup resumes by revisiting the URL. The one net-new piece is a purpose-built round-metadata form (`get_round_metadata_form`/`save_round_metadata`) that derives round_info's `TEGRd`/`TEG`/`Area`/`Year` instead of hand-typing them in the raw grid. Finishing starts the live round and shows the shareable link + "what happens next" (including the live leaderboard link). The standalone pages stay reachable for edits/edge cases. Full detail: `webapp/README.md`'s "New round (guided wizard)" section.

### Next priorities
1. **Mobile UI + dark mode** — making the webapp "app-like" on phones, in light + dark, **without changing the laptop/iPad render**. Direction chosen: **A — full native-app feel** (bottom tab bar, sticky app bar, reflowed data). Done: dark-mode foundation (`static/themes/dark.css` + `data-mode` toggle, opt-in default light) and the portrait scorecard (a first vertical slice). **Next: Phase M1 — the app shell.** Full approach + progress + pickup pointer in `webapp/MOBILE_PLAN.md`; scorecard work-package in `webapp/SCORECARD_PORT.md`; mockups in `webapp/mobile_mockups/` (served at `/mockups/`).
2. **Webapp ↔ Streamlit feature-parity audit** — page existence parity is done; now closing missing controls/views/toggles on existing pages so each matches its Streamlit source. Per-page checklist + progress in `webapp/PARITY_AUDIT.md`.
2. **Webapp formatting pass** — visual polish, number formatting, table styling consistency, layout refinement. In progress in local branches.
3. **REST API** — build proper `/api` layer powered by `teg_analysis`. Goal: expose the analysis layer over HTTP so any client (scripts, mobile, other frontends) can access it without needing Python. Currently a placeholder in `teg_analysis/api/`.
4. **Retire Streamlit** — long-term goal once REST API + new webapp are production-ready.

## Pandas 2.x compatibility

The Railway deployment runs pandas 2.x, which has three breaking changes that have caused production errors. All are fixed; note the patterns to avoid when adding code.

### 1. `DataFrame.applymap` removed (pandas 2.1+)

`applymap` was renamed to `map`. Use `.map(fn)` on a DataFrame, not `.applymap(fn)`.

**Fixed in:**
- `streamlit/101TEG History.py:77`
- `streamlit/helpers/course_analysis_processing.py:132`

**Search for future regressions:** `grep -rn "\.applymap(" .`

### 2. Assigning strings into an `int64` column (pandas 2.x strict dtypes)

Pandas 2.x raises `Invalid value '<ArrowStringArray> [] Length: 0, dtype: str' for dtype 'int64'` when a string array (even an empty one) is assigned into an integer-typed column. This occurs in the leaderboard rank pattern where ranks are integers but tied ranks get a `=` suffix appended.

**Root cause:** Creating `Rank` as `int64` then doing `df.loc[mask, 'Rank'] = df.loc[mask, 'Rank'].astype(str) + '='` fails even when `mask` is all-False (empty selection still produces an ArrowStringArray).

**Safe pattern — convert to `object` before any string assignment:**
```python
# Safe: convert to object first so both ints and strings are accepted
pivot_df['Rank'] = pivot_df['Total'].rank(method='min', ascending=ascending).astype(int).astype(object)
pivot_df.loc[duplicated_scores, 'Rank'] = pivot_df.loc[duplicated_scores, 'Rank'].astype(str) + '='
```

**Also safe (webapp pattern) — convert to string immediately, guard with `.any()`:**
```python
pivot_df['Rank'] = pivot_df['Total'].rank(method='min', ascending=ascending).astype(int).astype(str)
if duplicated_scores.any():
    pivot_df.loc[duplicated_scores, 'Rank'] = pivot_df.loc[duplicated_scores, 'Rank'] + '='
```

**Variant — pivot table columns are `float64` (not `int64`) when NaN is present.** The same error fires when assigning rank strings into a `float64` pivot column. Fix is the same: convert to `object` first.
```python
ranked_df[teg_col] = ranked_df[teg_col].astype(object)
ranked_df.loc[ranks.index, teg_col] = ranks
```

**Fixed in:** `streamlit/leaderboard_utils.py:37`, `streamlit/player_history.py:419`  
**Already safe:** `webapp/deps.py:80–86` (uses the string-first pattern)

### 3. Assigning strings into a typed column via `.iloc` (pandas 2.x strict setitem)

Pandas 2.x enforces the existing column dtype on `.iloc` setitem. Assigning a string Series into a `float64` or `int64` column via `.iloc[:, N] = df.iloc[:, N].apply(lambda ...)` raises `TypeError` even when all rows are being replaced.

**Root cause:** `.iloc[rows, col] =` is a positional setitem that enforces dtype. `.loc[]` has the same restriction (see pattern 2 above).

**Fix — use named-column assignment, which replaces the column wholesale:**
```python
# Unsafe: iloc enforces float64 dtype, rejects string assignment
formatted_df.iloc[:, 2] = formatted_df.iloc[:, 2].apply(
    lambda x: 'n/a' if np.isinf(x) else f"{x:,.1f}"
)

# Safe: named-column assignment replaces the column entirely
col2 = formatted_df.columns[2]
formatted_df[col2] = formatted_df[col2].apply(
    lambda x: 'n/a' if np.isinf(x) else f"{x:,.1f}"
)
```

**Fixed in:** `streamlit/helpers/scoring_achievements_processing.py:68`, `streamlit/helpers/scoring_data_processing.py:87`, `teg_analysis/analysis/scoring.py:133,341`

**Search for future regressions:** `python scripts/check_pandas_compat.py` (detects `iloc-col-assign` pattern)

For detailed next steps on the webapp, see `webapp/README.md`.

## Architecture

### Old vs new

The project has two distinct architectural phases. **The Streamlit app is the original architecture** — self-contained, deployed, not changing. **The decoupled architecture is the current direction**: `teg_analysis/` is a UI-agnostic analysis layer that any frontend can call; `webapp/` is the new frontend being built on top of it. Do not conflate the two — changes to `teg_analysis/` or `webapp/` should never touch `streamlit/`.

### Layers

1. **`teg_analysis/`** — The canonical, UI-agnostic analysis package. **All new analytical work goes here.** Fully independent of any frontend (no streamlit imports at module level):
   - `constants.py` — Centralised file paths, player data, tournament metadata
   - `io/` — File I/O (`read_file`/`write_file`), GitHub API (uses `GITHUB_TOKEN` env var), Railway volume management
   - `core/` — Data loading (`load_all_data`) and transformation
   - `analysis/` — Scoring, rankings, player_rankings, aggregation, streaks, records, eclectic, handicaps, commentary, pipeline, data_update, history, performance, leaderboards, bestball
   - `display/` — Formatting, HTML tables, scorecards, navigation utilities (returns HTML strings, never calls st.write)
   - `api/` — Placeholder for REST API endpoints

2. **`streamlit/`** — The original app. Uses its own `utils.py` and is intentionally self-contained. **No longer the deployed site** (the webapp replaced it on Railway), but kept as the stable legacy reference; it will not be migrated to use `teg_analysis/`.

3. **`webapp/`** — FastAPI + HTMX + Jinja2 + Tailwind frontend. **Deployed on Railway from `main`** (replaced the Streamlit app) via `railway.toml` → `uvicorn webapp.app:app`; `requirements.txt` is webapp-only (includes `pyarrow` for parquet reads). Also run locally with `uvicorn webapp.app:app --reload`. Needs `GITHUB_TOKEN` + a volume mounted at `/mnt/data_repo`; `ANTHROPIC_API_KEY` for reports and `GOOGLE_*` vars for data-update ingestion.

4. **`ad_hoc_analysis/`** — Jupyter notebooks for exploratory / one-off analysis. Calls `teg_analysis/` directly. Start with `quickstart.ipynb`.

For Streamlit internals (app structure, page organisation, caching, data loading, GitHub integration), see `streamlit/README.md`. For the full data pipeline (storage → I/O → loader → aggregation → webapp), see `DATA_FLOW.md`.

**Data storage decision (2026-07-07):** the Railway volume + GitHub-commit-as-sync-of-record
pattern is kept (not replaced by a database) — at this dataset size it already gives an
atomic-commit audit trail, off-host durability, and the local-Mac sync workflow essentially
for free. `all-data.parquet`/`all-scores.parquet` stay as two stored files (master →
derived, not two independent sources); the redundant `all-data.csv` mirror was retired. Full
review and phased hardening/mobile-ingestion plan: `DATA_STORAGE_INGESTION_PLAN.md`.

## Design Philosophy

### Core Development Principles
- **Start with the simplest solution that works** - Don't over-engineer
- **Use existing patterns and components from the codebase** - Maintain consistency
- **Only add complexity when absolutely necessary** - Resist feature creep
- **Prefer minimal, focused changes over comprehensive rewrites** UNLESS a rewrite will significantly simplify the codebase
- **Ask "What's the smallest change that solves this?" before implementing** - Think minimalism first

## Documentation

### Rule 1 — Always maintain documentation

Documentation is part of every code change, not an afterthought. When you add, rename, or remove a data file, function, module, or architectural layer, update the relevant doc in the same session. Never leave docs describing something that no longer exists.

### Rule 2 — Each file has one role; content lives in exactly one place

| File | Owns | Does not contain |
|------|------|-----------------|
| `README.md` | Public entry point — what it is, how to run, folder map | Deep detail; current state beyond one line |
| `CLAUDE.md` | Project-wide instructions for Claude — architecture, patterns, model rules, current state | Subfolder-specific detail |
| `DATA_FLOW.md` | Full data pipeline reference — storage → I/O → analysis → webapp | Per-subfolder data loading patterns |
| `teg_analysis/README.md` | Package API — functions, data levels, constraints | Pipeline or webapp detail |
| `streamlit/README.md` | Streamlit internals — structure, caching, page org | Anything outside `streamlit/` |
| `webapp/README.md` | Webapp stack, themes, design principles, current status | Anything outside `webapp/` |

**Root vs L1:** `README.md` and `CLAUDE.md` cover the whole project. L1 subfolder READMEs cover only that subfolder. If something is relevant to one subfolder only, it belongs in that subfolder's README, not in the root docs.

### Rule 3 — Additional `.md` files

New `.md` files should only be created when:
- The content is genuinely too large or specialised for the relevant README (e.g. `webapp/design_principles.md`, `DATA_FLOW.md`)
- It is a temporary working document (plan, spike notes) — in which case it must be deleted or consolidated when the work is done

Do not accumulate `.md` files. Prefer adding a section to an existing file over creating a new one. If a new file is created permanently, add it to the folder guide in `README.md` and reference it from the relevant README.

`.md` files should not grow so large that they become hard to navigate. If a file is getting unwieldy, split it logically — one clear topic per file — rather than letting it sprawl.

### When to update which file

| Change | Update |
|--------|--------|
| New module or layer in `teg_analysis/` | `CLAUDE.md` Architecture + `teg_analysis/README.md` |
| New webapp page area or pattern | `webapp/README.md` |
| Data file added, renamed, or removed | `DATA_FLOW.md` Storage Layer |
| New development command | `CLAUDE.md` Development Commands + `README.md` Quick start |
| Architecture decision | `CLAUDE.md` Architecture |
| Streamlit structural change (rare) | `streamlit/README.md` |

## Model Selection

### MANDATORY — Model check gate

**BEFORE doing ANY work — before reading files, before editing, before planning — you MUST output a model check block as your FIRST response text.** No exceptions. Format:

```
**Model check:** I am [current model]. This task is [simple/moderate/complex] → recommended model is [Haiku/Sonnet/Opus].
[If mismatch]: ⚠️ Recommended model is [model] (`/model [model]`). Say "continue" to proceed anyway.
[If match]: ✅ Proceeding.
```

If the task is a multi-step plan with mixed complexity tiers, call out which steps match the current model and which don't. Recommend doing same-tier work first, then switching.

### Complexity tiers

| Tier | Model | Task types |
|------|-------|------------|
| **Complex** | **Opus** | Architecture decisions, multi-file refactors, designing new modules/APIs, rewriting large files, debugging subtle cross-module issues, planning |
| **Moderate** | **Sonnet** | Single-file edits, adding/modifying functions, fixing known bugs, writing tests, import cleanup, removing dead code from a single file |
| **Simple** | **Haiku** | Deleting files, renaming variables, removing comments, formatting, updating docs, simple search-and-replace |

### At task transitions

When the current subtask is done and the next one is a different tier, STOP and output:

```
**Model note:** [Completed work] is done. Next task ([description]) is [tier] → switch to [model] with `/model [model]`.
```

Do NOT silently start work at a different tier.

### Opus review gate

After Haiku or Sonnet complete a batch of work, switch to Opus for review.

**Sonnet/Haiku: what to document when done**

Update the "Current state & next steps" section in CLAUDE.md with a brief summary of:
- What you changed (files modified, functions added/removed/renamed)
- What's next (highest-priority work)
- Anything you were unsure about or deliberately left for Opus to decide

**Opus: review checklist**

1. Read every modified file end-to-end
2. Check: do all internal callers (grep for old function names) still work?
3. Check: are backward-compatible aliases needed that weren't added?
4. Check: any functions deleted that actually had external callers?
5. Check: no streamlit imports crept into teg_analysis/
6. Run tests (`pytest tests/ -v`)
7. Flag issues in a comment or fix directly, then commit

