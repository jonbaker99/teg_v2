# P0 — public UI baseline

Captured 2026-09-20. Starting application/base commit: `aa7a208237fa901d4ea91e41674cfcc81560b2ce`. Worktree: `/Users/jon/projects/teg/worktrees/ui-p0`; branch: `codex/ui-p0`. The tree was clean at entry. The final response supplies this handoff's resulting commit SHA; use that SHA as F1's base.

P0 changes no application, data, or tests. It adds this handoff and the screenshot evidence permitted by the roadmap. Public analysis/navigation only; admin, setup, score input, live operations, data updates, and Gap remain excluded. No push, merge, or deployment. Lead retained design/evidence decisions; `gpt-5.6-luna` performed the read-only route/selector/test inventory. A fresh `gpt-6-astra` Medium review checked the handoff against source; its Contents test-coverage correction and reproduction wording suggestions were accepted. No lead-model change was needed or attempted.

## Baseline findings change how Fix should start

| Chat | Observed baseline and action for the next chat |
|---|---|
| F1 rank toggle | Confirmed on Latest Round and Latest TEG: `::after` is `none` at 768/1280px; `+` at 390px. Latest Round at 641px has a **0 × 0 button**. Programmatic click still changes `aria-expanded=true`; expanded glyph is also absent on desktop. F1 must restore a usable hit area as well as the glyph. |
| F1 dark title | Default `title_style=a` is readable (`rgb(236,236,234)`). The registered `e2` variant reproduces the defect: that pale text sits on a white `.page-title-outer` band. Screenshots cover Records, Latest Round, Scorecard, and Scoring Streaks at 390/1280px. Contents has its own title markup and no `.page-title`; include it as a regression check, not evidence of this exact selector defect. |
| F2 Records | **Not reproduced** in Clean Page: all five tabs fit 320/375/430px with every `details.rec-row` expanded. `scrollWidth == innerWidth` in all 15 states, including the Lisbon Coast location. The current phone renderer already uses a disclosure list. F2 should validate remaining layout/mode combinations and reconcile the TODO before proposing CSS. Do not infer a fix from old prose. |
| F3 Scoring/Streaks | Both have existing phone treatment and fit the sampled 390px five-player state. Scoring remains a dense pivot. Streaks has a 32% label column; the screenshot shows cramped adjacent AB/DM headings. Treat this as targeted readability/roster work, not an unstyled-tab implementation. |
| F4 Records/Scorecard | Latest Round already calls the shared Records builder. TEG 18 R4 has no records; TEG 17 R2 gives a populated worsts/PBs/score-count sample. Scorecard remains visibly narrow and centred on a phone; measure `.sc-portrait`/`.sc-scroll` and ancestors before assuming all whitespace is padding. Existing generic Latest Round rules already zero data-card side padding. |
| F5 navigation | Confirmed on `/scoring/all-rounds?n=100`: scroll to 900, then back to 650. `.nav` stays at `top:-49px` on phone and `-57px` on tablet/desktop; its bottom is 0. The phone bottom bar remains available. |

Additional baseline finding for the later UI backlog: Latest Round Scoreboard at 390px has document width 402px in both modes. `.lr-total-toggle` ends at x=402; the tab strip's offscreen buttons are separately contained. Preserve this evidence in F3/F6 triage; do not silently include a Scoreboard change in F1. This handoff is the only P0 documentation output, so existing TODOs remain untouched until their owning Fix chats reconcile them.

## Route, file, and test ownership

Paths below are relative to the repository root. All HTML names are under `webapp/templates/`; partial names are under its `partials/` directory. All rows inherit the shared shell assets described below. `W` means `tests/test_webapp_pages.py`; its `test_nav_page_renders` covers public routes listed in `webapp/nav.py`, but not browser layout or JavaScript behaviour.

