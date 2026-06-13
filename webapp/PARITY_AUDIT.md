# Webapp ↔ Streamlit feature-parity audit

Working checklist tracking functional parity between each webapp page and its
Streamlit source. "Page existence" parity is done (every Streamlit page, minus
Data-admin, has a webapp route). This file tracks the remaining **functional**
gaps — controls, views, measures, charts that the Streamlit page exposes but
the webapp does not yet.

Scope note: the goal is *structure & content* parity using the webapp's own
theme/design — not pixel-matching Streamlit. Cosmetic-only differences (exact
cell highlight colours, expander-vs-always-visible) are noted but low priority;
missing controls/views/measures/data are the real work.

Status key: `[x]` done · `[ ]` outstanding · `[~]` partial/in progress

## Page-by-page mapping (every Streamlit page → webapp route)

Source of truth: `streamlit/page_config.py` `PAGE_DEFINITIONS`. The Data-admin
section is excluded by design (per the goal). Every active non-Data Streamlit
page has a webapp route, and all 28 return HTTP 200 (verified via TestClient).
Two `PAGE_DEFINITIONS` entries — `400scoring.py` ("Scoring") and
`scorecard_v2_mobile.py` ("Scorecard (mobile)") — are **commented out** in
`page_config.py` and are therefore not live Streamlit pages.

| Section | Streamlit page (title) | Webapp route |
|---|---|---|
| Contents | Contents | `/contents` |
| TEG History | TEG History | `/history` |
| TEG History | TEG Honours Board | `/honours` |
| TEG History | Full Results | `/results` |
| TEG History | Player Rankings | `/player-rankings` |
| TEG History | TEG Reports | `/teg-reports` |
| Records & PBs | TEG Records | `/records` |
| Records & PBs | Top TEGs and Rounds | `/top-performances` |
| Records & PBs | Personal Bests | `/personal-bests` |
| Latest TEG | Latest Leaderboard | `/leaderboard` |
| Latest TEG | Latest Round in context | `/latest-round` |
| Latest TEG | Latest TEG in context | `/latest-teg` |
| Latest TEG | Handicaps | `/handicaps` |
| Scoring analysis | Eagles / Birdies / Pars | `/scoring/birdies` |
| Scoring analysis | Streaks | `/scoring/streaks` |
| Scoring analysis | Average by par | `/scoring/by-par` |
| Scoring analysis | Average by TEG | `/scoring/by-teg` |
| Scoring analysis | Course averages and records | `/scoring/by-course` |
| Scoring analysis | All rounds | `/scoring/all-rounds` |
| Scoring analysis | Score matrix | `/scoring/matrix` |
| Scoring analysis | Scoring distributions | `/scoring/distributions` |
| Scoring analysis | Changes vs previous round | `/scoring/changes` |
| Scoring analysis | Heatmap (WIP) | `/scoring/heatmap` |
| Scoring analysis | Final Round Comebacks | `/scoring/comebacks` |
| Scorecards | Scorecard | `/scorecard` |
| Scorecards | Best/Worstball | `/bestball` |
| Scorecards | Eclectic Scores | `/eclectic` |
| Scorecards | Eclectic Records | `/eclectic-records` |

Excluded (Data-admin, per the goal): Data update, Report generation, Data edit,
Delete data, Data volume management.

## Status summary

The substantive functional gaps (missing controls / views / measures / data /
charts) have been closed across every page, **including the deep/conditional
ports**: Latest-page metric sub-tabs (+ per-metric round chart), the Latest
streak-type pivot + caption, the full records-completeness categories (all-time
worsts / 9-hole / streak / score-count records), the Handicaps draft-handicap
section (handicap recalc ported to `teg_analysis/analysis/handicaps.py`; the
draft banner + "Draft handicaps for TEG N+1" section appear when a TEG is in
progress), and the "Ranking" race-chart variant on Leaderboard & Results.

