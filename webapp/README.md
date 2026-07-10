# Webapp

A FastAPI + HTMX + Jinja2 + Tailwind frontend for TEG analysis. **Deployed on Railway from `main`** (replacing the legacy Streamlit app) via `railway.toml` → `uvicorn webapp.app:app`; also run locally for development. This is the "new architecture" frontend — data comes entirely from `teg_analysis/`, making this a pure presentation layer. Required Railway env vars: `GITHUB_TOKEN` (data reads from GitHub), `ANTHROPIC_API_KEY` (TEG Reports), and the `GOOGLE_*` service-account vars (for data-update ingestion); a persistent volume is mounted at `/mnt/data_repo` as the read/write cache.

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

## Admin / data management

The webapp includes a password-gated admin area, all in `webapp/routes/admin.py`
(+ `webapp/routes/admin_round_setup.py`, `webapp/routes/admin_teg_setup.py`,
`webapp/routes/admin_live_round.py`) + `webapp/admin_auth.py`. A shared sub-nav
(`partials/admin_nav.html`) links the pages: **➕ New round** (the guided
wizard — start here), **Round setup**, **TEG setup**, **Live round**, **Sheet
import (fallback)**, **Edit data**, **Delete rounds**, **Volume** (browser),
**GitHub sync**, **Backups** and **File guide**. Every page is
behind the same cookie auth and each write calls `deps.clear_all_data_caches()`
so the site shows fresh data immediately. They drive headless logic in
`teg_analysis.analysis.data_update` / `teg_analysis.analysis.round_setup` /
`teg_analysis.analysis.teg_setup` / `teg_analysis.analysis.live_round` and
`teg_analysis.io` (sync / file catalog) — no Streamlit, no FastAPI in the
analysis layer.

Admin pages load `webapp/static/admin.css`, which (among the form/button styles)
applies a **compact override** to `.teg-table` — smaller font and tighter row
padding than the site default — scoped to `.main-content` so it only affects
admin pages (data density matters more than editorial spacing here). The same
compactness applies to the inline edit grid (`#edit-grid` cells).

**New round (guided wizard)** — templates `admin_new_round.html` (landing),
`admin_new_round_wizard.html`; route `webapp/routes/admin_new_round.py`; logic
`teg_analysis.analysis.round_wizard`.
- **Routes:** `/admin/new-round` (landing: pick TEG+Round, or resume a pending
  one), `/admin/new-round/{teg}/{round}` (the wizard at its current step, with
  `?step=` to jump), and one POST per step (`/metadata`, `/roster`, `/parsi`,
  `/golive`).
- **Purpose:** the single "start here" entry point for setting up a round for
  scoring. Setting up a brand-new TEG's first round otherwise means visiting
  four separate pages in order (metadata → roster → Par/SI → go live); a new
  round in an existing TEG is three of them. The wizard walks through only the
  **incomplete** steps and hands over the shareable link at the end. The
  individual pages below stay in the sub-nav for edits and edge cases — the
  wizard just orchestrates on top of their already-tested save functions.
- **Stateless / resumable:** the wizard holds no session state. Each step saves
  immediately, and which step is "current" is recomputed from the data on every
  visit (`round_wizard.get_wizard_status`, which reuses the same status probes
  as the standalone pages — round_info row exists? `handicaps` row confirmed?
  `round_pars` present? live round active?). So a half-finished setup resumes
  just by revisiting the URL, and a new round 2/3/4 auto-skips the roster step
  because that TEG's roster is already confirmed. Par/SI and Go live are
  **locked** until their prerequisites (metadata, then all three) are met.
