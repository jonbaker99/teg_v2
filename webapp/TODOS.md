# webapp — To-dos

Working list for the webapp. Detail references: [PARITY_AUDIT.md](PARITY_AUDIT.md) (page-by-page parity checklist), [MOBILE_PLAN.md](MOBILE_PLAN.md) (mobile/dark-mode phased plan).

---

## Bugs — fix before publish

- [ ] **`/personal-bests` round tabs error** — `"['Round_Label'] not in index"` in `routes/performance.py`. Summary and TEG tabs fine; round-detail view gets wrong data shape.
- [ ] **`/latest-teg` Streaks tab only shows final round** — `get_player_window_streaks(..., round_num=last_round)` in `routes/latest.py` should aggregate across all TEG rounds (and handle cross-round streaks).
- [ ] **Records & PBs on `/latest-round` and `/latest-teg`** — not verified correct; draft warning shown (`_RECORDS_DRAFT_NOTE` in `routes/latest.py`). Verify figures against known-good source then remove warning.

## Charts — known issues, parked

- [ ] **HTMX chart bug** — after a tab-swap, Plotly's top SVG layer (legend, annotations, shapes) mis-positions and stays broken until full page reload. Affects `/results` and any chart in an HTMX fragment. Root cause: top-layer CSS offset, not a sizing/resize issue (confirmed — don't retry resize/rAF approaches).
- [ ] **Restore `/results` race chart** — replaced with `.chart-placeholder` pending chart rebuild. Re-wire to `create_cumulative_graph` in `chart_utils.py`; per-variant meta in `_results_chart_meta()` in `routes/history.py`.
- [ ] **Chart appearance** — webapp charts look poor vs Streamlit. Goal: match Streamlit's clean rendered style via `chart_utils.py` / `get_plotly_theme`.

## Mobile & dark mode

- [ ] **Phase M1 — app shell on phones** — bottom tab bar, sticky app bar, reflowed layout. Pickup pointer: `MOBILE_PLAN.md` line 27. Foundations (Phase M0) are done.

## Planned enhancements

- [ ] **Score-count matrix % pill** — absolute / % toggle on `/scoring/matrix` and Scoring tab on `/latest-teg`. Use `.pill-group` component.
- [ ] **Bestball/worstball on `/latest-round`** — show best/worst bestball and worstball positions in the round-in-context page.
- [ ] **Related links section** — cross-page related-links block (low priority).
- [ ] **Search/filtering** — some routes have it, not everywhere.

## Cosmetic / parity (from PARITY_AUDIT.md)

Low priority — functional parity is complete; these are visual refinements.

- [ ] Styled history table (teg/area compound cell, player-name spans)
- [ ] Full trophy names in tab labels
- [ ] Vertical-line issue near chart/table on results page
- [ ] First/last-place cell highlighting on leaderboard
- [ ] Styled score/when cells in PB summary
- [ ] Metric tiles with delta indicators on latest pages
- [ ] Legend click-to-highlight (Altair behaviour)
- [ ] Data table behind expander on scoring pages
- [ ] Summary tab: per-player averages/bests/worsts (`create_course_summary_table`)
- [ ] Date column on records tables (verify data source)
- [ ] Ridgeline distribution chart
- [ ] Course/Player/TEG/Round multiselect filters on heatmap
- [ ] Multi-dimension row selection on heatmap
- [ ] Colour scheme / reverse / min-mid-max controls on heatmap
- [ ] Line/trend chart (avg by hole + TOTAL) on heatmap
- [ ] Desktop/Mobile layout toggle