| Route and server owner | Template / partial or shared renderer | Specific CSS/JS and tests |
|---|---|---|
| `/` — `webapp/app.py` | Redirect to `/contents`; no separate home template | Browser redirect check; Contents uses its own inline shell/title overrides |
| `/contents` — `routes/contents.py` | `contents.html` | Inline CSS, shared nav; browser coverage only (`/contents` is absent from W nav parametrization) |
| `/leaderboard`, `/leaderboard/table` — `routes/leaderboard.py` | `leaderboard.html`, `leaderboard_table.html`, shared `lb_cards.html`; standings helpers in `routes/history.py` | `.standings-page`, `.leaderboard-table`, `.chart-block`; W `standings`, `race_chart`, nav smoke |
| `/results`, `/results/table` — `routes/history.py` | `results.html`, `results_table.html`, `lb_cards.html` | Same standings/chart treatment; W `results`, `standings`, `race_chart` |
| `/latest-round`, `/latest-round/tab` — `routes/latest.py` | `latest_round.html`, `latest_round_tab.html`; `_build_scoreboard_table`, `_render_records_summary` | `.latest-round-page`, `#lr-content`, inline state/toggle JS; `scorecard.css`; W `latest_round` |
| `/latest-teg`, `/latest-teg/tab` — `routes/latest.py` | `latest_teg.html`, `latest_teg_tab.html`; same scoreboard/Records builders | `.latest-teg-page`, `#lt-content`, inline toggle JS; `scorecard.css`; W `latest_teg` |
| `/records`, `/records/tab/{tab_name}` — `routes/records.py` | `records.html`, `records_tab.html`; `_build_records_html` also imported by Latest Round/TEG | `.records-page`, `.records-table`, `.records-list`, `.rec-row`, `.data-card > .overflow-x-auto`; W nav smoke only |
| `/scorecard`, `/scorecard/content` — `routes/scorecard.py` | `scorecard.html`, `scorecard_content.html`; builders in `teg_analysis/display/scorecards.py` | `scorecard.css`, `.sc-landscape`, `.sc-portrait`, `.sc-scroll`; W nav smoke; `tests/test_scorecards_portrait.py` for builder contracts |
| `/player` — `routes/player.py` | `player_index.html` | Roster styling in theme CSS; W `player_index` |
| `/player/{code}`, `/player/{code}/tab/{tab_name}` — `routes/player.py` | `player.html`; `player_overview.html`, `player_rounds.html`, `player_scoring.html`, `player_records.html` | `player-profile.css/js`, `#player-profile`, `.pp-*`; W `player`, `rounds_chart` |
| `/teg-reports` — `routes/reports.py` | `teg_reports.html` | `teg_reports.css`, `newspaper_preview.css/js`; W `teg_reports`; report PDF checks only if newspaper CSS/report markdown changes |

`routes/` in the table means `webapp/routes/`. All scoring routes below belong to `webapp/routes/scoring.py`. Each inherits W nav smoke; these are coarse response checks, not dedicated scoring layout tests.

| Scoring page | Template / partial | Primary hook / additional behaviour |
|---|---|---|
| `/scoring/birdies` (+ `/tab`) | `scoring_birdies.html` / `scoring_birdies_tab.html` | `#sb-content` |
| `/scoring/streaks` (+ `/tab`) | `scoring_streaks.html` / `scoring_streaks_tab.html` | `#st-content`, `#st-controls` |
| `/scoring/by-par` (+ `/content`) | `scoring_by_par.html` / `scoring_matrix_content.html` | `#bp-content`; shared matrix partial |
| `/scoring/by-teg` | `scoring_by_teg.html` | `.scoring-byteg-page`, `.chart-block`, inline Plotly |
| `/scoring/by-course` (+ `/tab`) | `scoring_by_course.html` / `scoring_by_course_tab.html` | `#sc-content`, `.course-records-page` |
| `/scoring/all-rounds` (+ `/content`) | `scoring_all_rounds.html` / `scoring_all_rounds_content.html` | `#all-rounds`, mobile `.ar-list` |
| `/scoring/matrix` (+ `/content`) | `scoring_matrix.html` / `scoring_matrix_content.html` | `#sm-content`, wide layout |
| `/scoring/distributions` (+ `/content`) | `scoring_distributions.html` / `scoring_distributions_content.html` | `#distributions`, `.chart-block`, inline Plotly |
| `/scoring/changes` (+ `/content`) | `scoring_changes.html` / `scoring_changes_content.html` | `#changes`, mobile `.ch-list` |
| `/scoring/comebacks` (+ `/content`) | `scoring_comebacks.html` / `scoring_comebacks_content.html` | `#cb-content`, mobile `.cb-list` |
| `/scoring/heatmap` (+ `/content`) | `scoring_heatmap.html` / `scoring_heatmap_content.html` | `#hm-content`, `.hm-desktop`/`.hm-mobile`, wide layout |

The shared shell is `webapp/templates/base.html`: navigation, mode toggle, sticky-nav script, HTMX/Plotly lifecycle, and mobile chart treatment. CSS load order starts with `static/themes/base-vars.css`, registered layout CSS (importing `clean.css`), `teg_reports.css`, `themes/dark.css`, `mobile.css`, debug CSS, and `ui-polish.css`. `static/ui-polish.js` supplies shared disclosures/interaction handling. HTMX 2.0.4, Plotly 2.35.2, Tailwind Play CDN, fonts, and flag icons are external assets. Font/asset availability affects screenshot reproduction.

