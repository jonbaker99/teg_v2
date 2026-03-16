# Ideas

## FIXES

### Net competition scoring cutoff
The code in `teg_analysis/analysis/scoring.py` correctly implements the cutoff at TEG 8 (TEGs 1–7 use NetVP, TEG 8+ use Stableford), but two places document it incorrectly as TEG 6:
- `scoring.py` docstring (line 42–43) says "TEGs 1-5" / "TEG 6 onwards"
- `CLAUDE.md` general info section says "Up to TEG 5 ... from TEG 6 onwards"

**Fix:** Update those two docstrings/docs to match the actual logic (`<= 7` → NetVP, `>= 8` → Stableford).

---

## DATA UPDATES

### Remote data update workflow
Current approach uses the Streamlit admin page (`1000Data update.py`). This needs review — need to identify the best approach for updating core data (scores, handicaps, round info) remotely after each round, without requiring a laptop running the Streamlit app.

**Open question:** What's the best architecture here? Options likely include:
- A standalone script that can be run anywhere
- A lightweight form/API endpoint on Railway
- Direct GitHub commits from a mobile-friendly tool

---

## API / BACKEND

### Barebones API test harness
Build a minimal site or script that exercises the `teg_analysis` package's API to confirm it can generate every data table currently shown in the Streamlit app. Goal is to validate the API layer is complete and correct before investing in a new frontend. Not a production site — just a coverage check.

---

## FUTURE / DEFERRED

### Framework / platform choice
Big question: is Streamlit + Railway the right long-term stack, or should we move to something else (NiceGUI, FastAPI + React, etc.)? Defer until the API layer is proven.

### FastAPI + HTMX + Jinja2 + Tailwind PoC — `webapp/`
A proof-of-concept web app has been built in `webapp/` to test the FastAPI + HTMX + Jinja2 + Tailwind stack and try out different visual styles / UIs.

**Run it:**
```bash
# From repo root: /Users/jon/projects/teg/teg_v2
uvicorn webapp.app:app --reload
# Then visit http://localhost:8000
```

**What's included:**
- `/leaderboard` — Net + Gross leaderboards for any TEG, with HTMX dropdown to switch TEGs without page reload
- `/charts` — Cumulative Plotly charts (Stableford, Gross, Adjusted versions), switchable by TEG and chart type
- `/records` — All records pages (TEG, Round, 9-Hole, Streaks, Score Counts) as HTMX tabs

**Stack:** FastAPI routes → Jinja2 templates → Tailwind CSS (CDN) + HTMX (CDN) + Plotly.js (CDN). All data comes from `teg_analysis/` package via `lru_cache` wrappers in `webapp/deps.py`.

**Purpose:** Use this to experiment with different visual styles, layouts, and UI patterns before committing to a full migration away from Streamlit.