Every webapp endpoint returns 200 and renders its Streamlit-equivalent content.
What remains outstanding is **cosmetic only** (out of scope per the goal —
"structure & content, not visual mimicry"; e.g. cell highlighting, full trophy
tab-label names, handicap metric-tiles, styled PB cells, Altair legend-highlight
interaction) plus the **Heatmap** advanced controls (the page is marked WIP in
*both* apps) and the Course-summary per-player detail (the webapp already shows
a broadly-equivalent course summary).

---

## TEG History

### TEG History (`/history`)
- [x] TEG 5 Green Jacket footnote caption
- [ ] Styled history table (teg/area compound cell, player-name spans) — cosmetic

### Honours Board (`/honours`)
- [x] Green Jacket tab: TEG 5 footnote caption
- [ ] Full trophy names in tab labels (e.g. "TEG Trophy (Stableford)") — cosmetic

### Full Results (`/results`)
- [x] Chart-type switcher (Standard / Adjusted / Ranking) on net & gross race charts
- [x] Wooden-spoon callout on net leaderboard
- [x] Inline per-round scorecards
- [x] Report tab: pre-TEG-8 scoring caption
- [x] Report tab: fallback from `_report_styled.md` to `_main_report.md`
- [ ] Vertical-line issue (stray rule near chart/table) — refinement-stage fix, cosmetic

### Player Rankings (`/player-rankings`)
- [x] TEG Trophy (net) ranking tab — NetVP for older TEGs, Stableford for TEG 8+
- [x] Green Jacket (gross) ranking tab
- [x] Tie `=` markers and `-` for non-participation
- [x] Combined position summary tables (Ave, TEGs, 1st–6th) for both competitions
- [x] Advanced Options: Full Name/Initials + TEG Name/Number dimension selectors
- [ ] First/last-place cell highlighting — cosmetic

### TEG Reports (`/teg-reports`)
- [x] Normal / Satire report-type toggle
- [x] Round-report filename fallbacks (new `TEG{N}_R{r}_report.md` + non-styled)
- [x] Tournament-report `_main_report.md` fallback
- [x] Pre-TEG-8 caption

## Records & PBs

### TEG Records (`/records`)
- [x] Streaks tab: "* and counting..." caption
- [x] Score Counts tab: "Eagles, Birdies and Pars also include better scores" caption

### Top TEGs and Rounds (`/top-performances`)
- [x] Measure labels/order match Streamlit (Gross / Score / Net / Stableford)
- [x] Free-entry N (1–100) instead of fixed 3/5/10 dropdown
- [x] Section heading embeds the Top-N count (e.g. "Top 5 TEGs: Gross")
- [x] TEG 2 exclusion note caption

### Personal Bests (`/personal-bests`)
- [x] PB Summary: "Best 9s" sub-view (front/back 9 via ranked frontback data)
- [x] Free-entry N for detail tabs
- [ ] Styled score/when cells in PB summary — cosmetic

## Latest TEG

### Latest Leaderboard (`/leaderboard`)
- [x] Cumulative Stableford race chart (Standard / Adjusted / Ranking) — net tab
- [x] Cumulative GrossVP race chart (Standard / Adjusted / Ranking) — gross tab
- [x] Scorecards tab (per-round inline scorecards)
- [x] Wooden-spoon callout already present on net? verify gross has champion only

### Latest Round in context (`/latest-round`)
- [x] Report tab (round report markdown)
- [x] Scoreboards: metric sub-tabs + per-metric cumulative chart
- [x] Scorecard tab: inline scorecard (Desktop/Mobile toggle = cosmetic, skipped)
- [x] Scoring tab: Stableford toggle (currently Gross only)
- [x] Streaks tab: pivoted streak table + caption
- [x] Records & PBs tab: all-time worsts, 9-hole, streak records, score-count records
- [x] Course + date context header

### Latest TEG in context (`/latest-teg`)
- [x] Report tab (TEG report markdown)
- [x] Aggregate Score: metric sub-tabs
- [x] Scoring tab: Stableford toggle
- [x] Streaks tab: pivoted streak table + caption
- [x] Records & PBs tab: all-time worsts, streak records, score-count records