### Serialize writes to shared files

- `webapp/templates/base.html`, `webapp/static/mobile.css`, `webapp/static/themes/base-vars.css`, `clean.css`, `clean-page.css`, `clean-layered.css`, `dark.css`, and `webapp/static/ui-polish.css/js` affect many routes.
- `webapp/routes/latest.py` and its two latest-page templates/partials overlap F1/F3/F4. The rank glyph rules are at `mobile.css:847`; the 32% Streaks rule is at `mobile.css:666` on the starting base.
- `webapp/routes/records.py` owns `_build_records_html`; Latest Round/TEG reuse it through `_render_records_summary`. F2 must precede F4. Latest Round does **not** include `records_tab.html` directly.
- `webapp/static/scorecard.css` and `teg_analysis/display/scorecards.py` serve standalone and embedded cards. F4 is presentation-only and must preserve the standalone page.
- `webapp/routes/history.py`, `webapp/deps.py`, `partials/lb_cards.html`, and standings partials are shared between Results and Leaderboard. Avoid concurrent ownership during later standings work.
- One lead owns the task worktree and Git mutations. Investigations may run in parallel; shared CSS/template writes must follow `F1 → F2 → F3 → F4 → F5` integration order.

## Run locally without touching shared data

The successful local command was run from the task worktree:

```bash
cd /Users/jon/projects/teg/worktrees/ui-p0
/Users/jon/projects/teg/teg_v2/venv/bin/python -m uvicorn webapp.app:app --host 127.0.0.1 --port 8120
```

Port 8120 is task-specific. `_is_railway()` was false, and `_get_local_path` resolved to this worktree. All browser requests were public reads; no fixture data was written. Stop the task server when finished. The sandbox initially denied socket binding; the localhost-only escalation succeeded. Initial browser navigation before server startup failed with connection refused, then succeeded after startup.

Runtime caveat: the available project environment is Python **3.14.7 / pandas 2.3.3**, while `.python-version` pins 3.12 and requirements specify pandas 3.x. Screenshots establish this checkout's UI baseline, not deployment-runtime compatibility. System Python also lacked `python-multipart`; neither inspected interpreter had the Python Playwright package. The installed Playwright browser connector supplied Chromium **153.0.8010.50**, so no dependency installation or repository changes were needed. Future Python edits should use the pinned environment and required compatibility check.

Standard repo-supported setup/run commands remain `pip install -r requirements.txt`, `pip install -r requirements-dev.txt`, and `uvicorn webapp.app:app --reload`. For this worktree use the explicit interpreter above or an appropriately pinned environment, and keep the distinct port.

### Focused checks available to Fix chats

Run from the chosen task worktree with its interpreter. These existing selectors were inspected; **P0 did not execute pytest**, because it changes only documentation/evidence.

```bash
# F1: latest route/markup contracts; browser checks must cover glyphs and contrast.
python -m pytest tests/test_webapp_pages.py -k 'latest_round or latest_teg' -v
# F2: the existing Records page smoke case, not an overflow assertion.
python -m pytest 'tests/test_webapp_pages.py::test_nav_page_renders[/records]' -v
# F3: current latest-round tab rendering (scoreboard/scoring/eclectic/streaks).
python -m pytest tests/test_webapp_pages.py -k 'latest_round' -v
# F4: latest rendering and standalone portrait builder compatibility.
python -m pytest tests/test_webapp_pages.py -k 'latest_round or latest_teg' -v
python -m pytest tests/test_scorecards_portrait.py -v
# F5: public navigation shell smoke; scroll/menu/overlap need browser verification.
python -m pytest tests/test_webapp_pages.py -k 'nav_page_renders' -v
```

There is no existing dedicated glyph, dark-title, overflow, or sticky-nav browser test suite in this inventory. Latest Round's partial test does not cover Records/Scorecard tabs; exercise those explicitly in the browser. Do not mistake response smoke tests for visual acceptance. No application tests or full suite are warranted for P0 itself.

## Screenshot manifest and exact reproduction

All captures are under [screenshots/P0](screenshots/P0/), at application commit `aa7a208237fa901d4ea91e41674cfcc81560b2ce`. Tracked data is unchanged. Latest played state is **TEG 18, round 4, PGA Catalunya – Stadium, 14 October 2025**, five players. All available played TEGs have four to six players; no real eight-player baseline exists here. Later variable-roster acceptance needs an explicitly controlled test fixture, not a fabricated claim about these captures.

