# C1 — Clean Editorial Precision: decision spec

Captured 2026-09-20. Starting base: `e50078d` (Fix-stage merge, accepted F1–F6b integration). Worktree: `/Users/jon/projects/teg/worktrees/ui-c1`; branch: `claude/ui-c1`. Tree was clean at entry.

C1 is specification and prototype only — **no application CSS or template was touched**. Two Sonnet agents performed read-only value/selector inventory (theme-token values; control-pattern selectors and hit areas); the lead (Opus) owned every design decision, per the roadmap's C1 rules. No lead-model change was needed or flagged.

---

## 1. The problem, measured

| Symptom | Measured on `e50078d` |
|---|---|
| No type scale | **53 distinct `font-size` values across 169 declarations** in the public-app CSS (`base-vars.css`, `clean.css`, `dark.css`, `mobile.css`, `scorecard.css`, `player-profile.css`, `ui-polish.css`). In the five theme files alone: 28 literal steps. The four `--font-size-*` tokens `base-vars.css` already references (e.g. `var(--table-font-size, 0.875rem)`) **are never declared anywhere** — they silently resolve to their fallback on every use. |
| No spacing or size tokens | None exist. Spacing magnitudes in the theme files alone span 32 distinct rem values (`0.02`→`3`) plus six px values, with no underlying ramp. |
| No radius scale | **13 distinct non-zero `border-radius` values** (`2px, 3px, 4px, 6px, 8px, 10px, 13px, .35rem, 0.25rem, 0.375rem, 15%, 50%, 999px/9999px`) plus 3 token aliases (`--card-radius`, `--btn-border-radius`, `--stableford-radius`). |
| Softness | **9 distinct `box-shadow` values**, including a warm-brown two-layer shadow unique to Clean Layered's `.data-card`, on a site whose stated vibe is "thin rules, not heavy frames". |
| One heading level, not three | `.section-title`, `.chart-title` and `.card-header` are **byte-identical** apart from `display` and margins: Lora 700 / 13px / `0.09em` / uppercase / `var(--accent)` (`base-vars.css:1393`, `:1517`, `:1638`). |
| Green is overloaded | Green currently carries page label, all three heading classes, active tab, active pill, active nav link, leader-row tint, hover tint, hover text, toggle thumb, focus ring and link colour — simultaneously. `--table-hover-bg` and `--table-toprank-bg` are **the same colour** (`#F3F7F3`), so the leader row and the hovered row are indistinguishable. |
| Focus is green | A global `:where(a,button,select,input):focus-visible { outline: 2px solid var(--accent) }` (`ui-polish.css:9-12`), plus four `--select-focus-ring` overrides in `base-vars.css`, all resolve to green — keyboard focus is visually identical to "selected". |
| Four implementations of "one of N" | `.tab-underline` in `.section-nav`; `.pill` in `.pill-group`; `.scale-switch`/`.measure-toggle` with `role="switch"`; and `.pp-tab` in `.pp-tabs` — a wholly separate player-page tab bar (0.8rem not 0.8125rem, no uppercase, `--text-primary` indicator not `--accent`, `aria-pressed`, 2-column grid on phone instead of the scroller). `/leaderboard` renders three of the four on one screen. |
| Three state-transport mechanisms for tabs | (a) HTMX on the button; (b) `onclick` writes a hidden input then `htmx.trigger(<select>, 'change')`; (c) plain `<a href>` with query params. Active class is set both server-side and by global JS (`base.html:251-263`, `:338-345`), and three templates (`scoring_matrix.html`, `scoring_heatmap.html`, `latest_round.html`) duplicate that logic a third time inline. No `role="tablist"`/`aria-selected` exists anywhere. |
| Phone hit areas are 40px by default | 44px exists **only** below 640px, and the two site-wide phone defaults — `.pill` (`mobile.css:358`) and `.section-controls select` (`mobile.css:366`) — are **40px**. They reach 44px only via page-scoped overrides on Latest Round/TEG, title areas and player profile. Nothing above 640px meets 44px anywhere in production. |
| Dead experiment CSS | `base-vars.css:1181–1380` carries twelve inert page-title variants (`ts-b/c/c1/c2/c3/d/e/e2/f1–f5`) contributing ~26 untokened one-off colours (`#228B22`, `#7ec87e`, `#e8e5e0`, `#d0cdc8`, `#666`, `#111`, `#ccc`, …). Only the locked default `title_style=a` ships. |