- **Metadata step** is the one net-new piece (`round_wizard.get_round_metadata_form`
  / `save_round_metadata`): a purpose-built form (course datalist from
  `course_pars.csv` + date) that **derives** round_info's `TEGRd`/`TEG`/`Area`/
  `Year` (Area/Year inherited from the TEG's other rounds or `future_tegs.csv`,
  Year falling back to the date's trailing year) instead of hand-typing them in
  the raw Edit-data grid. The other three steps reuse `teg_setup` /
  `round_setup` / `live_round` save functions unchanged.

**Round setup** — templates `admin_round_setup.html`, `admin_round_setup_form.html`,
`partials/admin_round_setup_result.html`.
- **Routes:** `/admin/round-setup` (list), `/admin/round-setup/{teg}/{round}`
  (18-hole form), `/admin/round-setup/{teg}/{round}/save` (HTMX).
- **Purpose:** confirm a round's Par/SI *before* anyone plays it, so whoever enters
  scores afterwards (live round entry, below) sees Par/SI read-only, like it's
  printed on a scorecard, and never has to think about course setup. The list is
  scoped to rounds with `round_info.csv` metadata but no scores
  yet in `all-scores.parquet` — once a round is played its real Par/SI is already
  in `all-scores.parquet`, so there's nothing left to set up.
- **Flow:** `round_setup.get_round_setup_form` prefills from an existing
  `round_pars.csv` entry if already confirmed, else `course_pars.csv`'s default
  (the most recently played round at that course), else blank; flags courses in
  `constants.KNOWN_VARIABLE_ROUTING` (currently Praia D'El Rey — sometimes played
  back-9-first) for a manual double-check. Save upserts the confirmed 18 holes into
  `round_pars.csv` via `round_setup.save_round_setup`.

**TEG setup** — templates `admin_teg_setup.html`, `partials/admin_teg_setup_result.html`.
- **Routes:** `/admin/teg-setup` (redirects to the next TEG), `/admin/teg-setup/{teg}`
  (roster form — any TEG number, via the "Jump to TEG" field), `/admin/teg-setup/{teg}/save`
  (HTMX), `/admin/teg-setup/{teg}/add-player` (register a brand-new player; plain form
  POST → redirect so the roster re-renders with the new row).
- **Purpose:** confirm who's playing a TEG and their handicap before it starts — not every
  player plays every TEG. Reuses the existing handicap-calculation logic
  (`teg_analysis.analysis.handicaps.get_hc` / `get_current_handicaps_formatted`) rather than
  reimplementing it, so the read-only Handicaps page and this setup page stay in sync.
- **Flow:** `teg_setup.get_teg_roster_form` prefills from an existing `handicaps.csv` row for
  that TEG if already confirmed, else the calculated draft (`get_hc`), else blank/not-playing.
  A checkbox + handicap field per player lets the admin override before saving; save
  (`teg_setup.save_teg_roster`) upserts the one `handicaps.csv` row for that TEG in place
  (not-playing is written as the existing `0`-in-that-cell convention, no schema change).
  The roster offers **every known player** — `handicaps.csv` columns first, then anyone
  in `data/players.csv` without a column yet (they get one the first time they're saved
  onto a TEG).
- **Add a new player:** a card below the roster registers someone who has never played —
  full name + 2–3-letter code, validated (format, duplicate code/name) by
  `teg_analysis.core.players.add_player`, which appends to `data/players.csv` (the
  writable source of truth for player identity, seeded from the legacy
  `constants.PLAYER_DICT`; all code→name lookups route through
  `core.players.get_player_dict`, cached and cleared by
  `deps.clear_all_data_caches`). The new player then appears in the roster unticked —
  tick, set a handicap, save. See `DATA_STORAGE_INGESTION_PLAN.md`'s "TEG roster +
  handicap setup" section for the original design record (and a noticed-but-untouched
  data anomaly, a stray `TEG 50` row in `handicaps.csv`).

**Live round** — templates `admin_live_round.html`, `admin_live_round_review.html`,
`partials/admin_live_round_*.html`.
- **Routes:** `/admin/live-round` (list + start), `/admin/live-round/{token}/review`
  (editable scorecard grid + conflicts + finalize), `/admin/live-round/{token}/edit`
  (bulk admin edit — a plain form POST that redirects back to review),
  `/admin/live-round/{token}/resolve`, `/admin/live-round/{token}/finalize`,
  `/admin/live-round/{token}/cancel` (the rest HTMX).
