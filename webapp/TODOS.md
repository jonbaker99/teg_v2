# webapp — To-dos

Working list for the webapp. Detail references: [PARITY_AUDIT.md](PARITY_AUDIT.md) (page-by-page parity checklist), [MOBILE_PLAN.md](MOBILE_PLAN.md) (mobile/dark-mode phased plan).

---

## IN PROGRESS

- [ ] **Verify live report refresh after deployment (2026-09-13).**
  Report sync now includes tournament/round
  `*_report_storylinefirst_styled.md` and `*_storyline_plan.json` in “Sync all
  reports from GitHub”. Then run the sync and check deterministic blocks live.
  Regression tests reproduce stale volume reads before the fix; 33 sync tests
  pass afterward. Manual workaround: select those files in `data/commentary`
  and use “Pull selected”.
- [x] **Immediate feedback for Pull selected (2026-09-13).** Buttons show
  “Checking selected files…” during preview metadata requests, disable repeat
  submissions and show busy confirmation labels before copy progress. Verified
  with a delayed local browser flow through preview, progress and completion.

- [x] **Review shared UI polish on `ui/shared-polish-review`** — navigation,
  title alignment, mobile component insets, tab scroll cues and GET failure
  feedback implemented; user approved for merge 2026-09-12. Automated browser
  visual verification was unavailable. Follow-ups below retain unimplemented items.
- [ ] **Page smoke test report fixture drift** —
  `test_teg_reports_round_without_a_storyline_edition_falls_back_to_legacy_markdown`
  assumes TEG 14 R1 is legacy, but current local data resolves it as new.
  Pick a legacy round from available data rather than hardcoding that fixture.


- [ ] **Bestball/worstball on `/latest-round`** — show best/worst bestball and worstball positions in the round-in-context page.
- [ ] **`/scoring/matrix`** - score type as pills; TEG / Round / 9 as tabs
- [x] **Remote/on-the-fly report generation — admin-triggered, the clubhouse use case (2026-09-12).**
  `/admin/reports` runs the newspaper-style pipeline (storylines → draft → voice) directly on the
  webapp process, for both tournament and round reports, then pushes the result to GitHub — no
  laptop or CLI needed after a round ends. `POST /admin/reports/generate` (`kind=round|tournament`)
  claims a single-flight slot per (TEG, round) and enqueues a `BackgroundTasks` job;
  `GET /admin/reports/status` is the HTMX poll target, self-terminating once the run reaches a
  terminal state. All of it lives in the new `webapp/report_generation.py` (the status-file state
  machine + the background task) and `webapp/routes/admin_reports.py` (route plumbing only) — see
  `webapp/README.md`'s admin section for why status is a file, not the in-memory dict the
  volume-sync jobs use. **The staging step is the load-bearing part**: the pipeline writes its
  artefacts to a CWD-relative `data/commentary/` (`teg_analysis.reporting.paths.output_dir`), which
  on Railway is *not* the mounted volume (`data/` is excluded from the Docker image) — so every run
  copies its four output files into the real store before the site can see them, then
  `teg_analysis.io.push_files` commits them to GitHub in one batch. A failed push doesn't block
  reading the report (state `done_local_only`, retry from `/admin/volume-sync`); a failed
  generation never reaches staging (state `error`). Manual trigger only, full pipeline only
  (no stage-by-stage UI), real API billing (`ANTHROPIC_API_KEY`) — the mailbox/plan-usage path
  isn't viable standing in a clubhouse.
  **Validated live, same session:** a TEG 18 R4 round report (194s, 0 new D3 findings) and the TEG 18
  tournament report (379s, 0 new D3 findings), both generated, staged and committed to GitHub
  end to end.
- [x] **`/latest-round`'s Report tab fixed the same way (2026-09-12).** It was an HTMX tab reading
  the stale `teg_N_round_R_report_styled.md` blob, 4th of 7 tabs. Now it's the last item in the
  tab row and a real link to `/teg-reports?teg=N&round=R` for the specific round being viewed,
  hidden when that TEG/round has no newspaper edition. `latest.py` gained a `report_rounds_map`
  (`{teg: [rounds with a report]}`, via `newspaper_edition.available_rounds`) passed to
  `latest_round.html`, since the tab row sits outside `#lr-content` and both the TEG select and
  round pills swap it via HTMX without a page reload. **Caught mid-build**: `#lr-round-select` and
  `#lr-round-pills` are themselves replaced via `hx-swap-oob` on every tab swap
  (`partials/latest_round_tab.html`), so an initial version that cached those element references /
  attached click listeners directly to the pills went stale after the first swap. Fixed by
  re-querying fresh inside `sync()` and driving it off `htmx:afterSwap` on `#lr-content` instead —
  verified in a real browser (Playwright) that the link's `href`/hidden state stay correct across
  round switches both directions, not just on first load. The old `tab == "report"` branch in
  `_latest_round_tab_context` was deleted, not left dead.
