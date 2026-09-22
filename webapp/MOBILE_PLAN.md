# Mobile design plan

How we make the webapp feel brilliant — and a bit more "app-like" — on a phone,
in light **and** dark mode, **without changing how it looks on laptop or iPad.**

## Status — read this first

**Direction chosen: A — full native-app feel** (bottom tab bar, sticky app bar,
segmented controls, card/reflowed data), in light **and dark**. We build it via
the hybrid *strategy* in [§3](#3-the-look-and-feel-decision-decided): app shell
everywhere, card-reflow the hero tables, sticky-column scroll for the long tail.
Hard rule throughout: **desktop/iPad stay byte-identical** (all mobile rules sit
behind a `≤640px` breakpoint or an opt-in `data-mode`).

**Done so far** (live work plus pending branch `codex/mobile-ui-rollout`):
- ✅ **Dark-mode foundation** (in `main`) — `data-mode` cookie/toggle +
  `static/themes/dark.css`, opt-in, default light. See [§4.2](#42-dark-mode--foundation-built).
- ✅ **Portrait scorecard** (in `main`) — the first real vertical slice of the app
  pattern (holes-as-rows, pinned columns, pure-CSS Gross/Stableford toggle).
  Builders in `teg_analysis`, wired into the webapp. See [SCORECARD_PORT.md](SCORECARD_PORT.md).
- ✅ **App shell — bottom tab bar + Explore** — `static/mobile.css` and
  `base.html` provide four fixed shortcuts (Latest, History, Records and Cards)
  plus Explore at `≤640px`. Explore and the phone hamburger open the same
  native sheet, which lists every `NAV_SECTIONS` page as a direct link. The
  641–900px hamburger disclosure navigation stays unchanged.
  Preview: `mobile_mockups/mobile_shell_preview.html`.
- ✅ **Mockups** for Direction A in `webapp/mobile_mockups/` (served at `/mockups/`).
- ✅ **M1.4–M1.6 sweep + M2.7 leaderboard hero** — all in `static/mobile.css`
  (≤640px only; desktop verified pixel-identical by before/after screenshot
  diff on 5 pages):
  - **Controls (M1.5):** `.section-nav`/`.tab-underline` restyled as a
    segmented control (scrolls when the labels overflow); pills and
    `.theme-select` selects get ≥40px tap targets and 16px font (no iOS focus
    zoom). Also fixed a live bug: the old `.theme-select { display:none }`
    rule was hiding every page's TEG/filter selects on phones — now scoped to
    `.nav`.
  - **Tables (M1.6):** sticky first column + horizontal wrapper scroll for
    `.teg-table` and `.records-table` inside both `.table-wrapper` and
    Tailwind `.overflow-x-auto` wrappers (opt out per table with
    `.table-wrapper--no-pin`); `overflow-x` restated so phones don't depend
    on the Tailwind CDN for the no-page-scroll rule.
  - **Leaderboard hero (M2.7):** `/leaderboard` and `/results` standings
    show a champion/wooden-spoon pod pair (`partials/_standings_hero.html`,
    fed by `lb_hero` from `_results_context`) above the standings table; the
    text callout hides at ≤640px. **Superseded by I1** (2026-09-20): the
    per-player card list this section originally described
    (`partials/lb_cards.html`'s `.lb-cards`) was CSS-dead from the moment
    R3.2 shipped — `.standings-page .lb-cards { display: none }` always won
    on specificity, so no phone view ever showed it. I1 deleted it and
    replaced the phone standings experience with the unified table's own
    reflow: `partials/_standings_table.html` renders round values twice
    (desktop `<td class="col-round">` cells, a per-row `.standings-rounds`
    strip), and CSS shows exactly one copy per viewport — see
    `design_principles.md` → Tables for the pattern.
  - **App bar (M1.4):** compacted nav height/padding + soft elevation.
- ✅ **Core data layouts R2–R3.4** (in `main`) — compact interactive Latest Round with stable HTMX URL state, mobile History disclosure, equal-height standings rows, portrait scorecard refinements and responsive Best/Worstball field and contribution views. The Latest Round chart also proves the mobile chart pattern against the former HTMX blocker.
- ✅ **R4.1 tournament race charts** (in `main`) — Results and Leaderboard gain a phone-only player readout and tap-to-focus interaction, including crowded six-player handling. Desktop, iPad and the separate `/charts` route retain their previous output.
- ✅ **R4.2 player progression charts** (in `main`) — Career Trend and Gross vs Par by Round state their phone measure/direction without hover; the Rounds chart reuses `player-profile.js`'s existing tick-thinning/theme-adaptation/live-breakpoint pattern (dense histories, e.g. a 17-TEG player, stay readable at 320px); the measure pill's active state no longer relies on colour alone. Desktop and iPad are unchanged.
- ✅ **Mobile table redesigns** (in `main`) — Records, Personal Bests, Top Performances, Eclectic Records, Player Rankings, Handicaps, Scoring Matrix/By-TEG, Changes/Comebacks/All-rounds, By-course and Course Analysis all reflow for phone widths (proportional columns, wrapping course names, double-height rows where needed). Desktop/iPad unchanged.
- ✅ **R4.3 scoring-analysis charts** (pending integration from `codex/mobile-ui-rollout`) — `/scoring/by-teg`'s GrossVP-by-TEG line chart and `/scoring/distributions`' grouped bar chart reuse the R4.1/4.2 `.chart-block` treatment: native legend hidden and replaced by a below-chart tap-to-focus readout at ≤640px, so a 7-player field no longer eats the top of the chart in a wrapped legend. Colours are assigned explicitly server-side (matching Plotly's existing default colorway) so the desktop/iPad figures are unchanged. The distributions readout carries no numeric value (a bar-chart total isn't a meaningful stat) — it's a colour key only. `player_scoring.html`'s single-player score-distribution bar chart was left alone: single series, no legend to hide, not a fit for this pattern.
- ✅ **`/latest-round` Scoreboard polish batch** (`codex/mobile-ui-rollout`) — un-bold player names; the `.lr-readout` pill-style chart legend unified across all page widths (also affects `/results`, `/leaderboard`, `/scoring/by-teg`, `/scoring/distributions`, which share the same CSS); rank-header column-width/centring fix (`overflow-wrap: anywhere` pitfall, see `design_principles.md`); site-wide scroll-jump fix on htmx tab-bar swaps (`base.html`, not Latest-Round-specific — also fixed `/records`); Report link moved out of the tab bar and restyled; Streaks tab headers show initials instead of full names (`/latest-round` and `/latest-teg`); new Round-vs-TEG-cumulative-total toggle on the Scoreboard tab (round-only — see next bullet). Full detail: `STATUS.md`.
- ✅ **`/latest-teg` Scoreboard tab parity** (`codex/mobile-ui-rollout`) — the
  TEG aggregate tab now shares the round Scoreboard's `table.leaderboard`
  markup/CSS (rank badges, un-bolded names, tap-to-expand detail row,
  Personal-rank/All-time-rank columns) on both phone and desktop/iPad, via
  `_build_scoreboard_table`'s new `detail_cols` parameter
  (`webapp/routes/latest.py`). The one adaptation: a whole TEG has rounds,
  not a front/back-9 split, so the detail row shows one tile per round
  played (R1, R2, ...) instead of Out/In. The Plotly chart and the
  Round↔TEG-total toggle stay round-only by design — a TEG total already
  *is* the toggle's "TEG total" state, so there's nothing for a toggle to
  switch between here.

- ✅ **C4 responsive/table contract pass** (2026-09-20) — `.pill`/`.section-controls
  select` phone defaults raised 40px→44px (the M1.5 tap-target work above left
  these two at 40px; `mobile.css:355-370`), closing the last flat-40px gap in
  the M2.9 tap-target audit. Two page-level overflow bugs fixed:
  `/scoring/heatmap`'s legend row at ≤390px (`webapp/static/heatmap.css`) and
  `/scorecard`'s multi-section landscape wrapper at 768px in Clean Layered
  (`.sc-landscape:not(.data-card)` needed `max-width: 100%` alongside its
  existing `width: fit-content`, `webapp/static/scorecard.css`). A responsive
  audit of every public table route (`webapp/design_reviews/ui_workstream/C4-handoff.md`)
  found the rest already compliant with the phone/tablet/desktop contract —
  no further table-pattern work outstanding from that pass. **Still open**
  from the same audit: `bw-name-full`/`bw-name-short` (the player-name
  shortening pattern below, §Tables in `design_principles.md`) is only wired
  up for bestball/eclectic contribution bars; other player-name tables rely
  on tier-1 sticky-scroll or tier-2 card reflow instead, which already
  protects the identity column on phone but hasn't had the shortening pattern
  applied — a candidate for a dedicated pass, not blocking.

**▶ Pick up here (the remaining UI work):**
- **Per-page pass** (M2.9) — spacing and empty-state polish remain; tap
  targets and the table-route audit are now covered by C4 above.
- Dark-mode page-title contrast is **fixed** (F1, 2026-09-20, see
  `webapp/TODOS.md`) — no longer part of the deferred per-page dark QA.

Everything below §Status is the approach and remains the working reference.

---

## 1. Goals & hard constraints

**Goals**
- A modern, app-like feel on phones (thumb-friendly, fast, uncluttered).
- Works in **light and dark** mode.
- Keeps the project's editorial / printed-programme identity (Lora + Roboto
  Mono + forestgreen) — we're not throwing the design language away.

**Hard constraints (do not break)**
1. **Laptop and iPad must look exactly as they do today.** All mobile work is
   additive and scoped behind a phone-only breakpoint. The desktop/tablet CSS
   path is never touched.
2. **No new data layer.** `teg_analysis/` stays UI-agnostic; this is presentation
   only — templates, CSS, and at most small JS.
3. **Themable, not hard-coded.** Dark mode and any mobile skin must run through
   the existing CSS-variable system (`base-vars.css` + theme files), not inline
   colours.

---

## 2. Mobile best-practice principles we're applying

- **One primary action per screen; everything else one tap away.** Phones are
  for reading the leaderboard, not driving 6 filter dropdowns at once.
- **Thumb zone.** Primary navigation lives at the **bottom**, where the thumb is
  — not behind a top-corner hamburger.
- **Tap targets ≥ 44px.** Rows, tabs and toggles are finger-sized.
- **Content over chrome.** Minimal persistent UI; let the data fill the screen.
- **Respect the notch / home indicator** via `env(safe-area-inset-*)`.
- **No horizontal scrolling of the *page*** (only opt-in scroll *within* a wide
  table, with a clear affordance).
- **Performance:** system fonts fall back instantly; charts stay lightweight.
- **Dark mode is a first-class palette,** not an inverted screenshot — warm
  near-black paper, brightened green accent for contrast (WCAG AA on text).

---

## 3. The look-and-feel decision (DECIDED)

> **Decided (Jon): Direction A — full native-app feel.** Built via the hybrid
> *strategy* in this section (app shell everywhere; card-reflow hero tables;
> sticky-column scroll for the long tail). Direction B (editorial) is superseded
> — keep its mockup only as a reference. The rest of this section is the
> reasoning behind that call.

The mockups present **two ends of a spectrum**. The real build is a **blend**,
but seeing the extremes made the choice concrete.

| | **A — Full native-app** | **B — Polished mobile-editorial** |
|---|---|---|
| Nav | Bottom tab bar + sticky app bar | Light top bar + hamburger (as today) |
| Gross/Net | Segmented pill control | Underline tabs (as today) |
| Leaderboard | Reflowed into tappable **cards/rows** | Stays a **real table** (sticky name column, rounds scroll) |
| Chart | Rounded card, chip legend, scrubber | "Printed on the page", direct end-of-line labels |
| Feel | Most "app", furthest from desktop | Most "programme", closest to desktop |
| Build cost | **Higher** (see §5 table note) | **Lower** |

**My recommendation: a hybrid — "Editorial table strategy + app shell."**

- Take the **app shell** from A (bottom tab bar, sticky header, segmented
  controls) — that's what delivers the "modern app" feeling and it's cheap.
- Take the **table strategy** from B (keep the server-rendered table, add a
  sticky first column + opt-in horizontal scroll) as the *default* — because
  reflowing every table into cards is expensive (see §5). Reserve the card
  reflow for a **few hero tables** (Leaderboard especially), where it's worth it.
- Use the **editorial chart treatment** (restrained palette, direct labels)
  inside an app-style card.

This gets ~80% of the app feel for ~30% of the effort, and degrades gracefully
on the long tail of dense stat tables. This is the agreed build strategy.

---

## 4. Technical strategy

### 4.1 Isolating mobile so laptop/iPad are untouched

- **Single phone breakpoint: `max-width: 640px`.** Everything mobile-specific
  lives inside `@media (max-width: 640px)`. iPad portrait is 768px, so iPad and
  laptop never enter this path — constraint #1 satisfied by construction.
  - (Note: the existing nav hamburger triggers at `900px`. We leave that as-is;
    the *new* phone shell is gated at `640px`. The 641–900px tablet range keeps
    today's behaviour.)
- New CSS goes in a dedicated **`static/mobile.css`**, loaded after the theme
  file, containing *only* `@media (max-width:640px)` rules. Desktop CSS files are
  not edited, so there is zero risk to the desktop render.
- A new structural hook in `base.html` (bottom-nav markup) is rendered always
  but **`display:none` above 640px** — invisible and inert on laptop/iPad.

### 4.2 Dark mode — ✅ FOUNDATION BUILT

The app is already 100% CSS-variable driven, so dark mode is a **variable
override set**, not a re-skin. Built as:

- **`static/themes/dark.css`** — overrides the colour custom properties under
  `html[data-mode="dark"]` (warm near-black `#16150f`, text `#ececea`,
  brightened green `#6cc77f`, dark top-rank tint `#1b2a1d`). Higher specificity
  than the themes' `:root`, so it wins regardless of load order. Loaded on every
  page but **completely inert until `data-mode="dark"` is set** → light render
  byte-identical on every device.
- **Switching:** `data-mode="light|dark"` on `<html>` from a `mode` cookie
  (`theme.py: get_mode`, injected via `request.state.mode` in `app.py`), set by a
  **◑ toggle** in the nav (mirrors the theme-select cookie+reload pattern).
  Default **light** → constraint #1 satisfied (opt-in; OS dark setting is *not*
  auto-applied, so a dark-OS laptop is unaffected).
- **Charts:** `get_plotly_theme(theme, mode)` gains a dark surface. *Still to
  wire:* chart routes pass `request.state.mode` (deferred with the parked chart
  work — see §1b in README).
- **Scorecard:** its dark tokens (already in `scorecard.css`) now activate under
  the same `data-mode` hook.
- **Follow-ups:** Clean Layered's hard-coded mid-panels get a first dark pass
  here but warrant a dedicated polish; full per-page dark QA pending an
  in-browser sweep.

### 4.3 Navigation (the app shell)

- **Bottom tab bar** (phone only): four direct shortcuts — *Latest · History ·
  Records · Cards* — plus *Explore*. Explore and the phone hamburger open the
  same full-screen sheet, which lists every `NAV_SECTIONS` page as a direct
  link. `MOBILE_SHORTCUTS` owns only the shortcuts; `NAV_SECTIONS` remains the
  public-page source of truth.
- **Sticky top app bar:** page kicker + title + the TEG/context selector as a
  pill. Collapses on scroll (we already have a sticky-nav scroll handler to
  adapt).
- Everything here is new markup gated to `≤640px`; the desktop dropdown nav is
  left exactly as-is.

### 4.4 Tables on mobile (the crux)

The `/latest-round` Scoreboard table is the reference implementation for tier
2/3 fixed-column tables — see `design_principles.md` → *Mobile table pattern
— the reference implementation* for the exact selectors, widths and two
pitfalls already hit. Copy from there rather than re-deriving values.

Three tiers, cheapest first:

1. **Sticky-column scroll (default, all tables).** Keep the server-rendered
   `.teg-table`; inside `≤640px` make the rank+player columns `position:sticky`
   and let the numeric columns scroll horizontally with a fade affordance. Pure
   CSS, works on *every* table immediately. (Shown in `leaderboard_editorial`.)
2. **Card reflow (hero tables only).** For the Leaderboard, render each row as a
   card (rank, name, big total, secondary round line). **Cost note:** the table
   HTML is generated as a string in `teg_analysis/display/` /`deps.py`, so a true
   reflow needs either (a) `data-label` attributes added in the HTML builder, or
   (b) a dedicated mobile partial fed the same DataFrame. Prefer (b) for the 2–3
   hero pages; don't try to reflow all 30+ tables. (Shown in `leaderboard_app`.)
3. **Priority columns.** For very wide stat tables, hide low-priority columns
   under `≤640px` (CSS `display:none` on tagged `th/td`) and surface them in the
   row's detail view. Last resort.

### 4.5 Charts on mobile

- Reuse Plotly (already in the stack) but with a **mobile layout preset**:
  hidden modebar, larger touch targets, fewer ticks, legend moved below or
  replaced with **direct end-of-line labels** (cleaner on a narrow screen — see
  the editorial chart mockup), `responsive:true`.
- A dark Plotly theme (per §4.2).
- ⚠️ This intersects the **known HTMX chart-swap bug** (see
  `webapp/README.md` → Phase 1b). Mobile chart work should land **after** that
  fix, or avoid HTMX-swapped charts on the phone shell initially.

---

## 5. Phased implementation

**Phase M0 — Foundations (no visible change on desktop).**
1. ✅ **Done** — `static/mobile.css` scaffold (all rules inside `@media (max-width:640px)`).
2. ✅ **Done** — dark-mode variable layer (`static/themes/dark.css`) +
   `data-mode` cookie/toggle + dark Plotly theme helper. Default light, so
   laptop/iPad unchanged.
3. ✅ **Done** — four-shortcut bottom bar plus native Explore dialog in
   `base.html`, `display:none` >640px. The phone hamburger opens that same
   dialog; the tablet disclosure navigation remains separate.

> ✅ **Vertical slice already done:** the **portrait scorecard** implements the
> M1 table + control patterns (segmented Gross/Stableford toggle, pinned-column
> horizontal scroll, `≤640px` orientation switch) for one page — a working
> reference for steps 5–6 below. See [SCORECARD_PORT.md](SCORECARD_PORT.md).

**Phase M1 — The app shell on phones.**
4. ✅ Bottom tab bar styled + top bar compacted (≤640px only). *Remaining:* a
   more app-like sticky header (the existing JS sticky still applies).
5. Convert primary in-page controls (Gross/Net, metric tabs) to segmented /
   thumb-friendly variants *within the media query*.
6. Apply the **sticky-column scroll** table treatment globally (§4.4 tier 1).

**Phase M2 — Hero polish.**
7. Card-reflow the **Latest Leaderboard** (and maybe Latest Round / Records).
8. Mobile chart preset + direct-label race chart.
9. Per-page pass: spacing, tap targets, empty states, safe-area insets.

**Phase M3 — Refine.**
10. ✅ Direction picked (A). Delete the superseded editorial mockups once the app
    shell lands.
11. Accessibility + real-device QA (iOS Safari, Android Chrome), dark-mode
    contrast check, and a regression sweep confirming **desktop/iPad are
    pixel-unchanged**.

Each phase is independently shippable and reversible.

---

## 6. Per-page notes

- **Latest Leaderboard** — the hero. Card reflow + segmented Gross/Net + champion
  pods. (Mockups built.)
- **Latest Round / TEG in context** — chart-led; mobile chart preset. (Chart
  mockups built.)
- **Records / Top TEGs / Player Rankings** — widest tables; sticky-column scroll
  is the workhorse here, with priority-column hiding for the worst offenders.
- **Scoring analysis (11 views)** — mostly tables + a chart each; inherit the
  global table + chart treatments, minimal bespoke work.
- **TEG Reports** — long-form prose; just needs comfortable reading measure,
  font-size and dark-mode body colours. Cheapest page to make excellent.
- **Contents** — already responsive (`max-width:820px` → single column); becomes
  the natural "More" sheet target.
- **Scorecard** — portrait (holes-as-rows) view, all three modes (single round /
  whole TEG / vs field). Mockups built (`scorecard_app.html`,
  `scorecard_teg_app.html`, `scorecard_field_app.html`). Separable, mergeable
  work-package — full step-by-step + merge-to-`main` strategy in
  **[SCORECARD_PORT.md](SCORECARD_PORT.md)**.

---

## 7. The mockups

Self-contained dummy pages in `webapp/mobile_mockups/` (static data, real
palette/fonts). View options:
- **Run the webapp** and open `http://localhost:8000/mockups/` (mounted in
  `app.py`). The gallery shows all four in phone frames with a light/dark switch.
- **Open any file directly** in a browser / send to your phone — each is
  standalone and has its own light/dark toggle.

| File | Direction | Page |
|---|---|---|
| `index.html` | Gallery / chooser | side-by-side compare + global light/dark |
| `leaderboard_app.html` | A — App | Latest Leaderboard (card rows, bottom tabs) |
| `leaderboard_editorial.html` | B — Editorial | Latest Leaderboard (sticky-column table) |
| `chart_app.html` | A — App | Race chart (card, chip legend, scrubber) |
| `chart_editorial.html` | B — Editorial | Race chart (printed, direct labels) |
| `scorecard_app.html` | A — App | Scorecard — single round (holes as rows, score-shape cells) |
| `scorecard_teg_app.html` | A — App | Scorecard — whole TEG (holes × rounds, Gross/Stableford toggle) |
| `scorecard_field_app.html` | A — App | Scorecard — vs Field (holes × players, sticky cols, scroll) |

These are **throwaway design artifacts** — not part of the app's page hierarchy,
intentionally unwrapped (like `smoke_test`/`width_test`). Delete once the
direction is chosen and the real implementation lands.

---

## 8. Open questions for Jon

1. **Direction:** A, B, or the hybrid in §3? (Can mix per element.)
2. **Dark mode reach:** mobile-only, or available on desktop too? Auto-follow the
   OS, manual toggle, or both?
3. **How many hero tables** get the full card reflow vs. the cheaper
   sticky-scroll? (Leaderboard is a given; Records? Latest Round?)
4. **Bottom-nav destinations:** are *Latest · History · Records · Scoring · More*
   the right five?
