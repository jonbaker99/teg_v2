# C4 — Responsive/table contracts + three owner-assigned items

Captured 2026-09-20. Worktree: `/Users/jon/projects/teg/teg_v2/.claude/worktrees/c4-responsive-tables`;
branch: `worktree-c4-responsive-tables`.

## Base commit

**`62b68b5`** ("Merge C3: Clean Editorial Precision foundation implementation") — the tip named
by the C4 brief, used exactly as instructed. `8a93175` (STATUS/TODOS-only doc commit for C3) sits
on top of it on `main` but was not a prerequisite; branching from `62b68b5` per the brief's
explicit instruction.

## Scope

Per `webapp/design_reviews/ui-implementation-roadmap.md`'s C4 brief, plus three items the owner
assigned directly in this chat's starter prompt, beyond the roadmap's generic text:

1. Fix `.pill`/`.section-controls select`'s 40px phone defaults to the 44px touch floor.
2. Adopt `.action` (declared by C3, no call site yet) on `.rank-toggle` and History's
   `button.teg-cell` disclosure — sizing/colour only, not the open desktop-affordance decision.
3. Before/after screenshot comparison ONLY of `.main-content`'s padding/radius (shipped vs
   tokenised) — not the change itself.

## 1. `.pill`/`.section-controls select` → 44px

`mobile.css:358`/`:366` (on this base) raised `min-height: 40px` → `44px` on both. Before
touching them, grepped every page-scoped override compensating for the shortfall
(`webapp/design_reviews/ui_workstream/C3-handoff.md` had flagged this exact gap and named the
exact lines):

- `mobile.css` (Latest Round/Latest TEG/Leaderboard/Results title-area pills and selects,
  ~10 selectors, all exactly `min-height: 44px`) — **removed**, now purely redundant with the
  base default.
- `mobile.css` (`#lr-content .pill`) — kept (carries `padding-inline: 11px`, still needed) but
  dropped its now-redundant `min-height: 44px`/`font-size: 14px` (the latter also matched the new
  base default already).
- `player-profile.css` (`.pp-chart-controls .pill`, ≤640px) — **removed**, pure duplicate.

No selector was left under-compensated: every one of these already matched or exceeded 44px
before the change, so raising the shared default and removing the redundant copies is a
formality, not a rendering change, on those specific pages. It fixes the touch floor everywhere
else that relies solely on the site-wide default and had no page-scoped override.

## 2. `.action` adopted on two more controls

Added `class="action"` to:
- `.rank-toggle`'s `<button>` markup (`webapp/routes/latest.py`)
- History's disclosure `<button class="teg-cell history-toggle">` (`webapp/routes/history.py`)

Both already carry higher-specificity page-scoped selectors (an `#id`-anchored ancestor for
rank-toggle; `.history-table button.teg-cell`'s two-class-plus-type selector for History) that
continue to win the cascade for geometry — verified this holds **per CSS property**, not per
rule: `.action`'s `min-width: 44px` phone rule still leaked through for `.rank-toggle` because the
page-scoped rule never declared `min-width` at all (see §5, the regression this caused and its
fix). History's `button.teg-cell` does keep its own `color: inherit; font: inherit;` reset at
higher specificity, so the row label does not turn green from `.action`'s `color: var(--green)`.

**Net effect:** both controls now get `.action:focus-visible`'s `--focus` ring (2 classes,
beats `ui-polish.css`'s sitewide `:where(...):focus-visible` at effectively 1) instead of the
green sitewide default — the same fix C3 gave `.tab-underline`/`.seg-option`. Visual geometry is
otherwise unchanged. **History's desktop disclosure affordance is still an open owner question**
(no visible `+`/`-` above 640px, carried from C1b) — not decided here, per the brief's explicit
instruction not to decide it silently.

## 3. `.main-content` padding/radius — comparison only

Delivered as screenshots, **not applied**:
`webapp/design_reviews/ui_workstream/screenshots/C4/main-content-padding/` — 12 PNGs
(`/leaderboard` and `/records`, Clean Page light/dark at 1280px and 768px, Clean Layered light).

Method: Playwright `page.add_style_tag` injected the tokenised override
(`.main-content { border-radius: var(--r-1); padding-left/right: var(--sp-6); }`) post-load for
"after" shots only — no repo file was touched for this comparison, no `!important` (an
`!important` attempt gave a false positive by artificially beating Clean Layered's
higher-specificity selector, which a real edit never would).

**Findings:**
- **Clean Page:** visible but modest — every column shifts ~8px inward per side (40px→32px
  padding = 16px narrower card interior). Noticeable side-by-side at both 1280px and 768px, easy
  to miss in isolation. Radius 4px→3px is imperceptible in every shot.
- **Clean Layered: zero effect, confirmed both structurally and by pixel diff (byte-identical
  before/after).** `.page-panel .main-content` (clean-layered.css, specificity 0,2,0) always wins
  over the plain `.main-content` rule (0,1,0) this token swap targets — every page wraps
  `<main class="main-content">` inside `.page-panel` in `base.html`.

Owner decides; no CSS changed.

## 4. Table-contract audit

Full route sweep against the roadmap's contract (phone: compressed + protected identity +
intentional bottom nav; tablet portrait: simplified columns + clear nav; desktop: full rounds/
analysis; route-specific exceptions documented). Delegated to a lower-cost read-only agent per the
brief's "use lower-cost agents for overflow detection ... not shared-CSS decisions" instruction;
findings verified against source before acting.

