# Branch Guide

*Last updated: 2026-03-15*

## Branch Map

```
main (production - Railway)
  |
  |  [merged via PR #1, 2026-02-06]
  |  claude/golf-stats-api-cMQ4e — teg_analysis package extraction (deleted after merge)
  |
  +-- documentation (16 commits - audit/analysis only, no code changes)
  |     |
  |     +-- refactor (93 commits - teg_analysis package, NiceGUI prototype, FastAPI example)
  |
  +-- claude/nicegui-styles-css-... (3 commits - just a CSS file + screenshot)

[Disconnected histories - no common ancestor with main]
  railway-deployment (obsolete)
  multi-agent-prototype (dead-end)
```

## Active Branches

### `main` (deployed on Railway)
- **Last updated:** 2026-02-06
- **Status:** Production. Contains the working Streamlit app AND the `teg_analysis` package.
- **What it is:** The Streamlit app with business logic in page files, plus the newly extracted `teg_analysis/` standalone package, tests, and FastAPI example. All future work should branch from here.

## Branches Safe to Delete

All branches below have had their useful content either merged to `main` or superseded. They exist only on the remote.

### `refactor` (superseded)
- **93 commits ahead of main.** The `teg_analysis/` package was cherry-picked from here into `main` via the `claude/golf-stats-api-cMQ4e` branch. Also contains a NiceGUI prototype, 150K+ lines of docs, and throwaway scripts — none of which are needed.
- **Safe to delete.** The useful parts are on `main`.

### `documentation` (subsumed by refactor)
- **16 commits ahead of main.** Codebase audit and analysis, entirely contained within `refactor`.
- **Safe to delete.**

### `railway-deployment` (obsolete)
- Disconnected git history. Original Railway setup, superseded by `main`.
- **Safe to delete.**

### `multi-agent-prototype` (dead-end)
- Disconnected git history. Non-working crewai experiment.
- **Safe to delete.**

### `claude/nicegui-styles-css-...` (minor)
- 3 commits. Just a CSS file and screenshot, superseded by refactor's NiceGUI work.
- **Safe to delete.**

## Key Findings from the Codebase Audit

The `documentation` branch (included in `refactor`) catalogued the full codebase and found:
- **530 functions** across 79 Python files
- **8 exact duplicate** function pairs
- **10 near-duplicate** function groups
- **38 naming conflicts** (same name, different implementations)
- **32 unused functions**
- A 4-phase cleanup plan was proposed but only partially executed
