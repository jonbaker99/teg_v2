# webapp — To-dos

Working list for the webapp. Detail references: [PARITY_AUDIT.md](PARITY_AUDIT.md) (page-by-page parity checklist), [MOBILE_PLAN.md](MOBILE_PLAN.md) (mobile/dark-mode phased plan).

---

## IN PROGRESS
- [ ] **CHARTS**

## NEXT UP


## Bugs — fix before publish

## UI Changes

- [ ] **History table** - Consistent column widths for final 3 columns. Use full width of page. Consistent line break between first names and surnames in final 3 columns - either all or none.
- [ ] **Table font** - make a touch smaller to match streamlit
- [ ] **General tables** - consistent column widths where possible for similar type of columns

- [ ] **Eclectics** - use scorecard gross formatting


## Charts — known issues, parked

- [ ] **HTMX chart bug** — after a tab-swap, Plotly's top SVG layer (legend, annotations, shapes) mis-positions and stays broken until full page reload. Affects `/results` and any chart in an HTMX fragment. Root cause: top-layer CSS offset, not a sizing/resize issue (confirmed — don't retry resize/rAF approaches).
- [ ] **Restore `/results` race chart** — replaced with `.chart-placeholder` pending chart rebuild. Re-wire to `create_cumulative_graph` in `chart_utils.py`; per-variant meta in `_results_chart_meta()` in `routes/history.py`.
- [ ] **Chart appearance** — webapp charts look poor vs Streamlit. Goal: match Streamlit's clean rendered style via `chart_utils.py` / `get_plotly_theme`.

## Mobile & dark mode

- [ ] **Phase M1 — app shell on phones** — bottom tab bar, sticky app bar, reflowed layout. Pickup pointer: `MOBILE_PLAN.md` line 27. Foundations (Phase M0) are done.

## Data admin (update / edit / delete)

Currently out of scope — Streamlit handles this via three pages (`1000Data update.py`, `data_edit.py`, `delete_data.py`) backed by `helpers/data_update_processing.py` and `helpers/data_deletion_processing.py`. Needs building in the webapp before Streamlit can be retired.

- [ ] **Add scores** — form to add hole-by-hole scores for a new round, writing back to the data store
- [ ] **Edit scores** — tabular editor to correct existing scores
- [ ] **Delete scores** — delete a round or individual entries

## Scorecard improvements

- [ ] **Mouseover tooltips on scorecard cells** — on hover show: Hole, Par, SI, Score, Net, Stableford

## Planned enhancements

- [ ] **Score-count matrix % pill** — absolute / % toggle on `/scoring/matrix` and Scoring tab on `/latest-teg`. Use `.pill-group` component.
- [ ] **Bestball/worstball on `/latest-round`** — show best/worst bestball and worstball positions in the round-in-context page.
- [ ] **Related links section** — cross-page related-links block (low priority).
- [ ] **Search/filtering** — some routes have it, not everywhere.

## Cosmetic / parity (from PARITY_AUDIT.md)

Low priority — functional parity is complete; these are visual refinements.

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
