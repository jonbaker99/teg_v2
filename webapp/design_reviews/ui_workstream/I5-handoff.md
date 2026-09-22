# I5 — Implement Contents as the current-TEG home

Captured 2026-09-21. Worktree: `/Users/jon/projects/teg/worktrees/ui-i5`; branch: `claude/ui-i5`.
Base: `6218c0caf0ec5088bdbadcd0b39ae70154cc1e9e` (main tip, I1+I2 merged). Not merged, pushed or
deployed.

**Starting model:** Astra Medium's Claude-equivalent (Sonnet 5). No higher-reasoning lead was
needed: I3/I4 had already resolved the design judgement calls, and the three remaining owner
decisions (below) were taken live via `AskUserQuestion` before implementation started, leaving a
bounded, fully-specified route+template task. No model switch requested or made.

## Owner decisions taken before implementation

I3-handoff.md's "Unresolved" section left three product decisions open. Resolved directly with the
owner (not guessed):

1. **State 2 primary action.** Owner chose **Report primary** (overriding I4 R7's Results-primary
   recommendation): "Read the TEG N Report" is the solid primary action when `has_edition(n)` is
   true, with Full Results as an outlined secondary. When no report exists yet, Full Results is the
   sole primary — never a dead report link (E7 unchanged).
2. **Cold-load fallback (I4 R10).** Owner chose **yes** — State 1's leader rows defer to an HTMX
   partial (`GET /contents/leaders?teg=N`, `hx-trigger="load"`) whenever the render would otherwise
   pay for a cold `cached_round_data()` load. The budget is operationalised as "any cold cache miss
   defers" (`cached_round_data.cache_info().currsize == 0`) rather than a wall-clock timer, since a
   synchronous timeout can't cleanly interrupt a pandas load already in flight; this is the honest
   proxy for "would this request pay the cold-load cost."
3. **Wooden spoon in State 1.** Owner chose **keep it** (D3/I4 precedent from `history.py`).

## What changed

- **`webapp/deps.py`** — new `get_tournament_state()` (single source of truth for the three states,
  reading only the two small status CSVs to *choose* the state), `get_contents_state1_leaders()`
  (the one State-1 helper that touches `cached_round_data()`), `_leader_rows()` (ties named in
  full, no countback), `_format_date_dmy()` (local copy of `scorecard.py`'s date formatter — kept
  local since `deps.py` must not import route modules).
- **`webapp/routes/contents.py`** — `/contents` now builds `get_tournament_state()` and passes the
  unmodified `NAV_SECTIONS` (no more custom three-column regrouping); new `GET /contents/leaders`
  partial route for the cold-cache HTMX fallback.
