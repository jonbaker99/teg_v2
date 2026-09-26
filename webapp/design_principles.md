# Design Principles

The webapp should feel **lo-fi and data-forward** — like a well-kept scorecard or a broadsheet masthead, not a magazine or a SaaS dashboard. Quietly confident, never try-hard, while still respecting real aesthetics: restraint, alignment, honest empty states, one meaningful accent.

 **Typography direction (2026-09-19):** two families, each with one clear job
 — Lora for titles and structural labels, Inter for the tab bar and all
 content. See the **Typography** bullet below and **Typography (mechanics)**
 further down for the full role table. This replaces both an earlier
 "mono-first" direction and, before that, a "serif-first" one; where a page
 still doesn't match, treat it as *not yet converted*, not as the target.
 The `/player` roster is the reference implementation for the rest of the
 vibe (surfaces, restraint, no decorative chrome).

## Design vibe

Paste-ready brief for converting a page (or judging a new one). The gut check:
*does this look like it's trying to impress, or like it quietly does the job well?* Aim for the second.

**Typography**
- **Two families, one job each.** Lora (serif) is for titles and structural labels: site title, main nav, page title, and every section/card heading (`.section-title` / `.chart-title` / `.card-header`, set small-caps). Inter (sans) is for everything else: the tab bar and all table/page content. A third family (mono) was considered for the tab bar and rejected — it would decorate one small UI strip rather than serve a genuinely distinct content type, the one thing that earns a typeface its place here (see Typography (mechanics) below).
- **The tab bar's hierarchy signal is case, not a typeface.** It stays Inter but goes small-caps (uppercase, `letter-spacing: 0.02em`, sized down slightly to `0.8125rem` since caps read larger/heavier than mixed case at the same size) — the same device Lora's subheaders use, so both halves of the system read as one convention rather than two.
- **Table/metric numbers stay Inter with tabular figures** (`font-variant-numeric: tabular-nums`, set once globally on `body`), which is what gives digits mono-style column alignment without an actual monospace face.
- **Hierarchy comes from weight + size + colour + case, not adding fonts.** Values ~600 weight in the primary text colour; labels small, uppercase, letter-spaced, muted.

**Restraint (the "not try-hard" part)**
- **No decorative identity chrome** — no avatars, monogram circles, initials-in-bubbles, or filler icons added just to fill space.
- **No redundant affordances** — if the whole card is a link, don't also add a "View profile →" CTA. Let the element be the affordance.
- **Cut the sell.** No "dive into your career", no four-item em-dash lists, no adjectives doing marketing. Copy is short, factual, faintly wry.
- **One accent colour, one job per render.** Green has four sanctioned jobs on the shipped site — *honours/silverware*, *live tournament status* (Contents' `IN PROGRESS` eyebrow, I5), *active selection* (`.tab-underline`'s active-tab underline, and the small-caps `.section-title`/`.card-header`/`.chart-title` heading colour, a named exception kept as-is), and *top-rank emphasis* (the leaderboard/records top-rank row tint) — but never two of them on the same render: a page in progress marks the eyebrow green and keeps leader names ink (they're provisional positions, not honours yet); a complete page marks the winners' names green and keeps the eyebrow muted. Don't spend green on borders, CTAs, or hover text beyond these roles. The three foundation controls (`.tab-underline`, `.segmented .seg-option`, `.action`) use `--focus` (= `--ink`), not green, for their keyboard focus ring — an identical-to-"selected" ring on a green-selected segment is a real bug (see Components → Hit areas).

**Surfaces & layout**
- **Cards float directly on the page background** as their own surfaces — avoid nesting cards inside a big panel-within-a-panel. This means dissolving the *outer* panel, not removing card/section surfaces altogether: each group of content still needs a bounded surface (a card, or a clearly-divided section) to read as a distinct unit. A page where everything sits directly on the background with no grouping reads as an undifferentiated data dump, not a clean overview — that's the opposite of the goal. (Seen in practice: `/player/{code}`'s first conversion attempt over-applied this and lost all definition — see `webapp/TODOS.md` → Player Profiles.)
- **Thin single rules, not heavy frames.** One 1px divider beats a boxed, dotted-rule strip.
- **Everything aligns to a shared column with a consistent gutter** — content never sits flush against the viewport edge; titles and content share the same left edge.
- **Let data breathe** — modest, even spacing; don't cram.

