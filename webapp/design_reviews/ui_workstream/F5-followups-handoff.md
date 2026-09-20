# F5 follow-ups — scroll-delta guard and cross-route sweep

Captured 2026-09-20. Starting base: `e50078d68719cb1697894ead7b24daff2f0ba919` (`main` at task start). Worktree: `/Users/jon/projects/teg/worktrees/f5-scroll-delta-sweep`; branch: `codex/f5-scroll-delta-sweep`. The tree was clean at entry. The final response supplies this handoff's resulting commit SHA.

The starting recommendation was Sol High, matching F5's shared-shell tier. No higher lead tier was needed: the implementation decision was a bounded event-delta rule, while the main risk was verification breadth. A Luna explorer performed read-only route and test inventory; the lead retained sole write ownership. A fresh strong review is recorded before commit.

## Scope and decision

F5 revealed the sticky nav whenever `scrollY < lastY`. That fixed genuine upward scrolling, but an isolated 1px negative delta from wheel momentum, trackpad jitter, or elastic scrolling could also reveal it.

The follow-up uses an **8px cumulative upward guard**:

- Negative deltas accumulate in `upwardDelta`.
- Any positive delta resets `upwardDelta` to zero.
- Zero-delta events preserve the current sequence.
- The nav reveals at `upwardDelta >= 8`; the existing `scrollY <= 300` top-of-page rule is unchanged.
- The existing downward hide calculation, one-time nav-height measurement, sticky positioning, and phone bottom tab bar are unchanged.

A per-event 8px comparison was rejected because slow, genuine trackpad scrolling can arrive as several 2–3px events. Cumulative uninterrupted movement filters isolated reversals without reintroducing F5's stuck-nav defect.

| File | Change |
|---|---|
| `webapp/templates/base.html` | Added `upwardDelta` and an 8px `revealDelta`; replaced the single-event `y < lastY` reveal condition with cumulative direction-aware logic. |
| `webapp/TODOS.md` | Updated the closed F5 item with the delta guard and complete cross-route evidence, closing F6's missing-sweep follow-up. |
| `STATUS.md` | Updated the shipped Fix-stage summary and evidence trail. |
| `webapp/design_reviews/ui_workstream/F5-followups-handoff.md` | This handoff. |

## Public cross-route sweep

Browser: Chromium via the Codex in-app browser, CSS viewport height 844px, device pixel ratio 1.2. Each route was checked at 390, 768, and 1280 CSS px in light and dark modes under Clean Page and Clean Layered: **12 states per route, 384 total**.

For every state the sweep checked that the route rendered the shared nav without an error marker, the requested viewport/mode/layout cookie was active, the nav and phone bottom tab bar did not intersect, and a `.main-content` document-position anchor did not move as the nav hid or appeared. The largest measured anchor movement was `0.000046px`, floating-point rounding rather than layout shift. Browser console errors: zero.

When the page had enough vertical range to hide the nav fully, the sweep ran this sequence: hide past the 300px threshold; move up 1px; confirm the nav remains hidden; move down to reset; then move upward in 2px steps until the cumulative 8px guard is reached. None of the first three steps revealed early; all qualifying states revealed at the guard. **164 of 384 states** were long enough for the full sequence. Short pages retained `top: 0` and are reported as non-exercisable, not forced longer with synthetic DOM content.

