# C3 — Clean Editorial Precision: foundation implementation

Captured 2026-09-20. Worktree: `/Users/jon/projects/teg/worktrees/ui-c3`; branch: `claude/ui-c3`.

## Base commit

**`e9c999c`** (C1b's tip, `claude/ui-c1b`) — used exactly as instructed, not rebased.

Coordination check performed before branching: `git log --oneline main` (tip `e50078d`, the Fix-stage merge) and `git branch -a` were inspected for the two parallel chats named in the starter prompt.

- **Codex's Scoreboard-overflow fix** (`codex/latest-round-scoreboard-overflow`, `17f8d6d`, touching `.latest-round-page #lr-content .scale-switch` in `mobile.css`) — confirmed **not merged into `main`** (`git merge-base --is-ancestor 17f8d6d main` → false).
- **Codex's F5 nav-script extension** (`codex/f5-scroll-delta-sweep`, extending `base.html`, commit `e2a03bc` "Guard sticky nav scroll direction") — also confirmed **not merged into `main`**.
- `main`'s tip (`e50078d`) is a direct ancestor of `e9c999c` (`git merge-base e9c999c main` → `e50078d`), confirming C1b's own claim: it touched zero application code, so a rebase onto `main` would have been free — but since neither parallel branch is merged, `main` is not a superset of anything C3 needs, and the instruction's fallback condition ("if either is merged") never triggered. Proceeded from `e9c999c` directly, as instructed.
- Before touching `.scale-switch`, read `git show 17f8d6d -- webapp/static/mobile.css`: it changes `.latest-round-page #lr-content .scale-switch`'s width from `100%` to `calc(100% - 2 * var(--lr-inset))`. **C3 does not touch `.scale-switch` or that selector at all** (it's out of the three proving-ground pages), so nothing here was at risk of silently reverting that unmerged fix — noted only for the next chat that does touch it.

## Scope actually implemented

Per the roadmap's C3 brief plus C1/C1b's specifications. Nothing here was relitigated — every design decision was already made by the owner in C1/C1b.

### 1. Foundation tokens

Declared in `webapp/static/themes/clean.css`'s `:root` (confirmed on this base: `base-vars.css` still declares **zero** custom properties — C1's finding held), with dark counterparts in `dark.css`:

- **Type scale**: `--fs-100` (11px) through `--fs-700` (36px). `--fs-500` (20px) is declared, unused — reserved, no component needs a third heading level (C1 §3).
- **Spacing ramp**: `--sp-1` (4px) through `--sp-7` (48px).
- **Radius**: `--r-0` (0), `--r-1` (3px), `--r-2` (6px).
- **Rules**: `--rule-color` (new — same value as `--table-cell-border`), `--rule-hair`, `--rule-strong`, `--rule-inset`.
- **Shadow**: `--shadow-card` (Clean Layered `.data-card` only).
- **Semantic colour**: `--ink`/`--ink-2`/`--ink-muted` (corrected darker value, `#6f6f6f`/`#9c9a8f`), `--green` (forestgreen, unchanged value), `--focus` (`= var(--ink)`, C1b F3), `--success`/`--warning`/`--failure`, `--hover-bg` (alias of `--table-hover-bg`), `--leader-tint`/`--leader-tint-hover` (C1b L2, replacing `--sand` — `--sand` does not exist anywhere in this implementation), `--bg-content` (restored white content card, distinct from `--bg-panel`).

These are a **new parallel token set**, not a rename of `--text-primary`/`--text-muted`/`--accent`/`--bg-card` — those remain live for every component this chat didn't touch. No mechanical global font-size or colour replacement was performed.

### 2. Heading consolidation

`.section-title`, `.card-header`, `.chart-title` (previously three byte-identical blocks at `base-vars.css:1393`, `:1517`, `:1638` on the base commit) merged into one shared rule (now near the original `.section-title` location). `.card-header`'s larger top margin (`2.5rem`) is the one preserved difference, restated as a small override rule rather than duplicated properties. Font size stays literal `13px` (not migrated to `--fs-300`, per C1 §9). Colour changed from `var(--accent, #17683c)` to `var(--green, var(--accent, #17683c))` — same forestgreen value, the named exception from C1 §5 (headings keep green even though green now means "active selection" everywhere else). Zero template churn — no template references these classes by anything other than name, and the names didn't change.

### 3. Semantic colour roles — applied

