# webapp — To-dos

Working list for the webapp. Detail references: [PARITY_AUDIT.md](PARITY_AUDIT.md) (page-by-page parity checklist), [MOBILE_PLAN.md](MOBILE_PLAN.md) (mobile/dark-mode phased plan).

---

## IN PROGRESS

- [X] **Default look** - use 'clean page' and remove the dropdown unless I specifically ask to go into UI development mode
- [X] **Score-count matrix % pill** — absolute / % toggle on Scoring tab on `/latest-teg`. Use `.pill-group` component.

- [ ] **Bestball/worstball on `/latest-round`** — show best/worst bestball and worstball positions in the round-in-context page.
- [X] **Score matrix** - rename to score history
- [ ] **`/scoring/matrix`** - score type as pills; TEG / Round / 9 as tabs


## NEXT UP


## Bugs — fix before publish

## UI Changes

- [ ] **Prefer CSS bar charts over Plotly where feasible** — the bestball/worstball
  contribution bars (`build_bestball_contribution_bars`) use lightweight CSS bars
  that read better inline than the equivalent Plotly panels. Roll the same approach
  out to other small bar charts where Plotly is overkill.
- [ ] **Roll out mobile name shortening where width is tight** — the
  `Initial. SURNAME` swap (`_player_name_spans`, classes `bw-name-full` /
  `bw-name-short`) is used by the bestball/worstball contribution table and field
  card. Audit other tables where a player-name column compromises data display on
  narrow screens and apply the same helper (and, for wide tables, split into
  side-by-side tables that wrap). See `webapp/design_principles.md` → Tables.

## PLAYER PROFILES
- [ ] Revisit again to make UI cleaner and less cluttered
- [ ] UI design pass** — `/player/{code}` and the `/player` roster have been significantly reworked (metric cards, career highlights, records/worsts, bar charts, roster cards with stars). Functionality is complete. Revisit with fresh eyes for: layout rhythm and section ordering, chart sizing and padding, card density, label clarity, mobile view. See `webapp/routes/player.py` and `webapp/templates/partials/player_overview.html`.

## Mobile & dark mode

- [X] **Phase M1 — app shell on phones** — bottom tab bar, app bar, segmented controls, sticky-column tables. Done (see `MOBILE_PLAN.md` → Status).
- [X] **Phase M2.7 — leaderboard card reflow** — `/leaderboard` + `/results` standings as hero pods + card rows on phones.
- [ ] **Phase M2.8 — mobile chart preset** — blocked on the parked HTMX chart bug.
- [ ] **Phase M2.9 — per-page mobile pass** — spacing, tap targets, empty states; consider card reflow for Latest Round / Records. Pickup pointer: `MOBILE_PLAN.md` → Status.
- [ ] **Dark mode: page-title contrast on dark** — `.page-title` nearly invisible in dark mode (pre-existing, seen during M2 verification; part of the deferred dark QA sweep).

## Planned enhancements

- [ ] **Hole-level score correction** — inline editor to fix individual hole scores after entry. Not built in either app: Streamlit's `data_edit.py` and the webapp's `/admin/edit-data` both only cover metadata CSVs (round info, handicaps, etc.), not raw hole-level scores. Not a Streamlit-retirement blocker (Streamlit never had this either) — a standalone future enhancement.

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
