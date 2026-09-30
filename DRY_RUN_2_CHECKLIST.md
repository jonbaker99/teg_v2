# TEG 19 dry run 2 checklist

Temporary working log for the second TEG 19 dry run, on the draft PR "TEG 19 dry run 2 (do not merge)". **Never merge this branch.** Test data is committed here by the PR environment. Close the PR without merging and delete the branch when done.

Issues 1–17 are in `TEST_TOURNAMENT_ISSUES.md`. New problems found in this run continue from 18 below. Nothing is fixed on this branch.

## Isolation

| Check | Result |
|---|---|
| PR environment deploys this branch | Pass: `teg_v2-pr-150` deploys `claude/keen-fermi-abmt7t` @ `6094206` |
| PR volume is a few MB (production ~230 MB) | Pass: own volume, 0 MB at start, 83 MB after first page loads (files are cached lazily from this branch on first read); production 227 MB |
| Preview URL | https://teg-test2.up.railway.app |
| First write commits to this branch, not `main` | Pass: `98f44ba` "Turn public live-round entry link on" landed on this branch; `main` unchanged at `ec8ceb6` |

## A. Before any rounds

| # | Check | Issue | Result |
|---|---|---|---|
| A1 | Home page Next TEG tab shows the TEG 19 schedule and handicaps | 15 | |
| A2 | `/handicaps` shows TEG 19 handicaps, SN at 27, HM and GP not listed | 14 | |
| A3 | Production (read-only): `/handicaps` shows SN at 27. If not, `handicaps.csv` isn't pulled onto the production volume yet | 14 | |
| A4 | Production (read-only): admin live-round review page has no random-fill button | 17 | |

## B. Rounds 1–3

| # | Check | Issue | R1 | R2 | R3 |
|---|---|---|---|---|---|
| B1 | Go live: copyable absolute entry link on admin list and review page, on the preview domain | 1, #141 | Partial (issue 20) | Partial: link not usable straight after Go live; needed a reload (issue 20) | Partial (issue 20) |
| B2 | Public "Enter scores" banner switch turns the site banner on and off | #141 | Pass | Pass | Pass |
| B3 | Phone: entry ↔ leaderboard with nothing covering the links; all-scores-in banner says an admin finalises | 6, 2 | Pass | Pass | Pass |
| B4 | Hand-enter a few scores, then random fill: hand cells unchanged, scores eagle to triple bogey | 17 | Pass | Pass | Pass |
| B5 | Admin pages usable at phone width, no sideways scroll; review grid fits or scrolls in its box | 3 | Pass | Pass | Pass |
| B6 | Finalise once: step checklist shows progress and survives reload; second tap says already finalising | 4, 10 | Fail on phone: page jumps to top every 2s, so progress can't be watched (issue 18) | Fail on phone (issue 18) | Fail on phone (issue 18) |
| B7 | While finalising: `/admin/reports` disables Generate for this round, with a reason | Batch 2 | Pass | Pass | Pass |
| B8 | When done: confirmation at top with leaderboard link; review page read-only; "Generate round report" appears only now | 4, 5, 7 | Pass | Pass | Pass |
| B9 | Exactly one data commit for the finalise; no redeploy | 11 | Half: one commit (`9bd6b9e`, 13 data files) but Railway started a redeploy (issue 19) | Pass: one commit (`c666bec`), deploy skipped | Pass: one commit (`5a4b908`), deploy skipped, while R2 report was running |
| B10 | Round report: `/admin/reports` shows phases whichever TEG/round is selected; Generate again asks before overwriting | 8, 9 | Pass | Pass | Pass |
| B11 | `/leaderboard` Reports tab: headline per round, "pending" without a report, headline opens the report | 12 | Pass | Pass | Pass |

## C. Round 4 and completion

| # | Check | Issue | Result |
|---|---|---|---|
| C1 | Round 4 passes section B (see R4 below) | | Pass apart from issues 18 and 20 |
| C2 | Before the tournament report: home page shows winners (Champion, Jacket, Spoon) and final standings; Next TEG tab loads; `/handicaps` shows TEG 20 draft handicaps without crashing, applying the 36-point rule | 13, 14, 15, 16 | |
| C3 | Round 4 report and tournament report generated at the same time: both show progress and both finish | 8 | |
| C4 | After the tournament report: home page adds the headlines; standings and winners unchanged | 16 | |

Round 4 section B results:

| # | R4 |
|---|---|
| B1 | Partial (issue 20) |
| B2 | Pass |
| B3 | Pass |
| B4 | Pass |
| B5 | Pass |
| B6 | Fail on phone (issue 18) |
| B7 | Pass |
| B8 | Pass |
| B9 | Pass: one commit (`58a60da`, 15 files incl. `teg_winners.csv`, `completed_tegs.csv`), deploy skipped |
| B10 | Pass |
| B11 | Pass |

## D. Deletion

| # | Check | Issue | Result |
|---|---|---|---|
| D1 | Delete Round 4 (Admin → Delete rounds): exactly one commit, no redeploy; home page back to in progress; winners cleared | 13, Batch 2 | |
| D2 | Re-enter Round 4 with random fill and finalise: winners and standings return | 13 | |

