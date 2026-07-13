# Design Principles

The webapp should feel **lo-fi and data-forward** — like a well-kept scorecard or a terminal, not a magazine or a SaaS dashboard. Mono-first, quietly confident, never try-hard, while still respecting real aesthetics: restraint, alignment, honest empty states, one meaningful accent.

> **Direction note (2026-07):** this supersedes the earlier "printed programme /
> serif-first" framing. The site is moving to the lo-fi mono vibe below,
> page by page (the `/player` roster is the reference implementation). Where you
> still see serif-editorial styling, treat it as *not yet converted*, not as the
> target. The one intentional serif survivor is the top page title (masthead).

## Design vibe

Paste-ready brief for converting a page (or judging a new one). The gut check:
*does this look like it's trying to impress, or like it quietly does the job well?* Aim for the second.

**Typography**
- **Roboto Mono is the workhorse.** Data values, metric labels, meta lines, subtitles, and repeated item/card headings (e.g. player names) are all mono. Mono is the default, not the exception.
- **Avoid serif.** Serif is reserved for one deliberate masthead moment (the top page title) — never for data, repeated headings, or anything appearing more than once on a page. When in doubt, mono.
- **Hierarchy comes from weight + size + colour, not font-switching.** Values ~600 weight in the primary text colour; labels small, uppercase, letter-spaced, muted.

**Restraint (the "not try-hard" part)**
- **No decorative identity chrome** — no avatars, monogram circles, initials-in-bubbles, or filler icons added just to fill space.
- **No redundant affordances** — if the whole card is a link, don't also add a "View profile →" CTA. Let the element be the affordance.
- **Cut the sell.** No "dive into your career", no four-item em-dash lists, no adjectives doing marketing. Copy is short, factual, faintly wry.
- **One accent colour, one job.** Green means *honours/silverware* — don't also spend it on borders, CTAs, icons and hover text at once. When an accent means something, keep it meaningful.

**Surfaces & layout**
- **Cards float directly on the page background** as their own surfaces — avoid nesting cards inside a big panel-within-a-panel.
- **Thin single rules, not heavy frames.** One 1px divider beats a boxed, dotted-rule strip.
- **Everything aligns to a shared column with a consistent gutter** — content never sits flush against the viewport edge; titles and content share the same left edge.
- **Let data breathe** — modest, even spacing; don't cram.

**Honesty & polish**
- **Real empty states** — show `–` or "No silverware yet", never hide or fake a value.
- **Subtle feedback** — a small lift + accent border on hover is enough.
- **Theme-variable driven** — style with the CSS vars so light *and* dark both work; don't hardcode colours.

**Quick checklist**
- [ ] Data, labels, meta, and repeated headings in **mono**; serif only on the top page title
- [ ] No avatars / monograms / filler icons
- [ ] No CTA duplicating an already-clickable element
- [ ] Copy trimmed — factual, short, no marketing cadence
- [ ] Accent colour has exactly one meaning on the page
- [ ] Cards on the background, not boxed inside another panel
- [ ] Thin rules over heavy frames/dotted strips
- [ ] Consistent gutter; nothing flush to the edge
- [ ] Honest `–` empty states
- [ ] Colours from theme vars (light + dark both checked)

### Starter prompt — convert a page

Paste this into a fresh conversation (fill in the bracket) to kick off a
vibe conversion for one page:

> Apply our **Design vibe** to the `[PAGE — e.g. /player/{code} profile, or /teg-history]` page.
>
> First read `webapp/design_principles.md` — start with the **Design vibe** section (the lo-fi / mono-first direction + checklist). That's the target; the `/player` roster (`webapp/templates/player_index.html`) is the reference implementation to match.
>
> Then:
> 1. Look at the page as it renders now (route + template + the CSS it uses) and tell me, briefly, where it currently breaks the vibe — serif where it should be mono, decorative chrome, redundant CTAs, marketing-y copy, misused accent colour, boxed/heavy surfaces, edge alignment.
> 2. Propose the changes against the checklist before editing. Flag anything that's a judgement call or a shared component (so we don't accidentally restyle other pages), and ask if a change would affect more than this page.
> 3. Make the changes on a fresh branch off `main`, keeping them scoped to this page unless a fix is genuinely global (like the page-gutter fix was) — in which case flag it as global first.
> 4. Verify by actually rendering the page (launch the app, screenshot narrow + wide) before committing. Match existing patterns; reuse theme CSS vars so light + dark both work.
> 5. Commit, push, open a **draft PR**. Don't merge unless I say so.
>
> Keep the "not try-hard" spirit: quiet, data-forward, honest empty states, one meaningful accent. Ask before assuming.

Optional add-ons depending on the page:

- **Data-table heavy:** "Respect the Tables section below — mono numerics, thin borders, and the narrow-screen name-shortening / horizontal-scroll approach; don't let content run off the edge."
- **Look before code:** "Show me a quick mockup or describe the layout first; don't touch files until I approve the direction."

## Typography (mechanics)

- **Roboto Mono** is the default UI/data face — values, labels, meta, subtitles, repeated headings.
- **Serif (Lora)** only on the top page title (`.page-title`). Not for prose, data, or repeated headings.
- **Captions** — explanatory/footnote text beneath tables and charts uses the `.caption`
  class (defined in `themes/base-vars.css`). Use it rather than ad-hoc `text-muted`/`text-sm`
  combinations. *Note: `.caption` is still serif from the pre-conversion styling — a candidate
  to move to mono/sans as the vibe rolls out; update the class, not individual call sites.*

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
- **Row highlight on hover by default** — every data table should tint the hovered
  row using `var(--table-hover-bg)` (themed light + dark). `.teg-table` gets this for
  free; bespoke tables (scorecards, the contribution bar table) must opt in. Where
  cells carry their own background (e.g. scorecard shape cells), tint those cells on
  `tr:hover` so the highlight isn't masked.
- Aim for Datawrapper-like density: tight row spacing, thin borders, generous but not excessive cell padding
- **Player names on narrow screens** — where a player-name column would squeeze the
  data on mobile, emit both a full name and a short `Initial. SURNAME` form (e.g.
  `J. BAKER`) and swap to the short form below the mobile breakpoint via CSS, rather
  than letting names wrap or push data off-screen. Shared helper:
  `teg_analysis/display/scorecards.py:_player_name_spans` (classes `bw-name-full` /
  `bw-name-short`). For wide tables that can't fit on mobile even when shortened,
  prefer splitting into separate tables that sit side by side and wrap to stacked
  when narrow (see the bestball/worstball Bestball and Worstball contribution tables).

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