| Route state | States | Full scroll sequence | Result |
|---|---:|---:|---|
| `/` → `/contents` | 12 | 8 | Pass; redirect target confirmed. |
| `/contents` | 12 | 8 | Pass. |
| `/history` | 12 | 12 | Pass. |
| `/honours` | 12 | 0 | Pass; too short in all states. |
| `/player-rankings` | 12 | 0 | Pass; below the full-hide range in all states. |
| `/teg-reports` | 12 | 12 | Pass. |
| `/leaderboard` | 12 | 12 | Pass. |
| `/results?teg=18` | 12 | 12 | Pass. |
| `/latest-teg` | 12 | 0 | Pass; too short in all states. |
| `/latest-round?teg=18&round=4&tab=scoreboard&metric=Sc&scale=adjusted&player=DM&rewind=18&total=round` | 12 | 12 | Pass. |
| `/handicaps` | 12 | 0 | Pass; too short in all states. |
| `/records` | 12 | 0 | Pass; too short in all states. |
| `/top-performances` | 12 | 0 | Pass; too short in all states. |
| `/personal-bests` | 12 | 0 | Pass; too short in all states. |
| `/scorecard?teg=18&round=4&type=one_round_all_players` | 12 | 4 | Pass. |
| `/bestball` | 12 | 0 | Pass; too short in all states. |
| `/eclectic` | 12 | 0 | Pass; too short in all states. |
| `/eclectic-records` | 12 | 0 | Pass; below the full-hide range in all states. |
| `/player` | 12 | 4 | Pass; roster/index route. |
| `/player/DM` | 12 | 12 | Pass; representative profile. |
| `/scoring/birdies` | 12 | 0 | Pass; too short in all states. |
| `/scoring/streaks` | 12 | 0 | Pass; too short in all states. |
| `/scoring/by-par?teg=18` | 12 | 0 | Pass; too short in all states. |
| `/scoring/by-teg` | 12 | 10 | Pass. |
| `/scoring/by-course` | 12 | 12 | Pass. |
| `/scoring/all-rounds?n=100` | 12 | 12 | Pass; primary long-page stress fixture. |
| `/scoring/matrix` | 12 | 0 | Pass; below the full-hide range in all states. |
| `/scoring/distributions` | 12 | 4 | Pass. |
| `/scoring/round-distribution?range=all` | 12 | 10 | Pass. |
| `/scoring/changes` | 12 | 4 | Pass. |
| `/scoring/heatmap` | 12 | 4 | Pass. |
| `/scoring/comebacks?n=100&competition=gross` | 12 | 12 | Pass. |

### Input-level verification

The matrix used controlled small scroll steps so every route could be measured consistently. A separate Chrome DevTools wheel-input check covered the concern that F5 used only `scrollTo()` jumps:

| Viewport/layout/mode | Isolated upward wheel input | Genuine uninterrupted input | Result |
|---|---|---|---|
| 390px · Clean Layered · dark | `deltaY=-1` moved 0.83 CSS px; nav stayed at `-49px` | Five `deltaY=-2` events accumulated 8.33 CSS px; nav changed to `0px` on the fifth | Pass. |
| 768px · Clean Layered · dark | `deltaY=-1` moved 0.83 CSS px; nav stayed at `-57px` | `deltaY=-10` moved 8.33 CSS px; nav changed to `0px` | Pass. |
| 1280px · Clean Page · dark | `deltaY=-1` moved 0.83 CSS px; nav stayed at `-57px` | `deltaY=-10` moved 8.33 CSS px; nav changed to `0px` | Pass. |

Temporary viewport captures were visually inspected at 390px Clean Layered dark and 1280px Clean Page dark after genuine upward wheel input. The nav occupied its normal top band; the 390px bottom tab bar remained fully separate. No screenshots were committed because the DOM and input metrics are the reproducible evidence for this behavior-only follow-up.

This was desktop Chromium input emulation, not a physical iOS Safari run. Native elastic-overscroll behavior therefore remains unverified on-device; the handler now rejects the isolated reverse-delta pattern that motivated that concern.

## Excluded operational surfaces

Safe GET-only smoke checks covered `/admin`, `/admin/login`, `/admin/data-update`, `/admin/teg-setup`, `/admin/new-round`, `/admin/round-setup`, and `/admin/live-round` across the same widths, modes, and layouts: **84 states**.

The six protected URLs redirected to `/admin/login`; the direct `/admin/login` request rendered there. The login shell had no nav error, content jump, or bottom-tab collision. No authentication was attempted, no protected workflow was entered, and no live token or mutating endpoint was used. The protected pages themselves therefore remain unverified, as required by the public-UI scope.

## Focused automated check

```bash
/Users/jon/projects/teg/teg_v2/venv/bin/python -m pytest tests/test_webapp_pages.py -k nav_page_renders -v
```

Result: **28 passed, 47 deselected** in 1.49s. Warnings were existing dependency deprecations plus a non-failing pytest-cache permission warning. No wider suite was run because the change is one shared template's client-side scroll handler.

## Unrelated observations

The sweep recorded pre-existing page-width findings but did not change them, because they are unrelated to the delta guard:

- `/latest-round` showed the known 12px phone overflow in one sampled dark state on this base; P0 documents the broader defect and `webapp/TODOS.md` already tracks it.
- `/scorecard` showed pre-existing page overflow at 768px in all four layout/mode states. F4 already records the related shared tablet Scorecard overflow; its differing table state and measurement were not re-triaged here.
- The WIP `/scoring/heatmap` overflowed at 390px by 29–49px in three sampled layout/mode states.

No application file outside `webapp/templates/base.html` was changed. No push, merge, or deploy was performed.
