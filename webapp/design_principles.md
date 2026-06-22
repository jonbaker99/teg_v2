# Design Principles

The webapp should feel like a **printed programme**, not a data dashboard. Every decision should favour editorial clarity over information density.

Reference point: [theelgolfo.com](https://theelgolfo.com) — the existing Streamlit site has this quality. When in doubt, ask: "does this look like a programme or a dashboard?"

## Typography

- **Serif headers** (Lora) — editorial feel, not web-app feel
- **Mono font** (Roboto Mono) for tables only — numbers should look like data
- No mono or sans-serif for prose or headings

## Layout

- Page width is content-driven: `width: fit-content; min-width: min(800px, 90vw); max-width: min(90vw, 1280px)`
- Tables size to content (`width: auto`), not stretched to 100%
- Generous cell padding (~12px) — tables are airy, not dense
- No striping or heavy borders
- **No dark chrome** — nav bar always white/light; avoid dark menus

## Tables

- **Header alignment must match cell alignment** — if data is centred, header is centred
- **Columns have fixed widths** for numeric data (prevents column jitter between datasets)
- **No header background** — just bold text with a 2px bottom border
- **Light cell borders** (1px) — barely visible, just enough to guide the eye
- **Active/top rank** — subtle green tint, bold
- Aim for Datawrapper-like density: tight row spacing, thin borders, generous but not excessive cell padding
- **Player names on narrow screens** — where a player-name column would squeeze the
  data on mobile, emit both a full name and a short `Initial. SURNAME` form (e.g.
  `J. BAKER`) and swap to the short form below the mobile breakpoint via CSS, rather
  than letting names wrap or push data off-screen. Shared helper:
  `teg_analysis/display/scorecards.py:_player_name_spans` (classes `bw-name-full` /
  `bw-name-short`). For very wide tables that can't fit on mobile even when shortened,
  prefer a per-section toggle that shows one subset of columns at a time (see the
  bestball/worstball contribution table's Bestball/Worstball toggle).

## Components

- All inputs (dropdowns, buttons, tabs) follow the same styling language
- Tab underline style only — active tab gets a green underline, no pill background
- Focus rings green (forestgreen accent colour)

## Themes and layouts

Optimise primarily for the **Clean** theme. After any template or CSS change, verify both layouts still work:

- **Layout 1** (flat): Clean, Clean Page — single surface, no depth
- **Layout 2** (layered): Clean Layered — 3-layer visual hierarchy

The `.data-card` class is a **no-op in Layout 1**. Templates that wrap data output in `.data-card` work correctly in both layouts. Preserve this invariant when editing templates or CSS.

### CSS: `!important`

Only use `!important` when the logic genuinely requires it — not to brute-force a style outcome. The reasoning must be clear, and each use must be commented so it's traceable when debugging. Current known exceptions are noted in the relevant CSS files.

### CSS: comments must not contain `*/`

A `/* … */` comment whose **text** contains the sequence `*/` (e.g. writing
`(mb-*/mt-*)` in prose) closes the comment **early** — the browser then parses
the leftover prose as a bad selector and its error-recovery silently **drops the
next rule**. This once disabled the entire `.section-nav` rule with no visible
error (`tinycss2` and most linters don't catch it). When a comment needs to
mention utility globs, reword to avoid `*/` — e.g. `mb-*/mt-*` → `mb-, mt-`.

A guard enforces this: `python scripts/check_css_comments.py` scans the theme
CSS as a state machine and fails on any orphan `*/` (a comment that closed
early). It runs automatically on session start via the `SessionStart` hook in
`.claude/settings.json`.

## Structural class hierarchy

`.data-card` is the **data-display level** of a wider, consistent
**Page → Section/Tab → Data-display** wrapper hierarchy applied across every
template (`.section-nav`, `.section-controls`, `.toggle-group`,
`.section-panel`, `.data-card`, `.chart-container`, plus `.tab-underline--active`
for in-page tabs and `.text-link` for inline links). The canonical table and
per-class rules live in
[README.md → Structural class hierarchy](README.md#structural-class-hierarchy).

### Spacing is centralised on the section wrappers

The section wrappers **own the page's vertical spacing rhythm** in
`base-vars.css` — they are no longer layout-neutral:

- `.section-controls` carries `margin-bottom: 1.5rem` and `.section-nav`
  carries `margin-bottom: 2rem` (a tab bar reads as a stronger divider, so its
  panel/heading needs more separation), plus their own flex/gap defaults — so
  the gap below a filter row or tab bar is identical on every page.
- `.toggle-group` owns `margin-bottom: 1rem` (the gap before the data it
  controls), and `.data-card + .toggle-group` adds `1.5rem` above a toggle row
  that follows a data block (e.g. a chart-variant toggle between a table and its
  chart). Templates must NOT hand-roll `mb-*`/`mt-*` on toggle rows — to kill the
  gap in a one-off, use inline `style="margin-bottom:0"` (see `scoring_birdies`).
- `* + .section-title` and `.data-card + .data-card` add a `1.5–1.75rem` gap
  between stacked sections/cards automatically.
- Layout intent that legitimately varies per row (`justify-between`,
  `items-center` vs `items-end`, `gap-*` overrides) is still expressed with
  Tailwind utilities on the element and overrides the central defaults.

**Do NOT add vertical-margin utilities (`mb-*` / `mt-*` / `my-*`) to any of the
six rhythm-owning classes** — `.section-nav`, `.section-controls`,
`.toggle-group`, `.section-title`, `.data-card`, `.card-header`. Their vertical
spacing is owned centrally in `base-vars.css`; a utility on the element silently
overrides it (see below), reintroducing the per-page drift this convention
exists to prevent. To suppress a gap in a nested/edge case, use an inline
`style="margin-bottom:0"` (as in `results.html` / `bestball.html`).

> **Why a leftover utility wins.** The webapp loads Tailwind via the Play CDN
> (`cdn.tailwindcss.com`), which injects its generated utilities as a `<style>`
> block at the **end of `<head>`** — after `base-vars.css`. A utility (`.mb-3`)
> and a rhythm class (`.toggle-group`) have equal specificity, so the later
> source order wins: the Tailwind block always does. That's why a single stray
> `mb-*` makes a global spacing change appear to "not take effect" on that
> element. Keep the six classes free of margin utilities and the central rule is
> authoritative everywhere.

Content-level spacing on **non-rhythm** elements (prose `<p>`, dividers `my-6`,
page-intro text) is legitimate and stays inline — it was never part of the
centralised wrapper rhythm.

## Data-card pattern (Clean Layered)

The Clean Layered theme uses three visual layers:

1. **Outer background** — warm stone `#e0ddd8`
2. **Page panel** — warm taupe `#f5f3f0`
3. **Data cards** — white `#ffffff`, applied selectively around data output

### Decision rule

> If removing the card means the user can't see data → it's a control or label (stays on the panel). If it **is** the data → it gets a card.

### What goes on a data card

- Data tables (`teg-table`, `records-table`)
- Charts / Plotly figures
- Any dense data output

### What stays on the panel (no card)

- Selectors, dropdowns, filters
- Tab navigation
- Page subtitle text
- Section titles and in-page headers
- Champion/spoon announcements
- Prose or explanatory text

### Implementation

Wrap only the data output in `<div class="data-card">`. Text, titles, and controls stay outside.

```html
<!-- Table — no padding modifier needed -->
<div class="data-card">
  <div style="overflow-x: auto;">{{ table_html | safe }}</div>
</div>

<!-- Chart — needs vertical padding modifier -->
<div class="data-card data-card--padded">
  <div id="my-chart" style="width:100%; height:350px;"></div>
</div>
```

`.data-card` has zero vertical padding by default — table rows self-pad via cell padding. Use `.data-card--padded` for non-tabular content (charts, text blocks).

For HTMX partials, either put `.data-card` on the swap target in the parent template, or inside the partial itself — both patterns are used. See `templates/leaderboard.html` (Option A: card on swap target) and `templates/partials/leaderboard_table.html` (Option B: card inside partial).

### CSS classes

| Class | File | Purpose |
|---|---|---|
| `.data-card` | `clean-layered.css` | White card styling (bg, shadow, padding, margin) |
| `.data-card--padded` | `clean-layered.css` | Adds vertical padding for non-tabular content |
| `.data-card` base | `base-vars.css` | Empty rule — no-op in non-layered themes |