- [x] **`/latest-teg`'s Report tab fixed the same way (2026-09-12).** It was already the last tab
  (no reordering needed, unlike `/latest-round`), but was an HTMX swap reading the stale
  `teg_N_report_styled.md` blob. Now a real link to `/teg-reports?teg=N`, hidden unless the TEG has
  a newspaper edition (`report_tegs`, same pattern as `/results`) — `#lt-teg-select` isn't replaced
  via `hx-swap-oob` anywhere in `partials/latest_teg_tab.html`, so the simpler `/results`-style sync
  (cache the select, one `change` listener) is safe here, unlike `/latest-round`'s. `_render_report`
  was fully dead after this (both call sites now removed) and deleted, along with the now-unused
  `markdown`/`GithubException`/`read_text_file` imports and `_COMMENTARY_DIR`/`_MD_EXTS` constants
  it alone used. `/static/teg_reports.css` and the `_report_styled.md` read path are NOT fully dead
  yet — `.teg-report` is still used by the legacy round-report fallback in `/teg-reports` itself
  (`reports.py`'s `_legacy_round_report_html`).
- [x] **`/teg-reports` TEG select moved next to the Tournament/Round pills, and both pills now
  reflect what actually exists (2026-09-12).** The select used to sit in the page title row,
  separate from the pills below it; it's now in the same `.section-controls` row as the pills
  (matching `/results`/`/leaderboard`'s own select-next-to-tabs pattern), same size/styling.
  The Tournament pill only renders when the selected TEG actually has a tournament edition, and
  each round pill only for rounds that actually exist — previously "Tournament" always showed
  whenever any round existed, tournament edition or not. Fixed by a new
  `newspaper_edition.available_report_tegs()` (tournament OR round, superset of the
  tournament-only `available_tegs()`), which now drives the `/teg-reports` TEG dropdown — a TEG
  whose only report is, say, R1 is now reachable at all (it wasn't before: the dropdown was built
  from `available_tegs()`, tournament-only) and lands on R1 by default, showing only that pill.
  `webapp/routes/reports.py` also gained a `has_tournament` context flag
  (`newspaper_edition.has_edition(teg)`) for the pill-gating.
- [x] **Report tab wired into `/results` and `/leaderboard` (2026-09-11).** Plan by Opus, implemented
  by Sonnet. The tab is a real `<a>` to `/teg-reports?teg=N` — not an HTMX swap, since the report's
  typography/palette is deliberately unlike the rest of the site and a full page transition reads
  better than an in-place DOM swap — hidden when the TEG has no newspaper edition
  (`newspaper_edition.available_tegs()`; the tab row lives outside the HTMX swap target, so a small
  inline script keeps its `href`/visibility synced to the TEG dropdown). Carries a `↗` arrow
  (`.tab-arrow`) to flag it as a real navigation before the click. The old in-page render of
  `teg_N_report_styled.md` (`history.py`'s `tab == "report"` branch) was deleted, not left dead.
  **And the reverse link**: `/teg-reports` now shows "← Back to Results" (tournament report) or
  "← Back to Round N" (round report) next to the round pills, only when there's a specific
  teg/round to deep-link to. That required teaching `/results` and `/latest-round` to accept
  `?teg=`/`?round=` query params for the first time (both previously always opened on the default/
  latest TEG) — `results_page`/`latest_round_page` in `history.py`/`latest.py`.
- [x] **Newspaper report layout — switched `/teg-reports` over (2026-09-11).** Tournament reports
  now render through `teg_analysis/reporting/newspaper_edition.py` (`build_edition`,
  `render_desktop_html`, `plan_rows`) at `/teg-reports` itself; `/teg-reports-preview` is retired.
  `webapp/routes/reports.py` renders `templates/teg_reports.html`, which **extends `base.html`** —
  site nav and chrome stay in place. `.np-page` is a scoping wrapper (fonts/colour variables, CSS
  reset), not a page background; the TEG dropdown sits in the normal site content area below the
  "History / TEG Reports" header, and the newspaper "paper" card (`.np-paper`, own cream colour +
  grain texture + border/shadow) floats on the site's own grey/white page background beneath it,
  like any other content card (Jon's call, after an initial standalone-page version read as
  jarring). Round reports were **temporarily dropped from the UI entirely** (Jon's call, same
  session) — no newspaper-layout equivalent existed yet; **re-added 2026-09-11**, see the entry
  below. The satire-draft variant was also dropped from the UI (the drafts still exist on disk, unreachable from any
  route). The provisional `?pal=`/`?sf=`/`?rail=` preview switches were locked to
  `pal=a`/`sf=contrast`/`rail=s2` (the contrast standfirst gained its own neutral grey,
  `--ink-contrast`, instead of reusing the warmer `--ink-soft`) and the switcher UI + the other
  three palettes/standfirst treatments were removed from `newspaper_preview.css`.
  Design record: `webapp/report_layout_prototypes/README.md`. Pipeline context: `DATA_FLOW.md` §10.
  First of four sequenced to-dos — see `teg_analysis/reporting/STATUS.md` → START HERE → *Next*.

- [x] **Round reports re-added — `teg_analysis/reporting/round_storyline.py` (2026-09-11).** The
  round-storyline pipeline (plan → fact-isolated draft → voice pass, mirroring the tournament
  pipeline but with two mandatory storylines — `round_story`, the best round of the day, and
  `race_story`, how the round moved the three competitions, or the coronation on a final round)
  lands `teg_N_round_R_storyline_plan.json` + the matching styled markdown, which
  `newspaper_edition.py` (generalised, not forked — `build_edition(teg, round_num=...)`) parses
  into a round edition exactly as it does a tournament one. `webapp/routes/reports.py`'s
  `teg_reports` handler takes an optional `round` query param; `templates/teg_reports.html` grows
  a `.pill-group` of round links beside the TEG select once `available_rounds(teg)` is non-empty.
  Validated cold on TEG 14 R2 (quiet), TEG 18 R3 (Jacket lead change, Spoon flip) and TEG 18 R4
  (final round) — zero D3 findings, zero dropped articles, correct lead switching (`round_story`
  leads mid-tournament, `race_story` leads on the final round). Second and third of the four
  sequenced to-dos. Detail: `teg_analysis/reporting/STATUS.md` → START HERE.


- [x] **`editions.json` going stale whenever a styled report changes** — **fixed 2026-09-10.** It
  drifted three times (PR #95's headlines, `aebf3c3`'s re-sync, PR #100's rule pass), each time
  because the styled reports changed without someone re-running the inlining. The inlining is now
  part of `python -m scripts.build_newspaper_edition`, so one command does both;
  `scripts/inline_editions` still runs standalone to re-inline without a rebuild.

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

- [ ] **Mobile table identity columns** — preserve table identity columns
  explicitly rather than always pinning column one. Navigation buttons, tablet
  breakpoint and shared mobile component insets shipped in the UI polish pass.
- [ ] **Shared interaction states** — update tab/pill selection after successful
  responses, with consistent loading/error/retry feedback; preserve public
  filter/tab state in canonical page URLs so reload, sharing and Back work.
- [ ] **Live entry save feedback** — score-write and polling failures currently
  log to the console; show saved/pending/failed state and a recoverable retry path.
- [ ] **UI development consistency** — replace Tailwind Play CDN with a pinned
  static build (include classes emitted by analysis HTML builders); lazy-load
  Plotly on chart pages; extract shared controls/table wrappers into macros;
  add a small responsive component gallery and representative browser checks.
- [ ] **Reconcile UI documentation** — README still describes mobile/dark mode
  and report generation as unbuilt; design principles retain fit-content widths
  and serif-caption claims. Align docs with shipped code and clarify typography
  and accent rules before further redesigns.

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
- [ ] **Report page — revisit non-core-text formatting** — Jon liked the look of
  the "Herron Drafts" artefact built 2026-08-13 to read the TEG 17/12 voice
  trials on mobile (title block, at-a-glance results pane, per-round standings
  boxes, PBs/TEG-records appendix). Current `/teg-reports` rendering runs
  `report_styled.md` through plain `markdown.markdown(...)` with no bespoke CSS
  for those elements (`webapp/routes/history.py` → `tab == "report"`). Revisit
  styling for `.at-a-glance-box`, `.standings`, `.records` etc. against that
  artefact's treatment when UI formatting work picks up — hairline-rule
  callout box, monospace tabular standings strip, uppercase-label records
  block. Prose styling (voice) is a separate track — see
  `teg_analysis/reporting/`.

## PLAYER PROFILES
- [ ] Revisit again to make UI cleaner and less cluttered
- [ ] UI design pass** — `/player/{code}` and the `/player` roster have been significantly reworked (metric cards, career highlights, records/worsts, bar charts, roster cards with stars). Functionality is complete. Revisit with fresh eyes for: layout rhythm and section ordering, chart sizing and padding, card density, label clarity, mobile view. See `webapp/routes/player.py` and `webapp/templates/partials/player_overview.html`.

- [ ] **"Design vibe" (lo-fi/mono) attempt — rejected on review, more work needed before retrying.**
  The `/player` roster redesign (merged, PR #71) established a lo-fi/mono-first
  direction, written up as a reusable brief in `webapp/design_principles.md` →
  Design vibe (+ a "convert a page" starter prompt). Two follow-on attempts
  applied that vibe further and **did not land** on review — kept open as
  draft PRs (not merged, not closed) purely so the pages can be checked out and
  reviewed again without redoing the work:
  - **PR #75** `claude/player-profile-design-vibe-i9n289` — converts
    `/player/{code}` (name, metric cards, trophy cabinet, Career
    Highlights/Records) to mono; also made `.section-title` mono **globally**.
    Also relaxed the "green = silverware only" accent rule to "green = positive
    /red = negative" on detail cards — a deviation from the vibe doc's "one
    accent, one meaning" principle worth scrutinising if revisited.
  - **PR #76** `claude/design-theme-serif-fonts-0tqb5o` — a full site-wide
    "Mono" theme (record-book look: no cards, shaded bands, one accent) proposed
    as the new default. **Has merge conflicts with current `main`** (PR #78,
    a narrower sans-serif-body swap, merged separately and overlaps it) — would
    need rebasing before it's even mergeable, aside from the design rejection.
  - **Reasons for rejection (captured 2026-07, on PR #75's `/player/{code}`):**
    - **No definition/structure — read as a data dump, not an overview.**
      Content sat straight on the background with nothing to group it, so the
      page felt like "a list of data" rather than a clear picture of a
      player's career. Dissolving the panel-in-panel (the pattern that worked
      well for the *roster*) was over-applied here to mean "remove grouping
      surfaces entirely" — that's not what the vibe doc's "cards float on the
      background" principle means. Floating still requires *something* (a
      card, a rule, a grouped block) to give each section definition; it does
      not mean flattening everything into one undifferentiated column.
    - **Horizontal spacing looked unplanned, especially on the "at a glance"
      section.** Elements didn't align to a shared rhythm/column — this is
      the same category of miss the roster page had before the page-gutter
      fix, but wasn't caught here before review.
    - **Career bests as two plain tables was a regression from the
      "cards" version** — less inviting/scannable than the previous
      card-based Career Highlights layout. Converting to mono doesn't require
      converting cards to tables; card **containers** are fine (and probably
      needed, per the point above) — it's the fonts/decoration/copy inside
      them that should follow the vibe.
  - **Before trying again:** check out the two branches above and look first —
    don't restart from the vibe doc blind. The direction (mono-first,
    restrained) is very likely still right; the *execution* over-corrected
    into "no structure at all." Next attempt should explicitly keep grouping
    surfaces (cards or clearly-bounded sections) for each part of the profile
    (at-a-glance, trophy cabinet, career highlights, records), apply the
    shared-gutter/aligned-column discipline throughout, and keep Career
    Highlights as cards, not a plain table — converting *only* the
    typography/decoration/copy per the vibe checklist, not the underlying
    layout structure.

## Mobile & dark mode

- [X] **Phase M1 — app shell on phones** — bottom tab bar, app bar, segmented controls, sticky-column tables. Done (see `MOBILE_PLAN.md` → Status).
- [X] **Phase M2.7 — leaderboard card reflow** — `/leaderboard` + `/results` standings as hero pods + card rows on phones.
- [ ] **Phase M2.8 — mobile chart preset** — blocked on the parked HTMX chart bug.
- [ ] **Phase M2.9 — per-page mobile pass** — spacing, tap targets, empty states; consider card reflow for Latest Round / Records. Pickup pointer: `MOBILE_PLAN.md` → Status.
- [ ] **Dark mode: page-title contrast on dark** — `.page-title` nearly invisible in dark mode (pre-existing, seen during M2 verification; part of the deferred dark QA sweep).
- [ ] **Records table horizontal overflow on narrow screens** — long location strings (e.g. `TEG 8 (Lisbon Coast, Portugal, 2015)`) push the `/records` tables past the panel/viewport at narrow widths, causing horizontal scroll. Pre-existing (unrelated to the page-gutter fix). Apply the mobile table approach — sticky-column / horizontal-scroll container or name-shortening — per `design_principles.md` → Tables.

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
