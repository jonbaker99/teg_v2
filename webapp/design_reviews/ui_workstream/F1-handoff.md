# F1 — repair the two small visual defects

Captured 2026-09-20. Starting base: `bee432a42c855029681471edaab246866aef318b` (accepted P0 handoff commit). Worktree: `/Users/jon/projects/teg/worktrees/ui-f1`; branch: `codex/ui-f1`. The tree was clean at entry. The final response supplies this handoff's resulting commit SHA; use that SHA as F2's/F3's/F4's base once integrated.

F1 fixes exactly two confirmed public UI defects: the missing `+`/`-` rank-toggle glyph and zero-size hit area above 640px on `/latest-round` and `/latest-teg`, and dark-mode page-title contrast for `title_style=e2`. No redesign, no other defect touched. Lead performed the diagnosis, both CSS edits, and all verification directly (both patches were two small, tightly-scoped CSS blocks — cheaper to write than to hand off and review, so no worker delegation was used). No lead-model change was needed.

## Root causes

**Rank toggle.** `webapp/static/mobile.css` scopes its entire stylesheet inside `@media (max-width: 640px)` by explicit design (its own header comment says every rule sits there except the `display:none` mobile-markup hooks). The `.rank-toggle` glyph (`::after` content: `"+"`/`"\2013"`) and its sizing were defined only inside that block, so above 640px the `<button>` had no content and no explicit box model — it rendered as a genuinely empty, unstyled button and collapsed to 0×0 (matching P0's exact finding at 641px). `base-vars.css:373` already documents the established pattern for this: a mobile.css-only rule needs a separate desktop-scoped counterpart, "kept separate since that file is entirely inside that query" (the same split `table.leaderboard` itself already uses).

**Dark title.** `webapp/static/themes/clean-page.css` hard-codes `body.ts-e2 .page-title-outer { background: #ffffff; }` with no dark-mode override; `webapp/static/themes/clean-layered.css` hard-codes `body.ts-e2 .page-title-area { background: #f5f3f0; }`, also with no dark-mode override. The title text itself uses `var(--text-primary)`, which `dark.css` re-points to a pale `#ececea` in dark mode. Every other title style (including the default, `a`) leaves `.page-title-area` transparent over `--bg-page`, so this hard-coded light surface under `e2` was the only variant affected — confirmed against P0's finding that the default style is readable and only `e2` fails.

## Fix

| File | Change |
|---|---|
| `webapp/static/themes/base-vars.css` | Added an unconditional `.rank-toggle` rule (glyph `::after` content + 28×28px min hit area, padding, accent colour) scoped to `.latest-round-page #lr-content` / `.latest-teg-page #lt-content`, placed directly after the existing `table.leaderboard` desktop/mobile-split comment it mirrors. |
| `webapp/static/themes/dark.css` | Added `html[data-mode="dark"] body.ts-e2 .page-title-outer, html[data-mode="dark"] body.ts-e2 .page-title-area { background: #16150f; }`, matching the near-black value `.main-content` already resolves to in dark mode elsewhere in this file. |

`mobile.css`'s existing phone-width `.rank-toggle` rule (44px hit area, negative-margin overlay) is untouched and still wins at ≤640px by cascade order — it loads after `base-vars.css`. No template, route, or JS changes; markup and `aria-expanded` behaviour are unchanged.

## Verification

Ran locally from this worktree:

```bash
cd /Users/jon/projects/teg/worktrees/ui-f1
/Users/jon/projects/teg/teg_v2/venv/bin/python -m uvicorn webapp.app:app --host 127.0.0.1 --port 8121
```

Same runtime caveat as P0: available interpreter is Python 3.14.7 / pandas 3.x wheel present, while `.python-version` pins 3.12. This establishes the UI fix on this checkout, not deployment-runtime compatibility.

**Focused tests** (as specified for F1 in `P0-handoff.md`):
```
python -m pytest tests/test_webapp_pages.py -k 'latest_round or latest_teg' -v
```
17 passed, 0 failed. CSS-only change; no template/route logic touched, so no wider suite run — matches CLAUDE.md's blast-radius guidance.

**Browser verification (Playwright, Chromium):**

| Check | Route(s) | Width | Layout | Mode | Result |
|---|---|---|---|---|---|
| Rank-toggle glyph + size | `/latest-round`, `/latest-teg` | 641px | Clean Page | light | `+` glyph, 28×28px button (was 0×0) |
| Rank-toggle click | `/latest-round` | 641px | Clean Page | light | `aria-expanded` flips `false→true`, glyph flips `+`→`–` |
| Rank-toggle glyph + size | `/latest-round`, `/latest-teg` | 1280px | Clean Page | light | `+` glyph, 28×28px |
| Rank-toggle glyph + size | `/latest-round` | 641px | Clean Layered | light | `+` glyph, 28×28px |
| Rank-toggle unaffected | `/latest-teg` | 390px | Clean Page | light | unchanged: 44px-tall hit area, `min-height:44px` from `mobile.css`, glyph still renders |
| Dark title fixed | `/records`, `/scoring/streaks` | 1280px | Clean Page | dark, `title_style=e2` | `.page-title-outer` background `rgb(22,21,15)` (was `#fff`); title `rgb(236,236,234)` — readable |
| Dark title fixed | `/scorecard`, `/contents` | 1280px | Clean Page | dark, `title_style=e2` | same background fix; `/contents` confirmed to have no `.page-title` element (regression check only, no defect there) |
| Dark title fixed | `/records` | 1280px, 390px | Clean Layered | dark, `title_style=e2` | `.page-title-area` and `.page-title-outer` both `rgb(22,21,15)`; title readable |
| Dark title regression check | `/records` | 1280px | Clean Layered | dark, `title_style=a` (default) | unchanged: `.page-title-area` stays transparent, title still readable — confirms the fix is scoped to `e2` only |
| Dark title regression check | `/records` | 1280px | Clean Layered | **light**, `title_style=e2` | unchanged: light band `rgb(245,243,240)`, dark text — confirms the dark-mode-only scoping doesn't touch light mode |

Console: 0 errors on every page checked (1 recurring warning is the pre-existing Tailwind production-CDN notice, already noted in P0).

Screenshots: `webapp/design_reviews/ui_workstream/screenshots/F1/` — `f1-streaks-e2-1280-dark-after.png`, `f1-records-e2-layered-1280-dark-after.png`. Most checks above were measured programmatically (bounding box, computed style, `aria-expanded`) rather than screenshotted individually; the two screenshots are representative visual evidence for the dark-title fix under both layouts.

## Rules followed

- No heading/table redesign; both patches are narrowly scoped CSS additions using existing tokens (`var(--accent)`, the dark-mode near-black already used elsewhere).
- No excluded operational surface touched; no template, route, or JS edited.
- `mobile.css` was read but not edited — its stated invariant ("every rule inside the media query except display:none hooks") stays true; the desktop counterpart lives in `base-vars.css` per the pattern that file already documents for exactly this situation.
- Both registered Clean-family layouts (Clean Page, Clean Layered) verified working, light and dark.

## Unresolved / explicitly out of scope

- Records overflow (F2), Latest Round Scoring/Streaks/Records/Scorecard phone layouts (F3/F4), navigation persistence (F5), and the documented Scoreboard 12px overflow at 390px remain untouched, per the roadmap's F1 scope and P0's explicit instruction not to fold the Scoreboard finding into F1.
- Tablet width (768px) was not separately measured for the rank toggle beyond 641px/1280px; both sit on the same side of the only relevant breakpoint (640px), so no distinct behaviour is expected, but it wasn't screenshotted.
- No dedicated automated test exists for the glyph/contrast checks (P0 already noted this gap); verification here was manual/programmatic via Playwright, not a new test file — adding one was judged out of scope for a two-defect fix chat.

## Handoff

Proceed to F2 (Records overflow) and F3 (Scoring/Streaks) from this handoff's resulting commit SHA per the roadmap's integration order (`F1 → F2 → F3 → F4 → F5`); both may branch from P0's base or this commit per the roadmap ("F1/F2/F3 investigation only" in parallel, "sequence shared CSS writes"). This chat did not push, merge, or deploy.
