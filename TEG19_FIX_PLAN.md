# TEG 19 dry-run fixes: everything but Batch 2 ships before 10 October

Temporary working plan. Delete it once every item below is fixed or moved into `webapp/TODOS.md`.

## The answer

The dry run found 16 issues. Four of them break the site the moment TEG 19 completes. Three stop the live-round flow working smoothly on the day.

TEG 19 starts on **10 October 2026**. Everything except Batch 2 ships before then, in two waves:

- **Wave 1, starting now, in parallel:** Batch 1A (post-completion crashes), Batch 1B (live-round day flow and the random score fill), Batch 3 (report admin) and Batch 4a (the leaderboard reports tab).
- **Wave 2, once 1B and 3 are merged:** Batch 4b (admin pages on mobile). It restyles the pages those two batches change.
- **Then** a second dry run of the whole flow.
- **Batch 2 (finalise reliability):** pulled forward and done on 30 September (see Decision 2).

Evidence for every item is in `TEST_TOURNAMENT_ISSUES.md` on the dry-run branch (PR #140). Issue numbers below match that log.

## Decisions (settled)

1. **Handicaps for players who miss a TEG (issue 14): they're assumed to score 36 points a round.** The calculation already does this (`fillna(36)` in `get_hc`), so a missed TEG counts as that TEG's handicap. That only works if a handicap is saved for the missed TEG. Past TEGs followed that convention: SN sat out TEGs 11, 13, 14, 17 and 18, and JP sat out 14 and 16, yet each had a handicap saved. TEG setup (`save_teg_roster`) now writes `0` for anyone not playing, which breaks it: SN's TEG 19 handicap is 0, so SN's TEG 20 figure comes out wrong.
2. **Batch 2 waits until after the tournament.** With auto-deploy off, the redeploy risk (issue 11) goes away. With Batch 1B's feedback, a 40-second finalise is tolerable. Batch 2 changes the shared data pipeline, which is the wrong thing to change a week before the tournament. **Overridden 2026-09-30:** Jon asked for Batch 2 before the tournament; it is done (below). Keep auto-deploy off over the tournament anyway.
3. **Auto-deploy is off from 9 to 13 October.** Deploy fixes by hand (below), and only when no finalise or report is running. Turn it back on afterwards, or it's easy to merge a fix that never goes live.

**Deploying by hand:** in the Railway dashboard, open the project, press Cmd+K and choose *Deploy Latest Commit*. That deploys the newest commit on `main`. A Claude session with the Railway connector can also trigger it for you.

## The issues, grouped into batches

### Batch 1A: stop the site breaking when TEG 19 completes (must ship)

All four are silent until the last round is finalised, then they hit every visitor.

| # | Problem | Proposed fix | Main files |
|---|---|---|---|
| 13 | Home page shows dashes for Champion, Jacket and Spoon. Nothing saves the winners when a TEG completes. | Add a winners step to the finalise/data-update cache steps. It runs when a TEG becomes complete and on deletion, and fails loudly like the other cache steps. Remove or wire in the unused `calculate_and_save_missing_winners`. | `teg_analysis/analysis/history.py`, `analysis/data_update.py` |
| 14 | `/handicaps` crashes (NaN to int). HM and GP have no TEG 18 handicap and `0` for TEG 19, so they get gaps. SN's TEG 19 handicap is `0` because TEG setup saves 0 for non-players, so SN's TEG 20 handicap is wrong. | Keep the 36-point rule (decision 1). (a) For regulars who sit a TEG out, TEG setup saves their calculated handicap (not 0) and marks them not playing some other way, so the rule has a handicap to use. (b) Repair TEG 19's row for SN. (c) Exclude anyone with no handicap in either of the two TEGs (HM, GP). (d) One player's gap must never break the page. The home page's Next TEG tiles share this path. Check which other readers treat 0 as "not playing" before changing what's saved. | `teg_analysis/analysis/handicaps.py`, `analysis/teg_setup.py`, `data/handicaps.csv` |
| 15 | Home page Next TEG tab crashes (`KeyError: 'TEGNum'`) when the next TEG has no rounds set up. | Return `TEGNum` from `get_future_tegs`. Show TBC when there's no row at all (future_tegs.csv has no TEG 20). | `teg_analysis/analysis/history.py`, `webapp/routes/contents.py` |
| 16 | Home page final standings only appear once the tournament report exists. | Always load the standings panel. Show the headlines column only when a report exists. The panel partial already handles no report. | `webapp/templates/partials/_contents_complete_view.html` |

**Acceptance:** on test data with TEG 19 complete and no tournament report, the home page (both tabs) and `/handicaps` load, and show the right winners and standings. Add a regression test for each crash.

### Batch 1B: make the live-round day flow usable (must ship)

| # | Problem | Proposed fix | Main files |
|---|---|---|---|
| 6 | The Light / Dark toggle covers the "Enter scores" link on the live leaderboard. Players can't get back. | Move the toggle into the app bar or remove it (a mock-up leftover, `.demobar`). Check the entry page too. | `webapp/templates/live_round_leaderboard.html`, `live_round_entry.html` |
| 1 | The score-entry link appears once after Go live and can't be found again. | Show the full link, with a copy button, for every active round on the admin list and review pages. | `webapp/routes/admin_live_round.py`, `templates/admin_live_round*.html` |
| 4 | Finalise shows no progress. The success message is below the fold, so admins tap twice. | Show a clear in-progress state. On success, show the confirmation at the top, then offer the leaderboard. | `templates/admin_live_round_review.html`, `partials/admin_live_round_finalize_result.html` |
| 5 | A finalised round's review page still offers Save, Finalize and Cancel. | Render finalised and cancelled rounds read-only. | same as above |
| 7 | No next step after finalising. | Add a "Generate round report" button to `/admin/reports?teg=N&round=R`. | same as above |
| 2 | Players aren't told that finalising is admin-only. | Once all scores are in, the banner says who finalises. Mostly solved by 6. | `live_round_leaderboard.html` |
| 17 | Feature: filling each round by hand makes dry runs slow. | A test-only "Fill empty cells with random scores" button on the admin review page. Each score is par −2 to par +3 for that hole (eagle to triple bogey; never below 1), weighted towards par and bogey. It fills only empty cells, and writes through `apply_admin_edits` so the usual validation applies. **Hidden, and refused server-side, on production:** enable it only when `RAILWAY_ENVIRONMENT_NAME` isn't `production` (PR environments and local). | `webapp/routes/admin_live_round.py`, `templates/admin_live_round_review.html`, `teg_analysis/analysis/live_round.py` |

**Acceptance:** on a phone, a player can move between entry and leaderboard both ways. An admin can find any active round's link, finalise once with clear feedback, and move on to the report. On the PR preview, the random-fill button fills a round in one tap; on production, it's absent and its route refuses.

### Batch 2: finalise reliability (done, 2026-09-30)

**Done:** pulled forward at Jon's request. Finalise, sheet import and round deletion each make one GitHub commit. Finalise runs as a background job with a step checklist, and report Generate waits until the round's data is ready. Detail: `webapp/README.md` → Live round and `DATA_FLOW.md` → Write pipeline.

| # | Problem | Proposed fix |
|---|---|---|
| 10 | Finalise runs for about 40 seconds inside one web request. | Run it as a background job with a status file, reusing the report-generation pattern (`webapp/report_generation.py`). |
| 11 | Several commits in quick succession sometimes trigger a full redeploy, despite the `data/**` watch pattern. Seen on production on 29 September. The redeploy kills running reports and gives 502s. Cause not confirmed. | Write each admin action as **one** commit (backups, data, caches and registry together via `push_files`). Separately, check Railway's skip behaviour for rapid commits. |

**Acceptance:** finalising a round returns at once, shows progress, and makes exactly one commit. No redeploy is triggered in the PR environment's deploy list.

This is the riskiest batch. It touches the shared data pipeline, so run the full test suite.

### Batch 3: report admin (wave 1)

| # | Problem | Proposed fix |
|---|---|---|
| 8 | One vague status message covers a multi-minute run. | Record each phase in the status file. Show every running report, with each phase marked done, in progress or to do, on `/admin/reports`. |
| 9 | Generate has no check. In-progress runs error after the tap, and recent reports are silently regenerated (costing money). | Confirm before starting: "already generating, started HH:MM, at phase X" or "generated at HH:MM, regenerate and overwrite?". |

Main files: `webapp/report_generation.py`, `webapp/routes/admin_reports.py`, `templates/admin_reports.html`, `partials/admin_report_*.html`. Phase tracking may need a progress callback from the report pipeline (`teg_analysis/reporting/`). Keep that hook minimal and UI-agnostic.

**Acceptance:** with two reports running, `/admin/reports` shows both with their phases, whichever TEG and round is selected. Tapping Generate on a running report, or on one made in the last few hours, asks first.

### Batch 4a: leaderboard reports tab (wave 1, done)

| # | Problem | Proposed fix |
|---|---|---|
| 12 | Feature: round reports can't be reached from `/leaderboard` mid-tournament. | Add a Reports tab, shown during a tournament. It lists each round's report headline, links through to the report, and shows "pending" for rounds without one. Reuse `get_edition_summary`. |

Main files: `webapp/routes/leaderboard.py` and its templates. Don't touch the home page (`contents.py`), which is Batch 1A's.

**Acceptance:** mid-tournament, the tab lists every round, with headlines for rounds that have a report and "pending" for the rest. Each headline opens that round's report. Completed TEGs still reach the full edition.

### Batch 4b: admin pages on mobile (wave 2, after 1B and 3 merge)

| # | Problem | Proposed fix |
|---|---|---|
| 3 | Admin pages aren't mobile-friendly. The review grid is too wide for the screen. | Audit admin templates at phone width, starting with the pages used on the day: live-round list, review and finalise, reports, and round setup. Fix shared styles in `webapp/static/admin.css` first, then per page. Follow `webapp/design_principles.md`. |

**Acceptance:** at 390px wide, every admin page used on the day works with no sideways page scroll, and the review grid fits or scrolls within its own box.

### Housekeeping (with Batch 1A)

- **CLAUDE.md is out of date.** It says the webapp "only reads finished reports; it never generates them", but `/admin/reports` generates them. Correct the Architecture line.
- Move any unfinished items into `webapp/TODOS.md`, and update `STATUS.md`.

## How to work through it

Each batch is one task: its own branch and worktree, and one PR against `main` with a Railway preview. The four wave-1 batches touch different files, so they can run at the same time. Shared docs (`STATUS.md`, `webapp/README.md`) are the one overlap: each batch edits only its own section, and the second PR to merge brings in `main` and resolves any conflict.

**Model split** (repo rule: use tier aliases, not version names):

- **Plan and review with Opus.** Start each batch's lead session with `/model opusplan`. It uses Opus in plan mode and Sonnet for implementation.
- **Implement with Sonnet.** The lead delegates scoped edits to Sonnet subagents, giving each an exact file list that doesn't overlap with the others.
- **Review with Opus in a fresh context.** Use the repo's `code-reviewer` agent (`model: opus`) on the combined diff before the PR is marked ready.

**Per batch:**

1. **Plan (Opus):** read this file and the issue log. Confirm the root causes against the code. Write acceptance tests first for the crash fixes.
2. **Implement (Sonnet workers):** one worker per file group. Run only the relevant tests: `test_webapp_pages.py`, `test_data_update.py`, `test_teg_setup.py` for 1A; `test_live_round*.py`, `test_admin_routes.py` for 1B; `test_admin_routes.py` for 3; `test_webapp_pages.py` for 4a and 4b; the full suite for Batch 2.
3. **Review (Opus, fresh context):** the lead fixes the findings.
4. **Preview:** push, open the PR, and check the Railway preview on a phone.
5. **Merge:** only with your explicit go-ahead.

**Timeline:**

| When | What |
|---|---|
| now to 3 Oct | Wave 1: Batches 1A, 1B, 3 and 4a, in parallel |
| 3 to 5 Oct | Wave 2: Batch 4b |
| 6 to 7 Oct | Second dry run on a fresh PR environment (below). Fix only what it finds. |
| 8 Oct | Code freeze. Close PR #140 and delete its branch. |
| 9 Oct | Turn auto-deploy off. |
| 10 to 13 Oct | TEG 19 |
| after | Batch 2. Then turn auto-deploy back on. |

If a batch slips past 5 October, drop it rather than squeeze it in: 1A and 1B are the only must-haves. Anything merged late gets only a partial rehearsal.

## Second dry run: the same flow, checking the fixes

Branch fresh from `main`, open a draft PR, and use its Railway environment. First, confirm its disk usage is separate from production's.

1. Go live for Round 1. Find the link again from the admin list.
2. Enter a few scores on a phone. Go from the leaderboard to entry and back. Fill the rest with the random-fill button.
3. Finalise once. Check the feedback, the read-only review page, and the report button.
4. Generate the round report. Watch its phases on `/admin/reports`. Tap Generate again to check the confirmation. Check the leaderboard's Reports tab once it finishes.
5. Repeat for Rounds 2 to 4.
6. After Round 4, check the home page (both tabs) and `/handicaps` **before** generating the tournament report. Then check them again after.
7. Use every admin page on a phone.
8. Check the Railway deploy list for any redeploys triggered by data commits.

Log anything new in the same way. Close the PR afterwards.