- **Purpose:** start a live, multi-device round-entry session for an already-set-up
  round, hand out its shareable link, and review/finalize once everyone's done.
  The review page shows the **full staged scorecard as an editable grid** — the admin
  can correct any cell (not just flagged conflicts), links out to the live leaderboard,
  and finalizes. Admin edits go through `live_round.apply_admin_edits`, which is
  authoritative: an admin value overwrites a player entry and clears any conflict flag,
  and only cells whose value actually changed are written (a re-save is a no-op).
  Finalizing runs the staged scores through the *existing* `execute_data_update`
  pipeline exactly as "Add a round" does — one GitHub commit, every derived cache
  regenerated. See the player-facing side below and
  `DATA_STORAGE_INGESTION_PLAN.md`'s "Phase 3.4 design" for the full model.

**Sheet import (fallback)** — templates `admin_data_update.html`, `partials/admin_update_*.html`.
Phase 4.1 of `DATA_STORAGE_INGESTION_PLAN.md`: relabeled from "Add a round" now that Live
round (above) is the primary way to enter a round. Still fully functional — this is the
fallback for entering a round after the fact from the Google Sheet, not a deprecated path.
Phase 4.2 (removing the Sheet path entirely) is a human-gated decision for after a season of
real Live round use; not triggered yet.
- **Routes:** `/admin/data-update` (load + preview), `/admin/data-update/preview`,
  `/admin/data-update/execute` (HTMX).
- **Flow:** load the "TEG Round Input" Google Sheet → preview round totals +
  hole-level duplicate check → confirm (append / overwrite / add-new-only) →
  `execute_data_update` takes a **timestamped backup** of `all-scores`/`all-data`,
  writes them, regenerates the streaks/commentary/bestball/status caches and
  batch-commits to GitHub.