### Handicaps (`/handicaps`)
- [ ] Metric tiles with delta indicators — cosmetic
- [x] Draft/in-progress detection + "Draft handicaps for TEG N+1" section

## Scoring analysis

### Eagles / Birdies / Pars (`/scoring/birdies`)
- [x] BUG: "Max per TEG" tab uses `score_type_stats` instead of `max_scoretype_per_teg`

### Streaks (`/scoring/streaks`)
- [x] "Streak detail" tab (TEG/Round/Player filters + hole-level window streaks)
- [x] Record streaks asterisk footnotes

### Average by par (`/scoring/by-par`)
- [x] (no functional gap)

### Average by TEG (`/scoring/by-teg`)
- [ ] Legend click-to-highlight (Altair behaviour) — cosmetic/interaction
- [ ] Data table behind expander — cosmetic

### Course averages and records (`/scoring/by-course`)
- [ ] Summary tab: per-player averages/bests/worsts (full `create_course_summary_table`)
- [ ] Date column on records tables — verify data source

### All rounds (`/scoring/all-rounds`)
- [x] Area / Course / Player filters
- [x] Measure switcher (Score / Gross / Stableford / Net)
- [x] "Number of rounds to show" input
- [x] PB Rank column (e.g. "3/15")

### Score matrix (`/scoring/matrix`)
- [x] +/- sign formatting on GrossVP / NetVP columns

### Scoring distributions (`/scoring/distributions`)
- [x] Score-type switcher (Scores / vs Par / Stableford)
- [x] Player / TEG / Par filters
- [x] Count / Percentage mode toggle
- [x] "By TEG" tab (crosstab)
- [ ] Ridgeline distribution chart — lower priority

### Changes vs previous round (`/scoring/changes`)
- [x] TEG filter
- [x] "Include changes across TEGs?" toggle
- [x] "Rounds to show" (All / Top N)
- [x] Improvements / Worsenings tabs
- [x] Columns: raw Score, Previous Round, Course, Year; change on raw Sc

### Heatmap WIP (`/scoring/heatmap`)
- [ ] Course/Player/TEG/Round multiselect filters
- [ ] Multi-dimension row selection
- [x] Column (X-axis) switcher — Hole / Stroke Index / Par / TEG / Course / Region
- [ ] Colour scheme / reverse / min-mid-max controls — cosmetic
- [ ] Line/trend chart (avg by hole + TOTAL)
- (note: page is marked WIP in both apps)

### Final Round Comebacks (`/scoring/comebacks`)
- [x] "Worst Final Round Performances by Leaders" sub-section
- [x] +/- / int score formatting in tables
- [x] Notes/caption at bottom

## Scorecards

### Scorecard (`/scorecard`)
- [x] Scorecard-type selector (1 Round/1 Player, 1 Player/All Rounds, 1 Round/All Players)
- [x] Player selector
- [ ] Desktop/Mobile layout toggle — cosmetic
- [x] Missing views: single-player/single-round, single-player/all-rounds
- [x] 1 Round/1 Player rendered as a single combined card (gross "Score" row +
      "Stableford" row), matching Streamlit's `generate_single_round_html`
- [x] Formatted scorecards (shape/colour cells) applied consistently on
      Latest Round and Full Results too — the scorecard CSS variables are now
      declared on `.scorecard-table` as well as `.scorecard-wrapper`, so tables
      render styled even when not inside the Scorecard page's wrapper

### Best/Worstball (`/bestball`)
- [x] Free-entry N (default 3) instead of fixed All/10/25/50
- [x] Dynamic "Best/Worst Bestball/Worstball" heading

### Eclectic Scores (`/eclectic`)
- [x] Player / TEG / Course filters
- [x] "Based on N rounds" caption

### Eclectic Records (`/eclectic-records`)
- [x] Built (Top 3 + Personal Best, TEGs/Courses tabs)