Unless a row says otherwise: viewport height 844 CSS px; width from filename; Chromium desktop context resized to the viewport (not real mobile emulation); Clean Page; `title_style=a`, default card-header/font settings; mode from filename; scroll at top; JPG quality 75, viewport screenshot. Clear cookies/local storage before reproducing, set `theme=clean-page` (or `theme=clean-layered` for Layered), `mode=light|dark`, and any stated `title_style` cookies at `/`, then navigate. Wait for page load, `document.fonts.ready`, and layout settling (250ms for the primary matrix; 150ms after each navigation scroll; 300ms after Records HTMX switches). The browser context reported `devicePixelRatio=1`; Lora, Inter, and Material Symbols font checks passed. These are CSS-viewport references, not physical-device captures.

| Filename pattern | Count | Route/state and action |
|---|---:|---|
| `round-{390,768,1280}-{light,dark}.jpg` | 6 | `/latest-round?teg=18&round=4&tab=scoreboard`; page canonicalizes with `metric=Sc&rewind=18`; detail rows closed |
| `teg-{390,768,1280}-{light,dark}.jpg` | 6 | `/latest-teg`, current TEG 18 Aggregate tab; detail rows closed |
| `records-{390,768,1280}-{light,dark}.jpg` | 6 | `/records`, default TEG records tab, disclosures closed |
| `scoring-{390,768,1280}-{light,dark}.jpg` | 6 | `/latest-round?teg=18&round=4&tab=scoring`, Gross vs Par / Count |
| `streaks-{390,768,1280}-{light,dark}.jpg` | 6 | `/latest-round?teg=18&round=4&tab=streaks` |
| `round-records-{390,768,1280}-{light,dark}.jpg` | 6 | `/latest-round?teg=18&round=4&tab=records`, genuine empty state |
| `round-scorecard-{390,768,1280}-{light,dark}.jpg` | 6 | `/latest-round?teg=18&round=4&tab=scorecard`, Gross |
| `populated-records-{390,768,1280}-{light,dark}.jpg` | 6 | `/latest-round?teg=17&round=2&tab=records`, West Cliffs, 6 October 2024; full-page captures |
| `nav-up-{390,768,1280}-{light,dark}.jpg` | 6 | `/scoring/all-rounds?n=100`; `scrollTo(0,900)`, settle, `scrollTo(0,650)`, settle; captures at y=650 |
| `title-e2-{contents,round,records,scorecard,streaks}-{390,1280}-dark.jpg` | 10 | Cookie `title_style=e2`; `/contents`, `/latest-round?teg=18&round=4`, `/records`, `/scorecard?teg=18&round=4`, `/scoring/streaks`, respectively |
| `records-expanded-{320,375,430}-light.jpg` | 3 | `/records`, TEG tab, open every `details.rec-row`; full-page captures include long Lisbon Coast location |
| `layered-rank-expanded-{390,1280}-{light,dark}.jpg` | 4 | Clean Layered cookie; `/latest-round?teg=18&round=4`; programmatically click first `.rank-toggle` (desktop hit area is zero), verify `aria-expanded=true` |
| `rank-641-light.jpg` | 1 | `/latest-round?teg=18&round=4`, Clean Page, collapsed, boundary-width evidence |

**Total: 72 screenshots.** The first 42 are the seven-state × three-width × two-mode Fix baseline. Other captures isolate defects or protect against false diagnoses. They are not a completed all-public-route regression matrix.

### Checklist for subsequent visual acceptance

- [x] Capture Fix states at 390×844, 768×844, and 1280×844 in light and dark, using the manifest above.
- [x] Capture missing glyphs, a failing dark-title variant, the four targeted Latest Round tabs, expanded long-location Records, and navigation after upward scrolling.
- [x] Sample Clean Layered rank expansion at phone/desktop; default Clean Page covers the full Fix capture matrix.
- [ ] For every mapped public page, run all three widths × both modes × **both** registered layouts. Include `/` redirect, Contents, Leaderboard, Results, both Latest pages, Records, Scorecard, roster/profile, Reports, and all eleven scoring pages.
- [ ] Exercise each route's tabs/filters, HTMX swaps, Back/reload, empty states, long labels, and chart readiness. Scorecard: Gross/Stableford and standalone/embedded. Records: all five tabs with disclosures open. Latest Round: populated and empty Records, Scoring count/%, Scoreboard collapsed/expanded.
- [ ] Add Fix-specific 320/375/430px checks and F1's 641px boundary, then controlled variable-player fixtures. Preserve tablet/desktop references.
- [ ] Measure page versus contained overflow, title foreground/background, button rectangles, navigation overlap and focus/ARIA. Record console/network errors. A screenshot alone is not a passing interaction check.

