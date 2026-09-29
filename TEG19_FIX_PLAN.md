# TEG 19 dry-run fixes: two PRs before 10 October, the rest after

Temporary working plan. Delete it once every item below is fixed or moved into `webapp/TODOS.md`.

## The answer

The dry run found 16 issues. Four of them break the site the moment TEG 19 completes. Three stop the live-round flow working smoothly on the day.

TEG 19 starts on **10 October 2026**. Fix those seven first, in two PRs that can run in parallel. The rest can wait until after the tournament.

- **Before the tournament:** Batch 1A (post-completion crashes) and Batch 1B (live-round day flow). Then re-run the dry run.
- **After the tournament:** Batch 2 (finalise reliability), Batch 3 (report admin) and Batch 4 (admin mobile layout and the leaderboard reports tab).

Evidence for every item is in `TEST_TOURNAMENT_ISSUES.md` on the dry-run branch (PR #140). Issue numbers below match that log.

## Decisions (settled)

1. **Handicaps for players who miss a TEG (issue 14): they're assumed to score 36 points a round.** The calculation already does this (`fillna(36)` in `get_hc`), so a missed TEG counts as that TEG's handicap. That only works if a handicap is saved for the missed TEG. Past TEGs followed that convention: SN sat out TEGs 11, 13, 14, 17 and 18, and JP sat out 14 and 16, yet each had a handicap saved. TEG setup (`save_teg_roster`) now writes `0` for anyone not playing, which breaks it: SN's TEG 19 handicap is 0, so SN's TEG 20 figure comes out wrong.
2. **Batch 2 waits until after the tournament.** With auto-deploy off, the redeploy risk (issue 11) goes away. With Batch 1B's feedback, a 40-second finalise is tolerable. Batch 2 changes the shared data pipeline, which is the wrong thing to change a week before the tournament.
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

**Acceptance:** on a phone, a player can move between entry and leaderboard both ways. An admin can find any active round's link, finalise once with clear feedback, and move on to the report.

### Batch 2: finalise reliability (after the tournament)

| # | Problem | Proposed fix |
|---|---|---|
| 10 | Finalise runs for about 40 seconds inside one web request. | Run it as a background job with a status file, reusing the report-generation pattern (`webapp/report_generation.py`). |
| 11 | Several commits in quick succession sometimes trigger a full redeploy, despite the `data/**` watch pattern. Seen on production on 29 September. The redeploy kills running reports and gives 502s. Cause not confirmed. | Write each admin action as **one** commit (backups, data, caches and registry together via `push_files`). Separately, check Railway's skip behaviour for rapid commits. |

**Acceptance:** finalising a round returns at once, shows progress, and makes exactly one commit. No redeploy is triggered in the PR environment's deploy list.

This is the riskiest batch. It touches the shared data pipeline, so run the full test suite.

### Batch 3: report admin (after the tournament)

| # | Problem | Proposed fix |
|---|---|---|
| 8 | One vague status message covers a multi-minute run. | Record each phase in the status file. Show every running report, with each phase marked done, in progress or to do, on `/admin/reports`. |
| 9 | Generate has no check. In-progress runs error after the tap, and recent reports are silently regenerated (costing money). | Confirm before starting: "already generating, started HH:MM, at phase X" or "generated at HH:MM, regenerate and overwrite?". |

### Batch 4: admin mobile layout and leaderboard reports (after the tournament)

| # | Problem | Proposed fix |
|---|---|---|
| 3 | Admin pages aren't mobile-friendly. The review grid is too wide for the screen. | Audit admin templates at phone width, starting with the live-round review grid. Follow `webapp/design_principles.md`. |
| 12 | Feature: round reports can't be reached from `/leaderboard` mid-tournament. | Add a Reports tab, shown during a tournament. It lists each round's report headline, links through to the report, and shows "pending" for rounds without one. Reuse `get_edition_summary`. |

### Housekeeping (with Batch 1A)

- **CLAUDE.md is out of date.** It says the webapp "only reads finished reports; it never generates them", but `/admin/reports` generates them. Correct the Architecture line.
- Move any unfinished items into `webapp/TODOS.md`, and update `STATUS.md`.

## How to work through it

Each batch is one task: its own branch and worktree, and one PR against `main` with a Railway preview. Batches 1A and 1B touch different files, so they can run at the same time.

**Model split** (repo rule: use tier aliases, not version names):

- **Plan and review with Opus.** Start each batch's lead session with `/model opusplan`. It uses Opus in plan mode and Sonnet for implementation.
- **Implement with Sonnet.** The lead delegates scoped edits to Sonnet subagents, giving each an exact file list that doesn't overlap with the others.
- **Review with Opus in a fresh context.** Use the repo's `code-reviewer` agent (`model: opus`) on the combined diff before the PR is marked ready.

**Per batch:**

1. **Plan (Opus):** read this file and the issue log. Confirm the root causes against the code. Write acceptance tests first for the crash fixes.
2. **Implement (Sonnet workers):** one worker per file group. Run only the relevant tests: `test_webapp_pages.py`, `test_data_update.py`, `test_teg_setup.py` for 1A; `test_live_round*.py`, `test_admin_routes.py` for 1B; the full suite for Batch 2.
3. **Review (Opus, fresh context):** the lead fixes the findings.
4. **Preview:** push, open the PR, and check the Railway preview on a phone.
5. **Merge:** only with your explicit go-ahead.

**Timeline:**

| When | What |
|---|---|
| by 3 Oct | Batches 1A and 1B merged |
| 4 to 6 Oct | Second dry run on a fresh PR environment (below) |
| 9 Oct | Turn auto-deploy off. Close PR #140 and delete its branch. |
| 10 to 13 Oct | TEG 19 |
| after | Turn auto-deploy back on. Batches 2, 3 and 4. |

## Second dry run: the same flow, checking the fixes

Branch fresh from `main`, open a draft PR, and use its Railway environment. First, confirm its disk usage is separate from production's.

1. Go live for Round 1. Find the link again from the admin list.
2. Enter scores on a phone. Go from the leaderboard to entry and back.
3. Finalise once. Check the feedback, the read-only review page, and the report button.
4. Generate the round report.
5. Repeat for Rounds 2 to 4.
6. After Round 4, check the home page (both tabs) and `/handicaps` **before** generating the tournament report. Then check them again after.
7. Check the Railway deploy list for any redeploys triggered by data commits.

Log anything new in the same way. Close the PR afterwards.