- **round_info guard:** `find_tegs_missing_round_info` checks the new round's TEG
  exists in `round_info.csv`; if not, preview and execute both refuse (no partial
  write) and link to **Edit data → Round Info** to add the metadata first. (As a
  backstop, `analyze_teg_completion` also falls back to a `TEG N` label instead of
  crashing, so delete/regenerate flows can't half-apply either.)

**Edit metadata CSVs** — templates `admin_edit_data.html`,
`partials/admin_edit_grid.html`, `partials/admin_edit_result.html`.
- **Routes:** `/admin/edit-data?file=<slug>` (pick a CSV → editable grid),
  `/admin/edit-data/save`, `/admin/edit-data/regenerate-status` (HTMX).
- **Flow:** the file picker is driven by
  `data_update.EDITABLE_DATA_FILES` (round_info, future_tegs, handicaps,
  course_pars, round_pars, teg_winners, completed_tegs, in_progress_tegs). An inline grid of `<input>`
  cells (vanilla-JS add/delete-row) posts back; the route rebuilds the frame
  from `cell__{rid}__{cidx}` fields, light-coerces numeric columns and calls
  `data_update.save_data_file` (single-file commit). Auto-generated status files
  offer a **Regenerate** button → `data_update.regenerate_status_files`. A
  read-only `?file=processed` view shows `all-data.parquet`.

**Delete rounds** — templates `admin_delete_data.html`,
`partials/admin_delete_{preview,result}.html`. **This is the primary data-admin flow.**
- **Routes:** `/admin/delete-data` (select TEG + rounds),
  `/admin/delete-data/preview`, `/admin/delete-data/execute` (HTMX).
- **Flow:** pick a TEG and rounds — or tick **Whole TEG (all rounds)** to delete an
  entire tournament — → preview the exact rows → confirm → `execute_data_deletion`
  takes a **timestamped backup** first, removes the rows from `all-scores`/`all-data`
  and rebuilds every derived cache (status, streaks, commentary, bestball),
  batch-committing on Railway.

**GitHub ↔ store sync** — templates `admin_volume_sync.html`,
`partials/admin_sync_body.html`, `partials/admin_sync_preview.html`,
`partials/admin_sync_diff.html`, backed by `teg_analysis/io/sync.py`.
- **Routes:** `/admin/volume-sync?folder=<folder>` (status table),
  `/admin/volume-sync/preview` (the pre-action review screen),
  `/admin/volume-sync/diff` (per-file text diff), `/admin/volume-sync/pull` and
  `/admin/volume-sync/push` (HTMX, the actual transfer).
- **Flow:** pick a folder (`data`, `data/commentary`, …) → see a per-file status
  table comparing GitHub vs the store (Only on GitHub / Only in store / Different
  size / Same size) → tick files (a live **Selected (N)** box beside the action
  buttons lists what's currently ticked so the long table can't hide the
  selection) → **Pull** or **Push** → a **preview** (`build_sync_preview`) lists
  exactly what each file will do (Create new vs Overwrite, store-vs-GitHub
  modified times, which side is newer, conflicts highlighted) with an optional
  per-file **View diff** (`file_diff`, unified text diff for
  `.csv/.md/.txt/.json`; binary/parquet shows "binary") → **Confirm** runs
  `pull_files` (GitHub → store) or `push_files` (store → GitHub in one batch
  commit). The "store" is the Railway volume in production and the local working
  tree in dev. Use this to move just the reference CSVs you changed for a new TEG
  without a full redeploy.
- **Info icons:** each catalogued file in the status table carries a small **ℹ**
  that shows its role + how-it's-updated on hover and deep-links to the matching
  row on the **File guide** page (`get_file_definition` / `file_anchor`).
- **Environment banner:** the page shows whether the store is the Railway volume
  (live) or your local working tree (dev), with a small-print summary of the
  implications (pull overwrites working-tree files / push makes an out-of-band API
  commit when run locally).
- **Safety:** each pull backs up the existing store file to
  `data/backups/sync/<timestamp>/…` *before* overwriting (`backup_store_file`); an
  inline **Backups / restore** panel lists them and restores on demand
  (`restore_backup`, which now also backs up the copy it replaces, store-only —
  Push afterwards to send back to GitHub). See the dedicated **Backups** page
  below for the full browser. Pushes rely on GitHub's own
  history. The preview is the primary confirmation step; as a backstop, a direct
  (un-previewed) call to `/pull` or `/push` still runs `detect_pull_conflicts` /
  `detect_push_conflicts` and shows the overwrite-confirm screen
  (`partials/admin_sync_conflict.html`) if the destination copy is **newer**.

**Volume browser** — template `admin_volume.html`,
`partials/admin_volume_body.html`, backed by `teg_analysis/io/sync.py`
(`list_store_dir`, `read_store_file`, `delete_store_file`).
- **Routes:** `/admin/volume?path=<rel>` (browse), `/admin/volume/download?path=`
  (stream a file), `/admin/volume/delete` (HTMX, file delete).
- **Flow:** browse the store's actual file tree (breadcrumb + drill-in). Each file
  row offers **Edit** (catalogued editable files → Edit data), **Sync** (jump to
  GitHub sync for that folder), **Download**, **Restore (N)** (if backups exist →
  Backups page filtered to that file) and **Delete**. Delete takes a timestamped
  backup first (`delete_store_file`, restorable from the Backups page) and
  confirms. Paths are validated against traversal (`_safe_rel`). This is the main
  way to *see what's on the Railway volume*.

**Backups** — template `admin_backups.html`, `partials/admin_backups_body.html`.
- **Routes:** `/admin/backups?file=<optional rel>` (browse, with a per-file
  filter), `/admin/backups/restore` (HTMX).
- **Flow:** lists every store backup (newest first) taken before a pull, a volume
  delete or a prior restore (`list_sync_backups`). Restore rewrites the store copy
  and **backs up the copy it replaces first** (so restores are reversible too);
  store-only — Push from GitHub sync to send it back. Each backup can also be
  **Downloaded**. The volume browser's per-file **Restore (N)** deep-links here
  pre-filtered (`backups_for`).

**File guide** — template `admin_file_guide.html`, backed by
`teg_analysis/io/file_catalog.py` (`DATA_FILE_CATALOG`, `catalog_by_importance`,
`get_file_definition`, `file_anchor`).
- **Route:** `/admin/file-guide` (read-only reference).
- **Flow:** a table of every data file — role, format, how it's updated, editable
  link — **ranked by importance**. Each row is anchored (`file-<name>`) so the ℹ
  icons on the GitHub-sync and Volume pages can deep-link to it. The catalog is
  the single source of truth shared by the page and the info icons.

- **Auth:** one shared password from `WEBAPP_ADMIN_PASSWORD` (defaults to `teg`
  if unset), held in a cookie. This is **not** real security — it only stops a
  crawler accidentally triggering a write/commit/LLM run. `admin_auth.py`.
- **Env vars needed on Railway:** `WEBAPP_ADMIN_PASSWORD`, the `GOOGLE_*`
  service-account vars (sheet access, add-a-round only) and `GITHUB_TOKEN`
  (commit). Form POSTs need `python-multipart` (in `requirements.txt`).

## Live round entry (player-facing)

`webapp/routes/live_round.py` + `templates/live_round_entry.html`. Not behind
admin auth — a live round's token in the URL *is* its access control (trust
the small group, matching the pattern elsewhere in this app), started from
the admin Live round page above.

