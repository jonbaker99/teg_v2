# TEG 19 dry run 3: snag fixes plan

Temporary working doc. Delete it, or fold it into `TEG19_FIX_PLAN.md` as **Batch 6**, when the work merges.

Written 1 October 2026 from the third dry run (PR environment `teg_v2-pr-157`, branch `claude/focused-shannon-ft8e6r`). That branch is a test sandbox. **Never merge it, branch from it or cherry-pick from it.** It holds test data commits only. All fixes start from a fresh branch off `origin/main`.

**Deadline:** code freeze 8 October. TEG 19 runs 10 to 13 October.

## Snags fixed by this plan

| # | Snag | Fix in one line | Size |
|---|---|---|---|
| 23 | Score entry page has no way back to the site. | Add a slim site strip (brand + Leaderboard) to the entry and live-leaderboard pages. | S |
| 24 | Score entry page has no link to the admin review page. | Show "Review & finalise" in that strip when the admin cookie is valid. | XS |
| 25 | The "LIVE … Enter scores →" banner stays up after the round is finalised. | Banner becomes a state: live round → "Enter scores"; otherwise latest finalised round → "Round N results are in → Leaderboard". | M |
| 26 | Deleting rounds shows no step-by-step progress. | Run deletion as a background job with the same step checklist as finalise. | M/L |

Numbers continue `TEST_TOURNAMENT_ISSUES.md` (which ends at 22). Add these four rows there.

## Separate finding: production has a stale live round

`data/live_rounds.csv` on `main` (the production registry) has one row:

```
jyQz-lkfbVs,19,1,2026-09-29T19:32:12...,active
```

It is a leftover from 29 September. It is harmless while the public link switch is off (production has no `live_round_settings.csv`, so it is off). On the day it bites twice:

- Turning the public link on advertises this stale round on every page.
- **Go live** for TEG 19 Round 1 finds it, refuses a new round, and redirects to the stale token. Its staging file may hold old test scores.

In dry run 3 the PR environment inherited this row, and Round 1 was played on it.

**Action for Jon, not the agents:** before 10 October, cancel it on production (Admin → Live round → that row → Cancel round). It is a data write to `main`, so it is your call. Agents must not touch production data.

## Ground rules for every worker

- Read `CLAUDE.md` first. Key rules here: route handlers stay sync `def`; no frontend imports in `teg_analysis/`; never touch `streamlit/`; pipelines fail loudly; run only the tests your change could break.
- Player entry pages are phone-first and standalone. Test every UI change at 375px wide.
- Don't widen scope. Note any smell you find as a separate item in the hand-off.
- Each worker owns only the files listed for its snag. Ask the lead before editing anything else.

## Key context (verified on `main` at `bd58645`)

### Live round flow

- Registry: `data/live_rounds.csv` (`LIVE_ROUNDS_REGISTRY_CSV`). Columns `Token, TEGNum, Round, CreatedAt, Status`, plus `FinalizedAt, FailedSteps, DeletedAt` once used. Status is `active | finalized | cancelled | deleted`.
- Logic: `teg_analysis/analysis/live_round.py`. `list_live_rounds()` (line ~249), `get_public_entry_enabled()`, `get_public_live_rounds()` (line ~287, only `active` rows), `finalize_live_round()` (sets `finalized` + `FinalizedAt`), `mark_rounds_deleted()`.
- Public switch: `data/live_round_settings.csv`, row `PublicEntryLink,on|off`. Off when the file is missing.
- Player pages: `webapp/routes/live_round.py`. `GET /live-round/{token}` renders `live_round_entry.html`; `GET /live-round/{token}/leaderboard` renders `live_round_leaderboard.html`. No auth: the token is the access control.
- Admin pages: `webapp/routes/admin_live_round.py`. Review page is `GET /admin/live-round/{token}/review`. Finalise runs in the background via `webapp/finalize_jobs.py`.
- Admin auth: `webapp.admin_auth.is_authed(request) -> bool` (cookie check).

### Site-wide banner (snag 25)