**Honesty & polish**
- **Real empty states** — show `–` or "No silverware yet", never hide or fake a value.
- **Subtle feedback** — a small lift + accent border on hover is enough.
- **Theme-variable driven** — style with the CSS vars so light *and* dark both work; don't hardcode colours.

**Quick checklist**
- [ ] Titles and section/card headings in **Lora, small-caps**; tab bar in **Inter, small-caps**; everything else (data, prose, table content) in plain-case Inter; table numbers use tabular figures, not a mono face
- [ ] No avatars / monograms / filler icons
- [ ] No CTA duplicating an already-clickable element
- [ ] Copy trimmed — factual, short, no marketing cadence
- [ ] Accent colour carries only one of its sanctioned jobs (honours, live status, active selection, top-rank emphasis) per render — never two at once
- [ ] Cards/sections on the background (not boxed inside another panel) — but each still has a bounded surface; nothing floats with zero definition
- [ ] Elements align to a shared column/rhythm — no unplanned horizontal spacing
- [ ] Thin rules over heavy frames/dotted strips
- [ ] Consistent gutter; nothing flush to the edge
- [ ] Honest `–` empty states
- [ ] Colours from theme vars (light + dark both checked)

### Starter prompt — convert a page

Paste this into a fresh conversation (fill in the bracket) to kick off a
vibe conversion for one page:

 ```text
 Apply our **Design vibe** to the `[PAGE — e.g. /player/{code} profile, or /teg-history]` page.

 First read `webapp/design_principles.md` — start with the **Design vibe** section (the lo-fi / mono-first direction + checklist). That's the target; the `/player` roster (`webapp/templates/player_index.html`) is the reference implementation to match.

 Then:
 1. Look at the page as it renders now (route + template + the CSS it uses) and tell me, briefly, where it currently breaks the vibe — serif where it should be mono, decorative chrome, redundant CTAs, marketing-y copy, misused accent colour, boxed/heavy surfaces, edge alignment.
 2. Propose the changes against the checklist before editing. Flag anything that's a judgement call or a shared component (so we don't accidentally restyle other pages), and ask if a change would affect more than this page.
 3. Make the changes on a fresh branch off `main`, keeping them scoped to this page unless a fix is genuinely global (like the page-gutter fix was) — in which case flag it as global first.
 4. Verify by actually rendering the page (launch the app, screenshot narrow + wide) before committing. Match existing patterns; reuse theme CSS vars so light + dark both work.
 5. Commit, push, open a **draft PR**. Don't merge unless I say so.

 Keep the "not try-hard" spirit: quiet, data-forward, honest empty states, one meaningful accent. Ask before assuming.
 ```

Optional add-ons depending on the page:

- **Data-table heavy:** "Respect the Tables section below — tabular-figure numerics (not mono), thin borders, and the narrow-screen name-shortening / horizontal-scroll approach; don't let content run off the edge."
- **Look before code:** "Show me a quick mockup or describe the layout first; don't touch files until I approve the direction."

## Typography (mechanics)

Role table (2026-09-19 direction — Lora for titles/structural labels, Inter for the tab bar
and content; a third, mono, typeface was considered for the tab bar and rejected, see the
Typography bullet above):

| Element | Font | Case |
|---|---|---|
| Site title (`.nav-brand`), main nav (`.nav-link`, dropdown) | `--font-serif` (Lora) | as written |
| Page title (`.page-title`) | `--font-serif` (Lora) | as written |
| Section/card headings (`.section-title`, `.chart-title`, `.card-header`) | `--font-serif` (Lora) | small-caps |
| Tab bar (`.tab-underline`) | `--font-sans` (Inter) | small-caps |
| Table/page content, prose, player names | `--font-sans` (Inter) | as written |
| Table/metric numbers | `--font-table` (Inter, tabular figures) | as written |

