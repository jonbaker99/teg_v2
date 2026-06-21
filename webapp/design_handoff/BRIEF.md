# TEG webapp — design brief for Claude Design

A self-contained brief for prototyping new visual themes. **You do not have the codebase** — everything you need is in this folder. Restyle against the attached real pages; do not invent placeholder data.

---

## 1. What the app is

A private golf-tournament analysis website. The tournament is an annual event called **the TEG**; each TEG has ~4 rounds of 18 holes, played by a small fixed group of friends. The site is the group's record book: leaderboards, scorecards, player rankings, records & personal bests, statistical tables and charts, and written tournament reports.

- **Audience**: small, knowledgeable, returning. They care about clarity and accuracy, not marketing gloss.
- **Desired feel**: clean, editorial, professional — an **almanac / record book**, not a flashy consumer sports app. It should feel considered and quietly authoritative.
- **Density**: pages are data-heavy. Tables can be wide; charts are common; a single page mixes controls, tabs, tables and charts.

## 2. The current design system (the starting point)

A mature, **CSS-custom-property-driven** system. The structure is fixed in `css/base-vars.css`; the *look* comes entirely from a small token set re-declared per theme. Two themes exist today:

- **`clean-page`** (default) — a single white content surface floating on a warm grey page. Editorial serif headings (Lora) + monospace data (Roboto Mono), one forest-green accent. *This is the basis for Direction 1.*
- **`clean-layered`** — three stacked surfaces (stone → taupe panel → white cards); each content block sits in its own white card with a soft shadow. *This is the basis for Direction 2.*

Light/dark mode is **orthogonal** to the theme: a `mode` toggle flips `html[data-mode="dark"]`, which re-points the same tokens. See screenshots for both.

## 3. What I want you to design

Two **base directions**, each a complete and consistent visual language (not a one-off page):

### Direction 1 — "Refined Clean Page"
A more polished, professional evolution of the current default. Keep the core idea: a single white/neutral content surface on a quiet page, editorial serif + monospace data, one confident accent. Improve typographic rhythm, spacing, table styling, the page-title treatment, and overall finish so it reads as a premium record book.

### Direction 2 — "Card"
Every distinct piece of content — a table, a chart, a stat group, a leaderboard — sits in its own **card artifact** on a calm panel background, with clear elevation, consistent corner radius, and a deliberate vertical rhythm between cards. An evolution of `clean-layered`, but more refined and intentional.

### For each direction
Show **2–3 colour/font variants** rendered on the same Results and Player pages so they can be compared side by side. Suggested starting points (propose your own too):
- **Editorial green** — keep the forest-green accent; Lora + Roboto Mono.
- **Professional slate** — cooler neutral greys with a navy/slate accent; a crisp grotesk for headings, mono for data.
- **Warm almanac** — cream/paper background, claret or deep-green accent, a classic serif throughout.

### Unified component system
Design these **once** and show them as a component sheet, then apply them consistently across both directions. These are the repeating controls on every page:

| Component | Current behaviour to preserve |
|-----------|-------------------------------|
| **Primary tabs** | Underline style — text only, active tab gets a 2px accent underline (no filled background). Used for in-page section switching (e.g. TEG Trophy / Green Jacket / Scorecards / Report). |
| **Option / filter pills** | Fully rounded pills in a wrap group. Inactive = bordered, neutral text; active = accent-tinted fill + accent text + heavier weight. Used for chart-type choosers and roster/filter selection. |
| **Buttons / segmented controls** | Bordered; active state inverts (dark fill / light text). |
| **Selects / dropdowns** | 1px border, small radius, accent focus ring. |
| **Badges** | Small inline pills, solid and muted variants. |
| **Stat cards** | Centred large value + small uppercase label. Also a metric grid (4-up → 3-up → 2-up responsive). |
| **Card headers** | Small label sitting above/atop a content card. |
| **Data tables** | Monospace data, 2px header bottom-border, 1px row separators, accent-tinted hover row, optional emphasised top rank. Must handle **wide tables** (horizontal scroll, ideally a sticky first column). |
| **Charts** | Charts are **Plotly** blocks of arbitrary size — design the *frame* around a chart (title, caption, the pill switcher beneath), not the chart internals. |

## 4. Hard constraints (please honour all of these)