- Middleware in `webapp/app.py` (~line 98) sets `request.state.public_live_rounds = deps.get_public_live_rounds_cached()` for every non-static page.
- `webapp/deps.py` (~line 180): 30-second TTL cache around `get_public_live_rounds()`. Never raises. `clear_public_live_rounds_cache()` is registered with `clear_all_data_caches()`, which finalise and delete both call.
- Markup: `webapp/templates/base.html` (~line 180), a `.live-entry-banner` per round. CSS: `webapp/static/ui-polish.css` (~line 69).
- Railway runs one process (see `finalize_jobs.BOOT_ID` comment), so the in-memory cache is process-wide.

### Standalone entry pages (snags 23, 24)

- `live_round_entry.html` deliberately does not extend `base.html`. It is a full-height flex layout (`html,body {height:100%; overflow:hidden}`): app bar, banners, totals bar, chips, toolbar, scrolling grid, fixed keypad. Every pixel of height matters on a phone.
- `live_round_leaderboard.html` is also standalone, with a sticky `.appbar` and an "Enter scores" back link.
- Both define their own CSS variables, including a dark-mode block. Reuse those tokens.

### Deletion (snag 26)

- Route: `POST /admin/delete-data/execute` in `webapp/routes/admin.py` (~line 406). Runs `execute_data_deletion()` synchronously (~40 s) and returns `partials/admin_delete_result.html`. The only feedback is an `htmx-indicator` line in `partials/admin_delete_preview.html`.
- Pipeline: `teg_analysis/analysis/data_update.py` `execute_data_deletion()` (~line 865) takes `_update_lock` non-blocking (raises `UpdateInProgressError`), then `_execute_data_deletion_locked()`: backups, filter and write all-scores and all-data, `update_teg_status_files`, then cache steps via `_run_cache_step` (streaks, commentary, bestball, winners, reports_archive, live_rounds_registry), one `batch_commit_to_github`, then `remove_store_files`.
- Progress plumbing already exists: `_notify(progress, key, state, error)`, `_run_step(progress, key, fn)`, and `_run_cache_step(..., progress=None)`. `DATA_UPDATE_STEPS` shows the `(key, label)` tuple convention.
- Pattern to copy: `webapp/finalize_jobs.py`. Status JSON in the store (`_store_path`), atomic write, `claim()` single-flight, `BOOT_ID` stale detection, `_progress_recorder`, `step_rows()`, `current_step()`. Templates: `partials/admin_live_round_finalize_progress.html` (polls every 2 s, `outerHTML` swap) and `partials/admin_live_round_finalize_steps.html` (checklist).
- Tests touching it: `tests/test_admin_routes.py` (~line 288-310), `tests/test_data_update.py` (~line 313-420), `tests/test_finalize_jobs.py` (pattern for the new job tests).

## Snags 23 and 24: site strip on the entry pages

**Owner:** worker A. **Files:** `webapp/routes/live_round.py`, `webapp/templates/live_round_entry.html`, `webapp/templates/live_round_leaderboard.html`, `tests/test_live_round_routes.py`.

### Decision: slim strip, not `base.html`

Jon asked for "just the title bar and nav bar". The literal route is to extend `base.html`. Don't. Its sticky nav slides off on scroll, and its phone tab bar is fixed to the bottom, where it would cover the keypad. The page's height budget can't absorb either.

Instead, add one slim strip above the existing app bar on both pages. It looks like the site's title bar and carries the few links a player needs:

- Left: "The El Golfo" brand, linking to `/` (same text as `base.html`'s `.nav-brand`).
- Right: "Leaderboard" → `/leaderboard?teg={{ teg_num }}` (the site's TEG leaderboard, not the live one; the live one is already in the toolbar).
- Right, admin only: "Review & finalise" → `/admin/live-round/{{ token }}/review`.

If Jon later wants the full nav dropdowns, that is a separate, bigger change.

### Steps

1. In both route handlers, add `ctx["is_admin"] = is_authed(request)` (import from `webapp.admin_auth`). Wrap it so a cookie-check failure can never break the page (default `False`).
2. Pass `teg_num` to the leaderboard template if it isn't already reachable (`board` has it; check).
3. Add the strip markup inside `{% else %}` (not on the error page, which should get just the brand link, so a dead link still has a way home).
4. CSS: one row, about 32-36 px high, `flex: 0 0 auto`, respecting `env(safe-area-inset-top)`. Move the safe-area padding from `.appbar` to the strip so the notch isn't padded twice. Use the page's existing tokens (`--bar`, `--bar-line`, `--accent-text`, `--font-data`) so dark mode works. Links are at least 32 px tall for tapping.
5. The admin link uses a distinct but quiet style (e.g. a small `admin_panel_settings` Material icon). No other admin controls on the player page.
6. Don't touch the score-entry JS, polling or keypad.

### Acceptance

- At 375 px wide the strip fits on one line with the admin link showing, and the grid still shows at least 9 holes without scrolling on a 667 px-tall screen (iPhone SE). Check before and after.
- Brand goes to `/`. Leaderboard goes to the right TEG.
- Admin link shows only with a valid admin cookie. A player without the cookie sees no trace of it.
- Light and dark mode both readable.

### Tests

Add to `tests/test_live_round_routes.py`: entry page and live leaderboard page contain the brand link; the review link appears with the admin cookie and not without it. Run that file only.

## Snag 25: banner follows the round's state

**Owner:** worker B. **Files:** `teg_analysis/analysis/live_round.py`, `webapp/deps.py`, `webapp/app.py`, `webapp/templates/base.html`, `webapp/static/ui-polish.css`, `tests/test_live_round.py`, `tests/test_live_round_routes.py` (banner tests only; coordinate with worker A, who also edits this file, by adding tests in a separate block at the end).

### Step 1: reproduce before fixing

The code should already hide the banner: finalise flips the row to `finalized`, then `run_finalize` calls `deps.clear_all_data_caches()`, which clears the banner cache. So first write a failing test, or prove there is no bug:

- With the public switch on and an active round, `GET /` shows the banner.
- Flip the row to `finalized` (call `finalize_live_round` on a scratch repo, or write the registry directly) and call `deps.clear_all_data_caches()`. `GET /` must no longer show "Enter scores".

If that passes, the likely explanations are: a page loaded before finalise and not reloaded (pages don't refresh the banner), or a look within the 30-second TTL window from a request that ran mid-finalise. Record which in the hand-off. The redesign below makes this moot either way. If it fails, fix the real cause first and say so.

### Step 2: new state function

In `teg_analysis/analysis/live_round.py`, add `get_public_round_banners() -> list[dict]`. Keep `get_public_live_rounds()` working (tests may call it). Rules:

- Switch off → `[]`.
- Any `active` rows → one banner per row: `{"kind": "live", "token", "teg_num", "round_num"}`. Same as today.
- No `active` rows → the most recent `finalized` row by `FinalizedAt` (fall back to `CreatedAt` if blank) → one banner: `{"kind": "results", "teg_num", "round_num"}`. Ignore `cancelled` and `deleted` rows.
- Hide the results banner if `FinalizedAt` is more than 7 days old, so a forgotten switch doesn't advertise an old round. Put the 7 in a named constant.
- No GitHub or heavy reads beyond what `list_live_rounds()` already does.

### Step 3: wire it through

- `webapp/deps.py`: point the TTL cache at the new function (rename the cache helpers to `..._round_banners_...` and update every caller: `app.py`, `admin_live_round.py` lines ~141, ~161, ~396). Keep it never-raising.
- `webapp/app.py`: set `request.state.public_round_banners`.
- `base.html`: render by kind.
  - live: unchanged text. "TEG 19 Round 1 is in play. Enter scores →".
  - results: label "Results" instead of "Live", text "TEG 19 Round 1 results are in.", link "Leaderboard →" to `/leaderboard?teg=19`.
- Don't show the results banner on `/leaderboard` itself (the user is already there). Check `request.url.path`.
- CSS: a results variant of `.live-entry-banner` (calmer colour than live; reuse existing tokens in `ui-polish.css`).

### Acceptance

- Active round → live banner on every public page.
- Finalise it → within one page load, the banner becomes "results"; it links to the right TEG's leaderboard.
- Go live for the next round → back to the live banner for that round; no results banner alongside it.
- Cancel or delete the round → no banner for it.
- Switch off → no banner at all.
- Results row older than 7 days → no banner.

### Tests

Unit tests for `get_public_round_banners()` covering each rule (`tests/test_live_round.py`). Route tests for both banner kinds and the leaderboard-page exception. Run those two files.

## Snag 26: deletion progress as a background job

**Owner:** worker C. **Files:** `teg_analysis/analysis/data_update.py` (deletion functions only), new `webapp/delete_jobs.py`, `webapp/routes/admin.py` (delete-data routes only), `webapp/templates/admin_delete_data.html`, `webapp/templates/partials/admin_delete_preview.html`, `webapp/templates/partials/admin_delete_result.html`, a new `partials/admin_delete_progress.html`, `partials/admin_live_round_finalize_steps.html` (only if generalising it, see step 4), `tests/test_data_update.py`, `tests/test_admin_routes.py`, new `tests/test_delete_jobs.py`.

### Will it break other processes?

No, if the rules below hold. Deletion keeps the same `_update_lock`, so it still can't overlap a data update or a finalise. It still makes exactly one commit. Only the waiting moves from the HTTP request to a background task, which is how finalise and reports already work.

The one new risk is a Railway redeploy mid-job. That was always fatal; the job now says so ("interrupted") instead of hanging the request. Make the interrupted message say: "The deletion was interrupted. Check the round is gone on the site, then retry if needed." Retrying is safe: volume writes land before the commit, so a retry finds 0 rows, regenerates the caches and commits.

### Steps

1. **Pipeline (teg_analysis).** Add `DELETION_STEPS: tuple[tuple[str, str], ...]` next to `DATA_UPDATE_STEPS`:
   `backup` "Back up scores and data", `delete` "Remove the rounds", `status` "Update TEG status", `streaks`, `commentary`, `bestball`, `winners` (same labels as `DATA_UPDATE_STEPS`), `reports_archive` "Archive the round's reports", `live_rounds_registry` "Update the live-round registry", `commit` "Save to GitHub".
   Add `progress=None` to `execute_data_deletion()` and `_execute_data_deletion_locked()`. Wrap backup, delete and status in `_run_step`; pass `progress=progress` to every `_run_cache_step`; notify `commit` running/done/failed, or `skipped` when not deferring. Behaviour without `progress` must be identical. Keep the step keys equal to the `_run_cache_step` labels already used.
2. **Job module.** New `webapp/delete_jobs.py`, mirroring `finalize_jobs.py`. Differences:
   - One job at a time (the lock already forces it), so one status file: `data/_delete_status/current.json` via `_store_path`. Confirm the path is outside `sync.SYNC_FOLDERS`, as finalise's comment does.
   - Status also stores `teg` and `rounds`, and on success a JSON-safe copy of the result dict (`rows_deleted`, `backups` as strings, `committed`, `files_committed`, `cache_errors`, `reports_archived`, `archive_dir`).
   - `run_deletion(teg, rounds)` never raises. It calls `execute_data_deletion(..., progress=...)`, then `deps.clear_all_data_caches()`. `UpdateInProgressError` becomes a clear error state ("Another update is running. Try again in a minute.").
   - `claim()` returns the existing status if a deletion is in flight. Unlike finalise, a finished `done` status must not block a new deletion of other rounds.
   - Reuse `_now`, `_store_path`, `_age_seconds` from `webapp.report_generation`, and `BOOT_ID` from `finalize_jobs` (or define its own; both work, one process).
3. **Routes** (`webapp/routes/admin.py`):
   - `POST /admin/delete-data/execute`: validate as now, `claim`, add `delete_jobs.run_deletion` via FastAPI `BackgroundTasks`, return the progress partial. If a job is already active, return its progress with a note, never start a second.
   - New `GET /admin/delete-data/status`: auth-checked. Active → progress partial (polls itself). Done → `admin_delete_result.html` with the stored result. Error or stale → result partial with the error.
   - `GET /admin/delete-data`: if a job is active, render the progress partial in `#delete-preview` on load, so a reload or a locked phone resumes it.
   - All handlers stay sync `def`.
4. **Templates.** `admin_delete_progress.html` mirrors the finalise progress partial: polls `/admin/delete-data/status` every 2 s with `outerHTML` swap, shows "Step N of M: label", the checklist, start time and "You can leave this page". For the checklist, either generalise `admin_live_round_finalize_steps.html` to take a `rows` list (finalise passes `finalize_step_rows(status)`; keep its output identical), or add a small `admin_delete_steps.html`. Prefer generalising; it's the smaller diff. Remove the old `htmx-indicator` line from `admin_delete_preview.html`.
5. **Result partial.** Must render the same as today from the stored dict.

### Acceptance

- Confirm deletion → the checklist appears at once and ticks through the steps; done shows today's result card.
- Reload mid-run → progress resumes. A second Confirm while running → shows the running job, starts nothing.
- A data update or finalise running → deletion shows the "another update" error, no partial work.
- Exactly one GitHub commit per deletion, same message as before.
- At 375 px, the page doesn't jump while polling (check `base.html`'s `scrollActiveTabIntoView`, issue 18).

### Tests

- `tests/test_data_update.py`: progress callback hears every `DELETION_STEPS` key in order; a failing cache step reports `failed` and the run carries on; no callback → unchanged behaviour (existing tests pass untouched).
- New `tests/test_delete_jobs.py`, modelled on `tests/test_finalize_jobs.py`: claim single-flight, done doesn't block a new claim, stale boot id reads as interrupted, error recorded, result stored JSON-safe.
- `tests/test_admin_routes.py`: update the execute test for the new flow (Starlette's `TestClient` runs background tasks before returning) and add one for `/admin/delete-data/status`.
- Run those three files, plus `tests/test_finalize_jobs.py` and `tests/test_live_round_routes.py` if you generalised the finalise steps partial.

## Delivery

**Two PRs from `main`, so the low-risk fixes can ship even if snag 26 slips:**

- **PR A, "Batch 6 PR A":** snags 23, 24, 25 (workers A and B, in parallel, non-overlapping files).
- **PR B, "Batch 6 PR B":** snag 26 (worker C, in parallel with A and B, in its own worktree and branch).

Each PR: draft, targets `main`, concise testing notes, the Railway PR environment verified on the current commit before calling it ready.

**Never merge either PR.** Jon merges. Never push to `main`. Never touch branch `claude/focused-shannon-ft8e6r` or PR #157.

### Model workflow

- **Lead (Opus):** reads this doc, sets up worktrees and branches, briefs workers with their file list and acceptance criteria, owns all git, docs and PRs.
- **Workers (Sonnet):** one per snag owner above, run in parallel. Each reports changed files, tests run with results, and anything it couldn't do.
- **Review (Opus, fresh context):** reviews each PR's combined diff against this doc's acceptance criteria and `CLAUDE.md` invariants. The lead fixes findings before pushing.

### Docs, same PRs

- `TEST_TOURNAMENT_ISSUES.md`: add rows 23-26 with status.
- `TEG19_FIX_PLAN.md`: add a short Batch 6 section and timeline line; record the stale production registry row as a pre-tournament action.
- `webapp/README.md`: one line on the delete background job next to the finalise one, if that section exists.
- `STATUS.md`: one line per PR.
- Delete this file (or fold it into `TEG19_FIX_PLAN.md`) before the last PR merges.

### Pre-push checks

- `python scripts/check_python_compat.py` and `python scripts/check_pandas_compat.py`.
- The test files named per snag. Not the full suite, unless a worker had to touch a shared module beyond those listed.

## Manual test on the PR environments

For each PR's Railway environment (its data writes go to its own branch and volume):

1. Admin → TEG setup → confirm TEG 19 roster. Round setup → confirm R1 Par/SI. Turn the public link on.
2. Go live R1. On a phone, open the entry link: strip visible, brand and Leaderboard work. Log in as admin in the same browser: Review & finalise shows. (PR A)
3. Random-fill, finalise. Every public page now shows "TEG 19 Round 1 results are in. Leaderboard →". Go live R2 → live banner returns for R2. (PR A)
4. Admin → Delete data → TEG 19, R1 and R2 → Confirm: checklist ticks through; reload mid-run resumes it. (PR B)
5. Check Railway's deploy list: data commits should be SKIPPED, not deployed.
