# Webapp

A FastAPI + HTMX + Jinja2 + Tailwind frontend for TEG analysis. Local development only (not deployed). This is the "new architecture" frontend — data comes entirely from `teg_analysis/`, making this a pure presentation layer.

## Quick start

```bash
# From repo root
uvicorn webapp.app:app --reload
```

Visit `http://localhost:8000` in your browser. Use the theme switcher in the nav bar to compare visual designs.

### Local environment

- Runtime deps (`fastapi`, `uvicorn`, `jinja2`, `starlette`, `httpx`, `markdown`) must all be in the **same** env that launches uvicorn. The project's `venv/` historically held the reporting/analysis deps (pandas, anthropic, markdown) but not the webapp deps; `venv/bin/pip install -r requirements.txt` brings everything into one env.
- **Known gotcha — pin starlette `<0.38`:** the routes use the older
  `TemplateResponse(name, context)` positional form. Starlette **≥0.41 removed**
  it, so with a newer starlette **every** templated route 500s with
  `TypeError: unhashable type: 'dict'` (the context dict gets read as the
  template name). `requirements.txt` pins `starlette>=0.37,<0.38` +
  `fastapi>=0.110,<0.112` to avoid this. Proper fix (future): migrate all
  `TemplateResponse` calls to the modern `TemplateResponse(request, name, context)`
  signature, then drop the pins. (A related variant of this error also appears on
  Python 3.14 with jinja2 3.1.x — use Python 3.12/3.13 there.)

## Architecture

### Tech stack
- **FastAPI** — Python web framework; routes in `routes/`
- **Jinja2** — HTML templating; templates in `templates/`
- **HTMX** — Partial page updates without full reloads
- **Tailwind CSS** — Utility classes for layout and spacing
- **CSS custom properties** — All theming done via CSS variables

### File structure
```
webapp/
  app.py              # FastAPI init, middleware, static mounts, router includes
  deps.py             # Shared dependencies (data loading with @lru_cache)
  theme.py            # Theme registry + helper to resolve active theme
  chart_utils.py      # Plotly chart generation
  routes/             # One file per page area (history, records, scoring, etc.)
  templates/
    base.html         # Shell: nav, theme switcher, main content slot
    *.html            # Page templates (extend base.html) — flat at this level, no `pages/` subdir
    partials/         # HTMX partial templates (no <html>/<body> wrapper)
  static/
    themes/           # One CSS file per theme
    base-vars.css     # Default CSS variable definitions
    app.css           # Global styles, component classes
```

### Data flow
```
Jinja2 template
  ↓
  ├─ route gets Depends(get_data)  (from deps.py)
  ├─ cached_load_all_data() returns hole-level df
  ├─ route calls teg_analysis functions
  ├─ passes results to template
  ↓
TemplateResponse → HTML
```

All data comes from `teg_analysis/`. The webapp never calculates anything — it only formats and displays.

## Theme system

Three themes, registered in `theme.py`. Each overrides CSS custom properties defined in `base-vars.css`. Default: **Clean** (flat white, matching the Streamlit site — Phase 1a).

| Theme | Description |
|---|---|
| **Clean** (default) | Minimal flat white, editorial feel — mirrors the Streamlit app |
| **Clean Page** | Flat single white content card on a warm grey background |
| **Clean Layered** | 3-layer hierarchy: stone background → taupe panel → white data cards |

The page-title (`ts-*`) and card-header (`ch-*`) **style switchers were removed
from the nav** for Phase 1a (the nav now carries only the theme switcher). The
cookie/CSS infrastructure stays live (`theme.py` defaults + `base-vars.css`), so
the experiments can be re-enabled for the Phase 2 design review. Current locked
defaults: title style `a` (mono label + serif title), card header `ch3` (serif).

**How it works:**
1. User clicks theme in nav dropdown
2. HTMX request to `/set-theme/{name}` sets cookie
3. `theme.py` reads cookie, passes active theme name to templates
4. Template loads CSS file for that theme
5. Plotly charts dynamically themed via `get_plotly_theme(request)`

