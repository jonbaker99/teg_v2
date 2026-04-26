# Streamlit app

The original TEG dashboard, deployed on Railway. Self-contained — it does not use `teg_analysis/` and will not be migrated to do so. Treat it as stable; avoid changes.

## Running

```bash
# Local development
streamlit run streamlit/nav.py

# Production (Railway)
streamlit run streamlit/nav.py --server.port=$PORT --server.address=0.0.0.0
```

## App structure

- **Entry point**: `nav.py` — main navigation controller defining all pages
- **Data utilities**: `utils.py` — data loading, GitHub integration, caching
- **Page modules**: numbered files by category (see Page organisation below)
- **Data storage**: CSV/Parquet files in `data/`, also stored in GitHub for production

## Page organisation

- **History**: `101TEG History.py`, `101TEG Honours Board.py`, `102TEG Results.py`
- **Records & PBs**: `300TEG Records.py`, `301Best_TEGs_and_Rounds.py`, `302Personal Best Rounds & TEGs.py`, `303Final Round Comebacks.py`
- **Scoring**: `400scoring.py`, `ave_by_*.py`, `streaks.py`, `birdies_etc.py`, etc.
- **Latest TEG**: `leaderboard.py`, `scorecard_v2.py`, `latest_*.py`
- **Data admin**: `1000Data update.py`, `delete_data.py`

File naming: navigation pages use descriptive names with spaces; utility modules use snake_case. Pages numbered by category: 100s=History, 200s=Results, 300s=Records, 400s=Scoring, 1000s=Data admin.

## Data loading

Always use `read_file()` from `utils.py` — handles both local (CSV) and production (GitHub API) environments:

```python
def read_file(file_path: str) -> pd.DataFrame:
    if os.getenv('RAILWAY_ENVIRONMENT'):
        return read_from_github(file_path)  # Production: GitHub API
    else:
        return pd.read_csv(local_path)      # Development: local files
```

Key data files (in `data/`):
- `all-scores.parquet` — primary tournament dataset
- `handicaps.csv` — player handicap reference
- `round_info.csv` — course and tournament metadata

## Caching strategy

Aggressive caching optimised for Railway — no TTL, shared across all users on the instance, cleared manually after data updates.

```python
@st.cache_data  # No TTL — cleared manually after data changes
def read_file(file_path: str) -> pd.DataFrame:
    # GitHub API calls are expensive — cache aggressively
```

Clear all caches after updates: `st.cache_data.clear()`. Done automatically in `1000Data update.py` and `delete_data.py`.

Performance note: first page load is slow (GitHub API + cache population); subsequent loads are fast.

## GitHub integration

- Repository: `jonbaker99/teg_v2`
- Production reads all data files via GitHub API (requires `GITHUB_TOKEN` env var)
- Data updates commit changes back to GitHub
- Use functions from `utils.py` for all GitHub operations