- **Routes:** `GET /live-round/{token}` (the entry page itself),
  `GET /live-round/{token}/leaderboard` (a read-only live leaderboard page),
  `GET /api/live-round/{token}/scores?since={seq}` (poll for changes),
  `POST /api/live-round/{token}/scores` (write N cells — one tap, or a whole
  voice-entry batch — as a single JSON request; Pydantic-validated, the only
  JSON API in this codebase so far),
  `GET /api/live-round/{token}/leaderboard` (JSON standings the leaderboard page polls).
- **Score entry:** three input paths, all writing the same cell via the same API —
  the on-screen keypad (fixed 2–8 or relative-to-par, plus an **"Other"** field for
  anything off the buttons, e.g. a 14), **physical-keyboard** entry when a cell is
  active (type digits, Enter/Tab to commit-and-advance, arrows to navigate, Backspace
  to clear — for laptop use), and **voice** (OS dictation, parsed client-side). Any
  score 1–20 is accepted (`MAX_SCORE` in the template; the old 1–12 keypad ceiling was
  a button-layout limit, not a data one).
- **Finishing / leaderboard:** there's no hard "submit" (the admin still finalizes) —
  instead, once every visible player has all 18 holes in, a **"View leaderboard"** done
  banner appears, and a Leaderboard button is always in the toolbar. The live
  leaderboard is computed straight from staging by `live_round.get_live_leaderboard`
  (reusing `data_update.process_round_for_all_scores`, so gross/net/Stableford match
  the eventual finalized round), shows both competitions (TEG Trophy = net, Green Jacket
  = gross) with a "scoring in progress" banner until all 18 holes are in for everyone,
  and polls every 10s. It reads **only staging** — a live round isn't on the main-site
  `/leaderboard` or `/results` until it's finalized.
