# F3 — Latest Round Scoring and Streaks phone layouts

Captured 2026-09-20. Starting base: `756a309` (accepted F2 commit). Worktree: `/Users/jon/projects/teg/worktrees/ui-f3`; branch: `claude/ui-f3`. The tree was clean at entry. The final response supplies this handoff's resulting commit SHA.

F3 was scoped to finish the public `/latest-round` Scoring and Streaks tabs for phone widths. P0's baseline note said both tabs already had some phone treatment and fit the sampled 390px five-player state, flagging Streaks' 32%-width label column and a possible "cramped AB/DM heading collision" as the thing to investigate. This chat validated that note directly rather than acting on it as given.

## What was actually wrong (and what wasn't)

**Streaks: not reproduced.** Tested at 320/375/430px, light/dark, both Clean layouts, with both the sampled 5-player fixture (TEG 18 R4) and the largest player count that exists anywhere in the real data — 6 players (TEG 10 R1; no 8-player fixture exists in this dataset, confirmed via `df.groupby(['TEG','Round'])['Player'].nunique()`). In every state, `Streak Type`/`AB`/`DM`/`GW`/`JP`/`JB`(`/SN`) headers render cleanly with visible gaps between them — no collision, no overflow (`scrollWidth <= innerWidth` in all cases). P0's baseline note appears to have been a stale or overstated observation; this chat found no defect to fix on Streaks and made no changes to it.

**Scoring: one real, reproduced bug.** The score-count pivot's index column header is the *raw pandas index name* — literally the string `"GrossVP"` or `"Stableford"` (7–10 characters), not a short label. Inside the page's `≤640px` `table-layout: fixed` rules, all columns get equal width and the base `.teg-table thead th` rule is `white-space: nowrap` (confirmed by grep and by a `mobile.css` comment noting this is "fine at desktop" but not scoped for narrow fixed layouts). The header text has nowhere to go and visually bleeds into the next header cell — rendered as `"GrossVPAB"` at every phone width tested (320/375/430px), both themes, both modes, both the 5-player and 6-player fixtures. Confirmed via `getBoundingClientRect()`: the `th` box itself doesn't overlap (adjacent cells correctly touch at the border), but the *text* overflowed its box before the fix, which is exactly the failure mode design_principles.md documents as "pitfall #2" for `table-layout: fixed` (`webapp/design_principles.md`, Mobile table pattern section) — and one three other pages on this same site (`.scoring-matrix-page`, `.scoring-byteg-page`) already hit and fixed the same way.

## Fix

| File | Change |
|---|---|
| `webapp/routes/latest.py` | Both `elif tab == "scoring":` branches (`_latest_round_tab_context` and `_latest_teg_tab_context`) now pass `table_class="teg-table scoring-table"` to `_df_to_html(display_df, ...)` instead of the bare default, giving the pivot a class to target — same pattern the adjacent Streaks branch already uses (`table_class="teg-table streaks-table"`). |
| `webapp/static/mobile.css` | New rule, inserted directly after the existing Streaks first-column block inside the same `≤640px` media query: `.latest-round-page #lr-content table.scoring-table th, .latest-teg-page #lt-content table.scoring-table th { white-space: normal; overflow-wrap: anywhere; line-height: 1.15; }` — the exact wrap treatment already used by `.scoring-matrix-page`/`.scoring-byteg-page`'s `.teg-table thead th` (same file, further down), reused rather than reinvented. |

No width redistribution was needed — allowing the header to wrap onto a second line was sufficient; the design_principles.md "table-tier" preconditions (≤6 columns, one primary numeric column, short cell values) still hold for this table at the player counts that exist in real data (6 columns at 5 players, 7 at 6 players), so no tier change (sticky-scroll / card reflow) was warranted.

Delegation: the lead (this chat) diagnosed the bug directly (Playwright DOM measurement + a live CSS-injection test to confirm the fix before committing to it), then delegated the exact two-file patch (with the precise selectors/lines and the established sibling pattern to copy) to a Sonnet subagent, per the roadmap's delegation rule for a clearly-scoped CSS/template patch. The lead verified the applied diff, restarted the local server, and re-ran the full width/theme/mode sweep independently before accepting it.

## Verification

