# Branch Guide

*Last updated: 2026-02-06*

## Branch Map

```
main (production - Railway)
  |
  +-- documentation (16 commits - audit/analysis only, no code changes)
  |     |
  |     +-- refactor (93 commits - teg_analysis package, NiceGUI prototype, FastAPI example)
  |
  +-- claude/nicegui-styles-css-... (3 commits - just a CSS file + screenshot)

[Disconnected histories - no common ancestor with main]
  railway-deployment (obsolete - original Railway setup, superseded by main)
  multi-agent-prototype (dead-end - non-working crewai experiment)
```

## Active Branches

### `main` (deployed on Railway)
- **Last updated:** 2025-10-18
- **Status:** Production. The working Streamlit app.
- **What it is:** Monolithic Streamlit app with business logic mixed into page files and a large `utils.py`. Works fine, deployed on Railway, serves real users.

### `refactor` (most advanced work)
- **Last updated:** 2025-11-02
- **Status:** 93 commits ahead of main. Not merged.
- **Built on top of:** `documentation` branch (which is built on `main`)
- **What it contains:**
  1. **`teg_analysis/` package** — UI-independent business logic extracted from Streamlit into a clean Python package with 4 layers: `io/`, `core/`, `analysis/`, `display/`. ~24 files, 235+ functions. This is the API foundation.
  2. **NiceGUI prototype** — Near-complete alternative frontend (61 files, 23+ pages) using NiceGUI with SPA navigation.
  3. **FastAPI example** — Proof-of-concept (`examples/example_fastapi.py`) showing `teg_analysis` powering a REST API. The `teg_analysis/api/` sub-package exists but is a placeholder.
  4. **Massive documentation** — 150K+ lines of docs cataloguing all 530 functions across 79 Python files, identifying duplicates, unused code, and naming conflicts.
- **Problems:** Also messy — contains ~80 archived doc files, root-level throwaway scripts, a 94K-line JSON analysis file, and the NiceGUI work mixed in with core refactoring.

### `documentation` (subsumed by refactor)
- **Last updated:** 2025-10-25
- **Status:** 16 commits ahead of main. Entirely contained within `refactor`.
- **What it is:** A thorough audit of the codebase — function catalogue, dependency map, duplicate detection, cleanup plan. No code changes, purely analysis. Everything here is already in `refactor`.
- **Can be deleted** once refactor is dealt with.

## Redundant / Dead Branches

### `railway-deployment` (obsolete)
- **Last updated:** 2025-05-25
- **Status:** Disconnected git history (no common ancestor with main). 5+ months stale.
- **What it was:** Original effort to deploy on Railway. Main achieved this independently.
- **Safe to delete.**

### `multi-agent-prototype` (dead-end)
- **Last updated:** 2025-07-01
- **Status:** Disconnected git history. Self-described "non working multi agent attempt".
- **What it was:** Experiment using crewai + OpenRouter for AI-powered code analysis.
- **Safe to delete.**

### `claude/nicegui-styles-css-...` (minor)
- **Last updated:** 2025-11-05
- **Status:** 3 commits ahead of main. Just adds `styles.css` and `nfl_colours.png`.
- **Superseded by** refactor branch's more complete NiceGUI styling.
- **Safe to delete.**

## Key Findings from the Audit

The `documentation` branch (included in `refactor`) catalogued the full codebase and found:
- **530 functions** across 79 Python files
- **8 exact duplicate** function pairs
- **10 near-duplicate** function groups
- **38 naming conflicts** (same name, different implementations)
- **32 unused functions**
- A 4-phase cleanup plan was proposed but only partially executed

## What Matters Going Forward

The only branch with meaningful reusable work beyond main is **`refactor`**, specifically the `teg_analysis/` package. Everything else is either already in production (main), subsumed (documentation), or dead (railway-deployment, multi-agent-prototype, nicegui-styles-css).
