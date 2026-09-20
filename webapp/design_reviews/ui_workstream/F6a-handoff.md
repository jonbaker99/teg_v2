# F6a — resolve F6 Fix-stage review gate blockers

Captured 2026-09-20. Starting base: `cfa36f3` (accepted F1–F5 integration base, `claude/ui-f5`). Worktree: `/Users/jon/projects/teg/worktrees/ui-f6a`; branch: `claude/ui-f6a`. The tree was clean at entry. This chat's final response supplies the resulting commit SHA.

F6 (the read-only Fix-stage review gate) returned two blockers and a set of non-blocking follow-ups. This chat is a small, bounded follow-up on the Fix integration branch to resolve exactly the two blockers, per the roadmap's instruction that "Codex resolves accepted findings in a small follow-up on the same Fix integration branch before C1 begins." No application code was touched — screenshots and three documentation files only.

Starting recommendation followed: Sonnet, mechanical evidence recapture plus two documentation edits, no design decisions, no application code. No stronger lead was needed; work proceeded without a model-change flag.

## B1 — F3's screenshot evidence was invalid

**Finding:** `f3-scoring-320-6p-after-light.png` was byte-identical to `f3-scoring-320-dark-6p-before.png` (both md5 `e2492eb19112faca6d0e03568c929c5e`), and both showed the unfixed "GrossVPAB" header collision. `F3-handoff.md:54` also named a dark after-capture (`f3-scoring-320-6p-after-dark.png`) that was never committed.

**Resolution:**
- Kept `f3-scoring-320-dark-6p-before.png` unchanged — verified as a genuine, correctly named before capture.
- Started a fresh local server from this worktree (`/Users/jon/projects/teg/worktrees/ui-f6a`) on port **8126**, a port not otherwise in use (confirmed via `lsof` before starting, and via a direct `curl` 200 response against the target route after starting) — deliberately avoiding the stale-server-on-the-same-port trap F3's own handoff records.
- Captured genuine post-fix replacements with Playwright Chromium at 320×844, default theme (Clean Page — `DEFAULT_THEME = "clean-page"`, `webapp/theme.py`) and default `title_style=a` (`DEFAULT_TITLE_STYLE = "a"`, same file; no cookie override needed since these are the application defaults), route `/latest-round?teg=10&round=1&tab=scoring` (the 6-player TEG 10 R1 fixture F3 used):
  - `f3-scoring-320-6p-after-light.png` (replaced the bogus file)
  - `f3-scoring-320-6p-after-dark.png` (new)
- Verified in-browser via `getBoundingClientRect()` before each capture: the pivot's `GrossVP` header text renders fully inside its own `th` box (width ≈43.6px, no overlap with the adjacent `AB` header) in both light and dark; `document.documentElement.scrollWidth <= clientWidth` (no page-level overflow) in both modes.
- md5 of all three F3 scoring PNGs are now distinct:
  - `f3-scoring-320-dark-6p-before.png` = `e2492eb19112faca6d0e03568c929c5e`
  - `f3-scoring-320-6p-after-light.png` = `d63465b7a0e3e984990a0d0972c77470`
  - `f3-scoring-320-6p-after-dark.png` = `84d55a91941bc48041b7ccb946454410`
- Corrected `F3-handoff.md`'s screenshot manifest (around lines 52–56) to list exactly the files that exist, and noted the recapture inline with a pointer back to this handoff.

**Acceptance met:** the Scoring pivot's index header renders "GrossVP" wrapped inside its own column, not bleeding into "AB"; all three F3 PNGs have distinct md5s.

## B2 — P0's Scoreboard overflow finding was missing from TODOS.md

**Finding:** P0 measured `/latest-round` Scoreboard at 390px reporting document width 402px in both light and dark, with `.lr-total-toggle` ending at x=402 — a 12px page-level overflow (`P0-handoff.md` line 18). P0 explicitly assigned it to "F3/F6 triage" and listed it unresolved, but it appeared nowhere in `webapp/TODOS.md`.

**Resolution:** added an open `[ ]` entry under `webapp/TODOS.md` → UI Changes, at the top of that section, carrying the exact measurement, citing `P0-handoff.md` as the source, noting P0 deliberately kept it out of F1–F5, and proposing **C4** (responsive/table contracts) as owner — a table/control-width contract issue, not a one-off visual defect. No attempt was made to fix the overflow itself, per instruction.

## Roadmap correction