**CSS pattern:**
- `base-vars.css`: defines defaults (e.g. `--color-primary: #333;`)
- Theme file: overrides (e.g. `--color-primary: #005f73;`)
- All other CSS references variables, not hard-coded colours

## Key patterns

### Route → deps → template
```python
@router.get("/leaderboard")
async def leaderboard(request: Request, data=Depends(get_data)):
    # get_data() is @lru_cache, called once per process
    df = data.get_round_data()  # already cached
    leaderboard_df = create_leaderboard(df)
    return TemplateResponse("pages/leaderboard.html", {
        "request": request,
        "theme": get_active_theme(request),
        "leaderboard": leaderboard_df,
        ...
    })
```

### HTMX partial updates
- Nav links use `hx-get="/route" hx-target="#main-content"`
- Server returns only the content fragment (from `templates/partials/`)
- HTMX swaps into `#main-content` without full page reload

### Common page patterns

- **Simple selector + full-page reload** (e.g. `/teg-reports`): a vanilla form `GET` with `<select onchange="this.form.submit()">`. Cheap when no partial update is needed.
- **HTMX tab bar** (e.g. `/results` in `templates/results.html`): a hidden input holds the active tab; each tab button sets that input then triggers `htmx.trigger(…, 'change')` on the TEG `<select>`, which has `hx-get="/route/table"` returning the partial.
- **`_results_context()`-style HTMX endpoint**: a `{tab}` switch returns `{result_title, table_html}` rendered into `partials/results_table.html` — see `webapp/routes/history.py`.
- **Placeholder helper** in `webapp/routes/placeholder.py:_placeholder()` for stub pages before they're real.

### Component classes (in app.css / base-vars.css)
- **`teg-table`** — styled data table; used for results/rankings
- **`records-table`** — variant for records pages
- **`data-card`** — white card for data output (Clean Layered theme); no-op in other themes
- **`stat-card`** — headline statistics
- **`tab-underline`** / **`tab-underline--active`** — in-page tab & toggle buttons (underline style; `--active` is the single canonical active class)
- **`badge`** — small inline labels

### Structural class hierarchy