- **`--font-table` is a separate token from `--font-sans`** (both currently Inter) so table
  content can diverge from body text again later without touching `--font-sans` call sites.
  Tabular figures (`font-variant-numeric: tabular-nums lining-nums`, set once globally on `body`
  in `base-vars.css`) are what give digits mono-style column alignment without an actual
  monospace face — there is no real mono font loaded for data content any more.
- **Why not mono for the tab bar:** a typeface earns its place by serving a genuinely distinct
  *content* type (Lora = identity/structure, Inter = content, Inter-tabular = numeric data). A
  fourth or fifth face used only in a handful of short nav labels decorates one UI strip rather
  than serving a role — small-caps Inter gets the same "this is structural chrome" signal from
  case alone, echoing Lora's small-caps headings, so both halves of the system read as one
  convention. See `README.md`'s font-system section for the fuller decision history (Roboto
  Mono → Inter, then Inter → Lora for headings) and the dev-only `/design/fonts` /
  `/design/headers` comparison tools if this needs revisiting.
- **Captions** — explanatory/footnote text beneath tables and charts uses the `.caption`
  class (defined in `themes/base-vars.css`). Use it rather than ad-hoc `text-muted`/`text-sm`
  combinations. *Note: `.caption` is still sans, unlike the headings above it — a candidate to
  reconcile if it reads inconsistent in practice; update the class, not individual call sites.*

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
  data on mobile, emit both a full name and a short `Initial.SURNAME` form (e.g.
  `J.BAKER`) and swap to the short form below the mobile breakpoint via CSS, rather
  than letting names wrap or push data off-screen. Shared helper:
  `teg_analysis/display/scorecards.py:_player_name_spans` (classes `bw-name-full` /
  `bw-name-short`; the display-toggle CSS itself lives in `webapp/static/mobile.css`,
  loaded on every page, not just the scorecard bundle). Rolled out site-wide
  2026-09-21 — see `webapp/TODOS.md`'s "Roll out mobile name shortening" entry for
  the full list of pages and the one accepted remaining edge case.
  Prefer freeing room over shortening: every `/records` tab stacks full names under
  the record label instead, at every width (`_build_stacked_records_list`, `webapp/routes/records.py`). Generic
  `df_to_html`-rendered tables opt in with `webapp/tables.py::df_to_html(...,
  shorten_players=True)`; bespoke table renderers call `_player_name_spans`
  directly. For wide tables that can't fit on mobile even when shortened,
  prefer splitting into separate tables that sit side by side and wrap to stacked
  when narrow (see the bestball/worstball Bestball and Worstball contribution tables).

### Mobile table pattern — the reference implementation

The `/latest-round` Scoreboard tab's "Round leaderboard" table (built by
`_build_scoreboard_table` in `webapp/routes/latest.py`, styled by
`table.leaderboard` rules in `webapp/static/mobile.css` under the `≤640px`
media query) is the best-practice reference for mobile tables on this site.
When a future page converts its table to phone-friendly markup, copy these
selectors/values directly rather than reinventing them.