`ui-implementation-roadmap.md`'s "Scope and fixed decisions" stated "Codex is the sole editor and integrator. Claude is an independent design critic at named gates, not a co-editor." This was already false: F3, F4, and F5 were authored on `claude/ui-*` branches by Claude acting as editor/integrator, not just reviewer. Corrected the line to state either CLI may lead an implementation chat as editor/integrator per the model table, and Claude additionally performs the named independent review gates (F6, C6, I6, T1) and critique chats (C2, I4, E2), which stay read-only.

## Files changed

| File | Change |
|---|---|
| `webapp/design_reviews/ui_workstream/screenshots/F3/f3-scoring-320-6p-after-light.png` | Replaced (was byte-identical to the before capture) |
| `webapp/design_reviews/ui_workstream/screenshots/F3/f3-scoring-320-6p-after-dark.png` | New |
| `webapp/design_reviews/ui_workstream/F3-handoff.md` | Screenshot manifest corrected (lines ~52–56) |
| `webapp/TODOS.md` | New open entry under UI Changes for the Scoreboard 402px overflow |
| `webapp/design_reviews/ui-implementation-roadmap.md` | "Scope and fixed decisions" editor/integrator line corrected |
| `webapp/design_reviews/ui_workstream/F6a-handoff.md` | This handoff (new) |

## Checks run

No application code was touched — screenshots and three documentation/markdown files only. Per `CLAUDE.md`'s blast-radius guidance ("Nothing for docs, comments, to-dos or `--help` text — running the command once is the test"), no automated test suite was run. The local server used to (re)capture screenshots was exercised directly via `curl` (200 on the target route) and via the Playwright DOM checks described above under B1; that is the applicable check for this chat's scope.

## Screenshots captured

- `f3-scoring-320-6p-after-light.png` — 320×844, Clean Page, `title_style=a`, light, `/latest-round?teg=10&round=1&tab=scoring`
- `f3-scoring-320-6p-after-dark.png` — same route/viewport/theme, dark

Both committed under `webapp/design_reviews/ui_workstream/screenshots/F3/` (reusing F3's existing directory, since these are corrected F3 evidence, not a new chat's evidence set).

## Remaining F6 non-blocking follow-ups — routing

Per the owner's routing decision, F6's remaining non-blocking follow-ups (beyond the two blockers resolved above) route as follows and are **not** actioned in this chat:

- **Items 2–4:** route to **C3/C5**.
- **Items 5, 7, 8:** route to a **later pass**.
- **Item 6** (bump `base-vars.css`/`dark.css`/`mobile.css` `?v=` cache-busters in `base.html`): route to **pre-deploy**.

## Unresolved / explicitly out of scope

- The Scoreboard 402px overflow itself (B2) is now tracked in `webapp/TODOS.md` but not fixed — that is C4's scope, not this chat's.
- F6's remaining non-blocking follow-ups (items 2–8 above) are recorded for routing only, per the owner's instruction; none were investigated or actioned here.
- No new automated overflow/collision-regression test was added — this chat made no application changes, so there was nothing to add tests for; the general test-coverage gap flagged by P0/F1/F2/F3 for this class of visual check remains open.

## C1 addendum — one CSS scoping fix

C1 found F6a's own `.rank-toggle` fix (F1, tracked in `webapp/TODOS.md`) had one unverified phone-side claim: "390px phone sizing/behaviour unchanged" was checked for `min-height` only. The desktop-scoped `.rank-toggle` rule F1 added to `base-vars.css` was left unscoped (unlike its sibling `table.leaderboard` desktop rule, which relies on `mobile.css`'s later-loaded, equal-specificity rules to override every property it sets). `mobile.css`'s phone `.rank-toggle` rule doesn't set `min-width`, so the desktop rule's `min-width: 28px` floor leaked into phone widths too, even though `min-height`/`padding`/`font-size` were correctly overridden there by cascade order.

**Fix:** wrapped the desktop `.rank-toggle` block (and its `::after` glyph rules) in `@media (min-width: 641px)` in `webapp/static/themes/base-vars.css`, matching the comment's own stated scope. No values changed; `mobile.css` untouched; the two rules were not consolidated (that's C3's job).

**Verified** (Playwright, `/latest-round`, both Clean layouts — `clean-page` and `clean-layered`):
- 390px: `.rank-toggle` computed `min-width: 0px` (no floor), `min-height: 44px`, `::after` content `"+"`.
- 641px: `.rank-toggle` 28×28px, `::after` content `"+"`, click flips `aria-expanded` false→true.

**Checks run:** `python -m pytest tests/test_webapp_pages.py -k 'latest_round or latest_teg' -v` — 17 passed, 0 failed.

Updated `webapp/TODOS.md`'s F1 `.rank-toggle` entry to correct the "390px ... unchanged" claim and record this fix.

## Handoff

This chat's resulting commit becomes C1's base. No push, merge, or deploy performed.