## Finalise and delete log

| Action | Commits | Redeploy? | Notes |
|---|---|---|---|
| Public link on (R1) | 1 (`98f44ba`) | No (skipped) | |
| Finalise R1 | 1 (`9bd6b9e`) | **Yes**: deployment `b57b758b` built, then superseded (REMOVED) before going live | Only `data/**` changed |
| (my checklist push) | merge `69b1fb9` | Yes, went live 20:49:08Z | My error: merge commit carried the data diff. Not an app issue. Now rebasing before each push |
| Go live R2 | 1 (`1d67659`, registry) | No (skipped) | |
| Finalise R2 | 1 (`c666bec`, only `data/**`), ~35s | No: `51599e47` showed BUILDING for 15s, then SKIPPED | Railway lists a commit as BUILDING while it checks watch paths |
| Go live R3 | 1 (`d2efa97`, registry) | No (skipped) | |
| Finalise R3 | 1 (`5a4b908`, only `data/**`) | No: BUILDING 19s, then SKIPPED | R2 report running at the time |
| R3 round report | 1 (`67ab4fe`) | No (two SKIPPED records) | |
| Go live R4 | 1 (`6f48b3c`, registry) | No (skipped) | |
| Finalise R4 (TEG complete) | 1 (`58a60da`, only `data/**`) | No: BUILDING 22s, then SKIPPED | Writes TEG 19 winners row: Trophy Alex BAKER, Jacket Jon BAKER, Spoon Gregg WILLIAMS; TEG 19 moved to `completed_tegs.csv` |
| R2 round report | 1 (`23b40c8`, 5 files under `data/commentary/`) | No (skipped) | Ran across the R3 finalise without harm |
| R1 round report | 1 (`43da2f1`, 5 files under `data/commentary/`) | No (skipped) | Committed 20:48:57Z, 11s before the redeploy went live, so it survived by luck |

## E. Wrap-up

| # | Item | Result |
|---|---|---|
| E1 | Pass/fail summary; anything to fix before the 8 October code freeze | |
| E2 | Close this PR without merging, delete the branch, close PR #140 if still open | |

## New issues

| # | Area | Issue | Root cause | Status |
|---|---|---|---|---|
| 18 | Admin / finalise progress (phone) | While finalise runs, the page jumps to the top every 2s, so the step checklist can't be watched. | `base.html` `scrollActiveTabIntoView` runs on every `htmx:afterSettle`. At ≤640px it calls `scrollIntoView({block: 'nearest'})` on the active tab of every `.section-nav`. Admin pages include `partials/admin_nav.html`, a `.section-nav` at the top. The finalise progress partial polls every 2s (`hx-trigger="every 2s"`), so each poll scrolls the page back up to the admin nav. Expect the same on `/admin/reports` while its running panel polls. Fix direction: only scroll the tab row horizontally (set `nav.scrollLeft`), or skip when the swap didn't touch the nav. | Open |
| 19 | Deploy / Railway (**affects production**, issue 11 not fixed) | Finalise R1 made one commit, as intended, but Railway still started a redeploy. | Not confirmed. The commit touches only `data/**`, which the watch patterns exclude (`!/data/**`). The previous data-only commit (`98f44ba`, one CSV) was skipped. Production on 29 Sept shows the same mix: single-CSV commits under `data/` both skipped and deployed. So it isn't the file set or commit count. Railway's skip decision looks unreliable. Update: R2 finalise (`c666bec`) showed BUILDING for 15s then SKIPPED, so BUILDING alone doesn't mean a redeploy. R1's (`b57b758b`) differed: it logged "scheduling build on Metal builder" then "failed to fetch snapshot" for 5 minutes, and was REMOVED when my merge commit superseded it. So R1 may be a Railway snapshot fault rather than a watch-path miss. Keep watching R3, R4 and D1. Build log shows repeated "failed to fetch snapshot"; the old deployment keeps serving while it builds. The mitigation already planned (auto-deploy off 9–13 Oct, `TEG19_FIX_PLAN.md` decision 3) is the reliable guard; confirm it's actually off before the 10th. | Open |
| 20 | Admin / Go live | After tapping Go live on `/admin/live-round`, the entry link doesn't appear usably, and the round isn't added to the "Every live round" table below. A reload is needed to get the link. | `admin_live_round_start` returns `partials/admin_live_round_start_result.html` into a hidden `<tr><td colspan="5">` under that round in the "Start a live round" table (`admin_live_round.html:68–75`). Three gaps: (a) the "Every live round" table is server-rendered and never refreshed, so the new round only shows after a reload; (b) the result partial is a bare link, not the shared `live_round_entry_link.html` with Copy, so it doesn't match what #141 added elsewhere; (c) HTTP log shows two `POST /admin/live-round/start` 2s apart (20:51:15, 20:51:17). The second hits `LiveRoundAlreadyActiveError` and its error message replaces the link from the first. `hx-disabled-elt="this"` only covers the in-flight request. Fix direction: after a successful start, answer with `HX-Redirect` to `/admin/live-round` (or the new round's review page), where the link and Copy button already render. | Open |
