# I1 — Unify the public standings renderer

Captured 2026-09-20. Worktree: `/Users/jon/projects/teg/worktrees/ui-i1`; branch: `claude/ui-i1`.
Base: `bb3f8df5c5166b45ad4962149201c4f77d5b17ca` (main tip — C6/C6a's accepted integration base).
Not merged, pushed or deployed.

## Scope

`webapp/design_reviews/ui-implementation-roadmap.md` → I1: replace the public leaderboard/results
duplicate active/stale standings paths with one semantic responsive renderer. Preserve analytical
values, route contracts, the race chart, ties, links, empty states and Gross/Net behaviour. No Gap
column. Public standings only — no admin, live-round or `teg_analysis/`/`streamlit/` changes.

## What was actually there (read-only inventory before any edit)

Two parallel Explore agents mapped the full route/template/CSS/test surface before implementation
started. Key finding: `/leaderboard` and `/results` already shared one context builder
(`_results_context`, `webapp/routes/history.py`), but rendered it through **three** overlapping
paths:

1. A Python HTML-string table (`_leaderboard_table_html`).
2. A Jinja card list (`partials/lb_cards.html`'s `.lb-cards`/`.lb-card`), fed by a second,
   independently-built context key (`lb_cards`).
3. Two near-duplicate page partials (`leaderboard_table.html`/`results_table.html`), differing
   only in id prefix, the `active_lb_tab`/`active_tab` key name, and the HTMX URL.

Path 2 was confirmed **dead at every viewport** by CSS specificity: `.lb-cards` is
`display:none` at base, turned on at ≤640px, then turned back off by
`.standings-page .lb-cards { display:none }`, which always wins on the two pages that include it.
It has been dead since R3.2 shipped; `C4-handoff.md`'s audit table incorrectly recorded it as the
live "Tier 2 card reflow," a discrepancy now noted in `TODOS.md` rather than edited into that
historical handoff.

Path 3 is where the pages had drifted: `results_table.html` had an `{% elif raw_table %}` branch
for its Scorecards tab that `leaderboard_table.html` lacked, so `/leaderboard`'s Scorecards tab
was double-wrapping already-complete scorecard HTML in an extra `.data-card > .table-wrapper` —
the same defect class F4 fixed on Latest Round.

## Decisions taken with the owner before implementation

| Decision | Choice | Why |
|---|---|---|
| Compact-round breakpoint | ≤640px only | The site has exactly one breakpoint (`mobile.css` is a single `max-width: 640px` block). At 768px the widest real table (6 players × 4 rounds = 7 columns) fits with no overflow — confirmed live. This is a deliberate deviation from the roadmap's "phone and tablet" wording. |
| Page partials | Collapse into one shared `_standings_page.html` behind two thin `ns`-prefixed wrappers | Removes the real drift source (item 3 above) while keeping every route, id and swap target byte-identical. |
| Player links | Keep `link_players=False` as the shipped default | Profiles have been off since 2026-09-18 ("not ready to be live"); the flag stays fully wired and tested, not silently flipped on by this refactor. |

## What changed

- **`webapp/routes/history.py`** — added `_split_player_name` (unescaped forename/surname split,
  used by the new renderer only) and `_standings_rows(df, link_players)`, which builds
  `{round_labels, rows: [{rank, player, first, last, code, rounds, total, lead}]}` from the same
  formatted `lb` DataFrame the old table/card builders both consumed. `_results_context` now
  returns a single `standings` key instead of `table_html` + `lb_cards`. `_leaderboard_table_html`
  deleted (`table_html` stays on the scorecards/error branches, which are genuinely pre-rendered
  HTML from a different builder).
- **`webapp/templates/partials/_standings_table.html`** (new) — the unified table. Each `<tr>`
  emits its round values twice: `<td class="col-round">` cells for desktop, a `.standings-rounds`
  strip inside the player cell for phones. Keeps `teg-table leaderboard-table` (load-bearing for
  `names-break`, the leader-tint specificity chain, and an existing test) and the
  `col-rank`/`col-player`/`col-num`/`total` classes CSS already targets.
- **`webapp/templates/partials/_standings_page.html`** (new) — the shared page body (measure
  toggle, section title, callout, hero, table, race chart, chart-type pills, scorecards/raw/empty
  branches), parameterised by `ns` (`'lb'`/`'results'`), `active_measure`, `full_page` and
  `route_base`. Fixed the Scorecards double-wrap here: the `raw_table` branch (previously
  `results_table.html`-only) now also carries `/leaderboard`'s `scorecards_full_link`, so both
  routes render scorecards unwrapped with `/leaderboard` additionally showing its "Open the full
  Scorecard page" link.
- **`leaderboard_table.html` / `results_table.html`** — reduced to 7-line wrappers that set the
  four `ns`-scoped variables and `{% include "partials/_standings_page.html" %}`.
- **`partials/lb_cards.html` → `partials/_standings_hero.html`** — kept only the `lb_hero` pods
  (still live on phones); deleted the dead `.lb-cards`/`.lb-card` markup.
- **`webapp/static/mobile.css`** — deleted `.lb-cards`/`.lb-card*` (base hook, the whole card
  block, and the `.standings-page` override). Added `.standings-page .leaderboard-table
  .col-round { display: none }` and `.standings-rounds` styling (phone strip: muted, small,
  tabular, bold values — reusing the deleted card's proven type values) inside the ≤640px block;
  rewrote the fixed column widths for Rank/Player/Total now that round columns collapse; made
  `.col-total` visually primary on phones (1.15em/700, accent colour on the leader row), matching
  the `.lr-total-cell` reference pattern. Fixed two stale comment references (`_leaderboard_table_html`
  → the unified table; a wrong line-number back-reference).
- **`webapp/static/themes/base-vars.css`** — added `.standings-rounds { display: none }` as the
  base (desktop) hide, so the strip is invisible and out of the accessibility tree above 640px.
  Fixed a stale `_leaderboard_table_html()` reference in the leader-tint comment. Leader-tint
  selector shapes themselves untouched.
- **`webapp/templates/font_lab.html` / `typography_lab.html`** — dev-only lab pages that reused
  `_results_context`'s `table_html`; switched to including `_standings_table.html` with the new
  `standings` key so they don't 500.
- **Docs** — `MOBILE_PLAN.md`'s M2.7 entry marked superseded with the dead-card finding;
  `TODOS.md`'s M2.7 line annotated, plus a new item noting `C4-handoff.md`'s incorrect audit row;
  `design_principles.md` → Tables gained a second mobile-table reference section describing the
  "one row, two renderings" pattern and the dead-card pitfall it replaces; `STATUS.md` updated.

## Verification

**Tests** — `tests/test_webapp_pages.py`: 83 passed (75 pre-existing + 8 new), run under a
project-local Python 3.12 venv (`.venv312`, not committed) matching `.python-version`. New tests:
round-count-varies (`col-round` header count for TEG 18 vs TEG 2), round-strip/cell value parity
per row, tied-rank unit test on `_standings_rows`, empty-frame unit test, card-markup-gone
regression guard across all four standings routes, `/leaderboard` vs `/results` byte-identical
table-output test, Gross-omits-spoon. Also ran `tests/test_imports.py` +
`tests/test_no_streamlit_imports.py` (30 passed, 4 skipped) and
`scripts/check_pandas_compat.py` (0 errors, pre-existing warnings only, none touching this diff)
and `scripts/check_python_compat.py` (98 files parse clean under the pinned 3.12).

**Browser** (local server, `.venv312`, port 8177) — `/results` and `/leaderboard`, Net/Gross/
Scorecards tabs, at 390/768/1280px, light/dark, both Clean Page and Clean Layered, across:

- **TEG 18** — 5 players, 4 rounds, Stableford era (the default/latest).
- **TEG 7** — 6 players, `NetVP` era (widest field and the other measure; **no eight-player TEG
  exists** — confirmed during C5/C6, re-confirmed here from the data).
- **TEG 2** — 3 rounds (fewest round columns).
- **TEG 14** — 4 players (smallest field).

Confirmed: no page-level horizontal overflow at any width (`scrollWidth === clientWidth`); round
columns hidden and the strip shown at ≤640px, exactly reversed at ≥641px (768px shows the full
desktop table, validating the breakpoint decision); leader-row tint visually distinct from hover
and correctly applied to a genuine tie (TEG 7's `2=` rows); `/leaderboard` and `/results` render
pixel-identical standings tables for the same TEG/tab (also asserted in tests); `/leaderboard`'s
Scorecards tab no longer double-wraps (verified via the real HTMX tab-click flow, matching
standalone `/scorecard`'s unwrapped section style); zero `.lb-card` DOM nodes; `names-break`
re-fires and the race-chart readout stays wired after an HTMX TEG swap. Screenshots committed:
`screenshots/I1/` (results/leaderboard, 390/768/1280px, light/dark, both layouts, plus the
Scorecards-tab fix).

## Unresolved / carried forward

- **History's desktop `+`/`−` disclosure affordance** — open since C1b (C3/C4/C6 all restated it);
  untouched here, out of scope for I1.
- **`.main-content` padding/radius**, **`bw-name-full`/`bw-name-short` site-wide rollout**, **bare
  `.teg-table tbody tr.top-rank` on Records/History** — all pre-existing open owner decisions from
  C6, untouched here.
- Nothing new found blocking. No regressions identified in the browser sweep or test run.

## Ready / not-ready verdict for I2/I6

**Ready.** The standings renderer is unified, the dead card path is gone, the one real drift bug
(Scorecards double-wrap) is fixed, and all four representative data shapes (widest field, fewest
rounds, smallest field, both measures/eras) verify clean across viewport, theme and layout. Next:
I2 (public interaction/URL state) or I3 (Contents product contract), per the roadmap's dependency
map — both list C6 as their prerequisite and I1 as recommended-but-not-blocking, so either may
proceed from this base once merged.
