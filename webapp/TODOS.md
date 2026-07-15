# webapp — To-dos

Working list for the webapp. Detail references: [PARITY_AUDIT.md](PARITY_AUDIT.md) (page-by-page parity checklist), [MOBILE_PLAN.md](MOBILE_PLAN.md) (mobile/dark-mode phased plan).

---

## IN PROGRESS

- [ ] **Bestball/worstball on `/latest-round`** — show best/worst bestball and worstball positions in the round-in-context page.
- [ ] **`/scoring/matrix`** - score type as pills; TEG / Round / 9 as tabs


## NEXT UP

- [X] **2026-07-10 to-do batch (done)** — shipped on `claude/web-app-todos-planning-0o3uui` (PR #67):
  - by-teg `nan` → `-` (fixed centrally in `webapp/tables.py::df_to_html`, + `tests/test_tables.py`)
  - `/scoring/by-par` wider column padding (page-scoped `.by-par-panel`)
  - `/scoring/distributions` chart now follows the %/Count toggle; % mode overlays an "All players" team-average tick per score category
  - eclectic/bestball birdie-ring sizing (`.bw-scorecard`)
  - **performance:** player pages ~1.7s → ~190ms (cache the global records/worsts tables via `deps.register_cache_clearer`); scorecard no longer re-reads the full dataset per request (`get_scorecard_data(data=...)`)
  - **latest-teg Eclectic:** player-ranks table (all-time + own-history) + bestball-style contribution bars (`teg_analysis/analysis/eclectic.py`: `eclectic_player_teg_totals`, `rank_teg_eclectics`, `calculate_eclectic_contributions`; `display/scorecards.py::build_eclectic_contribution_bars`)
  - multi-series charts dim other series on legend hover (centralised Plotly renderer in `base.html`)


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
  - **Design-vibe typography pass done** (`/player/{code}`): player name, metric/trophy/detail values + labels, career-span meta and the doubles footnote all moved to Roboto Mono to match the roster; `.section-title` moved serif→mono **globally** (masthead `.page-title` stays the one serif survivor). Green/red detail-card borders kept intentionally (silverware-exclusive accent rule relaxed — see `design_principles.md`). Layout/spacing/section-ordering polish still open.

## Mobile & dark mode

- [X] **Phase M1 — app shell on phones** — bottom tab bar, app bar, segmented controls, sticky-column tables. Done (see `MOBILE_PLAN.md` → Status).
- [X] **Phase M2.7 — leaderboard card reflow** — `/leaderboard` + `/results` standings as hero pods + card rows on phones.
- [ ] **Phase M2.8 — mobile chart preset** — blocked on the parked HTMX chart bug.
- [ ] **Phase M2.9 — per-page mobile pass** — spacing, tap targets, empty states; consider card reflow for Latest Round / Records. Pickup pointer: `MOBILE_PLAN.md` → Status.
- [ ] **Dark mode: page-title contrast on dark** — `.page-title` nearly invisible in dark mode (pre-existing, seen during M2 verification; part of the deferred dark QA sweep).
- [ ] **Records table horizontal overflow on narrow screens** — long location strings (e.g. `TEG 8 (Lisbon Coast, Portugal, 2015)`) push the `/records` tables past the panel/viewport at narrow widths, causing horizontal scroll. Pre-existing (unrelated to the page-gutter fix). Apply the mobile table approach — sticky-column / horizontal-scroll container or name-shortening — per `design_principles.md` → Tables.

## Planned enhancements

- [ ] **Remote report generation (admin-triggered)** — no webapp UI/route currently triggers the `teg_analysis/reporting/` pipeline; report generation is a local/manual process (run the pipeline via script/notebook with `ANTHROPIC_API_KEY`, then get the output file onto the Railway volume) before it's viewable at `/teg-reports` or the Report tabs. Add an admin-triggered generate flow (e.g. a button on `/admin` that runs the pipeline as a background task and writes/syncs the resulting `..._report_styled.md`). (Note: the separate *viewing* bug — reports not appearing on Railway at all — was diagnosed and fixed 2026-07-12; see `teg_analysis/reporting/STATUS.md` → "Known issues". This item is about generation only.)

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