| Route | Phone treatment | Verdict |
|---|---|---|
| `/leaderboard`, `/results` | Tier 2 card reflow (`lb_cards.html`), desktop table hidden | Compliant |
| `/records` | Tier 3 `<details>` disclosure rows | Compliant |
| `/player/{code}` | Tier 1 default sticky-scroll | Compliant |
| `/scorecard` | Bespoke `.sc-scroll`/`.sc-landscape` | **Gap — fixed, see §5** |
| `/latest-round`, `/latest-teg` | Tier 3 reference implementation | Compliant (reference) |
| `/scoring/by-teg`, `/matrix` | Tier 3 dense fixed-grid | Compliant |
| `/scoring/heatmap` | Tier 3 transposed table | **Gap — fixed, see §5** |
| `/scoring/distributions`, `/by-par`, `/birdies` | Tier 1 default | Compliant |
| `/scoring/changes`, `/comebacks`, `/all-rounds` | Tier 2 byline-list reflow | Compliant |
| `/scoring/streaks`, `/by-course` | Tier 1 default + weighted first column | Compliant |
| `/history` | Tier 3 dedicated (fixed layout, disclosure toggle) | Compliant |

**Noted, not acted on:** `bw-name-full`/`bw-name-short` (the explicit name-shortening helper,
`teg_analysis/display/scorecards.py:_player_name_spans`) is wired up only for bestball/eclectic
contribution bars. Every other player-name table instead relies on tier-1 sticky-scroll or tier-2
card reflow, which already protects the identity column on phone but hasn't had the shortening
pattern itself applied. Not a page-level bug, so not fixed here — flagged in
`webapp/MOBILE_PLAN.md` and `webapp/TODOS.md` as a candidate for a dedicated pass.

## 5. Two real gaps found, fixed; one regression found and fixed within this same session

**`/scoring/heatmap`, ≤390px page overflow.** Root cause was not the transposed table (the
"expected" suspect) but `.hm-legend-range`'s `white-space: nowrap` inside an unwrapped flex row
(`heatmap.css`) — confirmed via `getBoundingClientRect` diagnosis before touching anything. Fixed
in `heatmap.css` itself, inside a new `@media (max-width: 640px)` block — **not** `mobile.css`,
because `heatmap.css` is a page-specific link loaded *after* `mobile.css` in `scoring_heatmap.html`,
so an equal-specificity rule in `mobile.css` would silently lose the cascade to this file's own
unscoped `.hm-legend` rule. (First attempt did exactly that and the overflow persisted — caught
by re-measuring, not assumed fixed.)