1. **Output as CSS custom properties, reusing the exact token names below.** Restyle the *values*; keep the *names*. This is what lets a chosen design drop straight back into the codebase as a new theme file. Don't rename tokens or hard-code colours in component rules.
2. **Light + dark mode** for every direction, implemented as a `html[data-mode="dark"]` override block that re-points the same tokens (see `css/dark.css` for the existing pattern).
3. **Preserve desktop information density.** This is a *refinement*, not a layout teardown. The laptop/iPad render (≈960px content column, the table/chart/tab arrangement in the screenshots) should stay recognisable. Don't drop columns, balloon whitespace, or turn dense tables into sparse cards on desktop.
4. **Mobile (≤640px) should feel app-like** — bottom tab bar, sticky app bar, reflowed data — without changing the desktop render.
5. **Fonts via Google Fonts.** Charts are **Plotly**; tables can be wide. Material Symbols is used for icons.

## 5. Token inventory (restyle values, keep names)

Light defaults (from `css/clean.css`, the baseline `:root`):

```css
:root {
  /* Typography */
  --font-heading: 'Lora', Georgia, serif;
  --font-body: 'Lora', Georgia, serif;
  /* (tables/data use 'Roboto Mono', monospace) */

  /* Page + text */
  --bg-page: #ffffff;
  --bg-card: #ffffff;
  --text-primary: #1a1a1a;
  --text-secondary: #555555;
  --text-muted: #999999;

  /* Nav */
  --nav-bg: #ffffff;
  --nav-text: #555555;
  --nav-text-muted: #999999;
  --nav-hover-bg: #f5f5f5;
  --nav-active-bg: transparent;
  --nav-active-text: #1a1a1a;

  /* Tables */
  --table-font-size: 0.875rem;
  --table-header-bg: transparent;
  --table-header-border: #1a1a1a;
  --table-cell-border: #e0e0e0;
  --table-hover-bg: #F3F7F3;
  --table-hover-text: forestgreen;
  --table-toprank-bg: #F3F7F3;
  --table-toprank-text: inherit;
  --table-stripe-bg: transparent;
  --table-cell-border-width: 1px;
  --table-header-border-width: 2px;

  /* Accent + buttons */
  --accent: forestgreen;
  --btn-active-bg: #1a1a1a;
  --btn-active-text: #ffffff;
  --btn-inactive-bg: #ffffff;
  --btn-inactive-text: #555555;
  --btn-border-radius: 0.25rem;
  --card-radius: 0.375rem;
  --card-shadow: 0 1px 2px rgba(0,0,0,0.06);

  /* Selects */
  --select-bg: #ffffff;
  --select-border: #d0d0d0;
  --select-focus-ring: forestgreen;

  /* Footer */
  --footer-bg: #f8f8f8;
  --footer-text: #999999;

  /* Stat cards */
  --stat-card-bg: #ffffff;
  --stat-card-border: #e8e8e8;
  --stat-card-value-color: #1a1a1a;
  --stat-card-label-color: #999999;

  /* Badges */
  --badge-bg: #1a1a1a;
  --badge-text: #ffffff;
  --badge-muted-bg: #f0f0f0;
  --badge-muted-text: #999999;

  --divider-color: #e8e8e8;
}
```

Dark overrides follow the same names under `html[data-mode="dark"]` (warm near-black `#16150f`, card `#1d1d1a`, text `#ececea`, brightened accent `#6cc77f`) — full block in `css/dark.css`.

## 6. What's in this folder

- `BRIEF.md` — this file.
- `PROMPT.md` — the kickoff prompt to paste into claude.ai/design.
- `pages/` — rendered HTML of three real pages (open in a browser; CSS resolves to `css/`):
  - `contents.html` — the site-map landing page (shell, nav, page title).
  - `results.html` — Results: tab bar + dropdown + leaderboard table + Plotly chart + pill switcher (the densest control+data mix).
  - `player.html` — a player profile: stat cards, trophy cabinet, metric grid, records, trend charts (the most card-dense page).
- `pages/screenshots/` — full-page PNGs of the same three pages: `*-light.png` (current default `clean-page`), `*-dark.png` (dark mode), and `results-card-light.png` / `player-card-light.png` (the existing `clean-layered` card layout — Direction 2's starting point).
- `css/` — the live stylesheets (`base-vars.css` = structure + components; `clean.css`/`clean-page.css`/`clean-layered.css` = token sets; `dark.css` = dark overrides).

## 7. Suggested working order

1. Propose the two directions at a high level — a mini moodboard + token set for each. Pause for feedback.
2. Design the unified component sheet.
3. Render the Results and Player pages in each direction's variants for side-by-side comparison.