- `--ink-muted`'s darker value is live wherever a component now reads it (declared, available site-wide via the token; not force-applied to every existing `--text-muted` call site — that would be the mechanical global replacement the brief prohibits).
- **Leader row (L2, the owner-selected fix)**: implemented, scoped to `.leaderboard-table tbody tr.top-rank` / `tr.top-rank:hover` in `base-vars.css` — **not** the bare `.teg-table tbody tr.top-rank` rule, which is used site-wide (Records, History, …) and stays on the old flat `--table-toprank-bg` colour. This is a deliberate scoping decision, not an oversight: C1's own affected-selector list (§10) assigns the leader-row retint to C5, but C1b's proving-ground description explicitly names "the leader-row fix" as something `/leaderboard` exercises — so it's implemented now, scoped narrowly enough not to touch any untouched page. **Flagged side effect**: `.leaderboard-table` is also the class `/results` renders through (`_leaderboard_table_html` in `webapp/routes/history.py`, shared by both routes via `_results_context`), so `/results` gets the same fix. This is intentional — same table shape, same bug — not scope creep, and it was checked, not missed.
- Specificity (load-bearing, per C1b §6): `.leaderboard-table tbody tr.top-rank:hover` (3 class-level selectors) beats both the bare `.top-rank` rule (1) and the generic `.teg-table tbody tr:hover` rule (1) by class count alone, regardless of source order. Verified in the browser (see Verify below).
- `--focus` applied to the three touched control patterns (`.tab-underline`, `.seg-option`, `.action`) only — **not** the sitewide `:where(a,button,select,input):focus-visible` rule in `ui-polish.css`, which still resolves green. That broader fix is out of scope for a smallest-representative-set chat; flagged for whoever picks it up next.

### 4. Three control patterns

- **`.segmented`/`.seg-option`** — new, activates the previously-dead `.toggle-group`. Implemented exactly per the owner-approved mockup (`mockups/c1b-segmented.html`, "approved as mocked, no change requested") — geometry, hover, focus and `aria-pressed` selected-state all copied from that file, not reinvented. Applied to `/leaderboard`'s Net/Gross measure (`partials/leaderboard_table.html`), replacing `.scale-switch.measure-toggle`. **`/results`' identical Net/Gross toggle (`partials/results_table.html`) was left unconverted** — same markup pattern, not touched, since C1's migration order assigns that page to C5; the underlying `.scale-switch`/`.measure-toggle` CSS rules were left fully intact so `/results` keeps rendering exactly as before.
- **`.action`** — new, declared with the approved geometry (28px desktop / 44px touch, `--green` text, `--focus` ring). **No live call site among the three proving-ground pages** — `.rank-toggle` (Latest Round) and History's `button.teg-cell` disclosure, the two production instances C1/C1b's mockups target, are both outside `/leaderboard`/`/records`/one player-profile page. Declared for C4/C5 to apply without redefining the geometry. This is a deliberate scope decision, not a gap: inventing an `.action` call site on a page that doesn't have one would be exactly the "redesign page-specific content beyond what's specified" the brief prohibits.
- **`.pp-tab` folded into `.tab-underline`** — `webapp/templates/player.html`'s profile tabs now carry `.tab-underline`/`.tab-underline--active` instead of `.pp-tab`/`.pp-tab--active`; `webapp/static/player-profile.js`'s `htmx:afterSwap` handler updated to toggle the same class name. `.pp-tab`/`.pp-tab--active` CSS rules removed from `player-profile.css` (comment left pointing at the shared rule). **Double-fire risk checked, not just assumed**: `.pp-tabs` already carries `.section-nav` in the template, so `base.html`'s global `.section-nav .tab-underline` click handler now also fires on profile-tab clicks, optimistically setting `.tab-underline--active` immediately on click, ahead of `player-profile.js`'s own `htmx:afterSwap` handler. Both agree on the same final state after a successful swap (confirmation, not conflict) — this is the same behaviour every other HTMX-driven `.tab-underline` bar on the site already has (leaderboard tabs, records tabs), not a new risk introduced by the fold. Verified live: see Verify below (check C).
- **Phone 2-column grid preserved** — `.pp-tabs`' `display: grid; grid-template-columns: 1fr 1fr` phone override (player-profile.css, ≤640px) was left in place. C1 flagged this layout as a divergence "with no reason to diverge," but that's a responsive-layout call, not typography/colour — out of C3's "don't redesign page-specific content" boundary. The buttons inside it now pick up standard `.tab-underline` phone typography (uppercase, tracked, 44px) automatically, so only the container's column layout still differs.

### 5. `.rank-toggle` 44px contract — documentation fix

`webapp/design_principles.md` corrected: added a "Hit areas: two-tier, not a flat 44px minimum" subsection stating the real contract (`pointer: coarse`/≤640px → 44×44px; ≥641px → 28px icon-only / 36px labelled) and noting the shipped F1/F6b desktop `.rank-toggle` (28×28px) was already compliant — the doc was wrong, not the code. No CSS changed for this item; it's a docs-only fix per the brief.