**Structural fact that changes where C3 works:** despite its name, **`base-vars.css` declares no custom properties at all** — it is pure structural CSS consuming `var()`. Every token is declared in `clean.css`'s `:root`, overridden for `--bg-page`/`--footer-bg` only by `clean-page.css`/`clean-layered.css`, and re-pointed wholesale by `dark.css` under `html[data-mode="dark"]`. Import chain: `clean-layered.css` → `clean-page.css` → `clean.css`. **New tokens must be declared in `clean.css`'s `:root`, not `base-vars.css`.**

---

## 2. Type scale — 7 steps replacing 53 values

| Token | Value | Role |
|---|---|---|
| `--fs-100` | 11px | Table column headers, kickers, units, badges, micro-labels |
| `--fs-200` | 12px | Captions, context/denominator text, secondary metadata |
| `--fs-300` | 14px | **Table and data default** (matches today's `--table-font-size: 0.875rem`, so the densest surfaces migrate at zero visual cost) |
| `--fs-400` | 16px | Body prose, control labels, select text |
| `--fs-500` | 20px | Reserved — see §3, not used by any current component under the two-level heading decision |
| `--fs-600` | 28px | Page title (H1), phone |
| `--fs-700` | 36px | Page title (H1), ≥768px |

Values are **px, not rem**, so a future root-size change can't silently rescale tables.

---

## 3. Two real heading levels, not three

The roadmap brief (`gpt-ui-review.md` §5) asks for three distinct heading levels. **Checked against every public template: `.section-title`, `.card-header` and `.chart-title` never nest.** No page uses one as a subordinate of another — they're sequential peers labelling different blocks on the same page. Example, `/leaderboard` (`partials/leaderboard_table.html`): `.section-title` (line 26) labels the table, `.chart-title` (line 33) labels the chart below it — same visual weight, same job, different call site, never parent/child. This is true everywhere both appear together (`design_lab.html`, `font_lab.html`, `leaderboard_table.html`, `results_table.html`, `latest_round_tab.html`). There is no page structure for a third level to serve.

**Owner decision (2026-09-20), after review: two real levels.** `--fs-500` above is declared but unused today — kept in the scale for a future genuine third level, not spent on inventing one now.

| Level | Class(es) | Treatment |
|---|---|---|
| **H1 — page identity** | `.page-title` | Lora 600, `--fs-600`/`--fs-700`, `--ink`. Unchanged. |
| **H2 — section label** | `.section-title`, `.card-header`, `.chart-title` | **Unchanged: Lora 700, 13px, small-caps, `--green`.** The owner explicitly likes this treatment and it is kept as-is. |

All three classes become CSS aliases of one rule — merging the *selectors*, not the markup, so **zero template churn**. `.card-header`'s existing `margin-top: 2.5rem` (vs `.section-title`'s `1rem`) is preserved as the one legitimate behavioural difference: it signals "starts a new group after a data block," not a different heading rank.

**This is a correction to the roadmap brief, flagged for C2, not a silent gap.** `gpt-ui-review.md` §5 and the workstream ask for three levels; C1 found no page structure that needs a third, and the owner confirmed collapsing to two after reviewing three rendered options (Inter semibold, larger Lora, Inter small-caps) and choosing to keep the current treatment unchanged instead. C2 should weigh this explicitly.

---

## 4. Spacing, rule and radius tokens

**Spacing** — one 4px-based ramp:
`--sp-1: 4px`, `--sp-2: 8px`, `--sp-3: 12px`, `--sp-4: 16px`, `--sp-5: 24px`, `--sp-6: 32px`, `--sp-7: 48px`.
The six rhythm-owning classes (`.section-nav` 2rem, `.section-controls` 1.5rem, `.toggle-group` 1rem, `.section-title`, `.data-card`, `.card-header`) keep owning vertical rhythm — re-expressed in tokens (`--sp-6`, `--sp-5`, `--sp-4`), not relocated. `design_principles.md`'s "no `mb-*`/`mt-*` on these six" rule is preserved verbatim.

