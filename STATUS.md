# STATUS

Current state and next priorities. Instructions and architecture live in `CLAUDE.md`; outstanding items live in `TODOS.md`.

**Last updated:** 2026-08-17 (reporting docs reconciled against the code; report-quality rework and readability pass logged below; earlier content current as at 2026-07-12)

## Where things stand

**`teg_analysis/`** — Phases 1–7 cleanup complete (all Streamlit imports removed; aggregation/streaks/scoring refactored; dead code removed). Merged to `main`. Canonical analysis layer, fully UI-agnostic.

**`webapp/`** — Full Streamlit page set replicated and functionally complete. `/` lands on the Contents site map. Nav mirrors Streamlit sections/titles/order from a single source of truth (`webapp/nav.py` → `NAV_SECTIONS`).

**Feature parity — closed.** Every functional gap against Streamlit is closed; all endpoints render their Streamlit-equivalent content. Not an active workstream; `webapp/PARITY_AUDIT.md` is an archive. Modules that came out of it: `analysis/player_rankings.py`, `analysis/handicaps.py`, `display/scorecards.py`, `pivot_window_streaks` in `analysis/streaks.py`. The only residue is cosmetic, absorbed into the formatting pass below.

**Data admin** — Behind cookie auth in `webapp/routes/admin.py`, driven by headless `analysis/data_update.py` + `io/sync.py`: add a round; delete rounds/TEGs; edit metadata CSVs; selective GitHub↔store file sync (pre-action preview + text diff); volume browser (per-file edit/sync/download/delete-with-backup); backups browser (restores back up the replaced copy first); file guide (`io/file_catalog.py`). Report generation is out of scope here.

**Reporting** — LLM-powered tournament reports (`teg_analysis/reporting/`), 5-stage pipeline: scored evidence-carrying beats + competition arcs (code) → structured story plan (LLM) → dry draft as QA scaffold + entertaining write-up + repetition lint (LLM) → CSS-class styled markdown, with mechanical verification (`verify.py`, 8 checks) after every generation. **All 17 TEGs (2–18) published and regenerated on one vintage**; ~$0.65 each. Can run on the Anthropic API (default) or hand prompts off to claude.ai plan usage. ⚠️ **What the site serves lags what was generated** — 16 of 17 styled files still hold pre-2026-08-13 prose, because the regeneration ran `style=False`. Details: `teg_analysis/reporting/README.md`, `teg_analysis/reporting/STATUS.md`.

**Player profiles** (`webapp/routes/player.py`, `webapp/templates/partials/player_overview.html`, `webapp/templates/player_index.html`) — `/player` and `/player/{code}` reworked: pill-driven roster landing with player cards; overview with 11 ranked metric cards, trophy cabinet with ordinal ranks, career highlights, records/worsts in natural language, career trend bar charts with rank annotations. Functionality complete; **UI design pass still outstanding** (`webapp/TODOS.md`).

**Data storage + native round entry** — Railway-volume + GitHub foundation kept and hardened (backups on add, concurrency lock, dead CSV mirrors retired). Google Sheets score capture replaced with a native mobile-first flow:

Code: `teg_analysis/analysis/round_setup.py`, `teg_setup.py`, `live_round.py`; `webapp/routes/admin_round_setup.py`, `admin_teg_setup.py`, `admin_live_round.py`, `live_round.py`.