| Concern | Selector / rule | Why |
|---|---|---|
| Full-bleed surface | `.latest-round-page` sets `--lr-inset: 12px`; `#lr-content table.leaderboard { width: 100% }` while surrounding controls (`.section-title-row`, `.lr-chart-tools`) carry `margin: … var(--lr-inset)` | The table itself runs edge-to-edge for maximum column width; only the chrome around it keeps a gutter |
| Fixed proportional columns | `<colgroup>` with `.lr-rank-col` 7%, `.lr-player-col` 27%, `.lr-total-col` 18%, `.lr-personal-col`/`.lr-alltime-col` 19% each, `.lr-toggle-col` 10%; table has `table-layout: fixed` | Percentage widths via `colgroup` are stable regardless of content length, unlike `nth-child` or auto layout, and read as a deliberate hierarchy (Total is 18% but visually dominant — see typography below) |
| Typography | `th`: `font: 700 11px/1.2 var(--font-table)`, `letter-spacing: .03em`, `text-transform: uppercase`, muted colour; `td`: `font-family: var(--font-table)`, `font-variant-numeric: tabular-nums`, 14px table default | Uppercase/tracked/muted headers read as structural chrome, not data; tabular-nums keeps numeric columns vertically aligned without a mono font |
| Density | `td { padding: 12px 5px }`, first/last columns `padding-inline: 2px` | Airy enough for a 44px tap target on the toggle row without wasting width on narrow numeric columns |
| Primary column | `.lr-total-cell { font-size: 1.15em; font-weight: 700 }` (accent colour on the leader row) | The Total is the number a player scans for first — it must out-weigh every other cell |
| Secondary column | `.lr-rank-context { color: var(--text-muted) }`; the `/` denominator is wrapped in `<small>` via the `rank_cell()` helper | Personal/All-time rank are context, not the headline stat — demoted by colour and by shrinking the least useful half of "n/N" |
| Player name handling | `<td class="lr-player-cell">` wraps `_wrap_player_name()`'s `<span class="player-name">` — the class lives on the inner span, never the `<td>` | **Real bug already hit**: putting `.player-name`'s `display: inline-block` rule on the `<td>` itself (by reusing the class there) broke the cell's table-cell layout — it shrink-wrapped to content width, leaving a gap that looked like a missing border segment. See the comment at `webapp/routes/latest.py` (`_build_scoreboard_table`, the `<td class='lr-player-cell'>` line) — keep cell-layout classes and text-wrapping classes on separate elements |
| Row shading | `tr.rank-1 { background-color: var(--table-toprank-bg) }`, bold text, accent colour on rank + total cells; class is applied whenever `Rank` (post-tie-suffix-strip) is `"1"` | Highlights the leader, not alternating rows — zebra striping adds visual noise with no informational value; ties must all get the shading, not just the literal top row |
| Expandable detail row | `.rank-toggle` button (`aria-expanded`, `aria-controls`) in its own narrow toggle column; `tr.rank-detail-row[hidden]` holds a `.detail-grid` (Out/In) plus `.detail-mix` — collapsed by default | Tier-3 "priority columns" (per `MOBILE_PLAN.md` §4.4) done properly: secondary numbers are hidden but reachable one tap away, not deleted or forced into horizontal scroll |

**Pitfalls already hit and fixed here — don't repeat them:**
1. **Cell-layout class vs. text-wrap class collision** (above) — a shared class
   used for two different purposes (table-cell display vs. inline-block
   name-wrapping) broke layout when both were applied to the same element.
2. **`table-layout: fixed` silently overflows, it doesn't expand.** The
   "Personal rank"/"All-time rank" headers are wider than their column's fixed
   width; a 375px screenshot showed the header text bleeding into the next
   column instead of the column growing to fit. Fixed by adding
   `white-space: normal; overflow-wrap: anywhere;` to `table.leaderboard th`
   (`webapp/static/mobile.css`) so headers wrap onto a second line instead of
   overflowing. Any fixed-width column whose header text is longer than its
   content needs the same treatment.

**Preconditions — this pattern is not a default for every table.** It fits
tables with roughly ≤6 columns, one clearly-primary numeric column, and short
cell values. Wider stat tables belong to a different tier from
`MOBILE_PLAN.md` §4.4 "Tables on mobile" — sticky-column horizontal scroll
(tier 1, the site-wide default for `.teg-table`) or card reflow (tier 2, hero
tables only). Don't force a wide table into this fixed-column layout; move it
to sticky-scroll or card reflow instead.

### Second mobile table reference: one row, two renderings (I1 standings)

`/leaderboard` and `/results`' standings table (`partials/_standings_table.html`,
fed by `_standings_rows` in `webapp/routes/history.py`) is the site's second
proven mobile table treatment, and a different shape from the pattern above:
the *number of data columns varies per TEG* (3–4 round columns depending on
how many rounds were played), so a fixed-proportion `<colgroup>` per column
doesn't fit. Instead, each `<tr>` emits its round values **twice** — once as
ordinary `<td class="col-round">` cells, once as a `.standings-rounds` text
strip inside the player cell — and CSS shows exactly one copy per viewport
(`.col-round` hidden and `.standings-rounds` shown at ≤640px, and the reverse
above it; `base-vars.css` + `mobile.css`). Only Rank, Player and Total keep
fixed widths; round columns collapse entirely rather than shrinking.