**`/scorecard`, 768px overflow in Clean Layered.** Pre-existing, previously flagged out-of-scope
by F4 (`webapp/TODOS.md`, the "Latest Round: Scorecard tab has excess side padding" entry) because
fixing it meant touching shared `scorecard.css` beyond that chat's brief. In scope for C4.
Root cause: `.sc-landscape:not(.data-card)` (`width: fit-content; margin: 0 auto`, used for the
whole-TEG Gross+Stableford stacked view) sized itself to its *un-clipped* table content rather
than to the available column width — confirmed via ancestor-chain measurement
(`getBoundingClientRect` up the tree) showing the element's own box, not its `.overflow-x-auto`
child, was 736px against a 680px container. Fixed with `max-width: 100%` alongside the existing
`width: fit-content`. Verified: overflow gone at 768px in both modes; the title/table
joint-centering this rule exists for is pixel-unchanged at 1280px (screenshot:
`webapp/design_reviews/ui_workstream/screenshots/C4/scorecard-1280-clean-layered-light.png`); the
widest available view ("1 Player / All Rounds") still scrolls internally via
`.overflow-x-auto` rather than clipping.

**Regression, introduced by §2 and caught by this session's own verification sweep, not left for
someone else to find.** Adding `.action` to `.rank-toggle` introduced a new phone
`min-width: 44px` floor via CSS's per-property cascade rule: the page-scoped
`.latest-round-page #lr-content .rank-toggle` selector has far higher overall specificity than
`.action`, but it never declared `min-width` at all, so for that one property `.action`'s value
applied regardless — pushing the button past its narrow `.lr-toggle-td` column (37.5px at 375px
viewport vs. the button's new 44px floor) and overflowing the page by 2–13px at phone widths, in
Clean Page only (Clean Layered's extra page inset happened to absorb it). Fixed with an explicit
`min-width: 0` in the page-scoped rule — the button's 44px effective touch target already comes
from `width: 100%` filling its table cell plus a full-row-height hit area (negative vertical
margin + padding), not from being 44px wide as an element. Caught by the first full verification
sweep (12 failures, all `/latest-round`/`/latest-teg`, all Clean Page, decreasing overflow as
viewport grows — the signature of a fixed floor against a shrinking column), fixed, and confirmed
clean by a second full 200-state sweep from a fresh browser context.

## Process note: CSS cache-busting

`mobile.css`, `scorecard.css` and `player-profile.css` are served with `?v=N` query params on
their `<link>` tags. Editing the file content without bumping `N` left a live/test browser (and,
transiently, the first verification sweep) serving the stale cached version — this produced a
false 12-failure report that looked identical to the real regression above until re-diagnosed.
Bumped `mobile.css` v34→v35 (`base.html`), `scorecard.css` v25→v26 (four templates:
`scorecard.html`, `latest_round.html`, `latest_teg.html`, `eclectic.html`), `player-profile.css`
v4→v5 (`player.html`). Re-verified with a brand-new Playwright browser context (no shared cache)
afterward — 200/200 pass. `base-vars.css`'s own comment-only edit needed no bump (zero rendering
change).

## Files changed

```
webapp/MOBILE_PLAN.md                (reconciled stale claims: dark-title fixed, C4 tap-target/audit coverage noted)
webapp/routes/history.py             (class="action" on button.teg-cell)
webapp/routes/latest.py              (class="action" on rank-toggle)
webapp/static/heatmap.css            (heatmap legend overflow fix, ≤640px)
webapp/static/mobile.css             (.pill/.section-controls select → 44px; redundant compensations removed; rank-toggle min-width:0 regression fix)
webapp/static/player-profile.css     (redundant 44px pill compensation removed)
webapp/static/scorecard.css          (.sc-landscape max-width:100% overflow fix)
webapp/static/themes/base-vars.css   (.action adoption comment only — no rule change)
webapp/templates/base.html           (mobile.css cache-bust v34→v35)
webapp/templates/eclectic.html       (scorecard.css cache-bust v25→v26)
webapp/templates/latest_round.html   (scorecard.css cache-bust v25→v26)
webapp/templates/latest_teg.html     (scorecard.css cache-bust v25→v26)
webapp/templates/player.html         (player-profile.css cache-bust v4→v5)
webapp/templates/scorecard.html      (scorecard.css cache-bust v25→v26)
```

New, untracked: `webapp/design_reviews/ui_workstream/screenshots/C4/` (padding/radius comparison
+ two verification screenshots).

No `streamlit/` file touched. No `teg_analysis/` file touched (no frontend imports added or
possible — none of this session's changes are in that package).

## Verify

Local server: throwaway venv at `/tmp/teg-c4-venv` (Python 3.12.7, matching the repo's pin — local
system Python was 3.14, confirmed mismatched via `scripts/check_python_compat.py` before creating
the venv), `uvicorn webapp.app:app --port 8071`.

- **Page-level overflow, full matrix, fresh browser context (no cache):** 10 routes
  (`/leaderboard`, `/results`, `/records`, `/player/JB`, `/scorecard`, `/latest-round`,
  `/latest-teg`, `/scoring/heatmap`, `/scoring/by-teg`, `/scoring/matrix`) × 5 widths
  (320/390/430/768/1280) × Clean Page/Clean Layered × light/dark = **200/200 pass**, 0 overflow.
  (An interim run against a stale CSS cache reported 12 failures — see the process note above;
  resolved and re-confirmed clean.)
- **Scoreboard-overflow width formula (scoreboard-overflow-handoff.md) — intact.** At 390px,
  `.scale-switch` computes `width: 351px` (= 375 clientWidth − 2×12px gutter), fully inside the
  viewport.
- **F5 scroll-delta nav guard — intact.** On `/latest-round` at 1280px: nav hides to `top:-57px`
  past the 300px threshold; stays hidden through 6px of cumulative upward scroll (below the 8px
  guard); reveals to `top:0px` once cumulative upward delta reaches 9px. Matches `base.html`'s
  `threshold=300`/`revealDelta=8` exactly.
- **Console errors:** 0 on `/leaderboard`, `/records`, `/scorecard`, `/scoring/heatmap` at 1280px
  light.
- `python scripts/check_css_comments.py` — OK, 15 files scanned.
- `python scripts/check_python_compat.py` — OK, 98 files parse cleanly under the pinned 3.12.
- `python scripts/check_pandas_compat.py` — 0 errors, 26 pre-existing warnings (none touched by
  this session's changes — all in `streamlit/`/unrelated `webapp/routes` code).
- `python -m pytest tests/test_webapp_pages.py tests/test_scorecards_portrait.py -q` — **90
  passed.** Chosen over the full suite: blast radius is CSS/markup-class additions across public
  webapp templates/routes, no `teg_analysis/` core module, schema, or cross-module signature
  touched — these two files cover nav-page rendering (all touched routes) and the portrait
  scorecard variant of the file this session's largest CSS fix lives in.
- Manual screenshot spot-check: `/scorecard` at 1280px Clean Layered light (joint-centering intact
  post-fix) — `webapp/design_reviews/ui_workstream/screenshots/C4/scorecard-1280-clean-layered-light.png`.

## Unresolved / flagged for the owner

1. **History's desktop disclosure affordance** — still no visible `+`/`-` above 640px. `.action`
   now supplies its colour/focus tokens but the visual-indicator decision is untouched. Carried
   from C1b through C3 to here, still open.
2. **`.main-content` padding/radius** — comparison delivered (§3), not applied. Owner decides.
3. **`bw-name-full`/`bw-name-short` site-wide rollout** — only wired up for bestball/eclectic
   bars; other tables rely on tier-1/tier-2 protection instead. Candidate for a dedicated pass,
   not a bug.
4. **Global green focus ring** (`ui-polish.css`) — unfixed outside the (now five) touched control
   patterns, unchanged from C3's flag.
5. **`/results`' Net/Gross toggle still `.scale-switch`** — unchanged, C5's job per the roadmap.
6. **Bare `.teg-table tbody tr.top-rank`** on Records/History — unchanged, by design (C3).

## Handoff

Base `62b68b5`. This chat's resulting commit becomes the next accepted base. No merge, push, or
deploy performed.