- **Page:** a standalone page (does **not** extend `base.html`'s desktop site
  chrome) styled like `webapp/mobile_mockups/round_entry_grid.html`, which it's
  ported from almost verbatim — same grid/keypad/voice-entry/player-group-chips
  interaction design, with the mockup's `BroadcastChannel`/`localStorage`
  cross-tab demo replaced by real `fetch`-based polling (every 3.5s while the
  tab is visible) against the API above. Roster comes from
  `teg_setup.get_teg_roster_form` (only "playing" players get a column) and
  Par/SI from `round_setup.get_round_setup_form` (a live round can't be started
  until that's confirmed — enforced in `live_round.start_live_round`).
- **Sync model:** the server (`teg_analysis.analysis.live_round`), never a
  client clock, assigns each write a monotonic sequence number in arrival
  order — that's what polling deltas are keyed on, and it's what makes the
  mockup's client-timestamp tie-divergence bug structurally impossible here.
  A write from a different device with a different value than the cell's
  current one is applied immediately (entry is never blocked) but flagged
  `conflict: true` (an amber ring in the UI) until an admin resolves it on the
  review page — see the admin section above and
  `DATA_STORAGE_INGESTION_PLAN.md`'s "Phase 3.4 design" for the full model.
- **Device identity:** a `localStorage` UUID plus a self-declared display name
  (asked once, on first load) — enough for conflict attribution, no new auth.
- **Finalize ordering:** `finalize_live_round` holds the module `_lock` only for
  the fast read-validate phase and the terminal status flip; the slow
  `execute_data_update` GitHub commit runs *outside* the lock so it never blocks
  other tokens' writes. A per-token in-process `_finalizing` set (checked under
  `_lock` in every write path) rejects a score that arrives during the commit
  window with a 409 instead of appending it to staging and then silently
  dropping it from the frame already being committed; a failed commit rolls the
  set back and leaves the round `active` to retry. Full ordering rationale is in
  the `finalize_live_round` docstring.

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
  tables.py           # Shared DataFrame -> escaped HTML table renderer (df_to_html)
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

**Dark mode (orthogonal to theme).** A light/dark **mode** is independent of the
named theme: a `mode` cookie (`theme.py: get_mode`, injected as
`request.state.mode`) sets `data-mode="light|dark"` on `<html>`, and
`static/themes/dark.css` overrides the colour variables under
`html[data-mode="dark"]`. It's loaded on every page but inert until dark is
selected (default **light**, so nothing changes unless the user toggles the ◑
button in the nav). Any theme can be shown light or dark. `get_plotly_theme()`
takes a `mode` arg for a dark chart surface (chart routes not yet passing it —
parked with the chart work).

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
def leaderboard(request: Request, data=Depends(get_data)):
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

### Sync `def` handlers, not `async def`
Route handlers here do **blocking** work — cached pandas recompute, volume/CSV
reads, and (on admin routes) GitHub commits. FastAPI runs a plain `def` handler
in its threadpool but runs an `async def` handler *on the event loop*, so an
`async def` handler doing sync work stalls every other in-flight request (worst
during a live round, when phones poll every few seconds while a finalize
commits). **Default to `def`.** Only use `async def` when the handler genuinely
awaits — in practice, reading a **dynamic-keyed** form (`await request.form()`
with keys like `par__{h}` or `score-{h}-{p}` that can't be `Form(...)`
parameters); in that case wrap the heavy sync call in
`starlette.concurrency.run_in_threadpool`. A form with fixed field names should
instead stay `def` and declare `Form(...)` parameters (FastAPI parses the body
for you and still threadpools the handler).

### HTMX partial updates
- Nav links use `hx-get="/route" hx-target="#main-content"`
- Server returns only the content fragment (from `templates/partials/`)
- HTMX swaps into `#main-content` without full page reload

### Common page patterns

- **Simple selector + full-page reload** (e.g. `/teg-reports`): a vanilla form `GET` with `<select onchange="this.form.submit()">`. Cheap when no partial update is needed.
- **HTMX tab bar** (e.g. `/results` in `templates/results.html`): a hidden input holds the active tab; each tab button sets that input then triggers `htmx.trigger(…, 'change')` on the TEG `<select>`, which has `hx-get="/route/table"` returning the partial.
- **`_results_context()`-style HTMX endpoint**: a `{tab}` switch returns `{result_title, table_html}` rendered into `partials/results_table.html` — see `webapp/routes/history.py`.

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

**Page width:**
The default content width is **960px** (`max-width` on `.content-wrapper` and
`.page-title-outer` in `base-vars.css`). This is the standard for all pages.

For pages with genuinely wide content (multi-TEG ranking grids, 18-hole heatmaps,
etc.) pass `"wide": True` in the route's `TemplateResponse` context — `base.html`
adds `body.layout-wide`, which CSS overrides to `max-width: 1280px`:

