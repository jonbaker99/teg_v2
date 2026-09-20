# F5 — restore navigation on long pages

Captured 2026-09-20. Starting base: `49a134c` (accepted F4 commit, F1+F2+F3+F4 integrated). Worktree: `/Users/jon/projects/teg/worktrees/ui-f5`; branch: `claude/ui-f5`. The tree was clean at entry. The final response supplies this handoff's resulting commit SHA.

F5 was scoped to fix long-page public navigation persistence: the shared `.nav` slides off screen past a scroll threshold and, per P0's confirmed baseline finding, did not reliably reappear on upward scroll. Lead model: Sonnet 5 (the session default). No switch to a higher-reasoning lead was needed — the root cause was a single, unambiguous logic defect in a ~20-line scroll handler, not an architectural or cross-cutting decision; flagging this explicitly per the task's instruction rather than switching pre-emptively.

## Root cause

`webapp/templates/base.html`'s sticky-nav IIFE (originally lines 212–229) measured `nav.offsetHeight` once at load and, on every `scroll` event, set the nav's `top` offset purely as a function of **absolute `scrollY`** past a 300px threshold:

```js
var offset = Math.min(y - threshold, navHeight);
nav.style.top = -offset + 'px';
```

Because `navHeight` (49–57px) is far smaller than the threshold, once `scrollY` exceeds `threshold + navHeight` (~349–357px) the nav is fully hidden (`offset` clamped to `navHeight`) and **stays** fully hidden for any `scrollY` above that point — including while scrolling back up — until `scrollY` drops back below `threshold + navHeight`. This exactly matches P0's confirmed reproduction: scroll to 900, back to 650, nav stays at `top:-49px`/`-57px` even though 650 < 900 (a clear upward scroll).

The handler never looked at scroll *direction*, only absolute position.

## Fix

| File | Change |
|---|---|
| `webapp/templates/base.html` | Added a `lastY` variable tracking the previous `scrollY`. On each scroll event, computed `scrollingUp = y < lastY` before updating `lastY`. The show condition became `y <= threshold \|\| scrollingUp` (was `y <= threshold`) — any upward movement shows the nav immediately (`top:0`), regardless of absolute scroll position. The downward-hide branch (`offset = min(y - threshold, navHeight)`) is unchanged. |

The existing one-time `navHeight` measurement and the 300px threshold were inspected and left as-is — the roadmap's rule was to inspect before changing, and neither needed to change to fix the direction bug. No resize listener was added: `navHeight` was already only measured once at load before this chat, so recomputing it on resize is a pre-existing gap, not a regression introduced here (see Unresolved).

## Verification

Ran locally from this worktree:

```bash
cd /Users/jon/projects/teg/worktrees/ui-f5
/Users/jon/projects/teg/teg_v2/venv/bin/python -m uvicorn webapp.app:app --host 127.0.0.1 --port 8125
```

Same runtime caveat as P0–F4: available interpreter is Python 3.14.7, while `.python-version` pins 3.12. UI verification only, not deployment-runtime compatibility.

**Focused test:**
```
python -m pytest tests/test_webapp_pages.py -k 'nav_page_renders' -v
```
27 passed, 0 failed. Shared-shell CSS/JS change (not a shared/core `teg_analysis` module or cross-module schema), scoped to one template's scroll script — no wider suite run, matching CLAUDE.md's blast-radius guidance.

**Browser verification (Playwright, Chromium):**