### 6. Small cleanups (owner-approved in C1's decision review)

- **Twelve dead `ts-*` page-title CSS blocks deleted** from `base-vars.css` (Style B, C, D, E, E2, C1, C2, C3, and F1–F5's viewport-width override + band styling — roughly 165 lines total across two contiguous ranges). Verified no remaining references (`grep` for every `ts-b`/`ts-c*`/`ts-d`/`ts-e*`/`ts-f*` class came back empty after deletion). The cookie/route machinery that could theoretically still set these body classes (`webapp/theme.py`, design-lab route) was left untouched — out of scope; those classes now simply fall back to the default Style A treatment if ever selected.
- **Glyph-rule duplication fixed** — the `.rank-toggle` "+"/"−" `::after` content rules were duplicated verbatim in `base-vars.css` (desktop, `@media (min-width: 641px)`) and `mobile.css` (phone, implicitly `@media (max-width: 640px)` via that file's whole-file scoping). Since the glyph content doesn't vary by width, it's now declared once, unscoped, in `base-vars.css`; both files' media-scoped rules keep only sizing.
- **`#16150f` hard-code fixed** in `dark.css` — the three literal occurrences (`body.page-bg`, `.page-panel`/`.main-content`, `body.ts-e2` title override) now read `var(--bg-page)`, which resolves to the same `#16150f` declared in that file's own `:root` block. Zero visual change; a future dark-page-colour change now only needs one edit.

## The `--sp-6` vs literal 40px content-card padding decision

**Decision: kept the literal 40px (`2.5rem`)**, did not switch to `--sp-6` (32px). `.main-content`'s background now reads `var(--bg-content)` (same `#ffffff` value, tokenised); `border-radius`, `box-shadow`, `margin`, and `padding-left`/`padding-right` were left as their existing literal values.

Reasoning: `--r-1` (3px) also doesn't match the card's existing `0.25rem` (4px) radius, so switching either dimension would introduce an unflagged 1px-or-8px shift beyond what either handoff explicitly authorized (only the padding question was called out as open; the radius mismatch wasn't discussed at all). C3's brief is to preserve existing rendering while declaring tokens, not to silently tighten spacing on every proving-ground page. If the owner wants the 32px/3px tightening, it's a one-line change in `clean-page.css`'s `.main-content` rule (and the equivalent in `clean-layered.css` if desired) — left for C5 or an explicit follow-up, not decided here by default.

## Migration notes for C4/C5

- **C4** (responsive/table contracts): `.pill` and `.section-controls select`'s 40px phone defaults still need raising to 44px (`mobile.css:358`, `:366` on this base) — noted in the design_principles.md fix but not touched here. `.action` is declared and ready for `.rank-toggle`/History's `button.teg-cell` disclosure to adopt.
- **C5** (leaderboard rhythm): `/results`' Net/Gross toggle (`partials/results_table.html`) still uses `.scale-switch.measure-toggle` — convert to `.segmented` following the exact pattern already applied to `partials/leaderboard_table.html` in this chat. The bare `.teg-table tbody tr.top-rank` rule (Records, History, other tables) still uses the old flat `--table-toprank-bg` — if C5 wants the L2 tint site-wide rather than leaderboard/results-only, that's a value change to `--table-toprank-bg` itself (or a broader selector), not something this chat pre-wired.
- **Global focus-ring bug** (`ui-polish.css`'s `:where(...):focus-visible` still green sitewide) is unfixed outside the three touched control patterns — a candidate for a dedicated pass, not silently assumed fixed.
- **`--shadow-card`** is wired into Clean Layered's `.data-card` only, as specified. Clean Page's `.main-content` shadow (`0 1px 4px rgba(0,0,0,0.08)`) has no token — it's a different value from `--shadow-card` and C1's spec only names one shadow token for one surface.

## Files changed

```
webapp/design_principles.md                        (44px doc correction)
webapp/static/mobile.css                            (rank-toggle glyph dedup)
webapp/static/player-profile.css                    (.pp-tab rules removed)
webapp/static/player-profile.js                     (.pp-tab-active → .tab-underline--active)
webapp/static/themes/base-vars.css                  (heading merge, .segmented/.action, leader-row, dead CSS deletion, glyph dedup, --focus on .tab-underline)
webapp/static/themes/clean-layered.css              (--bg-content override, --shadow-card wiring, cache-bust)
webapp/static/themes/clean-page.css                 (.main-content → --bg-content, cache-bust)
webapp/static/themes/clean.css                      (foundation token declarations)
webapp/static/themes/dark.css                       (foundation token dark counterparts, #16150f fix)
webapp/templates/base.html                          (CSS cache-buster bumps)
webapp/templates/partials/leaderboard_table.html    (.scale-switch → .segmented for Net/Gross)
webapp/templates/player.html                        (.pp-tab → .tab-underline, cache-bust)
```

No `streamlit/` file touched. No frontend imports added to `teg_analysis/`.

## Verify

Playwright matrix (throwaway venv, same pattern C1/C1b used — this checkout's interpreter doesn't carry `requirements-dev.txt`'s pin): `/leaderboard`, `/records`, `/player/JB` × 390/768/1280px × light/dark × Clean Page/Clean Layered = 36 combinations, viewport height 900, `networkidle` + 300ms settle.

- **Page-level overflow**: `document.documentElement.scrollWidth <= clientWidth` (1px tolerance) asserted at all 36. **0 failures.**
- **Leader row, rest vs hover** (`/leaderboard`, net tab, light/Clean Page/1280px): `.leaderboard-table tbody tr.top-rank`'s computed background is `rgb(228, 239, 228)` (`--leader-tint`) at rest, `rgb(201, 224, 201)` (`--leader-tint-hover`) on hover — **distinct, and darker, not lighter or flat**, confirming the L2 fix (and its specificity) actually renders correctly, not just parses correctly.
- **Focus ring on a selected (green) segment** (`/leaderboard`'s Net/Gross `.seg-option[aria-pressed="true"]`): focused outline is `solid 2px rgb(26, 26, 26)` (`--ink`/`--focus`) — clearly distinct from both the segment's green text and its light-green `--hover-bg` background. Confirms C1b's F3 decision actually resolves the green-on-green collision it was chosen to fix, not just in the mockup.
- **`.pp-tab` fold double-fire** (`/player/JB`): clicked the non-active "Rounds" tab, waited for the HTMX swap. Result: exactly one button (`Rounds`) ends up with `.tab-underline--active` and `aria-pressed="true"`; `Overview`/`Scoring`/`Records & Streaks` all correctly reverted to inactive. **No double-fire** — the global `base.html` handler and `player-profile.js`'s own handler agree on the same final state, as predicted above.
- **Console/page errors**: none on `/leaderboard`, `/records`, `/player/JB` at 1280px light/Clean Page.
- **Screenshots**: 36 PNGs saved to `webapp/design_reviews/ui_workstream/screenshots/C3/` (`<page>-<width>-<mode>-<layout>.png`).

## Checks run

- `python scripts/check_css_comments.py` — OK, 15 files scanned, no orphan `*/`.
- `python scripts/check_python_compat.py` — OK, 98 files parse cleanly under the pinned 3.12.
- `python -m pytest tests/test_webapp_pages.py -q` — **75 passed**. Chosen over the full suite: this chat's blast radius is CSS/two templates/one JS file touching `/leaderboard`, `/records`(nav-only, unchanged content), `/player`, and shared theme files — `test_webapp_pages.py` covers nav-page rendering (including `/leaderboard`, `/records`) and the full `/player` route surface (overview/rounds/scoring/records tabs, empty states, missing-handicap edge case). No `teg_analysis/` core module, schema, or cross-module signature changed, so the full suite wasn't warranted per `CLAUDE.md`'s blast-radius rule.
- Manual route smoke test (`curl`, all 200): `/leaderboard`, `/records`, `/player`, `/player/JB`, `/latest-round`, `/scorecard`, `/teg-reports`.
- Playwright screenshot/interaction matrix: see Verify section above once filled.

## Unresolved / flagged for the owner

1. **`--sp-6` vs 40px padding** — resolved by this chat's own decision (kept 40px); revisit if the tighter 32px is preferred (see above).
2. **`.data-card`/`.main-content` border-radius** (4px literal, matches neither `--r-1` 3px nor `--r-2` 6px) — not flagged in either prior handoff, not changed here; a candidate for an explicit radius decision alongside the padding one.
3. **Global green focus ring** (`ui-polish.css`) — unfixed outside the three touched patterns.
4. **`/results`' Net/Gross toggle** — still `.scale-switch`, not yet `.segmented` (C5's job, pattern already proven on `/leaderboard`).
5. **Bare `.top-rank` on other tables** (Records, History) — still the old flat top-rank colour; leader-tint fix is `/leaderboard`+`/results`-scoped only, by design.
6. Carried forward, unchanged, from C1b §6: production's History disclosure has no visible desktop affordance (`+`/`−` indicator only shows ≤640px) — still needs an owner call before C4 touches that template.

## Handoff

Base `e9c999c`. This chat's resulting commit becomes the next accepted base. No push, merge, or deploy performed.