- **`webapp/templates/contents.html`** — full rewrite: state panel (three states) + five
  bounded-surface `NAV_SECTIONS` groups below a hairline. Dropped all three `!important`s and the
  `min(95vw, 1600px)` width override (I4's surface-treatment ruling); no `.data-card` on the state
  panel (it's an announcement, not data output).
- **`webapp/templates/partials/_contents_state1_leaders.html`** (new) — shared leader-rows partial,
  used both inline (warm cache) and as the HTMX fallback response (cold cache), via a `leaders`
  mapping so both call sites share one template.
- **`tests/test_webapp_pages.py`** — 9 new focused tests (`-k contents`): all-28-links, one test per
  state (in-progress, in-progress-cold-defer, complete, complete-no-report, no-data), ties, the
  no-parquet-load acceptance criterion, and the "panel adds zero new destinations" criterion.
- **`webapp/design_principles.md`** — line 29 (accent-colour rule) and its checklist line rewritten
  to record green's actual jobs on the shipped site (honours, live status, active selection incl.
  `.section-title`'s existing green, top-rank emphasis) and the rule that only one applies per
  render, plus the `--focus` carve-out for the three foundation controls (I4 R4/R5, corrected
  citation and widened scope).
- **`webapp/TODOS.md`**, **`STATUS.md`** — Contents redesign TODO closed; STATUS dated 2026-09-21.

## Acceptance criteria (I3-handoff.md §6) — status

All 19 met. Highlights:
- **AC2/AC5/AC11** (all 28 links present, no new destination, `/player` unlinked) — asserted by
  test, not inspection (`test_contents_all_nav_links_present`,
  `test_contents_panel_actions_are_all_in_the_sitemap`).
- **AC3** (State 2 costs no parquet load) — `test_contents_complete_state_costs_no_parquet_load`
  asserts `cached_round_data.cache_info().misses` is unchanged across a `/contents` request.
- **AC6** (every panel action pins the current TEG) — `/leaderboard?teg={n}`, `/results?teg={n}`,
  `/teg-reports?teg={n}` throughout; verified by the per-state tests.
- **AC19** (named cold-load budget) — see decision 2 above.
- **AC13** (ties named in full) — `test_contents_ties_name_every_player`; live-browser end-to-end
  check confirmed real htmx swaps the loading skeleton for real leader data (see Verification).

## Verification

**Automated:**
- `python -m pytest tests/test_webapp_pages.py -q` — 112 passed (9 new).
- `python -m pytest tests/test_imports.py tests/test_no_streamlit_imports.py -q` — 30 passed, 4
  skipped (no frontend imports in `teg_analysis/`, no `streamlit/` touched).
- `python scripts/check_pandas_compat.py` — 0 errors (26 pre-existing warnings elsewhere,
  unrelated to this change).
- `python scripts/check_python_compat.py` — clean under the pinned 3.12 interpreter.
- Run under `/private/tmp/teg-i2-browser-venv` (a prior session's venv with the full dep set
  installed) rather than bare system Python — this worktree has no local venv of its own; note for
  whoever picks this up next.

**Browser (Playwright, isolated headless instance — did not touch the other active session's
shared browser profile):**
- All three states rendered via a live `uvicorn` server (`webapp.app:app`) and cookie-driven
  theme/mode switching (`webapp/theme.py`'s `theme`/`mode` cookies: `clean-page`/`clean-layered` ×
  `light`/`dark`).
- **12-combination matrix** (both Clean layouts × both modes × 390/768/1280px): zero horizontal
  overflow in every combination; state headline and all 5 sitemap groups render correctly.
- **320px and 430px**: zero overflow (full 320/390/430/768/1280 sweep per acceptance criterion 9).
- **Touch targets** (AC10, E10): sitemap links and state-panel buttons measured 44px tall at
  390px — the pre-existing sub-44px defect (`.contents-links a` was `padding: .35rem 0` on
  `0.875rem` text, ≈25px) is fixed.
- **Screenshots**: `/tmp/contents_390_light.png` (State 2, phone, Clean Page, light — not
  committed, local only), `/tmp/contents_1280_dark_layered.png` (State 2, desktop, Clean Layered,
  dark). Both read as an immediate three-second read: headline, who-won-what, one clear primary
  action, full sitemap below.
- **State 1 (in-progress) and State 3 (no-data)**: verified via `starlette.testclient.TestClient`
  against the real Jinja templates (monkeypatching `get_current_in_progress_teg_fast`/
  `get_last_completed_teg_fast`, since no TEG is actually in progress in the current data — TEG 18
  is complete, TEG 19 is only in `future_tegs.csv`). Not captured as live-browser screenshots for
  that reason; the CSS is shared with the browser-verified State 2 shell, and the shared-shell
  overflow/touch-target checks above cover the same layout code paths.
- **Cold-cache HTMX fallback, end-to-end**: temporarily patched the route (reverted before
  committing — confirmed clean via `grep TEMP-VERIFY` and a full re-run of the test suite
  afterward) to force State 1 + `leaders_deferred=True`, loaded the page in a real headless
  Chromium, and confirmed htmx actually fires `hx-trigger="load"`, fetches
  `/contents/leaders?teg=18`, and swaps the "Loading…" skeleton for the real Alex
  BAKER/Gregg WILLIAMS/Jon BAKER leader rows via `outerHTML` — not just that the route returns
  correct HTML in isolation.
- **Reload / direct navigation**: `/contents` is a plain `GET` with no client-side state to lose;
  every check above was a fresh navigation, which is the whole of this page's "reload" contract.

**Not run:** no PDF build check (`newspaper_preview.css` untouched); no live-round/admin checks
(out of scope, untouched).

## Deviations from the roadmap's process note

- **No worker delegation.** The roadmap allows a lower-cost worker to own the route/data slice or
  template/CSS slice. Given the tight cross-referencing between the state-detection contract, the
  template's field names, and the shared leader-rows partial (a bug from a route/template mismatch
  was caught and fixed mid-session — see below), splitting ownership here would have cost more in
  coordination than it saved. Implemented directly by the lead.
- **One bug caught and fixed in-session:** the first draft of the inline (warm-cache) leader
  include passed the Jinja include the ambient `state` dict via `with context`, but the partial
  read bare `net_leaders`/`gross_leaders`/etc. — a scope mismatch that silently rendered empty
  names. Caught immediately by a TestClient smoke check (not by review), fixed by refactoring the
  partial to take a single `leaders` mapping used consistently by both call sites, and re-verified.

## Revision (2026-09-22) — owner review: "too thin"

The owner reviewed the shipped page (screenshots sent) and said it didn't land: the in-progress
and complete states showed only leader *names*, no real standings, and no report content beyond a
bare button. Separately, Codex had independently written its own I3-equivalent plan on
`codex/contents-home-proposals` (branched `2026-09-20`, one day before Claude's I3, never
reconciled, never merged) proposing a two-column layout with a real standings table and a featured
report teaser. Comparing the two proposals (full comparison table in the session transcript)
surfaced ideas worth adopting selectively, plus one real bug Codex found — `finalize_live_round()`
doesn't require every rostered player to be present before committing a round, so the status
file's round count can overstate completion — which the owner confirmed doesn't apply to their
actual workflow (rounds are always entered for all players at once), so it's logged as a TODO only
(see `webapp/TODOS.md`), not fixed here.

**Design process.** Rather than iterate blind, an interactive HTML prototype
(`https://claude.ai/artifact/UD49p88BHCfBTTNH4GRstz`) was built and published, showing the
in-progress panel's two-column-vs-stacked layout at three widths and both themes with real-looking
content. The owner reviewed it live and iterated it three times in conversation before approving:
(1) two-column confirmed for in-progress; (2) the complete state redesigned entirely — instead of a
boxed report teaser sitting beside a "Final Results" headline, the report's own headline **becomes
the page's h1** (linked to the report), with a `TEG N results | Area | Month Year` dateline
replacing the old muted eyebrow; (3) an encoding bug in the prototype itself (em dash/middot/arrow
rendering as mojibake, from HTML entities being set via `element.textContent` instead of
`innerHTML`) was found and fixed before final approval — confirmed as an artifact-pipeline-only
issue, not present in the real webapp's UTF-8 `HTMLResponse`.

**What changed from the original I5 plan:**
- **In-progress**: the leader-names-only block is replaced by a real net-competition standings
  table (every player, `Rank`/`Player`/`Total`, ties as genuine duplicate rows — ties no longer
  need the old comma-joined-names/`"and 1 other"` logic, since a real table shows them naturally)
  plus a compact gross-competition summary line, laid out two-column (≥900px, stacking below) next
  to a round-report teaser (kicker/headline/standfirst/link) when one exists. Reuses I1's
  `_standings_rows()` + `partials/_standings_table.html` directly rather than building a second
  renderer — feeding it a `create_leaderboard()` frame with the round columns already dropped
  (not just the top-level `round_labels` key blanked after the fact — that doesn't affect each
  row's own `rounds` list, a real bug caught and fixed this session, see below).
- **Complete**: when a tournament report exists, its headline/standfirst/link now lead the page
  directly; winners (unchanged: Trophy/Jacket green, spoon ink) and a single `Full Results`
  secondary action follow below. Falls back to the original "TEG N — Final Results" treatment,
  unchanged, when no report exists — never invents a headline.
- **Cost model simplified**: the old "defer leader rows only if `cached_round_data()` happens to be
  cold" branching (I4 R10's literal reading) is gone. In-progress rich content now *always* defers
  to `GET /contents/panel` — simpler, and honest regardless of process warmth. The complete state's
  report resolution moved from "would have been deferred" to **synchronous**, because its headline
  text now determines the page's own h1; deferring it would mean a visible flash from the fallback
  headline to the real one, which the site's I2 public-interaction contract exists to prevent.
  `get_edition_summary()` — new, `teg_analysis/reporting/newspaper_edition.py`, `@lru_cache`,
  wrapping `build_edition()` (not itself cached, can hit GitHub on a cold Railway volume read) — is
  the entire reason this stays cheap: full cost once per process, free after. It was placed in
  `teg_analysis`, not `webapp/routes/contents.py` as first sketched, specifically so
  `webapp/deps.py`'s `get_tournament_state()` could call it directly without `deps.py` importing a
  route module (an established rule — see `_format_date_dmy`'s docstring).

**Bugs caught and fixed this session, all via smoke-testing before commit, none by review:**
1. Blanking `standings["round_labels"] = []` after calling `_standings_rows()` left every row's own
   per-row `rounds` list (built earlier, from the DataFrame's actual columns) still populated — the
   table partial's `<tbody>` loop reads that per-row list, not the top-level key, so round columns
   kept rendering despite the header row correctly losing them. Fixed by dropping the round columns
   from the DataFrame *before* calling `_standings_rows()`, so both are naturally empty together.
2. `get_contents_standings()`-equivalent logic was first drafted inside `webapp/deps.py`, requiring
   a local (function-body) import of `webapp.routes.history` to reach `_standings_rows()` — technically
   safe (breaks the import cycle the same way `_results_context()`'s own local imports do) but a
   needless deviation from the approved plan, which placed this logic in `webapp/routes/contents.py`
   (a route file, free to import from another route file at module level, matching
   `webapp/routes/leaderboard.py`'s existing import of `_results_context` from `history.py`). Moved
   before commit.
3. The two-column CSS grid rendered a dead empty second column when no round report existed for the
   in-progress state (a single grid child still only fills the first track). Fixed: the `two-col`
   modifier class is now applied conditionally on `panel.report_summary` being present, so the
   standings surface takes the full row width when there's nothing to put beside it.

**Verification (this revision):**
- `python -m pytest tests/ -v` — 766 passed, 23 skipped, 0 failed (the full suite, correcting the
  original I5 session's under-scoped focused-subset run — `webapp/deps.py` and
  `teg_analysis/reporting/newspaper_edition.py` are both shared/core modules per CLAUDE.md's
  Definition of Done).
- `check_pandas_compat.py` — 0 errors; `check_python_compat.py` — clean under pinned 3.12.
- Browser matrix: 320/390/430/768/900/1280px × both Clean layouts × light/dark = 24 combinations,
  zero horizontal overflow in every one, via an isolated headless Playwright instance (did not
  touch another active session's shared browser profile).
- Real-data verification against the live dataset throughout, not just stubs: TEG 18's actual
  report ("Alex Baker Wins It in Round One") rendered correctly as the complete-state h1 with no
  extra setup; a temporarily-forced in-progress override against TEG 18's real round data produced
  a correct 5-row standings table, gross-competition line, and round-report teaser, screenshotted
  at 1280px and 390px, then reverted before commit (confirmed via `grep TEMP-VERIFY` + a full
  `test_webapp_pages.py` re-run).
- The complete-state **no-report fallback** could not be exercised against real data this
  session — every TEG in `data/completed_tegs.csv` (2 through 18) now has a generated report, so
  there's no real gap to render against. Covered by
  `test_contents_state_complete_no_report_falls_back_to_results_primary` (stubbed) instead; the
  code path is real and tested, just not currently reachable via live data.

**Docs updated:** this file; `STATUS.md`; `webapp/TODOS.md` (Contents entry + a new partial-roster
finalization TODO, scoped out of this chat per the owner's explicit call).

Handoff: this worktree's next commit SHA (see final response) supersedes `93c6a12` as I5's result.
Still not merged, pushed, or deployed.

## Handoff

Base `6218c0caf0ec5088bdbadcd0b39ae70154cc1e9e`. This worktree's HEAD commit (see final response for
SHA) becomes I6's base. Not merged, pushed, or deployed — owner decision per workflow rules.
