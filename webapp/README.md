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
- **Known gotcha on Python 3.14:** jinja2 3.1.x + starlette emit `TypeError: cannot use 'tuple' as a dict key (unhashable type: 'dict')` on **every** template render (the template cache key isn't hashable in 3.14). Use Python 3.12 or 3.13 for local dev until starlette/jinja2 ship a fix. Symptom: every templated route 500s with that exact message.

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

Three themes, registered in `theme.py`. Each overrides CSS custom properties defined in `base-vars.css`. Default: **Clean Page**.

| Theme | Description |
|---|---|
| **Clean Page** (default) | Flat single-surface design |
| **Clean Layered** | 3-layer hierarchy: stone background → taupe panel → white data cards |
| **Clean** | Minimal white, editorial feel |

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
- **`tab-btn`** / **`tab-btn-active`** — tab navigation
- **`badge`** — small inline labels

## Design principles

See [design_principles.md](design_principles.md) — typography, layout, table conventions, component rules, theme/layout invariants, and the data-card pattern.

See [page_title_switcher.md](page_title_switcher.md) — page title and card header switcher system (cookie-based style testing, page container architecture).

## Development

### Adding a new page
1. Create route in `routes/my_page.py` (define `router = APIRouter()` and your handler).
2. Create template in `templates/my_page.html` (flat — no `pages/` subdir).
3. Follow the route → deps → template pattern.
4. Register the route in `app.py` in **two places**: import it in `from webapp.routes import (…, my_page, …)`, then call `app.include_router(my_page.router)`.
5. Pass `active_page="my-key"` in the `TemplateResponse` context so the nav highlights correctly. The value must match one of the keys hardcoded in `base.html` (search `active_page in [...]` to find the lists).

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

26 endpoints implemented with data parity vs Streamlit:
- History, results, records, scoring (multiple views), honours, personal bests, comebacks, handicaps, bestball

**Formatting pass in progress:**
- Table styling consistency
- Number formatting (vs-par notation, decimal places, alignment)
- Column widths and cell padding
- Layout refinement for multi-content pages
- Card header styling (4 options: grey bar, mono label, serif label, hidden)

**Not yet built:**
- REST API — planned; will expose `teg_analysis` over HTTP so any client (scripts, mobile, other frontends) can access the analysis layer without needing Python
- Mobile responsive design
- Search / filtering UI (some routes have it, not everywhere)

