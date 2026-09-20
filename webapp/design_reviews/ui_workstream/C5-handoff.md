# C5 — Leaderboard rhythm/controls

Captured 2026-09-20. Worktree: `/Users/jon/projects/teg/worktrees/ui-c5`; branch: `claude/ui-c5`.

## Base commit

**`3e1d6f4`** ("C4 follow-up: tokenise .main-content padding/radius in Clean Page") — the tip
named by the C5 brief. At session start, local `main` was two commits behind `origin/main`
(`8a93175` vs. `3e1d6f4`); confirmed `3e1d6f4` on `origin/main` before branching from it.

## Scope

Per `webapp/design_reviews/ui-implementation-roadmap.md`'s C5 brief and
`gpt-ui-review.md`'s "Tighten leaderboard rhythm": compact the Leaderboard/Scorecards tab row
and the Net/Gross measure control into one zone, remove a redundant label, let the table start
sooner, and resolve C4-handoff's open item 5 (`/results` still on `.scale-switch`).

## 1. Compact control zone (base-vars.css)

Root cause, confirmed by measurement, not assumed: `.section-nav`'s `margin-bottom: 2rem` and
`.toggle-group`'s own `margin-bottom: 1rem` don't collapse against the following
`* + .section-title { margin-top: 2.5rem }` rule, because `.toggle-group` is `display: inline-flex`
(not a block box) — margins stack instead of collapsing. Net effect on `/leaderboard` and
`/results`: ~32px between the tab row and the Net/Gross control, then ~56px between that control
and the section heading, before the table even starts.

Added two new rules (base-vars.css, alongside the existing `.section-nav + .section-controls`
collapse precedent):

```css
.section-nav + .section-panel > .toggle-group:first-child {
    margin-top: -1rem;   /* 32px → 16px net gap under the tab row */
}
.toggle-group + .section-title {
    margin-top: 0;        /* rely on toggle-group's own 1rem, don't also add 2.5rem */
}
```

Both selectors are scoped tightly enough to affect only the Leaderboard/Results measure control
(verified `.toggle-group` has exactly one template call site before this chat,
`partials/leaderboard_table.html`, plus `results_table.html` after §2 below — grepped every
template first). No other page's `.toggle-group` or `.section-title` spacing changes.

Documented in `webapp/README.md`'s Structural class hierarchy table.

## 2. `/results` Net/Gross → `.segmented`

Decision: migrate, don't justify keeping `.scale-switch`. `design_principles.md`'s own toggle-
switch rule says a binary on/off switch is the wrong semantic for two equally-weighted options —
that's exactly why `/leaderboard` already moved to `.segmented` in C3. Leaving `/results` on
`.scale-switch` was an inconsistency with no remaining rationale, not a deliberate choice.

`partials/results_table.html`: replaced the standalone `<button class="scale-switch
measure-toggle">` with the same `.toggle-group > .segmented > .seg-option × 2` markup
`leaderboard_table.html` already uses (C3), ids swapped to `results-tab-input`/
`results-teg-select`. Removed the now-dead `.measure-toggle` CSS: the base-vars.css rule block
(margin + neutral track/thumb colours) and its mobile touch-target override in `mobile.css`
(`.standings-page .measure-toggle`) — `.segmented`'s `.seg-option` already gets a 44px phone/
coarse-pointer floor sitewide, so no replacement mobile rule was needed. `.scale-switch` itself,
`.switch-track`, `.switch-thumb` are untouched — still load-bearing for `/latest-round`'s Round/
TEG-total and Normal-scale toggles (genuinely binary, correctly still switches).

## 3. Redundant label