This trades a small amount of duplicated markup for a renderer that never
needs to know the round count in advance, and — because both copies come
from the same `r.rounds` loop in one Jinja partial — the two can't drift
apart the way two separately-maintained partials (or a card partial fed by a
second, separately-built context key) could. Reach for this shape when a
table's column count is genuinely data-dependent; reach for the fixed
`<colgroup>` pattern above when it's fixed and known.

**Pitfall avoided here, worth remembering:** this table previously had a
third rendering path — a phone-only card list (`.lb-cards`/`.lb-card`) fed by
a *second* context key (`lb_cards`) built by duplicating the same row logic.
It shipped for a full stage (R3.2) before anyone noticed a later CSS rule
(`.standings-page .lb-cards { display: none }`) always won on specificity,
making it dead at every viewport. Two independently-maintained renderings of
the same data is exactly the shape that produces silent drift — the fix
(I1) was to make one Jinja loop responsible for both visible states, not to
better-coordinate two of them.

## Components

- All inputs (dropdowns, buttons, tabs) follow the same styling language
- Tab underline style only — active tab gets a green underline, no pill background
- Focus rings green (forestgreen accent colour) sitewide by default — **except**
  the three foundation control patterns below (`.tab-underline`, `.segmented`
  `.seg-option`, `.action`), which use `--focus` (= `--ink`) instead: a
  keyboard ring identical to "selected" is a real bug on a green-selected
  segment. See **Hit areas** and `C1b-handoff.md` §3 (decision F3).

### Public read-state contract

Public tabs represent views and use `.tab-underline`. Mutually exclusive measures use `.segmented > .seg-option`. Compact buttons such as Retry represent actions and use `.action`; pills remain appropriate for dense filter values rather than view or measure semantics.

A measure row with three or more options adds `.segmented--grid`. Below 640px that reflows the joined bar into an even two-column grid of separately bordered options, because four labels as long as "Gross vs Par" wrap and leave the bar ragged and too tall on a phone. Above 640px the modifier does nothing. Latest Round's and Latest TEG's metric rows both use it; the older `.metric-grid`/`.metric-pill` pair they used to share is retired.

Read-only HTMX pages opt into the shared contract by declaring their canonical query keys on `<body data-public-state-keys="…">`. Every full-page handler must accept and render the same state as its partial endpoint, with invalid values normalised safely, so a copied canonical URL reproduces the confirmed view.

`static/ui-polish.js` treats the server-rendered DOM as confirmed state. A request may put its target into `aria-busy`, but it must not insert an in-flow loading treatment or fade the confirmed view. Selected controls and URL history change only after the main target swaps successfully. Discrete choices push one history entry; continuous text, number and range controls replace the current entry. Back and forward reload the canonical URL.

A failed transport or a partial marked `data-public-response-error` leaves the prior view and URL intact, restores confirmed control values, and exposes the shared Retry action. Retry replays the exact failed GET, remains in place while that request is pending, and cannot be double-fired. Public partial error branches include `partials/_public_response_error.html`; write requests never enter this contract.

Latest Round is the bounded exception. Its audited pending/confirmed controller remains authoritative; shared I2 work changes only its feedback styling unless that state machine is explicitly reopened and re-audited.

### Hit areas: two-tier, not a flat 44px minimum

**Correction (2026-09-20, C3):** this file previously implied a single 44px
floor for every interactive control (see the Latest Round scoreboard table's
44px toggle target, still correct as far as it goes). That's a touch-device
rule, not a universal one — the actual contract, resolved during the C1
review after finding the shipped desktop `.rank-toggle` (28×28px, F1/F6b)
already didn't match the stated flat rule:

- **`@media (pointer: coarse)` or ≤640px** → **44×44px minimum** (touch)
- **fine pointer / ≥641px** → **28×28px minimum** for icon-only controls
  (e.g. `.rank-toggle`, `.action`), **36px height** for labelled controls
  (e.g. `.tab-underline`, `.seg-option`)

