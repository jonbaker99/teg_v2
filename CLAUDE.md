# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python Streamlit application for analyzing TEG (annual golf tournament) data. The app is deployed on Railway and reads golf tournament data from GitHub via API calls to serve results to multiple users.

## Development Commands

### Running the Application
```bash
# Local development
streamlit run streamlit/nav.py

# Production deployment (Railway)
# Uses: streamlit run streamlit/nav.py --server.port=$PORT --server.address=0.0.0.0
```

### Dependencies
```bash
# Install dependencies
pip install -r requirements.txt

# Key dependencies: streamlit, pandas, numpy, google-auth, gspread, PyGithub, plotly, altair
```

## Architecture

### Two-Layer Structure

The project has two main layers:

1. **`teg_analysis/`** — Standalone Python package with all core analysis logic, **fully independent of Streamlit** (no streamlit imports at module level):
   - `constants.py` — Centralised file paths, player data, tournament metadata
   - `io/` — File I/O (`read_file`/`write_file`), GitHub API (uses `GITHUB_TOKEN` env var), Railway volume management
   - `core/` — Data loading (`load_all_data`) and transformation
   - `analysis/` — Scoring, rankings, aggregation, streaks, records, commentary, pipeline, history, performance, leaderboards, bestball
   - `display/` — Formatting, HTML tables, navigation utilities (returns HTML strings, never calls st.write)
   - `api/` — Placeholder for REST API endpoints

2. **`streamlit/`** — The production Streamlit app (deployed on Railway), which currently uses its own `utils.py` rather than `teg_analysis/`. Migrating the Streamlit app to use `teg_analysis/` is a future goal.

### Streamlit App Structure
- **Entry point**: `streamlit/nav.py` - Main navigation controller defining all pages
- **Data utilities**: `streamlit/utils.py` - Core data loading and GitHub integration functions
- **Page modules**: Numbered files (100s=History, 200s=Results, 300s=Records, etc.)
- **Data storage**: CSV/Parquet files in `data/` directory, also stored in GitHub for production

### Data Flow Pattern
```python
# Environment-aware data loading
def read_file(file_path: str) -> pd.DataFrame:
    if os.getenv('RAILWAY_ENVIRONMENT'):
        return read_from_github(file_path)  # Production: GitHub API
    else:
        return pd.read_csv(local_path)      # Development: Local files
```

### Key Data Files
- `all-scores.parquet` - Primary tournament analysis dataset
- `handicaps.csv` - Player handicap reference data
- `round_info.csv` - Course and tournament metadata

### Page Organization
Navigation organized by functional areas:
- **History**: Tournament history and results (`101TEG History.py`, `102TEG Results.py`)
- **Records & PBs**: Records, personal bests, and worsts (`300TEG Records.py`, `301Best_TEGs_and_Rounds.py`, etc.)
- **Scoring**: Detailed scoring analysis (`ave_by_*.py`, `scoring.py`, `streaks.py`, etc.)
- **Latest TEG**: Current tournament focus (`leaderboard.py`, `scorecard_v2.py`, `latest_*.py`)
- **Data**: Administrative functions (`1000Data update.py`, `delete_data.py`)

## Caching Strategy

The app uses an aggressive caching strategy optimized for Railway deployment:

### Cache Principles
- **No TTL on caches** - Data persists until manually cleared
- **Shared cache** across all users on Railway instance
- **Manual cache clearing** after data updates/deletions
- **File read caching** to eliminate GitHub API bottlenecks

### Critical Cache Pattern
```python
@st.cache_data  # No TTL - cleared manually after data changes
def read_file(file_path: str) -> pd.DataFrame:
    # GitHub API calls are expensive - cache aggressively
```

### Cache Management
- Clear all caches after data updates: `st.cache_data.clear()`
- Cache is cleared in data update (`1000Data update.py`) and deletion (`delete_data.py`) operations
- Reference data (handicaps, course info) cached until manual clear
- Tournament data cache invalidated when `all-scores.parquet` is modified

## Development Guidelines

### File Naming Convention
- Navigation pages use descriptive names with spaces
- Utility modules use snake_case
- Pages are numbered by category (100s, 200s, 300s, etc.)

### Data Loading Pattern
Always use the centralized `read_file()` function from `utils.py` which handles both local development and Railway production environments automatically.

### GitHub Integration
- Repository: `jonbaker99/teg_v2`
- Production reads all data files via GitHub API
- Data updates commit changes back to GitHub
- Use functions from `utils.py` for GitHub operations

### Performance Considerations
- First page load is slow (GitHub API + cache population)
- Subsequent loads are fast (cached data)
- Cache shared across all users on Railway instance
- Manual cache clearing ensures data freshness after updates

## Design Philosophy

### Core Development Principles
- **Start with the simplest solution that works** - Don't over-engineer
- **Use existing patterns and components from the codebase** - Maintain consistency
- **Only add complexity when absolutely necessary** - Resist feature creep
- **Prefer minimal, focused changes over comprehensive rewrites** UNLESS a rewrite will significantly simplify the codebase
- **Ask "What's the smallest change that solves this?" before implementing** - Think minimalism first

### Development Approach
- Build incrementally on existing patterns
- Prioritize code maintainability over clever solutions  
- Test changes thoroughly before expanding scope
- Document the reasoning behind architectural decisions

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

Update NEXT_SESSION.md with a "Changes made" section that includes:
- Files modified/deleted, with before/after line counts
- Functions added, removed, or renamed (old name → new name)
- Any backward-compatible aliases added
- Any callers updated and how
- Anything you were unsure about or deliberately left for Opus to decide

**Opus: review checklist**

1. Read every modified file end-to-end
2. Check: do all internal callers (grep for old function names) still work?
3. Check: are backward-compatible aliases needed that weren't added?
4. Check: any functions deleted that actually had external callers?
5. Check: no streamlit imports crept into teg_analysis/
6. Run tests (`pytest tests/ -v`)
7. Flag issues in a comment or fix directly, then commit

### general info
- a 'teg' is a tournament. each teg consistents of a number of rounds (usually 4, with a few exceptions). each round consists of 18 holes. the 18 holes can be categorised as a 'front 9' (holes 1-9)  and 'back 9' (holes 10-18)
- There are two competitions in each TEG, gross and net. Up to TEG 5, the net competition was based on total net vs par; from TEG 6 onwards the net competition was based on total stableford points