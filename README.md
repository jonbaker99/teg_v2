# TEG v2

Golf tournament analysis for the TEG (The El Golfo) group. Tracks scores, records, streaks, and standings across 17+ annual tournaments with 7 players.

## What's here

This repo has two things:

1. **`streamlit/`** -- A working Streamlit dashboard deployed on Railway (`main` branch). Leaderboards, scorecards, records, historical data, commentary reports.

2. **`teg_analysis/`** -- A standalone Python package that contains the core analysis logic, extracted from the Streamlit app so it can power any frontend (API, CLI, notebook, etc). This is the focus of current development.

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

# Run the FastAPI example (needs: pip install fastapi uvicorn)
python examples/example_fastapi.py
# Then visit http://localhost:8000/docs
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

streamlit/           The existing Streamlit app (deployed on Railway)
tests/               Test suite for teg_analysis
examples/            FastAPI proof-of-concept
data/                Tournament data files (parquet, CSV, commentary reports)

CLAUDE.md            Development guidelines
PROJECT_PLAN.md      Objectives, next steps, resume instructions
BRANCHES.md          Guide to all branches
```

## Current status

See [PROJECT_PLAN.md](PROJECT_PLAN.md) for the full plan, known issues, and how to resume work.

The Streamlit app on `main` is stable and deployed. The `teg_analysis` package on this branch (`claude/golf-stats-api-cMQ4e`) is the foundation for the API -- validated as working standalone with all 6,390 rows of data.
