# TEG 19 dry run 2 checklist

Temporary working log for the second TEG 19 dry run, on the draft PR "TEG 19 dry run 2 (do not merge)". **Never merge this branch.** Test data is committed here by the PR environment. Close the PR without merging and delete the branch when done.

Issues 1–17 are in `TEST_TOURNAMENT_ISSUES.md`. New problems found in this run continue from 18 below. Nothing is fixed on this branch.

## Isolation

| Check | Result |
|---|---|
| PR environment deploys this branch | Pending |
| PR volume is a few MB (production ~230 MB) | Pending |
| Preview URL | Pending |
| First write commits to this branch, not `main` | Pending |

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
| B1 | Go live: copyable absolute entry link on admin list and review page, on the preview domain | 1, #141 | | | |
| B2 | Public "Enter scores" banner switch turns the site banner on and off | #141 | | | |
| B3 | Phone: entry ↔ leaderboard with nothing covering the links; all-scores-in banner says an admin finalises | 6, 2 | | | |
| B4 | Hand-enter a few scores, then random fill: hand cells unchanged, scores eagle to triple bogey | 17 | | | |
| B5 | Admin pages usable at phone width, no sideways scroll; review grid fits or scrolls in its box | 3 | | | |
| B6 | Finalise once: step checklist shows progress and survives reload; second tap says already finalising | 4, 10 | | | |
| B7 | While finalising: `/admin/reports` disables Generate for this round, with a reason | Batch 2 | | | |
| B8 | When done: confirmation at top with leaderboard link; review page read-only; "Generate round report" appears only now | 4, 5, 7 | | | |
| B9 | Exactly one data commit for the finalise; no redeploy | 11 | | | |
| B10 | Round report: `/admin/reports` shows phases whichever TEG/round is selected; Generate again asks before overwriting | 8, 9 | | | |
| B11 | `/leaderboard` Reports tab: headline per round, "pending" without a report, headline opens the report | 12 | | | |

## C. Round 4 and completion

| # | Check | Issue | Result |
|---|---|---|---|
| C1 | Round 4 passes section B (see R4 below) | | |
| C2 | Before the tournament report: home page shows winners (Champion, Jacket, Spoon) and final standings; Next TEG tab loads; `/handicaps` shows TEG 20 draft handicaps without crashing, applying the 36-point rule | 13, 14, 15, 16 | |
| C3 | Round 4 report and tournament report generated at the same time: both show progress and both finish | 8 | |
| C4 | After the tournament report: home page adds the headlines; standings and winners unchanged | 16 | |

Round 4 section B results:

| # | R4 |
|---|---|
| B1 | |
| B2 | |
| B3 | |
| B4 | |
| B5 | |
| B6 | |
| B7 | |
| B8 | |
| B9 | |
| B10 | |
| B11 | |

## D. Deletion

| # | Check | Issue | Result |
|---|---|---|---|
| D1 | Delete Round 4 (Admin → Delete rounds): exactly one commit, no redeploy; home page back to in progress; winners cleared | 13, Batch 2 | |
| D2 | Re-enter Round 4 with random fill and finalise: winners and standings return | 13 | |

## Finalise and delete log

| Action | Commits | Redeploy? | Notes |
|---|---|---|---|

## E. Wrap-up

| # | Item | Result |
|---|---|---|
| E1 | Pass/fail summary; anything to fix before the 8 October code freeze | |
| E2 | Close this PR without merging, delete the branch, close PR #140 if still open | |

## New issues

| # | Area | Issue | Root cause | Status |
|---|---|---|---|---|