## Documentation claims later chats must reconcile

| Source claim | Evidence on this base / owning follow-up |
|---|---|
| TODO M2.7 / MOBILE_PLAN hero cards replace phone tables | `mobile.css` later standings rules show `.standings-page .leaderboard-table` and hide `.lb-cards`; do not restore cards while fixing unrelated defects. Reconcile during C/I standings work. |
| TODO Scoring/Streaks/Records are unstyled on phones | Generic latest table rules, specific Streaks width/initials, and shared Records disclosure rendering already exist. F3/F4 should update these entries precisely. |
| TODO Scorecard has no Latest Round mobile treatment | No dedicated Scorecard selector does not mean no treatment: generic latest `.data-card` padding/width rules apply. F4 must measure the actual inset source. |
| TODO Records overflow is confirmed | Current expanded five-tab Clean Page measurements did not reproduce it. F2 owns validation in remaining states and close/reword decision. |
| TODO page title is generally near-invisible | Default `a` is readable in sampled states; `e2` fails. F1 should name the failing variant rather than globally changing typography. |
| MOBILE_PLAN all CSS is inert above 640px / desktop unchanged by construction | Base display hooks and shared `.lr-readout` styles in `base-vars.css` exist; byte-identical desktop output cannot follow from the filename or old plan alone. Check rendered output per change. |
| MOBILE_PLAN R4.3 awaits integration; TODO progression/scoring chart slices are undone | Current `scoring_by_teg.html`, distribution partial, `base.html` mobile-chart treatment, and `player-profile.js` already contain those behaviours. Reconcile state during C/T review. |
| MOBILE_PLAN bottom-nav examples / open direction and dark-mode questions | `nav.py` supplies History, Latest, Records, Scoring, Cards. Manual mode cookie works at every width. Current roadmap supersedes the old immediate native-app direction; Editorial Golf is a later experiment. |
| README says results chart is a placeholder and structural hooks are no-ops | Current Results chart markup renders Plotly; base-vars gives section controls/navigation explicit spacing. Old look-and-feel roadmap prose is stale. Reconcile in documentation work, not by recreating old implementation. |
| Design principles specify fit-content page width and always-light nav | Current base-vars sets 100%/960px content wrappers (wide opt-in 1280px); dark mode explicitly darkens nav. These instructions contradict current source and should be updated, preserving the current Clean-family contract. |
| README says theme picker is in nav | `base.html` comments out the picker; both registered layouts remain reachable through the `theme` cookie. Do not look for a visible picker in baseline reproduction. |

Chart dark-mode statements require care: the route code still uses chart style helpers without consistently passing the mode. Existing mobile chart treatment is not proof of complete chart dark parity. Do not close that claim merely because the page shell is dark.

## Validation and handoff limits

Verified worktree/branch/base and clean starting status; inspected current route/template/selector/test sources; rendered all 42 primary captures with HTTP 200 and no `Error:` body marker; measured the 15 narrow expanded Records states; measured rank glyphs/ARIA, `e2` colour pairing, and nav scroll coordinates. The lead visually inspected representative Scoring, Streaks, embedded Scorecard, populated Records, dark-title failure, and hidden-nav captures. Remaining captures are reference artifacts, not individually certified visual passes.

Browser console showed Tailwind's production-CDN warning; initial load also requested a missing favicon. Later sampled pages reported zero console errors. No claim of exhaustive console/network QA or real-device Safari/Android testing. Artifact checks confirmed 72 decodable JPEGs (2,946,062 bytes), valid local Markdown links, and the recorded route endpoints. No data mutation, application edits, compatibility test, or pytest execution. Missing `focus-style` skill was not found in the available local skill roots; this handoff uses concise repository documentation conventions.

Unresolved: F2's old overflow claim needs remaining-state confirmation; F3/F4 need targeted design/measurement, eight-player fixtures are absent, runtime differs from deployment pins, and the Scoreboard's 12px overflow needs later triage. P0 establishes evidence, not Fix acceptance. Proceed to F1 from the exact resulting P0 commit supplied in the final response; keep its two-defect scope and include this handoff's `e2`/zero-hit-area findings.
