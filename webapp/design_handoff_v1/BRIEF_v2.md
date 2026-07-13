# TEG webapp — design brief v2 (three-theme reimagine)

A self-contained brief for prototyping new visual themes. **You do not have the codebase** — everything you need is in this folder plus the attached pages/screenshots. Restyle against the attached real pages; do not invent placeholder data.

This is a second round. Round 1 (see `BRIEF.md` / `PROMPT.md` in this same folder, kept for reference) produced two directions and three colour variants — "Editorial green," "Professional slate," "Warm almanac" — that came back safe and samey: rounded cards, one muted accent, a serif/mono pairing, gentle shadows. **Do not reproduce that look or anything adjacent to generic AI-generated SaaS design** (soft pastel gradients, glassmorphism, Inter/system-ui everywhere, purple-to-blue accent gradients, oversized rounded corners on everything). This round needs genuinely distinct visual languages, not three palettes wearing the same skeleton.

---

## 1. What the app is

A private golf-tournament analysis website. The tournament is an annual event called **the TEG**; each TEG has ~4 rounds of 18 holes, played by a small fixed group of friends. The site is the group's record book: leaderboards, scorecards, player rankings, records & personal bests, statistical tables and charts, and written tournament reports.

- **Audience**: small, knowledgeable, returning. They care about clarity and accuracy, not marketing gloss.
- **Density**: pages are data-heavy. Tables can be wide; charts are common; a single page mixes controls, tabs, tables and charts.

## 2. The current design system (starting point / constraint, not aesthetic target)

A mature, **CSS-custom-property-driven** system. The structure is fixed in `css/base-vars.css`; the *look* comes entirely from a small token set re-declared per theme. See `css/` in this folder for the live stylesheets, and section 5 below for the full token inventory.

Light/dark mode is **orthogonal** to the theme: a `mode` toggle flips `html[data-mode="dark"]`, which re-points the same tokens.

## 3. The three themes for this round

Each is a **complete, self-consistent visual language** covering: overall page chrome, top-level site navigation, in-page navigation (tabs, filter pills, section switching), and the layout/presentation of prose, data tables, and charts. Within each theme, produce **3 distinct colour + font stylings** — different enough from each other that they wouldn't be mistaken for variants of the same palette, while still clearly belonging to the same theme concept.

### Theme A — "Plain"
Elegant, clean, zero distraction — but still unmistakably professional, not a bare unstyled page. The data is the entire point; every visual choice should recede in service of legibility and scan-ability. Think: a well-typeset reference table, a serious almanac, a well-designed spreadsheet — not a "minimalist startup landing page." Restraint should read as confidence, not as absence of design.

### Theme B — "Editorial"
Reads like a newspaper sports section or a tournament programme: real typographic hierarchy (drop caps, rules, byline-style labels, pull quotes for the commentary reports), column-like rhythm, ink-on-paper colour logic. This can lean further into "print" than the current `clean-page`/`clean-layered` themes do — column rules, small caps, numbered sections — as long as wide tables and charts still work cleanly.

### Theme C — "Striking"
Visually engaging and opinionated — bolder colour, stronger contrast, more confident use of scale and colour-coding in tables/charts (e.g. colour-coded rank tiers, accent-heavy stat cards, a distinctive chart palette) — while staying legible and usable for repeated, serious reference use. This is not "flashy consumer sports app with badges and confetti" — it's "this data deserves to look this good," in the spirit of a well-designed sports almanac infographic or a Bloomberg/FiveThirtyEight data page, not a gambling-app dashboard.

For each of the 3 themes, propose **3 colour/font stylings** and give each a short distinct name (not just "Variant 1/2/3"). Render all 9 combinations on the same Results and Player pages so they're comparable side by side.

## 4. Unified component system

Design once per theme (components can differ *between* the three themes, since they're distinct visual languages — but must be internally consistent across all 3 stylings within a theme) and show as a component sheet:

| Component | Current behaviour to preserve (functionally, not visually) |
|-----------|-------------------------------|
| **Site navigation** | Top-level nav across all pages/sections. |
| **Primary tabs** | In-page section switching (e.g. TEG Trophy / Green Jacket / Scorecards / Report). |
| **Option / filter pills** | Chart-type choosers and roster/filter selection; wrap group, clear active/inactive state. |
| **Buttons / segmented controls** | Bordered controls with a clear active state. |
| **Selects / dropdowns** | Standard form control, clear focus state. |
| **Badges** | Small inline status/label pills. |
| **Stat cards** | Centred large value + small label; also a responsive metric grid (4-up → 3-up → 2-up). |
| **Card headers** | Small label identifying a content block. |
| **Data tables** | Must handle **wide tables** (horizontal scroll, ideally sticky first column) and support rank/tier colour-coding for Theme C. |
| **Charts** | Charts are **Plotly** blocks of arbitrary size — design the *frame* around a chart (title, caption, pill switcher beneath), not the chart internals. |

## 5. Hard constraints (please honour all of these)

1. **Output as CSS custom properties, reusing the exact token names below.** Restyle the *values*; keep the *names*. This is what lets a chosen design drop straight back into the codebase as a new theme file. Don't rename tokens or hard-code colours in component rules. If a theme genuinely needs a token that doesn't exist yet (e.g. a rank-tier colour scale for Theme C), propose new token names following the existing naming convention and call them out explicitly as additions.
2. **Light + dark mode** for every styling, implemented as a `html[data-mode="dark"]` override block that re-points the same tokens (see `css/dark.css` for the existing pattern).
3. **Preserve desktop information density.** This is a *restyle*, not a layout teardown. The laptop/iPad render (≈960px content column, the table/chart/tab arrangement in the screenshots) should stay recognisable. Don't drop columns, balloon whitespace, or turn dense tables into sparse cards on desktop.
4. **Mobile (≤640px) should feel app-like** — bottom tab bar, sticky app bar, reflowed data — without changing the desktop render.
5. **Fonts via Google Fonts.** Charts are **Plotly**; tables can be wide. Material Symbols is used for icons.
6. **No generic AI-design tells**: no purple/blue gradient accents, no glassmorphism, no Inter-everywhere, no excessive rounded-corner-on-everything, no floating soft-shadow cards as the default surface. Each theme should feel like it was designed by someone who thought specifically about golf record-keeping, not a generic dashboard template.

## 6. Token inventory (restyle values, keep names)

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

Dark overrides follow the same names under `html[data-mode="dark"]` (see `css/dark.css` for the existing pattern — do not just invert the light palette, design dark intentionally per styling).

## 7. What's in this folder

- `BRIEF.md` / `PROMPT.md` — round 1 output, kept **only as a "don't repeat this" reference**, not a starting point.
- `pages/` — rendered HTML of three real pages (open in a browser; CSS resolves to `css/`): `contents.html`, `results.html`, `player.html`.
- `pages/screenshots/` — full-page PNGs of the same three pages in light/dark/card variants.
- `css/` — the live stylesheets (`base-vars.css` = structure + components; token files = the values to restyle).

## 8. Deliverable

For each of the 3 themes × 3 stylings (9 total), rendered HTML of the Results and Player pages, plus a shared component sheet per theme. Organise output as `theme-a-plain/{styling-name}/`, `theme-b-editorial/{styling-name}/`, `theme-c-striking/{styling-name}/`, each containing the restyled pages and its token CSS file.