Ran locally from this worktree (a stale server process from an earlier stage of this same session, bound to the same port, briefly produced a false "not fixed" reading after the patch landed — root-caused via `lsof`, force-killed, and a clean restart resolved it; noted here so a future chat isn't misled by the same symptom):

```bash
cd /Users/jon/projects/teg/worktrees/ui-f3
/Users/jon/projects/teg/teg_v2/venv/bin/python -m uvicorn webapp.app:app --host 127.0.0.1 --port 8123
```

**Focused tests:**
```
python -m pytest tests/test_webapp_pages.py -k 'latest_round' -v
```
10 passed, 0 failed (includes `test_latest_round_tab_partials_render[scoring]` and `[streaks]`). CSS + a one-line table-class change; no wider suite run — matches CLAUDE.md's blast-radius guidance (route/template change scoped to two tabs of one page, not a shared/core module).

**Browser verification (Playwright, Chromium), Scoring tab, `teg=10&round=1` (6-player fixture) and `teg=18&round=4` (5-player fixture):**

| Check | Widths | Themes | Modes | Result |
|---|---|---|---|---|
| Header overflow (`"GrossVP"`/`"Stableford"` bleeding into next header) | 320, 375, 430, 768, 1280 | Clean Page, Clean Layered | light, dark | Fixed at all 3 phone widths (wraps to 2 lines, stays inside its own column); tablet/desktop were already fine before this chat (no fixed-layout there) and remain unchanged |
| Page-level horizontal overflow (`scrollWidth <= innerWidth`) | 320, 375, 430, 768, 1280 | Clean Page, Clean Layered | light, dark | 0 of 20 states overflow |
| Header bounding-box collision (`th[0].right > th[1].left`) | 320, 375, 430, 768, 1280 | Clean Page, Clean Layered | light, dark | 0 of 20 states collide |
| HTMX tab switching (Scoreboard → Scoring → Streaks) preserves URL state, no console errors | 375 | Clean Page | dark | `?tab=` query param updates correctly on each click; both tabs render their correct table; 0 console errors |
| Score-type / Count-% pill controls still present and wired | 320–430 | Clean Page | light, dark | Unchanged — still HTMX `hx-get` buttons, same markup, not touched by this fix |
| Streaks tab (regression check, 5- and 6-player) | 320, 375, 430 | Clean Page | light, dark | Unchanged from baseline — clean, no collision, matches P0's screenshot at 390px |

Console: 0 errors on every page checked (the pre-existing Tailwind production-CDN warning is the only recurring entry, as noted in P0/F1/F2).

Screenshots: `webapp/design_reviews/ui_workstream/screenshots/F3/` —
- `f3-scoring-320-dark-6p-before.png` — the bug, 6-player fixture, dark, 320px
- `f3-scoring-320-6p-after-light.png`, and the equivalent dark capture — after the fix
- `f3-streaks-320-6p-light.png`, `f3-streaks-320-6p-dark.png` — Streaks regression check, 6-player fixture
- `f3-streaks-375-dark-after-tab-switch.png` — Streaks reached via a live HTMX tab click, confirming state/URL sync

## Rules followed

- No redesign of either tab; the fix reuses an existing, established site pattern (`.scoring-matrix-page`/`.scoring-byteg-page`'s header-wrap rule) rather than inventing a new one.
- Scoreboard, Bestball/Worstball, tablet, and desktop behaviour untouched — verified unchanged at 768/1280px and via the full focused-test run.
- Score-type/count-% controls and HTMX tab switching/URL state preserved and re-verified live in-browser, not just via response smoke tests.
- No latest-round state handling or live-write path touched.
- `mobile.css` was read in full for the relevant page section before adding markup, per the task's explicit instruction; the new rule was placed directly beside its closest sibling (Streaks first-column block) rather than appended elsewhere.
- CSS/template patch delegated to a Sonnet subagent with explicit file/selector ownership; the lead owned the diagnosis, the shared route-level decision (the new `table_class` string), and integration/verification.

## Unresolved / explicitly out of scope

- Records and Scorecard tabs inside Latest Round remain F4's scope (F4 depends on F2, already accepted) — not touched here.
- No 8-player fixture exists anywhere in the current dataset (max is 6, TEG 7/8/10/15). The Scoring/Streaks column-count math (`players + 1` fixed-width columns) has been verified correct up to 6 players; whether it needs a different tier (sticky-scroll or card reflow, per design_principles.md's stated preconditions) at 7–8 players cannot be verified without a fixture and should be re-checked once one exists, or the first time a TEG roster actually reaches that size.
- The existing tab-strip horizontal-scroll behaviour (partial "WORSTBALL"/"STR" buttons visible at the viewport edges) is pre-existing, unrelated to this fix, and out of scope per P0's explicit instruction not to fold the Scoreboard/tab-strip finding into a Fix-stage chat.
- No new automated overflow/collision-regression test was added (matches F1/F2's precedent — this class of visual check has been verified manually/programmatically via Playwright each time, not via a new test file); flagging again, as P0/F1/F2 did, that this remains a general test-coverage gap for the workstream.

## Handoff

This chat's resulting commit is the next accepted base for F4 (Latest Round Records and Scorecard), which depends on F2 (already accepted) and should integrate after this commit per the roadmap's `F1 → F2 → F3 → F4 → F5` order. No push, merge, or deploy performed.