**Rules** — three, hairline-first:
`--rule-hair: 1px solid var(--rule-color)` (cell/row dividers), `--rule-strong: 2px solid var(--ink)` (table header underline — already the convention), `--rule-inset: inset 3px 0 0` (row state marker; replaces tinted backgrounds where a tint would fight hover).

**Radius** — collapse 13 values to three:
`--r-0: 0` (tables, rules, table-adjacent surfaces), `--r-1: 3px` (controls, inputs, selects, buttons), `--r-2: 6px` (genuine entity cards only — player highlight, report edition). `999px`/`9999px` pills and 8–13px panel radii are retired. `50%`/`15%` survive only where geometry requires a circle (mode toggle, score shapes on scorecards) — explicitly exempted so `scorecard.css` is not disturbed.

**Shadow** — one token, `--shadow-card`, used only by Clean Layered's `.data-card`. Everywhere else, shadow → hairline. The single largest "remove accidental softness" lever.

---

## 5. Semantic colour roles

Verified for contrast during mockup construction (see §8):

| Role | Token | Light value | Dark value | Means |
|---|---|---|---|---|
| Ink | `--ink` | `#1a1a1a` | `#ececea` | Primary text, headings, strong data |
| Ink secondary | `--ink-2` | `#555555` | `#b6b4aa` | Supporting text |
| Ink muted | `--ink-muted` | `#6f6f6f` | `#9c9a8f` | Labels, units, context. **Corrected from the planned `#767676` during verification** — `#767676` fails 4.5:1 on the Clean Page panel (`#f5f3f0`) at 4.10:1; `#6f6f6f` passes at 4.54:1. Both are raised from today's `#999999`, which fails outright. |
| Rule | `--rule-color` | `#e0e0e0` | `#2e2e29` | Hairlines, cell borders (unchanged values) |
| Green | `--green` | `forestgreen` (`#228B22`) | `#6cc77f` | **Active selection, live status, positive golf state** — and nothing else, except the named exception below |
| Sand | `--sand` | `#f2ede1` | `#403420` | Leader/champion row tint. Warm, non-green, doesn't fight the green hover tint |
| Focus | `--focus` | `#1a6fd4` | `#5b9bde` | Keyboard focus ring **only** — a separate hue so focus is never confused with selection |
| Success | `--success` | `= --green` | `= --green` | Under par, birdie, gain |
| Warning | `--warning` | `#8a6d1f` | `#c9a227` | Stale data, partial round |
| Failure | `--failure` | `#a3302a` | `#e06a63` | Failed write/load, over-par emphasis where the domain needs it |

**Consequence:** the leader row moves from green tint to sand tint + `--rule-inset` in green — resolving the "leader tint competes with hover tint" bug (`--table-hover-bg`/`--table-toprank-bg` are currently the same colour, `#F3F7F3`).

**Named exception, not silently resolved:** the owner's H2 decision (§3) keeps `.section-title`/`.card-header`/`.chart-title` green. This is a direct exception to "green means active selection/live status/positive state — and nothing else" and to `gpt-ui-review.md`'s "static headings should not all be green." It survives because it is *already scoped* — only these three structural-label classes, never `.page-title`, never body text — and the owner explicitly wants it kept. **C2 should weigh this exception explicitly.**

`--green` stays `forestgreen` — matches the frozen Streamlit app and the live site's identity. Not a change candidate.

**Contrast verification performed** (WCAG 2.1 formula, computed not assumed): `--ink-muted` on both Clean Page panel and pure white, light and dark; `--green` on `--sand`, light and dark (3.76:1 light / 5.85:1 dark — 13px bold treats as WCAG large text, needing 3:1, which both pass; this is the existing production treatment, not a new regression); `--focus` on card backgrounds, light and dark; `--sand` vs card background for visible distinction, both modes (dark sand was raised from an initial `#332b1d`, contrast 1.21 against the dark card, to `#403420`, contrast 1.39 — a deliberate warm-vs-neutral cue, not a luminance jump, since sand is meant to read as a warm tint next to a near-black card, not as a lighter card).

---

## 6. Three control patterns

One shared geometry: height 36px desktop / 44px touch, `--r-1` radius, `--fs-300` label, `--focus` ring — and **`--focus` must render visibly distinct from `--green`**, since today's single global ring makes keyboard focus and "selected" the same colour.

