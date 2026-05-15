# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TEG v2 is a golf tournament analysis project. It has two architectural layers: a legacy Streamlit app (deployed on Railway, self-contained, stable) and a newer decoupled architecture — a UI-agnostic `teg_analysis/` Python package plus a `webapp/` FastAPI frontend in progress. All new analytical work belongs in `teg_analysis/`.

## Domain knowledge

- A **TEG** is an annual golf tournament. Each TEG consists of several rounds (usually 4), each of 18 holes split into a front 9 (holes 1–9) and back 9 (holes 10–18).
- There are two competitions per TEG: **gross** and **net**. Up to TEG 7, net was total net vs par; from TEG 8 onwards it is total Stableford points.

## Note on documentation

Do not read or reference `to_do_jon.md` unless the user explicitly asks you to. It is a personal draft notes file, not project documentation.

## Development Commands

```bash
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
- **Webapp**: 26 endpoints implemented with data parity vs Streamlit. All functional. Ready for visual polish.
- **Architecture**: Decoupled design documented and validated. `teg_analysis` is fully UI-agnostic.

### Next priorities
1. **Webapp formatting pass** — visual polish, number formatting, table styling consistency, layout refinement. In progress in local branches.
2. **REST API** — build proper `/api` layer powered by `teg_analysis`. Goal: expose the analysis layer over HTTP so any client (scripts, mobile, other frontends) can access it without needing Python. Currently a placeholder in `teg_analysis/api/`.
3. **Retire Streamlit** — long-term goal once REST API + new webapp are production-ready.

### To investigate
- **Data file rationalisation** — `all-data.parquet` (53 cols, used by `teg_analysis`) and `all-scores.parquet` (17 cols, used by Streamlit) are both hole-level but differ in columns. Unclear if they should be one source. Investigate before making changes to either. See `DATA_FLOW.md`.

## Pandas 2.x compatibility

The Railway deployment runs pandas 2.x, which has two breaking changes that have caused production errors. Both are fixed; note the patterns to avoid when adding code.

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

**Fixed in:** `streamlit/leaderboard_utils.py:37`  
**Already safe:** `webapp/deps.py:80–86` (uses the string-first pattern)

For detailed next steps on the webapp, see `webapp/README.md`.

## Architecture

### Old vs new

The project has two distinct architectural phases. **The Streamlit app is the original architecture** — self-contained, deployed, not changing. **The decoupled architecture is the current direction**: `teg_analysis/` is a UI-agnostic analysis layer that any frontend can call; `webapp/` is the new frontend being built on top of it. Do not conflate the two — changes to `teg_analysis/` or `webapp/` should never touch `streamlit/`.

### Layers

1. **`teg_analysis/`** — The canonical, UI-agnostic analysis package. **All new analytical work goes here.** Fully independent of any frontend (no streamlit imports at module level):
   - `constants.py` — Centralised file paths, player data, tournament metadata
   - `io/` — File I/O (`read_file`/`write_file`), GitHub API (uses `GITHUB_TOKEN` env var), Railway volume management
   - `core/` — Data loading (`load_all_data`) and transformation
   - `analysis/` — Scoring, rankings, aggregation, streaks, records, commentary, pipeline, history, performance, leaderboards, bestball
   - `display/` — Formatting, HTML tables, navigation utilities (returns HTML strings, never calls st.write)
   - `api/` — Placeholder for REST API endpoints

2. **`streamlit/`** — The original production app (deployed on Railway). Uses its own `utils.py` and is intentionally self-contained. It will not be migrated to use `teg_analysis/` — it represents the old architecture and should be left stable.

3. **`webapp/`** — FastAPI + HTMX + Jinja2 + Tailwind proof-of-concept. Not deployed; used locally to experiment with different UIs and visual styles. Run with `uvicorn webapp.app:app --reload` from the repo root.

4. **`ad_hoc_analysis/`** — Jupyter notebooks for exploratory / one-off analysis. Calls `teg_analysis/` directly. Start with `quickstart.ipynb`.

For Streamlit internals (app structure, page organisation, caching, data loading, GitHub integration), see `streamlit/README.md`. For the full data pipeline (storage → I/O → loader → aggregation → webapp), see `DATA_FLOW.md`.

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

