# Mobile design plan

How we make the webapp feel brilliant — and a bit more "app-like" — on a phone,
in light **and** dark mode, **without changing how it looks on laptop or iPad.**

This is a *plan to follow later*, not work that's been done. The only thing built
so far is the set of **dummy mockups** in `webapp/mobile_mockups/` (see
[§7](#7-the-mockups)). Everything else below is the proposed approach.

> Status: **proposal / awaiting look-and-feel decision.** Nothing in the live
> app has changed yet apart from the mockups + a static mount to serve them.

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

## 3. The look-and-feel decision (this is the bit for Jon)

The mockups present **two ends of a spectrum**. The real build will most likely
be a **blend**, but seeing the extremes makes the choice concrete.

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
on the long tail of dense stat tables. **Decision needed from Jon:** pick A, B,
or the hybrid (or mix per-element).

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

### 4.2 Dark mode

The app is already 100% CSS-variable driven, so dark mode is a **variable
override set**, not a re-skin.

- Add `static/themes/dark-vars.css` (or a `[data-mode="dark"]` block in each
  theme) overriding `--bg-*`, `--text-*`, `--line`, `--accent`, `--accent-soft`,
  table tints, etc. The mockups contain a validated dark palette to copy:
  warm near-black `#16150f` / `#131311`, text `#ecebe4`, brightened green
  `#6cc77f`, dark top-rank tint `#1b2a1d`.
- **Switching:** a `data-mode="light|dark"` attribute on `<html>`, set from a
  cookie (mirrors the existing `theme` cookie pattern in `theme.py`), with an
  optional "Auto" that follows `prefers-color-scheme`.
- **Protecting laptop (constraint #1):** default = **light**. Dark is opt-in via
  the toggle, so a laptop user sees no change unless they choose it. *(Decision
  for Jon: should dark also auto-follow the OS on mobile only? My default: yes on
  mobile, manual elsewhere.)*
- Charts: extend `get_plotly_theme()` / `chart_utils.py` with a dark variant so
  Plotly figures match (paper/plot bg, font, gridline colours).

### 4.3 Navigation (the app shell)

- **Bottom tab bar** (phone only): 5 destinations mapped to the `NAV_SECTIONS`
  groups — e.g. *Latest · History · Records · Scoring · More*. "More" opens a
  full-screen sheet listing the rest (driven by the same `webapp/nav.py` source
  of truth — no second nav definition).
- **Sticky top app bar:** page kicker + title + the TEG/context selector as a
  pill. Collapses on scroll (we already have a sticky-nav scroll handler to
  adapt).
- Everything here is new markup gated to `≤640px`; the desktop dropdown nav is
  left exactly as-is.

### 4.4 Tables on mobile (the crux)

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
1. Add `static/mobile.css` (empty shell + the `≤640px` media query scaffold).
2. Add the dark-mode variable layer + `data-mode` toggle + cookie; wire a dark
   Plotly theme. Default light, so laptop/iPad unchanged.
3. Add the bottom-nav + app-bar markup to `base.html`, `display:none` >640px.

**Phase M1 — The app shell on phones.**
4. Style the bottom tab bar + sticky app bar (≤640px only).
5. Convert primary in-page controls (Gross/Net, metric tabs) to segmented /
   thumb-friendly variants *within the media query*.
6. Apply the **sticky-column scroll** table treatment globally (§4.4 tier 1).

**Phase M2 — Hero polish.**
7. Card-reflow the **Latest Leaderboard** (and maybe Latest Round / Records).
8. Mobile chart preset + direct-label race chart.
9. Per-page pass: spacing, tap targets, empty states, safe-area insets.

**Phase M3 — Decide + refine.**
10. Pick the final look from the mockups; delete the unused direction.
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