- **Pre-round setup** (`/admin/round-setup`) — confirm Par/SI (`round_pars.csv`, defaults from `course_pars.csv`)
- **TEG setup** (`/admin/teg-setup`) — confirm roster + handicaps (not every player plays every TEG)
- **Live round entry** — `/admin/live-round` to start/review/finalize; `/live-round/{token}` for players, no login (the link is the access control). Fixed/relative keypad toggle, player-group chip picker, OS dictation voice entry on a sticky-keypad grid. Server assigns write order, so concurrent edits to the same cell are flagged for admin review rather than silently resolved. Finalize runs reviewed scores through `execute_data_update` — one GitHub commit, same as any round addition.
- **Live leaderboard** — `/live-round/{token}/leaderboard`, `get_live_leaderboard` computing gross + net/Stableford from staging via `process_round_for_all_scores`. Shows "scoring in progress" until every player is thru 18; reads staging only (a live round isn't on the main site until finalized). "View leaderboard" banner once a group has all 18 in.
- **Admin review** — full staged scorecard as an editable grid. `apply_admin_edits` is the authoritative bulk-edit primitive; `resolve_conflict` wraps it.
- **Direct entry + score ceiling** — physical-keyboard entry on the active cell (digits, Enter/Tab, arrows, Backspace) plus an "Other" keypad field; ceiling raised 12 → `MAX_SCORE = 20` across keypad/voice/admin. Covered by `tests/test_live_round_e2e.py::test_live_leaderboard_out_of_range_and_admin_edit`.

Design detail lives in docstrings in `analysis/live_round.py` and `webapp/README.md` → "Live round entry". Planning doc retained as reference: `DATA_STORAGE_INGESTION_PLAN.md`.

**Guided new-round wizard** (`teg_analysis/analysis/round_wizard.py`, `webapp/routes/admin_new_round.py`, templates `admin_new_round.html` / `admin_new_round_wizard.html`) — `/admin/new-round` (first in admin sub-nav) orchestrates round metadata → roster+handicaps → Par/SI → go live as one linear stepper. Stateless and resumable: each step saves via the existing tested functions and the current step is recomputed from data on every visit (`get_wizard_status`), so round 2/3/4 auto-skips confirmed roster and a half-finished setup resumes by revisiting the URL. Net-new piece is a round-metadata form (`get_round_metadata_form`/`save_round_metadata`) deriving `TEGRd`/`TEG`/`Area`/`Year`. Standalone pages remain reachable for edits. Detail: `webapp/README.md` → "New round (guided wizard)".

## Recent change log

### 2026-08-17 — Reporting docs reconciled against the code

No pipeline change. `teg_analysis/reporting/` docs (README, ARTEFACTS, STATUS, ONBOARDING, EXPERIMENTS)
were checked against the code, the artefacts on disk, a full test run (**518 passed** then; 520 after the 08-16 voice-slot tests) and a full
`verify --all --rounds` run, and corrected. Four corrections change what to do next:

- **The library has no fixture gaps and only one vintage.** All 17 TEGs have the complete artefact chain;
  the old "regenerate 2–8, 15, 16, 9" and "rebuild TEG 14's fixtures" items were already done.
- **D3 is clean on every tournament report** — 0 errors across all 17, so the 81-fault backlog cleared on
  the 2026-08-13 regeneration. The only 4 errors left are in round reports.
- ⚠️ **16 of 17 styled reports don't match their finals**, so none of the regenerated prose has reached a
  reader. `style=False` was deliberate; the consequence was never measured until now.
- **Three new small issues logged**: `TIGHTEN_SYSTEM` still contradicts the em-dash ban (dormant), a
  stray tracked `reply.txt` at the repo root holding an unpublished TEG 17 report, and raw `SI n` leaking
  into published prose.

### 2026-08-16 — Writer prompt gains a swappable voice slot

`WRITER_SYSTEM` went from two composed constants to three. The new `WRITER_CONTRACT` holds everything
true of a report whatever register it is written in (the winner's-story duty, structure, palette,
notation rules); `WRITER_VOICE` keeps only the register and can be replaced per call via
`build_writer_system(voice=...)`. `write_from_dry(teg, voice, label)` runs the real writer over a
frozen dry draft in a supplied voice, so trialling a register no longer needs a source edit;
`plan_scope=` and `bundle_context=` control how much material goes in with the draft.

Opt-in throughout — the production chain passes no voice, and nothing regenerates until a backfill
runs. Detail: `teg_analysis/reporting/STATUS.md` → START HERE.

### 2026-08-14 → 08-15 — Report quality: counterfactual importance, then a readability pass

Two rounds of change to what a report says and how it reads. Detail in
`teg_analysis/reporting/STATUS.md` → START HERE.

**The data layer (08-14).** Three root causes of "the reports are hard on the champion" turned out to be
in the data, not the prompts. `importance` claimed to measure contribution to the result but never
consulted the result — it is now **counterfactual** (`impact.py`): replace a player's scores over the
event with their own TEG average, recompute each competition in its own metric, and measure the swing.
Detection was lopsided 2.6:1 negative because bad things were found on gross and good things on net —
two new detectors bring it to 1.52:1. And nothing computed *why* the champion won, so `win_anatomy.py`
plus a required `why_the_champion_won` plan field now do. Champion's share of negative beats: 20% → 14%.

**The voice (08-15).** Voice was being defined in four places and three had drifted; it now lives once in
`reporting/prompts.py` and every prompt imports it, which incidentally moved the round writer onto the
current register. Then Jon read the reports — *"80% good, lacking a bit in humour, and a bit hard to
read"* — and the humour dial was settled at `humour6`, em-dashes banned outright, sentences capped at a
~15-word average. Enforced by a new `verify.py` check, not just prompt text, because the previous
sentence cap was contradicted elsewhere in the prompt and consequently ignored 18–31% of the time.

### 2026-08-15 — Report generation can run on plan usage, or in any other model

Report generation no longer has to bill per API call. `llm.py` gained a provider switch —
`TEG_LLM_PROVIDER=api|agent` — with **`api` still the default**, because it is the only mode that
works with nobody present. Three ways to run, one flag each:

- `--tegs 2-18` — the API, as before.
- `--tegs 14 --plan` — the pipeline writes each prompt to `data/llm_mailbox/` and waits; the
  `teg-report-respond` Claude Code skill answers it in-session, drawing on claude.ai plan usage.
- `--tegs 14 --paste gpt5` — same hand-off, but for you to paste into ChatGPT or Gemini, with
  output kept in `data/commentary/variants/gpt5/`.

Both hand-off modes can run at once: runs are discovered by scanning, and a paste run is marked
manual so the skill cannot answer prompts meant for another model.

The pipeline itself is unchanged — `backfill_all` and the four-call chain have one
implementation under either provider. Structured output, which the API path got free from
`messages.parse`, now ships its JSON Schema in the prompt and validates with Pydantic on the way
back, re-asking with the error on failure.

New: `teg_analysis/reporting/mailbox.py`, `paths.py`, a `--tegs` CLI on `backfill`, and
`.claude/skills/teg-report-respond/`. **The mechanism has since been run on real reports** (TEG 17 and
TEG 14 both went through the hand-off); what remains unmeasured is whether plan-usage output matches API
output in quality. Detail in `teg_analysis/reporting/README.md` → *Who answers the prompts*.

### 2026-07-09 → 07-10 — Codebase review remediation (complete)

Batched review of `webapp/` and `teg_analysis/` (streamlit frozen throughout), eight change-sets plus a closing review pass. All resulting rules are now recorded as invariants in `CLAUDE.md`.

- **Live-round data integrity** — server-side validation in `apply_score_writes`/`apply_admin_edits`; a stray value/hole/player can no longer silently drop a round
- **Pipelines fail loudly** — `update_*_cache` take `all_data` and raise; orchestrators collect into `cache_errors` via `_run_cache_step`, surfaced as an admin warning banner
- **One copy of the scoring math** — `process_round_for_all_scores` canonical in `data_update.py`, thin re-export in `core/data_loader.py`
- **No event-loop blocking** — route handlers sync `def`; finalize's GitHub commit runs outside `live_round._lock`, with an in-process `_finalizing` set gating mid-commit writes (409, not silent drop)
- **Webapp dedup** — one escaping `webapp/tables.py::df_to_html` replaced 7 copy-pasted renderers (all cells now HTML-escaped); swallowed `except` → `logger.exception`; `deps.cached_winners()`/`cached_streaks_data()` replaced three ad-hoc winner sources and per-request streak reads
- **Deterministic aggregation** — `aggregate_data` uses a fixed `_AGGREGATION_LEVEL_FIELDS` map instead of per-call `groupby().nunique()` discovery (byte-identical output, deterministic order)
- **Stableford gate** — aligned to the domain rule via `STABLEFORD_ERA_TEG = 8`
- **Prototype routes deleted** — `charts_proto`, `width_test`, `title_preview`, `showcase`, `smoke_test`, `placeholder`
- **Test guards made real** — streamlit-import guard and the `test_core_functions.py`/`test_independence.py` smoke tests now assert/raise instead of returning a bool pytest ignored; this also exposed a stale `format_vs_par(0)` expectation

Tests: 349 passed, 4 skipped (env-only altair imports). No `streamlit/` file changed.

### 2026-07-10 — Webapp to-do batch (branch `claude/web-app-todos-planning-0o3uui`, PR #67)

- **Quick fixes** — `df_to_html` renders scalar NaN/None as `-` (fixes `/scoring/by-teg`); `/scoring/by-par` column padding; `/scoring/distributions` chart follows the %/Count toggle and overlays an "All players" team-average tick per category in % mode; eclectic/bestball birdie-ring sizing
- **Performance** (profiled with warm caches) — player pages ~1.7s → ~190ms by caching player-independent global records/worsts tables in `webapp/routes/player.py` via `deps.register_cache_clearer` (first consumer); `core/metadata.py::get_scorecard_data` gained an optional `data=` param so five webapp callers pass `cached_load_all_data()` instead of re-reading the dataset per request (biggest win on Railway's mounted volume)
- **Latest-TEG Eclectic** — now mirrors the bestball "in context" tab: player-ranks table (all-time vs completed TEGs + own history) and CSS-bar contribution breakdown, via new UI-agnostic `eclectic_player_teg_totals`/`rank_teg_eclectics`/`calculate_eclectic_contributions` (`analysis/eclectic.py`) and `build_eclectic_contribution_bars` (`display/scorecards.py`); in-progress TEG shows a provisional-ranks caption
- **Charts** — multi-series charts dim other series on legend hover (centralised Plotly renderer in `base.html`)

Tests: 357 passed, 4 skipped.

### 2026-07-12 — Report refresh + sync filter (branch `claude/railway-mounted-storage-badrzy`)

`main` had already moved report reads onto the volume (`read_text_file`, discovery from `completed_tegs.csv`), auto-caching a *new* report on first view. Gap: a *regenerated* report (same filename, new content) stayed stale with no refresh path. Added `sync.sync_report_files()` — re-pulls every report-pattern file (`_REPORT_FILE_PATTERNS`, excluding the ~250 draft/version `.md`) GitHub→store with backups — wired to a one-click "Sync all reports from GitHub" on `/admin/volume-sync`. Sync page also gained a filter/search box and visible-only "select all".

Tests: `tests/test_sync.py` (pattern filter + overwrite), `tests/test_admin_routes.py` (endpoint). Docs: `DATA_FLOW.md` I/O layer.

### 2026-07-12 — TEG Reports load-perf fix (branch `claude/teg-reports-load-perf-0e74ea`)

`/teg-reports` was slow on every load. Two causes in `webapp/routes/reports.py`:

1. `read_text_file` cached volume *hits* but never *misses*, so each probe of a non-existent candidate path was an uncached GitHub 404 round-trip — ~3–4 per load (~1–2s) even with a warm volume
2. Discovery rendered the full markdown of every existing round report to HTML just to test existence, then discarded it (4 wasted renders/load)

Fix: discovery is existence-only (new `_round_report_text`/`_tournament_report_text` raw-text finders; `_load_*_report` renders only for display) and memoised in-process (`lru_cache` on `_completed_teg_numbers`/`_rounds_played_for_teg`/`_available_rounds_for_teg` + new `_satire_available`), cleared via `deps.register_cache_clearer` so the report-sync button still surfaces regenerated reports. The *displayed* report stays uncached. Steady state: 4 renders + 9 reads → 1 render + 1 read; per-load GitHub 404s now paid once per process.

Tests: 116 passed (report/admin/sync subset).

## Next priorities

1. **Mobile UI + dark mode** — make the webapp app-like on phones, light + dark, **without changing the laptop/iPad render**. Direction chosen: **A — full native-app feel** (bottom tab bar, sticky app bar, reflowed data). Done: dark-mode foundation (`static/themes/dark.css` + `data-mode` toggle, opt-in default light) and the portrait scorecard. **Next: Phase M1, the app shell.** Approach + progress + pickup pointer: `webapp/MOBILE_PLAN.md`; scorecard work-package: `webapp/SCORECARD_PORT.md`; mockups in `webapp/mobile_mockups/` (served at `/mockups/`).
2. **Webapp formatting pass** — visual polish, number formatting, table styling consistency, layout refinement, plus the WIP heatmap. In progress in local branches.
3. **REST API** — proper `/api` layer over `teg_analysis`, so any client can use the analysis layer without Python. Currently a placeholder in `teg_analysis/api/`.
4. **Retire Streamlit** — delete `streamlit/` once the REST API and webapp are production-ready. Nothing depends on it now; it is kept only as a reference.
