# teg_analysis

A UI-agnostic Python package for TEG (golf tournament) analysis. All scoring, rankings, records, and statistics live here — use it from any frontend (Streamlit, FastAPI, Jupyter, CLI, etc.).

## Quick start

```python
from teg_analysis.core.data_loader import load_all_data
from teg_analysis.analysis.aggregation import get_ranked_teg_data

# Load hole-level data
all_data = load_all_data()  # 6,390 rows × 53 cols

# Aggregate to TEG level and add ranks
teg_data = get_ranked_teg_data(all_data)

# Use analysis functions
from teg_analysis.analysis.streaks import build_streaks
streaks = build_streaks(all_data)
```

## Package structure

```
teg_analysis/
  constants.py       File paths, player data, tournament metadata
  
  io/                File and data I/O
    file_operations.py  Read/write parquet and CSV (local or GitHub)
    github_operations.py GitHub API integration
    volume_operations.py Railway volume management
  
  core/              Data loading and transformation
    data_loader.py   load_all_data() — loads hole-level tournament data
    data_transforms.py Data manipulation utilities
    metadata.py      Metadata helpers
  
  analysis/          All analytical functions
    aggregation.py   Aggregate data at different levels (hole → round → TEG → 9-hole)
    rankings.py      Add rank columns to aggregated data
    scoring.py       Par-related scoring analysis
    records.py       Personal bests, worsts, records
    streaks.py       Build and calculate streaks
    history.py       Tournament winners, eagles, historical summaries
    performance.py   Performance measure tables
    leaderboards.py  Leaderboard generation
    bestball.py      Best-ball / worst-ball competition format
    commentary.py    Commentary/narrative generation
    pipeline.py      Data pipeline coordinator
  
  display/           Formatting and output
    formatters.py    Format data for display (HTML, styled tables)
    html_tables.py   Generate styled HTML tables
    navigation.py    Navigation utilities
    tables.py        Table building helpers
  
  api/               REST API endpoints (placeholder)
    __init__.py
```

## Core concepts

### Data levels

All analysis starts with hole-level data and aggregates upward:

```
Hole-level    load_all_data()              6,390 rows × 53 cols — one row per player/TEG/round/hole
  ↓ aggregate_data(df, "FrontBack")
9-hole level  get_9_data()                 one row per player/TEG/round/front-or-back
  ↓ aggregate_data(df, "Round")
Round-level   get_round_data()             one row per player/TEG/round
  ↓ aggregate_data(df, "TEG")
TEG-level     get_complete_teg_data()      one row per player/TEG
  ↓ aggregate_data(df, "Player")
Career-level  get_Pl_data()                one row per player — all-time totals
```

**Which level for which question:**

| Question | Level | Function |
|----------|-------|----------|
| Score on a specific hole | Hole | `load_all_data()` |
| Front 9 vs Back 9 splits? | 9-hole | `get_9_data()` |
| How did a player do in one round? | Round | `get_round_data()` |
| Best/worst TEG a player has had? | TEG | `get_complete_teg_data()` |
| Career totals / all-time averages? | Career | `get_Pl_data()` |

### Adding ranks

Ranking functions take aggregated data and add rank columns:

```python
teg_data = get_complete_teg_data(all_data)
ranked_teg_data = add_ranks(teg_data)
# or use the convenience function
ranked_teg_data = get_ranked_teg_data(all_data)
```

Rank columns include:
- `Rank_within_player_*` — rank within that player's history
- `Rank_within_all_*` — rank across all players

### Caching

All data loading is cached:

```python
# First call: reads from parquet/GitHub
all_data = load_all_data()

# Subsequent calls: returns cached result
all_data = load_all_data()  # instant
```

Cache is in-process (`@lru_cache`). Cleared manually after data updates.

## Key functions

### Data loading
- `load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=True)` — Load hole-level data. TEG 50 is a test tournament (created to verify data pipelines) and should never appear in results or statistics — `exclude_teg_50` defaults to `True` and should stay that way.
- `get_9_data()` — 9-hole (front/back) level aggregation
- `get_round_data()` — round-level aggregation
- `get_complete_teg_data()` — TEG-level aggregation (excludes incomplete tournaments)
- `get_Pl_data()` — career-level aggregation (one row per player, all-time totals)
- `add_ranks(df)` — Add rank columns to any aggregated data
- `get_ranked_frontback_data()`, `get_ranked_round_data()`, `get_ranked_teg_data()`, `get_ranked_career_data()` — convenience wrappers: load + aggregate + add ranks in one call

### Aggregation
- `aggregate_data(df, level)` — Aggregate to "Round", "TEG", or "FrontBack" level
- `get_player_count()` — Number of active players

### Scoring & analysis
- `build_streaks(all_data)` — Streaks data structure per hole per player
- `get_eagles_data(all_data)` — Eagles records
- `get_teg_winners(all_data)` — Who won each tournament
- `calculate_par_performance_matrix()` — Score distribution by par type
- `prepare_comeback_data()` — Comeback/improvement records

### Display formatting
- `prepare_record_table(all_data, ...)` — Format records for display
- `prepare_performance_table(all_data, ...)` — Format performance/best-TEG tables
- `create_leaderboard(df, column)` — Create ranking leaderboard

See the modules for full API — each function is documented.

## Design constraints

- **No Streamlit imports** — the package must work standalone
- **No frontend dependencies** — return data, not UI strings (except display/ module which returns HTML)
- **No side effects** — functions are pure; no printing or file writes except where documented
- **Idempotent** — same input always gives same output

## Testing

```bash
pytest tests/ -v
```

## Data files

Located in `../data/`:
- `all-data.parquet` — Hole-level tournament data (53 cols, 6,390 rows)
- `round_info.csv` — Course and tournament metadata
- `handicaps.csv` — Player handicaps per tournament
- `streaks.parquet` — Pre-computed streak counters (for performance)
- `bestball.parquet` — Best-ball competition data
- `commentary_*.parquet` — AI-generated commentary (round/tournament summaries)

## Development

### Adding a new analysis function
1. Add it to the appropriate module in `analysis/`
2. Import in module's `__init__.py` if it should be public
3. Write tests in `tests/`
4. Use it from the frontend (Streamlit, webapp, or API)

### What belongs here
- Any calculation, scoring rule, or analytical output
- Data transformation at any level
- Ranking, aggregation, or filtering logic

### What doesn't belong here
- UI code (that's the frontend's job)
- Page routing or request handling
- Streamlit-specific code

## Status

Package is stable and merged to `main`. All cleanup phases (1–7) complete:
- All Streamlit imports removed ✅
- Dead code removed ✅
- Large modules refactored ✅
- Tests pass ✅

This is the canonical source for all analytical work.
