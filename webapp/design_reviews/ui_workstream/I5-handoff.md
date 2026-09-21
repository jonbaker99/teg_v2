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

## Handoff

Base `6218c0caf0ec5088bdbadcd0b39ae70154cc1e9e`. This worktree's HEAD commit (see final response for
SHA) becomes I6's base. Not merged, pushed, or deployed — owner decision per workflow rules.