| Pattern | Use | Selected state | Replaces |
|---|---|---|---|
| **Tabs** — `.section-nav > .tab-underline` | Mutually exclusive *views*: Leaderboard/Scorecards, the six Latest Round tabs, Bestball/Worstball, Gross/Stableford on Comebacks, all HTMX-tab pages (Honours, Records, Player Rankings, Eclectic, …) | 2px `--green` underline, `--ink` bold text | Unchanged, canonical. **`.pp-tab` (player pages) folds into this** — a second, divergent tab implementation (0.8rem not 0.8125rem, no uppercase, `--ink` not `--green` indicator, 2-col grid on phone instead of the scroller) with no reason to diverge. |
| **Segmented measure** — new `.segmented` on `.toggle-group` | Mutually exclusive *measures*: Net/Gross, Round/TEG-total, Score/Stableford scale, Gross vs Par/Stableford, Count/%, the Metric pill row, Direction/Streak-type, rows/columns/palette on Heatmap | `--green` text + `--green` 1px border, shared hairline container, no "off" state | `.scale-switch`/`.measure-toggle` (a switch implying one option is "on" — wrong semantics for Net/Gross per `design_principles.md`'s own toggle-switch rule), `.pill`/`.pill-group` used as measures, and the hand-rolled active-state JS duplicated inline in `scoring_matrix.html` and `scoring_heatmap.html` (both fold into the one global handler). **`.toggle-group` already exists in `base-vars.css` but is used by zero templates** — this activates a dead class rather than inventing one. |
| **Compact action** — `.action` | Real actions: rank expand/collapse, retry, open report, History's `button.teg-cell` disclosure | Pressed (`aria-expanded`), not selected | `.rank-toggle`, ad-hoc buttons |

**Documented exceptions (not folded into `.segmented`):**
- `.lr-readout-entry` (chart player focus) — manipulates a chart series, not page state (`gpt-ui-review.md` §4 explicitly allows this).
- Round-number pills (`latest_round.html`, `scorecard.html`, `teg_reports.html`) and the player-pill roster (`partials/player_pills.html`) — navigation to a different resource (a round, a player), not a page-state measure. Keep `.pill` geometry.

Retiring `.scale-switch` as a *measure* control also retires the "check the off state" trap documented in `design_principles.md` → Toggle switches: a segmented control has no off state to get wrong. **`.scale-switch` itself is not deleted** — the Latest Round `.lr-scale-toggle` (Normal/Vs-bogey) is a genuine binary default and keeps the switch geometry per that same doc's own decision rule.

---

## 7. The two F6a follow-ups routed to C1

**44px hit-area contract — resolved, not re-deferred.** `design_principles.md:157` states 44px as a flat rule; the F1 desktop `.rank-toggle` is 28×28px, correctly scoped to `@media (min-width: 641px)` by F6b. **The rule was wrong, not the code**: 44px is a touch standard, not a universal one.

- `@media (pointer: coarse)` or ≤640px → **44×44px minimum**
- fine pointer / ≥641px → **28×28px minimum** for icon-only controls, 36px height for labelled controls

This makes the shipped `.rank-toggle` compliant. It also exposes a **real gap found during inventory**: the two site-wide phone defaults, `.pill` (`mobile.css:358`) and `.section-controls select` (`mobile.css:366`), are **40px**, not 44px — they reach 44px only through page-scoped overrides on Latest Round/TEG, title areas and player profile. Every other phone surface using a bare `.pill` is below the documented standard today. **C4 fixes the two default rules**, which removes most page-scoped 44px overrides as a side effect.

**Mid-word "Gros/sVP" wrap — resolved at the source; the fix already exists, unused.** Confirmed in `screenshots/F3/f3-scoring-320-6p-after-light.png`. Full chain traced:

1. `teg_analysis/analysis/scoring.py:439` — `df.groupby([field, 'Pl'])` makes the pandas index name the raw field string, `"GrossVP"`.
2. `webapp/routes/latest.py:320-345` (`_format_scoring_display`) calls `reset_index()`, promoting that raw name to a column header. It computes `friendly = "Gross vs Par"` (from `SCORING_FIELDS`, `latest.py:486`) **but uses it only for the section title, never the header**.
3. `webapp/tables.py:50-53` emits the column name verbatim.
4. `mobile.css:679-683` sets `overflow-wrap: anywhere` on `table.scoring-table th` to stop it overflowing `table-layout: fixed` (`mobile.css:654`) — which produces the mid-word break.

The header is a leaked internal field name; the correct human label is already computed one line away. **Fix: rename the index column to `friendly` in `_format_scoring_display`, then relax `anywhere` → `break-word`.** It wraps at the space as "Gross vs / Par". C4 implements; the exact call sites are above.

---

## 8. Mockups and screenshot manifest

Per the owner's selection: standalone HTML prototypes, real TEG 18 data, two screens — **`/leaderboard`** (standings) and **`/records`** (analysis).

- `/leaderboard` exercises all three control patterns at once (Leaderboard/Scorecards tabs, Net/Gross measure, chart-type segmented control), plus the champion/spoon facts rail and the leader row.
- `/records` exercises hairline sections, disclosure rows, muted context text, and the narrow-width case F2 already stress-tested.

### Files

```
webapp/design_reviews/ui_workstream/
  C1-handoff.md
  mockups/
    c1-standings.html   ← self-contained, tokens inline, /leaderboard
    c1-analysis.html    ← self-contained, tokens inline, /records
  screenshots/C1/
    standings-{390,768,1280}-{light,dark}-{page,layered}.png   (12)
    analysis-{390,768,1280}-{light,dark}-{page,layered}.png    (12)
```

Mockups **import no app CSS and no app CSS imports them** — Clean Page and Clean Layered cannot regress, and C3 inherits a reference, not a dependency. Both files carry the full token block inline (duplicated between the two, not shared via a third file, to keep each genuinely self-contained per the owner's decision).

### Reproduction

Each mockup reads `?layout=page|layered&mode=light|dark` from its own URL and sets `data-layout`/`data-mode` on `<html>` via a small inline script (deterministic — does not depend on system dark-mode or browser chrome). Default with no query string: `layout=page&mode=light`.

Captured with Playwright Chromium (locally installed into a throwaway venv for this chat — the repo's own `requirements-dev.txt` Playwright pin was not available in this checkout's interpreter), viewport height 844px, `file://` URLs, `networkidle` + 200ms settle before each capture. **Data state:** representative TEG 18 standings for 5 players (Gregg Williams, David Mullin, John Patterson, Jon Baker, Stuart Neumann) — invented round-by-round figures summing to plausible totals, not pulled from the live dataset; the records mockup uses the **real** Best/Worst Gross/Net/Stableford values and owners visible in `screenshots/P0/records-390-light.jpg`, with representative (unverified) location/year context. **No real 8-player fixture exists in this checkout** (noted in `P0-handoff.md`) — this system is not proven at 8 players by these captures.

### Checks run

- **No page-level overflow at any of the 24 captures**: `document.documentElement.scrollWidth <= clientWidth` asserted in-browser at every width/mode/layout combination. 0 failures.
- **Two-tier hit-area contract**: every `.action`, `.seg-option`, `.tab-underline` and `summary` element's rendered bounding box asserted ≥44px at ≤640px, ≥28px at ≥641px. **First pass found a real bug**: `.tab-underline` in both mockups was 29px tall at 390px width — the phone 44px floor from §6 had been specified but not implemented in the mockup CSS. Fixed (`@media (max-width: 640px), (pointer: coarse) { .tab-underline { min-height: 44px; … } }`), both files, then re-captured. Second pass: 0 failures.
- **Evidence integrity**: all 24 PNG md5s distinct (the exact failure class F6 caught in F3's screenshot evidence).
- **Contrast**: computed per §5, not asserted from theory — the `--ink-muted` correction and the dark-mode `--sand` adjustment were both found this way.

### Not run

- `python scripts/check_css_comments.py` — no `.css` file was touched.
- `pytest` — no application code was touched; per `CLAUDE.md`'s blast-radius rule, no suite is warranted for a docs/prototype-only chat.
- Local markdown link check — this document has no internal relative links beyond repo paths already verified to exist during research.

Both mockups are additionally published as private Claude Artifacts for interactive review (not part of the committed deliverable, not linked from application code): `c1-standings.html` → `https://claude.ai/artifact/WGNRxtTh2a9W8dcsLXtort`, `c1-analysis.html` → `https://claude.ai/artifact/UzLWTLikjysaRKru2T1jGm`. Reproduce the same four combinations there via the same query string.

---

## 9. Token mapping (representative, not exhaustive)

Full line-by-line rewrite of 169 declarations is C3/C4's implementation work, not this spec. This table gives the mapping methodology and the largest buckets; C3 applies it site-wide.

| Old value(s) | Selectors (examples) | New token |
|---|---|---|
| `11px`, `0.6875rem`, `0.7rem` | `.stat-label`, `.badge`, `.badge-muted`, `.player-card-meta`, table `th` | `--fs-100` |
| `12px`, `0.75rem`, `0.8rem` | `.caption`, `.lr-report-link`, `.theme-select`, `.page-footer`, `.chart-placeholder code` | `--fs-200` |
| `13px`, `0.8125rem`, `var(--table-font-size, 0.875rem)` | `.tab-underline`, `.pill`, `.teg-table`/`.records-table` fallback, `.scale-switch-label` | `--fs-300` (14px — a 1px nudge up from the 13px cluster; `.section-title`/`.card-header`/`.chart-title`'s literal `13px` is explicitly **not** migrated, see §3) |
| `14px`, `0.875rem`, `0.825rem` | `.nav-link`, `.tab-btn`, `.teg-select`, `.position-table`, `.player-ranking-table` | `--fs-300` |
| `1rem`, `16px` | `.records-table--borderless thead th`, `.collapsible > summary`, `.title-stars` | `--fs-400` |
| `1.75rem` (page title) | `.page-title-area .page-title` | `--fs-600` (phone) / `--fs-700` (≥768px) |
| `0.65rem`, `0.625rem`, `0.6rem`, `0.6875rem` | `.page-title-area .page-label`, `.metric-label`, `.trophy-honour-label`, `.pc-stat-lbl` | `--fs-100` |
| `0.9375rem`–`1.05rem` cluster (mid-size one-offs) | `.result-callout`, `.player-card-name`, `.pc-stat-val`, `.detail-heading` | `--fs-300`/`--fs-400`, nearest by intent — C3 to confirm case-by-case, not a blanket rule |
| `2px`, `4px`, `0.25rem`(non-token), `.35rem` | `.history-table .teg-flag.fi`, `.lr-report-link`, `.nav-link`, `.theme-select` | `--r-1` (3px) |
| `0.375rem`, `var(--card-radius)`, `6px`, `8px`, `10px`, `13px` | `.card`, `.stat-card`, `.trophy-cabinet`, `.player-card`, `.teg-select`, `.chart-placeholder` | `--r-2` (6px) for genuine entity cards; `--r-1` for controls — C3 splits by the "is this a control or an entity" test in `design_principles.md`'s own data-card decision rule |
| `999px`, `9999px` | `.switch-track`, `.badge`, `.pill`, `.hc-tile-delta`, `.lr-readout-entry` | Retired — pills/badges move to `--r-1` per §6 (badges are not one of the three control patterns and keep their own rounded-label treatment at `--r-1`, not `--r-2`) |
| `#999999` (`--text-muted`) | `clean.css:30`, `dark.css:22` (`#86857e`) | `--ink-muted` (`#6f6f6f` / `#9c9a8f`) |
| `#F3F7F3` used for **both** `--table-hover-bg` and `--table-toprank-bg` | `clean.css:46,48` | Split: `--hover-bg` keeps `#F3F7F3`; top-rank becomes `--sand` |
| `var(--accent, #17683c)` on the three heading classes | `base-vars.css:1399,1524,1644` | `--green` (unchanged value, named exception per §5) |
| 9 distinct `box-shadow` values | `.nav`, `.card`, clean-page/-layered surfaces, `.data-card` | `--shadow-card` (Clean Layered `.data-card` only); everything else → `border: var(--rule-hair)` or no shadow |

---

## 10. Affected-selector list, grouped by owning chat

**C3 — foundation:**
`clean.css` (`:root` token declarations), `dark.css` (dark counterparts), `.section-title`/`.card-header`/`.chart-title` (consolidate), `.tab-underline` + `.pp-tab` (fold), `.toggle-group`/`.segmented` (new), `.action` (new), `.rank-toggle` (44px contract doc fix), `base-vars.css:1181–1380` (twelve dead `ts-*` blocks — confirm deletion with owner first, see Risks), the `#16150f` hard-code and glyph-rule duplication already routed to C3 by F6a.

**C4 — table and responsive contracts:**
`mobile.css` (`.pill` 40px→44px default, `.section-controls select` 40px→44px default, `table.scoring-table th` wrap rule), `webapp/routes/latest.py` (`_format_scoring_display` header rename), `scoring_matrix.html`/`scoring_heatmap.html` (hand-rolled JS → `.segmented`), the `/latest-round` Scoreboard 402px overflow (`webapp/TODOS.md`).

**C5 — leaderboard rhythm:**
`partials/leaderboard_table.html`, `partials/results_table.html` (`.scale-switch.measure-toggle` → `.segmented` for Net/Gross and Round/TEG-total; `.lr-scale-toggle` stays a switch), leader-row treatment (`tr.rank-1` → sand + `--rule-inset`), facts rail, control-zone composition.

---

## 11. Migration order

1. **C3 — foundation.** Declare all tokens in `clean.css`'s `:root` (not `base-vars.css` — see §1) + dark counterparts in `dark.css`. Consolidate the three heading classes onto one shared rule. Introduce `.segmented` (activating the currently-dead `.toggle-group`) and `.action`. Fold `.pp-tab` into `.tab-underline`, checking `player-profile.js`'s toggle call for double-firing against the global handler (see Risks). Apply to the smallest representative components only.
2. **C4 — table and responsive contracts.** Phone/tablet/desktop table contracts; the Gros/sVP header fix; the 44px two-tier contract including the two 40px phone defaults; consolidating the hand-rolled active-state JS onto `.segmented`; the open Scoreboard 402px overflow.
3. **C5 — leaderboard rhythm.** Control zone, facts rail, sand leader treatment, table starts sooner. Retire `.scale-switch.measure-toggle`; leave `.lr-scale-toggle` alone.

---

## 12. Risks

- **Two-level heading decision is a correction to the brief, not a silent gap.** C2 should weigh it explicitly rather than assume C1 missed the requirement.
- **`--ink-muted` contrast change.** Raising `#999999`→`#6f6f6f`/`#767676`→`#9c9a8f` touches every muted label site-wide. It's a readability fix (the current value fails 4.5:1 on white) but will look visibly darker at first. Flagged for C2.
- **`.scale-switch` is shared.** It also styles the Latest Round scale toggle. Retiring it *as a measure control* must not break that genuinely binary one. Spec is explicit: `.scale-switch` survives for real on/off; only `.measure-toggle` migrates.
- **Token declarations don't live where the name suggests.** `base-vars.css` declares zero custom properties. C3 must declare the new scale in `clean.css` (or promote a genuinely token-only `base-vars.css` — a naming fix worth flagging to the owner, not silently reinterpreting) and verify the fallback chain doesn't mask a missing declaration again, as it does today for `--font-size-*`.
- **`.pp-tab` folding into `.tab-underline` touches `player-profile.js`.** Its active-state toggle (`player-profile.js:142-144`) does `classList.toggle('pp-tab--active', …)` directly. `.pp-tabs` already carries `.section-nav`, so once `.pp-tab` becomes `.tab-underline` the global `base.html` handler (scoped to `.section-nav .tab-underline`) may double-fire alongside the page-local one. C3 must check for double-toggling, not just visual match.
- **Hand-rolled active-state JS in three templates.** `scoring_matrix.html`, `scoring_heatmap.html` (inline `onclick`) and `latest_round.html` (history/popstate) each duplicate the global active-swap logic independently, with extra behaviour (hidden-input sync, browser-history push) that consolidation must not silently break.
- **Tailwind Play CDN source order.** A stray `mb-*`/`mt-*` utility beats any token-driven rule on the same element (documented pattern, unchanged by C1).
- **Mockup data fidelity.** Standings data is representative, not real; no 8-player fixture exists anywhere in this checkout.
- **Deleting the twelve dead `ts-*` blocks needs an explicit owner nod** before C3 does it — `webapp/README.md` calls them "deferred to the Phase 2 review," which is arguably now, but C1 does not delete application CSS itself.
- **This session's Playwright was a throwaway local install**, not the repo's pinned `requirements-dev.txt` version — sufficient for this chat's static-prototype captures, but C3 onward should use the repo's own pinned setup for application-page screenshots.

---

## Handoff

Base `e50078d`. This chat's resulting commit becomes C2's base. No push, merge, or deploy performed.
