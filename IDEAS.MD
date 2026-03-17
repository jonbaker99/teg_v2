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

## WEBAPP — NEW PAGES

### Player profiles (`/player/<name>`)
Career stats, scoring trends, head-to-head records, best/worst rounds for a single player. Natural click-through destination from leaderboard and records pages.

### Round/scorecard detail (`/teg/<n>/round/<r>`)
Hole-by-hole scorecard for a given round. Detail view people would click through to from the leaderboard.

### Head-to-head comparison (`/compare`)
Pick two players, see side-by-side career stats — scoring averages, win records against each other, performance by course.

---

## WEBAPP — UI / DESIGN

### Theme refinement / page title design pass
Page titles at the top of the content area look incongruous across themes. Needs a typography hierarchy pass — spacing, font sizing, and page header treatment to feel cohesive.

### Charts/visualisations on more pages
The `/charts` page exists but leaderboard and records could benefit from inline sparklines or mini-charts (scoring trends, handicap progression over time).

### Responsive / mobile polish
Tables and stat cards need work on small screens if the webapp is to be shareable with other TEG participants.

---

## WEBAPP — FEATURES

### Data filters / query controls
Allow users to filter leaderboard/records by TEG range, player subset, or course — without reloading the page (HTMX swap).

---

## FUTURE / DEFERRED

### Framework / platform choice
Big question: is Streamlit + Railway the right long-term stack, or should we move to something else (NiceGUI, FastAPI + React, etc.)? Defer until the API layer is proven.

### REST API / retire Streamlit
Expose `teg_analysis/` as a proper REST API so other frontends (mobile, etc.) can consume the data. Once the webapp covers the same feature set, deprecate Streamlit and consolidate on a single frontend.

