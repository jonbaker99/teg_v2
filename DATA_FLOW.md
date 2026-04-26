# Data Flow Map

Reference guide for how data flows from raw files through the analysis pipeline and into rendered pages.

**Maintenance note:** Update this file whenever data files are added, renamed, or restructured, or when the pipeline layers change.

---

## 1. Storage Layer

Raw data files in `data/`:

```
data/
  all-data.parquet        ← 53-col hole-level data (pre-computed cumulative stats, rankings)
  all-scores.parquet      ← 17-col hole-level data (raw scores only, used by Streamlit)
  round_info.csv          ← course / date / area metadata per TEG+Round
  handicaps.csv           ← player handicaps per TEG
  streaks.parquet         ← pre-computed streak counters per hole per player
  bestball.parquet        ← best-ball competition data
  commentary_*.parquet    ← AI-generated commentary (round/tournament summaries, streaks)
```

**Unresolved:** `all-data.parquet` and `all-scores.parquet` both contain hole-level data at the same granularity but with different columns (53 vs 17). It is not yet clear whether these should be rationalised into a single source. Investigate before making changes to either file.

---

## 2. I/O Layer

File reading abstraction in `teg_analysis/io/file_operations.py`:

```
read_file(path)
  ├─ Local dev    →  pd.read_parquet/csv from data/
  └─ Railway      →  check Railway volume → if missing, pull from GitHub API → cache to volume

write_file(path, df)  →  Railway volume  +  GitHub commit  (triggered by Streamlit data update and delete pages only)
```

**Note:** The webapp is **read-only** — no write path.

---

## 3. Core Data Loader

`teg_analysis/core/data_loader.py` — loads hole-level baseline data:

```
load_all_data(exclude_teg_50, exclude_incomplete_tegs)
  1. read_file("data/all-data.parquet")          → 53-col hole-level df
  2. read_file("data/round_info.csv")            → merge Area column
  3. optionally filter TEGs
  ▼
[hole-level df, 6390 rows × 53 cols]

Key columns: Pl, Player, TEGNum, Round, Hole, Sc, PAR, GrossVP, NetVP,
             Stableford, HoleID, FrontBack, Year, Course, Area,
             cumulative stats (*Cum*), running averages (*Avg*), Career Count
```

---

## 4. Aggregation Layer

`teg_analysis/analysis/aggregation.py` — sums scores at different levels:

```
hole-level df
  │
  ├─ aggregate_data(df, "Round")     → round-level df    (Player+TEG+Round+Course+Date…)
  │    └─ get_round_data()           ← convenience wrapper
  │
  ├─ aggregate_data(df, "TEG")       → TEG-level df      (Player+TEG+Year+Area…)
  │    └─ get_complete_teg_data()    ← excludes incomplete TEGs
  │
  └─ aggregate_data(df, "FrontBack") → 9-hole df         (Player+TEG+Round+FrontBack…)
       └─ get_9_data()               ← convenience wrapper
```

---

## 5. Rankings Layer

`teg_analysis/analysis/rankings.py` — adds rank columns:

```
add_ranks(df)
  ├─ Rank_within_player_Sc
  ├─ Rank_within_player_GrossVP
  ├─ Rank_within_player_NetVP
  ├─ Rank_within_player_Stableford
  ├─ Rank_within_all_Sc
  ├─ Rank_within_all_GrossVP
  ├─ Rank_within_all_NetVP
  └─ Rank_within_all_Stableford

Convenience wrappers:
  get_ranked_teg_data()       = get_complete_teg_data()  + add_ranks()
  get_ranked_round_data()     = get_round_data()         + add_ranks()
  get_ranked_frontback_data() = get_9_data()             + add_ranks()
```

---

## 6. Analysis Functions (On-Demand)

Called directly, not cached in deps:

```
teg_analysis/analysis/
  history.py
    ├─ get_teg_winners(all_data)       → Trophy / Jacket / Spoon per TEG
    ├─ get_eagles_data(all_data)       → eagle records
    └─ get_holes_in_one_data(all_data) → HiO records

  streaks.py
    ├─ build_streaks(all_data)         → streak counters per hole per player
    ├─ get_max_streaks(streaks_df)     → career best per player
    └─ get_current_streaks(streaks_df) → current ongoing streaks

  scoring.py
    ├─ calculate_par_performance_matrix() → avg GrossVP by par type
    └─ count_scores_by_player()          → score frequency distribution
```

---

## 7. Webapp Caching Layer

`webapp/deps.py` — `@lru_cache(maxsize=1)` wrappers, no TTL, cleared manually:

```
cached_load_all_data()         → hole-level df  (53 cols)
cached_round_data()            → round-level df
cached_complete_teg_data()     → TEG-level df   (complete TEGs only)
cached_9_data()                → 9-hole df
cached_ranked_teg_data()       → TEG-level df   + rank cols
cached_ranked_round_data()     → round-level df + rank cols
cached_ranked_frontback_data() → 9-hole df      + rank cols

Helpers:
  create_leaderboard(df, col)  → pivot Player×Round → totals → ranks
  format_value(val, field)     → styled string
  get_default_teg_num()        → latest TEG
```

---

## 8. HTTP Request → Response Flow

### Leaderboard
```
GET /leaderboard
  ├─ theme_middleware  →  request.state.theme
  ├─ routes/leaderboard.py
  │   ├─ cached_round_data()      filter to selected TEG
  │   ├─ create_leaderboard(df)   pivot Player×Round → totals
  │   ├─ _build_table_html(df)    → HTML string
  │   └─ TemplateResponse("leaderboard.html", ctx)
  └─ Browser

GET /leaderboard/table  (HTMX swap)
  └─ TemplateResponse("partials/leaderboard_table.html", ctx)
```

### Records
```
GET /records/tab/{tab_name}  (HTMX swap)
  ├─ routes/records.py
  ├─ cached_ranked_*_data()  or  cached_load_all_data()
  ├─ prepare_records_table() / prepare_streak_records_table()
  │  (teg_analysis/display/formatters.py)
  ├─ _build_records_html(df)     → HTML string
  └─ TemplateResponse("partials/records_tab.html", ctx)
```

### Charts
```
GET /charts
  ├─ routes/charts.py
  ├─ cached_load_all_data()
  ├─ create_cumulative_graph()  (webapp/chart_utils.py)  → Plotly Figure
  ├─ fig.to_json()
  └─ TemplateResponse("charts.html", {figure_json: …})
```

### Player Page
```
GET /player/{code}
  ├─ routes/player.py
  ├─ cached_ranked_teg_data() + cached_round_data() + cached_load_all_data()
  ├─ get_teg_winners(), get_eagles_data(), build_streaks()  (called directly)
  ├─ _build_stat_cards(), _build_trophy_cabinet(), _build_overview_context()
  └─ TemplateResponse("player.html", ctx)
```

---

## 9. Full End-to-End

```
[GitHub repo]  ←──────────────────────────── write_file() (Streamlit update pages only)
     │
     │  read_from_github() (Railway first-boot or cache miss)
     ▼
[Railway volume / local data/]
     │
     │  read_file()
     ▼
[all-data.parquet]  +  [round_info.csv]
     │
     │  load_all_data()
     ▼
[hole-level df, 53 cols]
     │
     ├──────────────────────────────────────────────────────────────┐
     │  aggregate_data()    │  aggregate_data()    │  aggregate_data()
     ▼                      ▼                       ▼
[round df]           [TEG df]                [9-hole df]
     │                   │                       │
     │  add_ranks()      │  add_ranks()          │  add_ranks()
     ▼                   ▼                       ▼
[ranked round df]   [ranked TEG df]      [ranked 9-hole df]
     │                   │                       │
     └───────────────────┴───────────────────────┘
                         │
              webapp/deps.py  @lru_cache wrappers
                         │
              webapp/routes/*.py  (filter, pivot, format)
                         │
              Jinja2 templates  (HTML + Plotly JSON)
                         │
                    Browser
```