```python
return templates.TemplateResponse("my_page.html", {
    "request": request,
    "wide": True,   # ← opt into 1280px layout
    ...
})
```

Currently wide: `/scoring/matrix`, `/scoring/heatmap`.
Partials (HTMX responses) never need `wide` — only the full-page handler does.

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
6. If the page has wide content (ranking grids, heatmaps), pass `"wide": True` in the context to opt into the 1280px layout. Default is 960px — see **Page width** above.

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

**Full Streamlit page set replicated**, including data-admin (add a round, edit
metadata CSVs, delete rounds/TEGs, volume browser, GitHub sync, backups, file
guide — see [Admin / data management](#admin--data-management) above); report
generation remains out of scope. The nav mirrors Streamlit's structure exactly
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
- Mobile responsive design + dark mode — **plan drafted** in
  [MOBILE_PLAN.md](MOBILE_PLAN.md); look-and-feel mockups (app vs editorial,
  light + dark) live in `mobile_mockups/` and are served at `/mockups/` when the
  webapp runs. Awaiting a direction decision before the broad implementation.
  - **First slice shipped:** the **Scorecard** page now renders a portrait
    (holes-as-rows) layout on phones (`≤640px`) for all three views, with a
    Gross/Stableford toggle and dark-ready (inert) colour tokens. Desktop/iPad
    are unchanged. See [SCORECARD_PORT.md](SCORECARD_PORT.md). *(Dark mode
    activates once the app-wide `data-mode` toggle is built.)*
    - **Portrait now applies everywhere a scorecard is shown.** The field
      scorecards on **Latest Round** and **Full Results** use
      `build_round_comparison_responsive(round_data, uid)`
      (`teg_analysis/display/scorecards.py`), which emits the landscape
      gross+stableford block plus a portrait Gross/Stableford toggle in one
      go. The toggle's CSS is now **class-based** (`.scm-gross`/`.scm-pts` +
      `.lbl-gross`/`.lbl-pts`), so multiple cards can coexist on a page (one
      per round on Full Results); `uid` keeps each radio group unique.
    - **Scorecard cells have hover tooltips** (native `title`:
      Hole/SI/Par/Score/Net/Stableford) on every page — built in the
      `teg_analysis` builders so they apply wherever a scorecard renders.
    - **Eclectic Scores** (`/eclectic`) now renders with the **gross scorecard
      shapes** via `build_eclectic_scorecard_table` (to-par per hole, coloured
      like a real card) instead of a plain table.
    - **Consistent page width:** `.content-wrapper` / `.page-title-outer` use
      `width:100%` (capped at `min(90vw,1280px)`) instead of `fit-content`, so
      the page no longer resizes to its content — all pages and all scorecard
      views share one width.
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
- ~~**Fix the `/latest-teg` Streaks tab — it only reflects the final round.**~~ Fixed: removed `round_num` filter so the whole TEG is windowed.

**Planned enhancements:**
- ~~**Add an absolute / % pill** to the Scoring tabs on `/latest-teg` and
  `/latest-round`.~~ Done: a Count / % `.pill-group` toggle switches the
  score-count table between raw counts and column percentages (rounded to the
  nearest %). *(Still TODO on the `/scoring/matrix` score-count matrix.)*
- ~~**Show bestball/worstball positions on `/latest-round`.**~~ Done: a
  **Bestball / Worstball** tab renders a field card (one row per player's
  gross-vs-par per hole, field best highlighted green / worst black, plus
  Bestball and Worstball to-par rows in the eclectic shading), with each
  round's bestball and worstball totals ranked against all rounds all-time.
  Below the card, a **Player contributions** CSS-bar table breaks down each
  player's holes/solo-holes/signed shot-impact on the two totals
  (`build_bestball_contribution_bars`).
- ~~**Show the best eclectic for the latest TEG.**~~ Done: an **Eclectic** tab
  on `/latest-teg` shows the TEG's best eclectic (by hole + total) in the
  eclectic scorecard format, ranked against all TEGs.

