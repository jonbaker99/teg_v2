# TEG v2

Golf tournament analysis for the TEG (The El Golfo) group. TEG is both the name of the group and each annual tournament event — so "TEG 17" means the 17th tournament. Tracks scores, records, streaks, and standings across 17+ annual tournaments with 7 players.

## Architecture: old vs new

The project has evolved through two phases:

**Phase 1 — Streamlit (original, stable):** All analysis and UI live together in the `streamlit/` folder. This is deployed on Railway and working. It is intentionally self-contained — changes to the rest of the codebase do not affect it, and it will not be migrated.

**Phase 2 — Decoupled (current direction):** Analysis logic has been extracted into `teg_analysis/`, a UI-agnostic Python package. This is the source of truth for all analytical work — it can be called from a webapp, a REST API, a Jupyter notebook, or any other frontend. The new `webapp/` frontend is being built on top of it.

The key principle: **`teg_analysis/` owns the analysis; frontends are interchangeable.**

## What's here

1. **`streamlit/`** -- The original Streamlit dashboard, deployed on Railway. Self-contained; not changing.

2. **`teg_analysis/`** -- The UI-agnostic analysis package. The canonical source for all TEG data, scoring, records, and statistics. Use this for any new analytical work.

3. **`webapp/`** -- New frontend in progress (FastAPI + HTMX + Jinja2). Calls `teg_analysis/` for all data. Not yet deployed.

## Quick start

```bash
# Install dependencies
pip install pandas numpy pyarrow plotly PyGithub

# Verify the analysis package works
python -c "
from teg_analysis.core.data_loader import load_all_data
df = load_all_data()
print(f'{len(df)} rows, {df.TEGNum.nunique()} TEGs, {df.Player.nunique()} players')
"

# Run the Streamlit app (needs: pip install -r requirements.txt)
streamlit run streamlit/nav.py

# Run the webapp (needs: pip install fastapi uvicorn jinja2)
uvicorn webapp.app:app --reload
# Then visit http://localhost:8000

# Open the ad-hoc analysis quickstart notebook (needs: pip install jupyter)
jupyter notebook ad_hoc_analysis/quickstart.ipynb
```

## Project structure

```
teg_analysis/        Core analysis package (standalone, no Streamlit dependency)
  constants.py       File paths, player data, tournament metadata
  io/                File I/O, GitHub API, Railway volume management
  core/              Data loading and transformation
  analysis/          Scoring, rankings, aggregation, streaks, records, commentary
  display/           Formatting, HTML tables, navigation utilities
  api/               (Placeholder for REST API endpoints)

ad_hoc_analysis/     Jupyter notebooks for exploratory / one-off analysis
streamlit/           The existing Streamlit app (deployed on Railway)
tests/               Test suite for teg_analysis
examples/            FastAPI proof-of-concept
data/                Tournament data files (parquet, CSV, commentary reports)

CLAUDE.md            Development guidelines for Claude Code
DATA_FLOW.md         Reference guide for the data pipeline
```

## Folder guide

| Directory / File | Purpose |
|---|---|
| `teg_analysis/` | Standalone analysis package — io, core, analysis, display, api layers. See `teg_analysis/README.md` |
| `webapp/` | FastAPI + HTMX frontend (local development only). See `webapp/README.md` |
| `streamlit/` | Production Streamlit app, deployed on Railway. See `streamlit/README.md` |
| `data/` | Tournament data files (parquet, CSV, commentary markdown) |
| `ad_hoc_analysis/` | Jupyter notebooks for exploratory / one-off analysis |
| `tests/` | Test suite for `teg_analysis` |
| `examples/` | FastAPI proof-of-concept |
| `CLAUDE.md` | Development guidelines for Claude Code |
| `DATA_FLOW.md` | Data pipeline reference guide |

## Current status

The Streamlit app is deployed and stable. The `teg_analysis` package is merged to `main` — all cleanup complete, ready to power multiple frontends. The `webapp/` is in active development with 26 endpoints and data parity vs Streamlit.

See [CLAUDE.md](CLAUDE.md) for current work priorities and architecture decisions. See folder-level READMEs (`teg_analysis/README.md`, `webapp/README.md`, `streamlit/README.md`) for each component.