The rule was wrong, not the shipped code. Two site-wide phone defaults still
fall short of the 44px touch floor and remain open — `.pill` and
`.section-controls select` are 40px by default (`mobile.css:358`, `:366`),
reaching 44px today only through page-scoped overrides; fixing the two
default rules is C4's, not this correction's.

### Toggle switches: check the "off" state, not just the "on" state

The `.scale-switch` track/thumb component (base-vars.css) colours its
`aria-checked="true"` state with `var(--accent)` and leaves `false` at
`var(--btn-inactive-bg)` — `#ffffff` on Clean, identical to `--bg-card`. On a
white card that unchecked track is only a 1px grey outline: it reads as
missing/broken, not as "off". This has bitten the live site before (the
original `.scale-switch` itself needed this fix) and again on the
Leaderboard/Results Net-Gross toggle (`.measure-toggle`).

Before shipping any new toggle: render both states side by side against the
actual card background and confirm the unchecked state is still visibly a
control. Two fixes, pick based on the semantics:

- **A genuinely binary on/off toggle** (e.g. a scale mode with a real
  default): keep the accent-on-checked pattern, but give the unchecked track
  a real fill (not `--btn-inactive-bg`) — e.g. `var(--table-toprank-bg)`.
- **A toggle between two equally-weighted options** (e.g. Net/Gross, where
  neither side is "better"): don't recolour the track by state at all — same
  track fill and same thumb colour in both states, so the control never
  implies one option is active/correct and the other isn't. See
  `.measure-toggle` in base-vars.css for the pattern.

## Themes and layouts

Design and verify routine UI changes against **Clean Page**, in light and dark modes. **Clean Layered is mothballed**: do not include it in routine browser checks or expand implementation scope to support it unless the user explicitly requests work on that layout.

The `.data-card` class remains a no-op in Clean Page. Retain semantic wrappers where useful; the old layered styles remain available as historical code, not an active design target.

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

 **Why a leftover utility wins.** The webapp loads Tailwind via the Play CDN
 (`cdn.tailwindcss.com`), which injects its generated utilities as a `<style`
 block at the **end of `<head`** — after `base-vars.css`. A utility (`.mb-3`)
 and a rhythm class (`.toggle-group`) have equal specificity, so the later
 source order wins: the Tailwind block always does. That's why a single stray
 `mb-*` makes a global spacing change appear to "not take effect" on that
 element. Keep the six classes free of margin utilities and the central rule is
 authoritative everywhere.

Content-level spacing on **non-rhythm** elements (prose `<p`, dividers `my-6`,
page-intro text) is legitimate and stays inline — it was never part of the
centralised wrapper rhythm.

## Data-card pattern (Clean Layered)

The Clean Layered theme uses three visual layers:

1. **Outer background** — warm stone `#e0ddd8`
2. **Page panel** — warm taupe `#f5f3f0`
3. **Data cards** — white `#ffffff`, applied selectively around data output

### Decision rule

 If removing the card means the user can't see data → it's a control or label (stays on the panel). If it **is** the data → it gets a card.

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

Wrap only the data output in `<div class="data-card"`. Text, titles, and controls stay outside.

```html
<!-- Table — no padding modifier needed --
<div class="data-card"
  <div style="overflow-x: auto;"{{ table_html | safe }}</div
</div

<!-- Chart — needs vertical padding modifier --
<div class="data-card data-card--padded"
  <div id="my-chart" style="width:100%; height:350px;"</div
</div
```

`.data-card` has zero vertical padding by default — table rows self-pad via cell padding. Use `.data-card--padded` for non-tabular content (charts, text blocks).

For HTMX partials, either put `.data-card` on the swap target in the parent template, or inside the partial itself — both patterns are used. See `templates/leaderboard.html` (Option A: card on swap target) and `templates/partials/leaderboard_table.html` (Option B: card inside partial).

### CSS classes

| Class | File | Purpose |
|---|---|---|
| `.data-card` | `clean-layered.css` | White card styling (bg, shadow, padding, margin) |
| `.data-card--padded` | `clean-layered.css` | Adds vertical padding for non-tabular content |
| `.data-card` base | `base-vars.css` | Empty rule — no-op in non-layered themes |