`webapp/routes/history.py` `_results_context`: `section_title` was
`f"{competition} {status_word} Leaderboard"` (e.g. "TEG Trophy Final Leaderboard"). The trailing
"Leaderboard" duplicates the page h1 outright when a TEG is in progress (h1 reads "TEG N
Leaderboard" too — literal repeated word); dropped it: `f"{competition} {status_word}"` → "TEG
Trophy Final" / "Green Jacket Latest". Grepped `tests/` and templates first — nothing asserts the
old exact string.

## Not done / explicitly out of scope

- **No new combined widget.** Tabs and the measure control stay two visually distinct rows
  (server-rendered inside the swapped partial, so the control's `aria-pressed` state never goes
  stale after an htmx swap) — just close enough together to read as one zone. Moving the
  segmented control into `.section-nav` itself (outside the swap target) was considered and
  rejected: it would need new JS to keep its state in sync with the swapped `#lb-content`, adding
  real complexity for a purely cosmetic gain the brief didn't ask for ("don't necessarily invent
  a new combined widget").
- **Gap-to-leader** — not added, per the explicit rule.
- **lb_cards / renderer unification** — untouched; that's I1.
- **Charts, backend calculations** — untouched.
- **Phone table behaviour** — untouched and reverified identical (the `.standings-page` dense
  reflowed table, not `lb_cards`, still renders on both routes at ≤640px — same as before this
  chat).
- **History's desktop disclosure affordance / `bw-name-full` rollout** — untouched, per the
  brief; still open from C4.

## Files changed

```
webapp/README.md                          (Structural class hierarchy table entry for the two new rules)
webapp/routes/history.py                   (section_title: dropped redundant "Leaderboard")
webapp/static/mobile.css                   (removed dead .standings-page .measure-toggle block; cache-bust v35→v36)
webapp/static/themes/base-vars.css         (compact control zone rules; removed dead .measure-toggle block; cache-bust v33→v34)
webapp/templates/base.html                 (base-vars.css/mobile.css cache-bust bumps)
webapp/templates/partials/results_table.html  (.scale-switch → .segmented, matching /leaderboard)
```

No `streamlit/` file touched. No `teg_analysis/` file touched.

## Verify

Local server: scratchpad venv (Python 3.12.14, matching the repo's pin — system Python is 3.14,
confirmed mismatched via `scripts/check_python_compat.py` before creating the venv),
`uvicorn webapp.app:app --port 8091`.

- `python scripts/check_css_comments.py` — OK, 15 files scanned.
- `python scripts/check_python_compat.py` — OK, 98 files parse cleanly under the pinned 3.12.
- `python scripts/check_pandas_compat.py` — 0 errors on touched files (pre-existing warnings
  elsewhere, unrelated to this session).
- `python -m pytest tests/test_webapp_pages.py -q` — **75 passed.** Chosen over the full suite:
  blast radius is CSS rhythm + one template's control markup + one display-string edit across
  `/leaderboard`/`/results`, no `teg_analysis/` core module or schema touched — this file covers
  every touched route's rendering.
- Playwright, fresh browser context, both routes: 1280px, 768px, 390px; light, dark, Clean
  Layered; `/leaderboard` and `/results` (five-player TEG 18, historical five-player TEG 2 with a
  3-round layout, tied-score formatting); Net↔Gross click (htmx swap updates `aria-pressed` and
  the section heading correctly); Scorecards tab (measure control correctly disappears —
  conditional stayed inside the swapped partial, so this needed no new logic); an unknown `teg`
  query param (falls back to the default TEG, unchanged existing behaviour). Console: 0 errors on
  either route beyond the pre-existing Tailwind-CDN-in-production warning and a missing-favicon
  404, both unrelated.
- **No real eight-player TEG exists in the data** (max is six, TEGs 7–10/12/15) — verified via
  `cached_round_data()` player counts. Verified the six-player TEGs instead as the closest
  available "wide" case; the control-zone/rhythm change is layout-independent of player count
  either way (it only affects the two control rows above the table, not table width).

## Handoff

Base `3e1d6f4`. This chat's resulting commit becomes the next accepted base for C6. No merge,
push, or deploy performed.