Every page is wrapped in a consistent **Page → Section/Tab → Data-display**
hierarchy so visual formatting can be applied once per level. The section
wrappers **own the page's vertical spacing rhythm** (defined in `base-vars.css`)
— they are no longer layout-neutral. Layout intent that legitimately varies per
row (`justify-between`, `items-center` vs `items-end`, `gap-*` overrides) is
still expressed with Tailwind utilities on the element and overrides the central
defaults. See [design_principles.md → Spacing is centralised on the section
wrappers](design_principles.md#spacing-is-centralised-on-the-section-wrappers).

| Level | Class | Wraps / role |
|---|---|---|
| **Page** | `.page-container` → `.page-title-outer` / `.page-panel` → `.content-wrapper` → `.main-content` | The shell in `base.html` (already consistent — don't hand-edit) |
| **Section** | `.section-nav` | The in-page primary tab bar (a row of `.tab-underline` buttons). Owns `margin-bottom` + flex/gap |
| | `.section-controls` | Selector / filter rows (dropdowns, number inputs). Owns `margin-bottom` + flex/gap |
| | `.toggle-group` | Sub-toggle rows inside a panel (score-type, metric, chart-variant, direction/mode). Owns `margin-bottom`; `.data-card + .toggle-group` adds the gap above when it follows a data block |
| | `.section-panel` | Every HTMX swap-target / content container (the `id="…"` div that `hx-target` points at) |
| **Data display** | `.card-header` | The single canonical section label (driven by the `ch-X` body class) |
| | `.data-card` | Every table/chart wrapper — **all** tables and charts sit in one |
| | `.table-wrapper` | Horizontal-scroll wrapper inside a `.data-card` for wide tables (`overflow-x:auto`) |
| | `.chart-container` | Plotly target `<div>`s — carries `width:100%`; per-chart `height` stays inline |
| | `.input-numeric` | Compact numeric input (`width:5rem`) for "top N" selectors |

**Navigation:** site nav uses `.nav*` (`.nav-link.active` for the active site
section — unchanged); in-page tabs are `.section-nav > .tab-underline` with the
single active class `.tab-underline--active`; sub-toggles are
`.toggle-group > .tab-underline`; inline data links use `.text-link`.

**Rules when adding a page/partial:**
- Primary in-page tab bar → `.section-nav`; selector rows → `.section-controls`;
  secondary toggles → `.toggle-group`; the HTMX swap target → `.section-panel`.
- Active tab/toggle state → `.tab-underline--active` (never bare `.active`; a
  `.tab-underline.active` CSS alias exists only as a safety net). If JS toggles
  the active state, it must add/remove `.tab-underline--active` too.
- Wrap every table and chart in `.data-card`; wrap wide tables in
  `.table-wrapper`; give Plotly divs `.chart-container` and keep only `height`
  inline. Use `.input-numeric` for compact number inputs.
- **Do not add vertical-margin utilities (`mb-*`/`mt-*`/`my-*`) to
  `.section-controls`, `.section-nav` or `.toggle-group`** — their spacing is
  owned centrally (`.section-nav` `2rem`, `.section-controls` `1.5rem`,
  `.toggle-group` `1rem` below + `1.5rem` above when it follows a `.data-card`).
  For a nested/edge override, use inline `style="margin-bottom:0"`.

**Scope note:** dev/demo templates (`smoke_test`, `width_test`,
`title_preview`, `showcase`, `placeholder`) are not part of the page hierarchy
and are intentionally left unwrapped.

#### Debug overlay (verifying class coverage)

A dev-only overlay colour-codes every structural wrapper so you can flick
through pages and confirm each element is classed at the right level. It is
**off by default and completely inert** — all rules live in
`static/themes/debug-structure.css`, scoped under `body.debug-structure`.

- **Toggle:** `Ctrl/Cmd + Shift + D` (state persists across pages via
  `localStorage`), or run `toggleStructureDebug()` in the browser console.
- **What you see:** concentric outlines via `outline-offset`, each level
  further out than the box it contains, with a class-name label top-left —
  black `PAGE .main-content` → blue `.section-nav` / orange `.section-controls`
  / green `.section-panel` → purple `.toggle-group` → red `.data-card` → cyan
  `.chart-container`; amber `.card-header`, pink `.text-link`, and an inset bar
  on `.tab-underline--active`.
- **Reading gaps:** a table/chart with no red box, or a tab bar with no blue
  box, is unclassed. (Expected non-gap: `.card-header` only renders under a
  `ch1/2/3` card-header style, so it shows no amber box on `ch0`.)

## Design principles

See [design_principles.md](design_principles.md) — typography, layout, table conventions, component rules, theme/layout invariants, and the data-card pattern.

See [page_title_switcher.md](page_title_switcher.md) — page title and card header switcher system (cookie-based style testing, page container architecture).

## Development

### Navigation (single source of truth)

The top nav and the **Contents** site map are both driven by `webapp/nav.py`
(`NAV_SECTIONS`). This mirrors the Streamlit app's section grouping, page
titles and ordering (see `streamlit/page_config.py`), excluding the Data-admin
section. `NAV_SECTIONS` is injected into every template via
`request.state.nav_sections` (set in `app.py`'s `theme_middleware`), and
`base.html` renders the nav dropdowns by looping over it. To add/rename/reorder
a nav entry, edit `NAV_SECTIONS` only — do not hand-edit the nav markup in
`base.html`.

Each section entry has `label`, `active` (set of `active_page` values that
highlight the section) and `pages` (list of `(title, url, active_key)`).

### Adding a new page
1. Create route in `routes/my_page.py` (define `router = APIRouter()` and your handler).
2. Create template in `templates/my_page.html` (flat — no `pages/` subdir).
3. Follow the route → deps → template pattern.
4. Register the route in `app.py` in **two places**: import it in `from webapp.routes import (…, my_page, …)`, then call `app.include_router(my_page.router)`.
5. Pass `active_page="my-key"` in the `TemplateResponse` context so the nav highlights correctly. Add the page (and, if needed, its `active_page` key) to the relevant section in `webapp/nav.py`.

### Adding a new theme
1. Create `static/themes/my-theme.css`
2. Override CSS variables from `base-vars.css`
3. Register in `theme.py` THEMES list
4. If you add Plotly charts, add to PLOTLY_THEMES dict too

### Working with templates
- Base template: `templates/base.html` (shell with nav + content slot)
- Extend it: `{% extends "base.html" %}` in page templates
- Partials: `templates/partials/*.html` (HTMX swap targets, no `<html>` wrapper)
- Pass context via TemplateResponse: `{"key": value, ...}`

**`base.html` blocks** — the shell exposes four override points:
- `title_suffix` — appended to the browser tab title
- `extra_head` — inject per-page `<link>`/`<style>`/`<script>` tags (e.g. `<link rel="stylesheet" href="/static/my.css">` for page-specific CSS not in the global theme)
- `page_title` — the page header area. Standard shape:
  ```html
  {% block page_title %}
  <div class="page-title-area">
    <span class="page-label">Section</span>
    <h1 class="page-title">My Page</h1>
  </div>
  {% endblock %}
  ```
- `content` — the actual page body

**Nav highlighting** — the `active_page` context value (e.g. `"teg-reports"`, `"history"`, `"results"`) is matched against the lists hardcoded in `base.html`'s nav dropdowns. If yours isn't one of the listed keys, the parent dropdown won't show as active — either reuse an existing key or add yours to the relevant list in `base.html`.

## Current status

**Full Streamlit page set replicated** (excluding the Data-admin section — data
update/edit/delete, report generation, volume management — which is
intentionally out of scope). The nav mirrors Streamlit's structure exactly
(sections, page titles, ordering) via `webapp/nav.py`. Pages: Contents,
TEG History / Honours / Full Results / Player Rankings / TEG Reports, TEG
Records / Top TEGs and Rounds / Personal Bests, Latest Leaderboard / Latest
Round / Latest TEG / Handicaps, the 11 Scoring-analysis views, and Scorecard /
Best-Worstball / Eclectic Scores / Eclectic Records.

`/` now lands on **Contents** (the site map), matching Streamlit.

### Look-and-feel roadmap

Look-and-feel work is sequenced in two phases. The guiding aesthetic target
(editorial / printed-programme) is in [design_principles.md](design_principles.md);
this roadmap is the **plan to get there**.

**Phase 1 — make the webapp production-ready (replace Streamlit on Railway).**
The bar is the existing Streamlit app: lo-fi but clear to read, consistently
laid out, nothing jarring. The endpoint of Phase 1 is "the webapp can take over
as the live site."

- **1a — Match the Streamlit app in the Clean theme.** Make the `clean` theme
  look like the Streamlit site: consistent layout from the menu bar through to
  individual pages, no wonkiness. Fix anything obviously broken in the UI as we
  go. *Grounding fact:* the palette/typography already match Streamlit — both
  use Lora (headings + body) + Roboto Mono (data) + forestgreen accent, and the
  same top-rank tint `#F3F7F3` (see `.streamlit/config.toml`). So 1a is mostly
  **layout and spacing consistency**, not recolouring. The structural hooks
  added in PRs #8/#9 (`.section-nav`, `.section-controls`, `.toggle-group`,
  `.section-panel`, `.data-card`, `.chart-container`) are the levers — they are
  still empty no-ops; spacing currently lives in ad-hoc per-template Tailwind
  utilities, which is the main source of inconsistency.

  *Decisions for 1a:*
  - **Match the feel, not the layout.** Reproduce Streamlit's cleanliness,
    consistency and readability — keep the webapp's own top-nav-dropdown
    paradigm and structure (no sidebar). Live reference for comparison:
    [theelgolfo.com](https://theelgolfo.com).
  - **Shell first, then systematic audit.** Fix the shared shell (nav bar,
    page-title band, table + section-spacing defaults via the structural hooks)
    where the wins are obvious; then run the app, screenshot every page, and
    work through a per-page wonkiness inventory.
  - **One clean default, kept themable.** Settle on a single Streamlit-style
    page-title and card-header treatment for Clean, driven entirely by
    CSS/theme variables (not per-template) so it stays swappable. The `ts-*` /
    `ch-*` switcher experiments are not removed — they're deferred to the
    Phase 2 review.
- **1b — Consistent, clean charts (and tables if needed).** Set the right
  app-wide defaults so charts look clean, uncluttered, and professional — as if
  *printed on the page*, but retaining mouseover where it adds value. Driven from
  `chart_utils.py` / `get_plotly_theme`.

  > **TODO — restore the `/results` race chart.** As part of the `/results`
  > polish, the net/gross race charts there were **replaced with a placeholder**
  > (`.chart-placeholder` in `partials/results_table.html`) pending this chart
  > rebuild. The placeholder names its data source —
  > `create_cumulative_graph(all_data, 'TEG N', y_series=…)` in
  > `webapp/chart_utils.py`; the per-variant series/title/subtitle are computed by
  > `_results_chart_meta()` in `routes/history.py` (which replaced the old
  > `_results_chart` figure-builder — see git history for that implementation).
  > When charts are rebuilt, re-wire the placeholder block back to a real figure.
  > Other pages (leaderboard, latest, scoring, player) still use the old inline
  > chart and are unchanged.

  > **⚠️ Known issue — charts to be redone, parked for later.** Goal: make the
  > webapp charts look and behave like the **Streamlit** ones, which render
  > correctly. Two problems on the webapp side:
  > 1. **Appearance** — the current charts look poor next to Streamlit's.
  > 2. **Broken on HTMX tab-swap** — on `/results` (and any chart inside an
  >    HTMX-swapped fragment), after clicking a chart/tab the legend, gridlines
  >    and end-of-line labels render stranded/duplicated below the plot, and stay
  >    until a full page reload.
  >
  > **Diagnosis so far (don't re-chase the wrong leads):**
  > - It is **not** a sizing/timing problem. A live console check after
  >   reproducing showed all dimensions correct (`container_h:420`, `svg_h:420`,
  >   `svg_w:752`, `plotbg_h:374`).
  > - It is **not** a dimension-recalc problem either: manually resizing the
  >   browser window (which fires Plotly's own resize) does **not** fix it. So
  >   the common "force `Plotly.Plots.resize` on tab-show / `htmx:afterSettle`"
  >   advice does not apply here — confirmed, don't bother.
  > - The stranded elements — legend, end-of-line labels (annotations) and the
  >   round-divider vertical lines (shapes) — are exactly the things Plotly draws
  >   on its **separate top/info SVG layer**, not the main plot SVG. So the top
  >   layer is persistently mis-placed relative to the main plot, and a redraw or
  >   resize doesn't re-sync it. (`svg_count:3` may just be Plotly's normal
  >   main + top + hover layers — could not confirm duplication; jsdom can't
  >   render Plotly and no browser is installable in the web sandbox.)
  > - It only happens **after an HTMX swap** and persists until a full reload, so
  >   suspect the inline `<script>` running mid-swap and/or an ancestor's CSS
  >   throwing off Plotly's top-layer positioning — note `.content-wrapper` is
  >   `width: fit-content` and the nav is JS-`position: sticky`.
  >
  > Several attempts to fix this as a sizing/resize problem (rAF, height-pin,
  > explicit size, ResizeObserver) did **not** work and have been reverted — the
  > templates are back to the simple inline `Plotly.newPlot(..., {responsive:true})`
  > baseline.
  >
  > **Where the chart code lives:**
  > - Figure construction: `webapp/chart_utils.py` (`create_cumulative_graph`,
  >   `create_round_graph`) — ported from `streamlit/make_charts.py` (the
  >   reference to match).
  > - Figures built per page in the routes: `routes/history.py` (`_results_chart`),
  >   `routes/leaderboard.py`, `routes/latest.py`, `routes/scoring.py`
  >   (by-teg, distributions), `routes/player.py`.
  > - Rendered by inline `<script>` blocks in the partials (`results_table.html`,
  >   `leaderboard_table.html`, `latest_round_tab.html`,
  >   `scoring_distributions_content.html`, `scoring_by_teg.html`,
  >   `chart_container.html`, `player_scoring.html`, `player_overview.html`).
  >
  > **Likely fix directions when revisited:** call `Plotly.purge(gd)` before
  > drawing, and/or render charts from a single global `htmx:afterSettle` handler
  > rather than inline-per-fragment scripts (so re-swaps can't stack renders) —
  > i.e. mirror how Streamlit mounts a single chart component.

**Phase 2 — better UI (beyond parity).** Only after Phase 1 lands.

- **2a — Improve the Clean / default theme** using design best practice.
- **2b — A new, more layered / interesting theme**, built from current best
  practice rather than the existing experiments.

For Phase 2, the existing theme-chooser experiments (page-title `ts-*` variants,
card-header `ch-*` variants, archived themes in `static/themes/archive/`) are a
**starting point, not a destination** — we draw inspiration from general best
practice, current trends, and real-world sites / dashboards / data-viz as we go,
rather than defaulting to what's already there.

**Working invariant:** primary target is the **Clean** theme; after any change,
verify Clean Layered still works (both layouts — see design_principles.md).

### Webapp ↔ Streamlit feature-parity audit

The functional parity pass is **substantially complete** — the missing
controls/views/measures/charts have been closed across every page, and all
endpoints render their Streamlit-equivalent content. Per-page detail and the
remaining (cosmetic / WIP-heatmap / deep-port) items are tracked in
**[PARITY_AUDIT.md](PARITY_AUDIT.md)**.

Analysis logic added during the audit (kept UI-agnostic in `teg_analysis/`):
`analysis/player_rankings.py` (ranking tables + position summaries),
`analysis/eclectic.py` records helpers, and `display/scorecards.py` (scorecard
HTML builders).

**Not yet built:**
- REST API — planned; will expose `teg_analysis` over HTTP so any client (scripts, mobile, other frontends) can access the analysis layer without needing Python
- Mobile responsive design
- Search / filtering UI (some routes have it, not everywhere)
- **"Related links" section** — replicate the cross-page related-links block the
  Streamlit app shows (links from each page to related pages). One day.

**Pre-publish checks (TODO before the site goes live):**
- **Verify the "Records & PBs" content** on `/latest-round` and `/latest-teg`.
  The records/PBs computed there have not been confirmed correct; a draft
  warning is shown on those tabs in the meantime. Check the figures against a
  known-good source before publishing, then remove the warning
  (`_RECORDS_DRAFT_NOTE` in `webapp/routes/latest.py`).
- **Fix the `/personal-bests` detail tabs `best_rounds` / `worst_rounds`** —
  they error with `"['Round_Label'] not in index"` (from `routes/performance.py`).
  The summary and TEG tabs are fine. A column the round-detail view expects
  (`Round_Label`) isn't present in the data it's given.
- **Fix the `/latest-teg` Streaks tab — it only reflects the final round, not
  the whole TEG.** e.g. it reports Jon BAKER's best par-or-better streak in
  TEG 18 as 1, missing the run of 4–5 in round 2. Likely cause: the streaks
  branch in `_latest_teg_tab_context` (`webapp/routes/latest.py`) calls
  `get_player_window_streaks(..., round_num=last_round)`, so it only windows
  the last round. A TEG-level view should aggregate streaks across all rounds
  of the TEG (and handle streaks that span a round boundary, if intended).

**Planned enhancements (TODO):**
- **Add an absolute / % pill** (percentage = share of each column) to the
  score-count matrix on `/scoring/matrix` and to the **Scoring tab on
  `/latest-teg`** — a `.pill-group` toggle that switches the table between raw
  counts and column percentages.
- **Show bestball/worstball positions on `/latest-round`** — add the round's
  best bestball / best worstball / worst bestball / worst worstball positions
  to the Latest Round in context page.