| Check | Route(s) | Width | Mode | Result |
|---|---|---|---|---|
| P0's exact reproduction: scroll to 900, back to 650 | `/scoring/all-rounds?n=100` | 390px | light | Fixed: `nav.style.top` = `0px` (was `-49px`) |
| Same scroll sequence | `/records` | 768px | light | Fixed: `top` = `0px` (was `-57px`) |
| Same scroll sequence | `/records` (via `/scoring/all-rounds`) | 1280px | dark | Fixed: `top` = `0px`, no overlap with `.main-content` |
| Down-scroll hide still works (regression) | `/scoring/all-rounds?n=100` | 390px | light | `scrollY=900` from top → `top:-49px` (fully hidden), unchanged |
| Long-page scroll on a shorter page (`/latest-round`, max scroll 507px) | `/latest-round` | 1280px | light | Initial `scrollTo(0,900)`→`650` both clamp to the same 507px max-scroll point (no direction change, correctly no-op); re-tested with an in-range 500→300 scroll: nav shows at `top:0` — confirms the fix generalizes and the flat result at the first attempt was a test-fixture artifact (page too short), not a defect |
| `resize` event mid-hide | `/scoring/all-rounds?n=100` | 390px | light | Dispatching `resize` while hidden, then scrolling up, still shows nav at `top:0` — no crash/stuck state |
| Phone bottom tab bar unaffected | `/scoring/all-rounds?n=100` | 390px | light | `.mobile-tabbar` unchanged: fixed at viewport bottom (`y:787`, `height:57`), independent of `.nav`'s sticky-top logic |
| Console errors | All routes/widths above | — | light/dark | 0 errors; only the pre-existing favicon 404 (first load) and Tailwind production-CDN warning, consistent with P0–F4 |

Content jump: `.nav` remains `position: sticky`; changing its own `top` offset does not add or remove document flow height, so no layout shift was observed or expected — confirmed visually in the screenshots below.

HTMX swaps: the nav element and its scroll listener live outside every route's `hx-target` (`#lr-content`, `#records-content`, etc.); an HTMX partial swap doesn't touch or re-run the nav script, so behavior is unaffected by tab switching. Not independently re-tested with a live HTMX click in this chat beyond the pages already exercised (F1–F4 covered HTMX swap regressions extensively for their own scope); no interaction between this fix and HTMX swaps is expected since the two systems don't share DOM or listeners.

Screenshots: `webapp/design_reviews/ui_workstream/screenshots/F5/` —
- `f5-nav-up-390-light-after.png` — `/scoring/all-rounds?n=100`, 390px, light, after scroll-to-900-then-650: nav visible at top
- `f5-nav-up-768-light-after.png` — `/records`, 768px, light, same sequence
- `f5-nav-up-1280-dark-after.png` — `/scoring/all-rounds?n=100`, 1280px, dark, same sequence

## Rules followed

- Inspected the existing one-time nav-height measurement and 300px threshold before changing anything; neither was altered.
- No navigation redesign; no markup, CSS, or route changes — a four-line JS logic change to the existing scroll handler only.
- Phone bottom tab bar (`.mobile-tabbar`) not touched; confirmed unaffected.
- No admin or operational route touched; this is a shared-shell (`base.html`) change affecting every route by construction, as flagged in P0/roadmap, but the change itself only alters *when* the nav is visible, not any admin-specific behavior.
- Lead (this chat) owned the shared-shell edit directly — a four-line, single-root-cause fix was cheaper to write and verify directly than to scope and hand off, matching F1/F2/F4's precedent for small, tightly-bounded patches. No subagent was used for the browser/scroll matrix either, for the same reason.
- No lead-model change: flagged per the task's instruction that Sonnet was sufficient, with the reasoning above, rather than switching to Opus pre-emptively.

## Unresolved / explicitly out of scope

- `navHeight` is still measured once at page load and never recomputed on resize/orientation change. If the nav's own height changes after load (e.g. a hamburger-menu breakpoint change on resize), the hide-offset clamp could be stale. This is a pre-existing characteristic of the script, not introduced by this fix, and no defect from it was observed in the resize check above — flagging for a future pass if it's ever seen to cause a visible bug.
- In-page section navigation (e.g. `.section-nav` tab strips) was not found to interact with the primary `.nav` sticky logic — they are separate elements with separate scroll/positioning concerns; no cross-effect observed or expected.
- No new automated scroll-behavior test was added (P0–F4 precedent: this class of check is verified manually/programmatically via Playwright each time, not via a new test file); the workstream's general test-coverage gap still stands.

## Handoff

This chat's resulting commit is the accepted integration base for F6 (Fix review gate), which reviews the combined F1–F5 diff read-only. No push, merge, or deploy performed.
