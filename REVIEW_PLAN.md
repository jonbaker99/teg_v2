# Codebase Review — Findings & Execution Plan

> **Temporary working document** (per CLAUDE.md docs Rule 3): delete this file once every
> batch below has landed, folding anything of lasting value into the relevant README.
>
> Produced by the 2026-07-09 review of `webapp/` and `teg_analysis/` on branch
> `claude/teg-v2-review-pnnj84` (which also carries the unmerged live-round / wizard
> feature work — findings apply to this branch's state). `streamlit/` was out of scope.
>
> Verified at review time: `python scripts/check_pandas_compat.py` → 0 errors
> (all warnings checked and safe); `pytest tests/` → **241 passed, 3 failed**
> (2 real — see W0 — plus 1 env-only `altair` import failure).

---

## How to use this document

Work is batched into **chats** (sessions), each sized to one coherent scope. Run them in
order — later chats assume earlier ones have landed. For each chat:

1. Start the chat on the model tier listed (per CLAUDE.md Model Selection).
2. Paste the chat's **starter prompt** (in the ```text block under each chat) as the
   kickoff message. Prompts are self-contained: they tell the fresh session to read this
   file for full context.
3. On completion, tick the checkboxes here, update the "Current state" section of
   CLAUDE.md if the change is architectural, and run the **review gate** (below).
4. Chats marked ⚠️ **owner decision** need an answer from Jon before starting —
   fill the answers into the prompt where marked `<<...>>`.

**Review gate (end of every Sonnet/Haiku chat, and Chat 8 in full):** on Opus —
re-read every changed file end-to-end; grep for old function names to catch orphaned
callers; confirm nothing under `streamlit/` changed; run `pytest tests/ -v` and
`python scripts/check_pandas_compat.py`; then commit.

---

## Owner decisions needed (blocking Chat 7)

- [ ] **Prototype routes**: `charts_proto`, `width_test`, `title_preview`, `showcase`,
      `smoke_test`, `placeholder` are publicly served on the production site
      (`webapp/app.py:59-74`). Delete, or gate behind admin auth? Which are still used? DELETE
- [ ] **Stableford era gate**: comeback/collapse analysis filters Stableford to
      `TEGNum >= 6` (`teg_analysis/analysis/aggregation.py:433,500,605,740`) but the
      domain rule (`get_net_competition_measure`) says Stableford from TEG 8.
      Is 6 intentional (Stableford *recorded* from TEG 6) or a bug? A BUG
- [ ] **Docs contradiction**: CLAUDE.md says the live-round planning doc was deleted,
      but `DATA_STORAGE_INGESTION_PLAN.md` exists and is referenced from
      `webapp/routes/admin_live_round.py:5` and `teg_analysis/analysis/live_round.py`.
      TODOS.md says it's "kept as a historical/reference record", so the likely fix is
      correcting CLAUDE.md — confirm, or delete-and-fold instead? CONFIRM

---

## Findings — Part 1: webapp/

| ID | Sev | Location | Defect | Failure scenario / cost |
|----|-----|----------|--------|--------------------------|
| W1 | HIGH | `webapp/routes/live_round.py:107` | Player score-write API has **no server-side validation**; the 1–20 cap exists only in template JS (`live_round_entry.html:271`) and is separately hardcoded in `admin_live_round.py:161` | A client POST with `value=99` finalizes into the permanent record; a stray `hole=42` gives a player 19 staged rows so the 18-row filter in `finalize_live_round` **silently drops their whole round**; a typo'd player code creates orphan staging rows |
| W2 | HIGH | all `webapp/routes/*.py` | Every handler is `async def` but does blocking sync work (pandas recompute, volume reads, GitHub commit in finalize) — FastAPI can't threadpool `async def`, so it all runs on the event loop | While finalize commits to GitHub (seconds, also holding `live_round._lock`), every polling phone and every page request stalls — worst at live-round peak concurrency |
| W3 | MED | `scoring.py:49`, `latest.py:65`, `history.py:95`, `performance.py:25`, `eclectic.py:30`, `scorecards.py:20`, `player.py:513` | `_df_to_html` copy-pasted 7× with inconsistent escaping (only player.py escapes) | A course/player name containing `&`/`<` breaks rendering on six page families; every table tweak ×7 |
| W4 | MED | `scoring.py`, `latest.py`, `history.py`, `performance.py`, `eclectic.py` (~40 sites) | Blanket `except Exception as e: return {"error": str(e)}` with **no logging** | Production regressions show "Error: 'X'" to the user and leave nothing in Railway logs — undiagnosable after the fact |
| W5 | MED | `history.py:307` vs `player.py:78` vs `history.py:234` | Winners data sourced three ways: recomputed per `/honours` tab click, lru-cached in player.py, and read from `data/teg_winners.csv` for `/history` | Redundant compute; three sources that can disagree after a data edit |
| W6 | MED | `player.py:190/227` (double `_metric_specs`), `:256-434` (`_records_held`/`_worsts_held`), `:587` (per-TEG rank loop), `:1049` (`build_streaks` from scratch) | Player profile recomputes heavy work per request/tab-click; ignores the maintained `streaks.parquet` cache | The flagship profile page is the slowest in the app; all redone on every tab switch |
| W7 | MED | `scoring.py:158`, `latest.py:378,428,587,602` | `streaks.parquet` read from disk per request — no `deps` cached accessor, unlike every other dataset | Needless volume reads on hot tabs; inconsistent caching pattern |
| W8 | LOW/MED | `webapp/app.py:59-74` | Prototype/debug routers mounted in production (see owner decision) | Unauthenticated debug pages on the live site |
| W9 | LOW | `latest.py:449`, `scoring.py:164`, `deps.py:205`, `player.py:699,897` | Fragile TEG-label parsing scattered; hardcoded fallback TEG `18`; unused `theme` params | Breaks quietly if a label format changes; dead params confuse readers |
| W10 | MED (tests) | `tests/` | Zero tests for `/player` (recently overhauled), `/latest-*`, `/scoring/*`, `/honours`, `/results` context builders | A column rename in teg_analysis ships silently as W4-style runtime errors |

Pandas 2.x: **no new violations** in webapp (checker warnings at `deps.py:166-172` use the
documented safe pattern; `player.py:295/381` are comparisons, not assignments).

## Findings — Part 2: teg_analysis/

| ID | Sev | Location | Defect | Failure scenario / cost |
|----|-----|----------|--------|--------------------------|
| T1 | HIGH | `tests/test_live_round.py` (`test_finalize_refuses_when_not_active`, `test_finalize_only_includes_complete_18_hole_rounds`) | Commit `aa3549b` added the roster-confirmation guard (`live_round.py:254`) without updating fixtures — both fail with `FileNotFoundError: data/handicaps.csv` | The suite is red on this branch before any new work starts |
| T2 | HIGH | `pipeline.py:105-110,164-166,295-300`; `data_update.py:523-533,718-728` | `update_streaks_cache` / `update_commentary_caches` / `update_bestball_cache` swallow all exceptions and return `None`; `execute_data_update`/`_deletion` treat `None` as benign and report success | An add commits new all-scores while streaks/commentary/bestball stay **silently stale**; the site shows wrong streaks/records and the admin is told everything worked |
| T3 | MED | `tests/test_no_streamlit_imports.py:101` | Test **returns** `True`/`False` instead of asserting — pytest passes it unconditionally | The "no streamlit in teg_analysis" architecture guard is unenforced except when run as a script |
| T4 | MED | `core/data_loader.py:167` vs `analysis/data_update.py:103` | `process_round_for_all_scores` duplicated; the data_loader copy mutates its input (`rename(inplace=True)`, no `.copy()`) and has no internal callers (export-only) | Core scoring math in two places has already drifted once; silent divergence risk |
| T5 | MED | `aggregation.py:103,126` | `aggregate_data` rediscovers a fixed schema via `groupby().nunique()` over every column ×4 levels on **every call**; `list(set(group_columns))` makes column/sort order nondeterministic | Wasted compute behind every cached accessor and the per-request `/scoring/by-teg`; run-to-run ordering wobble |
| T6 | MED | `aggregation.py:433,500,605,740` | Stableford gated at `TEGNum >= 6` vs domain rule (TEG 8+) — see owner decision | Comeback tables may include two TEGs they shouldn't, or a correct magic number goes unexplained |
| T7 | LOW/MED | `pipeline.py:33-41` | `_get_deps()` returns `locals()` — obfuscated imports; `execute_data_update` reloads `load_all_data` 4× across cache-regen steps | Defeats grep/static analysis; slow admin updates |
| T8 | LOW | `live_round.py` | Every poll re-reads registry + staging CSVs; one `_lock` across all tokens, held through finalize's GitHub commit | Acceptable at group scale; the lock scope is what makes W2 bite |
| T9 | INFO | `commentary.py:797-799` | Compat-checker `rank-int-unprotected` warnings — verified numeric-only use | No change needed |
| T10 | MED (tests) | `teg_analysis/reporting/` (~4.5k lines), `analysis/commentary.py`, comeback fns in `aggregation.py` | Zero tests | Regressions in report generation / comeback tables ship undetected |
| T11 | LOW (docs) | CLAUDE.md vs `DATA_STORAGE_INGESTION_PLAN.md`; `reporting/*.md` ×5 | Docs contradiction + .md accumulation (see owner decision) | Docs describe a state that isn't true |
| T12 | MED (tests) | `tests/test_core_functions.py` (`test_metadata_functions`, `test_data_loader_functions`, `test_aggregation_functions`, `test_ranking_functions`, `test_display_functions`), `tests/test_independence.py` (`test_no_streamlit_dependency`) | Same return-`True`/`False`-instead-of-assert pattern as T3 (found while fixing T3; pytest emits `PytestReturnNotNoneWarning` on all six) — pytest passes them unconditionally regardless of what the function found | These checks (data-loader/aggregation/ranking/display smoke tests, and the teg_analysis-independence guard) are unenforced; a real regression would show only as a warning, never a failure |

---

## Execution plan — batched into chats

Each chat = one session, one coherent scope, sized to stay reviewable. Order matters.

### Chat 1 — Make the suite green and the guards real *(Sonnet)*
- [x] **T1**: Seed `handicaps.csv` in the live-round test fixtures; add a test asserting
      the unconfirmed-roster refusal path. Files: `tests/test_live_round.py`.
- [x] **T3**: Convert `test_no_streamlit_imports` to `assert not imports, ...`
      (keep script mode working). Files: `tests/test_no_streamlit_imports.py`.
- [ ] Review gate (Opus).

**Flagged for the Opus review gate:** while fixing T3, found the same
return-`True`/`False`-instead-of-assert pattern in `tests/test_core_functions.py`
(5 test functions) and `tests/test_independence.py` (`test_no_streamlit_dependency`)
— now tracked as **T12** in the findings table above. Out of scope for this chat
(T3 only named `test_no_streamlit_imports.py`), but it's the same class of
unenforced guard and worth a follow-up chat to convert all six.

*Why together*: both are test-infrastructure fixes; tiny; everything else depends on a
trustworthy green suite.

**Starter prompt:**
```text
Read REVIEW_PLAN.md (Chat 1) for full context, then fix the test suite — code changes to
tests only, no product code:

1. T1: tests/test_live_round.py has 2 failures (test_finalize_refuses_when_not_active,
   test_finalize_only_includes_complete_18_hole_rounds) because finalize_live_round now
   reads data/handicaps.csv (roster-confirmation guard at
   teg_analysis/analysis/live_round.py:254) and the fake-file fixtures don't seed it.
   Seed a handicaps row for the TEGs those tests use, and add one new test asserting
   finalize raises ValueError when the TEG has no handicaps row.
2. T3: tests/test_no_streamlit_imports.py returns True/False so pytest always passes it.
   Convert to `assert not imports, <formatted list>` while keeping the
   `python tests/test_no_streamlit_imports.py` script mode working.

Done when: `pytest tests/ -v` is green except the known env-only altair import test.
Then tick the Chat 1 boxes in REVIEW_PLAN.md, commit, and note anything left for the
Opus review gate.
```

### Chat 2 — Live-round server-side validation *(Sonnet)*
- [x] **W1**: Add `MAX_SCORE = 20` (+ hole 1–18, player-in-roster checks) inside
      `apply_score_writes` and `apply_admin_edits`; make the admin route and the entry
      template consume the same constant (template gets it via context). Reject invalid
      cells with a clear error rather than dropping them silently. Tests for each
      rejection. Files: `teg_analysis/analysis/live_round.py`,
      `webapp/routes/live_round.py`, `webapp/routes/admin_live_round.py`,
      `webapp/templates/live_round_entry.html`, `tests/test_live_round*.py`.
- [ ] Review gate (Opus).

*Why alone*: highest user-facing data-integrity risk; touches the API contract, so keep
the diff focused and well-tested.

**Flagged for the Opus review gate:**
- Validation is all-or-nothing per batch: if any cell in a write is invalid,
  `InvalidScoreCellError` is raised and *nothing* in that batch is written (not even the
  valid cells) -- a partial silent write felt like the same class of surprise this fix is
  meant to remove. Worth confirming that's the right call for voice-entry batches (a
  whole transcript could be dropped by one bad token) vs. writing the valid subset and
  reporting the rest as rejected.
- The player-facing API (`webapp/routes/live_round.py`) surfaces `InvalidScoreCellError`
  as a 422 with the structured `errors` list in the body, per the starter prompt. The
  admin bulk-edit route (`webapp/routes/admin_live_round.py`'s `/edit`, a plain form POST
  + 303 redirect, not a JSON API) instead redirects back to the review page with
  `?error=<message>`, rendered via the existing `{% if error %}` block -- there's no
  natural place to return a 422 status from a redirect-based form handler. That route
  already pre-filters obviously-bad values before calling `apply_admin_edits` (silently
  ignoring blank/out-of-range typed values, a UX choice for a free-text grid, not a
  validation bypass), so the new `apply_admin_edits`-level validation is mostly
  defense-in-depth there; the `?error=` path exists for the player-not-on-roster case,
  which the route's own pre-filter doesn't check.
- `apply_score_writes`/`apply_admin_edits` now call `get_teg_roster_form(teg_num)` on
  every write to validate the player -- an extra `handicaps.csv`/`players.csv` read per
  request, same class of per-poll cost already accepted for T8 at this group scale.

**Starter prompt:**
```text
Read REVIEW_PLAN.md (finding W1 / Chat 2) for full context, then add server-side
validation to live-round score writes. Today the 1-20 cap exists only in template JS
(webapp/templates/live_round_entry.html, `const MAX_SCORE = 20`) and is separately
hardcoded in webapp/routes/admin_live_round.py:161; apply_score_writes and
apply_admin_edits in teg_analysis/analysis/live_round.py accept anything.

1. Define MAX_SCORE = 20 once in teg_analysis/analysis/live_round.py.
2. In apply_score_writes and apply_admin_edits, reject cells with hole outside 1-18,
   value outside 1-MAX_SCORE (None stays valid = clear), or player not in the TEG's
   playing roster (get_teg_roster_form). Reject loudly (raise or return a per-cell
   error list the API surfaces as 422) — do NOT silently drop cells.
3. Make admin_live_round.py and the entry template consume the same constant (pass it
   into the template context instead of the JS literal).
4. Tests in tests/test_live_round*.py for each rejection case, plus one asserting a
   valid batch still writes.

Watch out: a stray out-of-range hole row currently makes a player's card 19 rows, so
finalize's 18-row filter silently drops their whole round — add a test proving that can
no longer happen. Done when pytest is green. Tick the Chat 2 boxes in REVIEW_PLAN.md,
commit, and flag anything for the Opus review gate.
```

### Chat 3 — Data-pipeline hygiene: no silent failures *(Opus)*
- [x] **T2**: Make the `update_*_cache` functions raise (or return typed error markers);
      `execute_data_update`/`execute_data_deletion` collect failures into a
      `cache_errors` field in the result; admin result templates render a warning banner
      when present. Files: `teg_analysis/analysis/pipeline.py`,
      `teg_analysis/analysis/data_update.py`,
      `webapp/templates/partials/admin_update_result.html`,
      `webapp/templates/partials/admin_live_round_finalize_result.html`, tests.
- [x] **T7**: Replace `_get_deps()`/`locals()` with plain deferred imports; load
      `all_data` once in the orchestrators and pass it into the `update_*` functions.
- [x] **T4**: De-duplicate `process_round_for_all_scores` — keep the data_update
      version, re-export from `core.data_loader`/`core.__init__`, delete the mutating
      copy (grep all callers incl. tests first).
- [x] Review gate = the chat itself is Opus; still run the checklist before committing.

**Chat 3 landed:** the `update_*_cache` functions now take `all_data` (loaded once per
orchestrator) and raise on failure instead of swallowing to `None`; both orchestrators
wrap the three named cache steps in `_run_cache_step`, so the primary all-scores/all-data
write still lands while any cache failure is collected into a new `cache_errors` list on
the result dict (rendered as a warning banner in both admin result partials).
`process_round_for_all_scores` now has one implementation (in `analysis/data_update.py`);
`core/data_loader.py` keeps a thin non-mutating re-export for its long-standing importers.
Tests added: a mocked cache-step failure asserts `cache_errors` is populated while
`records_added`/`rows_deleted` stay correct (add + delete paths). Full suite green
(254 passed, 4 skipped); `check_pandas_compat.py` 0 errors; `streamlit/` untouched.

*Why together*: all three live in `pipeline.py`/`data_update.py`/`core`; one coherent
"the update pipeline fails loudly and has one copy of the math" change.

**Starter prompt:**
```text
Read REVIEW_PLAN.md (findings T2, T7, T4 / Chat 3) for full context. Goal: the data
update pipeline fails loudly and has one copy of the scoring math.

1. T2 (the important one): update_streaks_cache / update_commentary_caches /
   update_bestball_cache in teg_analysis/analysis/pipeline.py catch every exception and
   return None; execute_data_update / execute_data_deletion in
   teg_analysis/analysis/data_update.py treat None as benign and report success — so an
   add can commit new all-scores while derived caches stay silently stale. Make the
   update_* functions raise (or return a typed error), have the orchestrators collect
   failures into a `cache_errors` field on the result dict (the primary write should
   still land — partial success is better than losing the round), and render a warning
   banner in webapp/templates/partials/admin_update_result.html and
   admin_live_round_finalize_result.html when cache_errors is non-empty. Tests: mock one
   update_* to fail, assert cache_errors is populated and records_added still correct.
2. T7: delete the _get_deps()/locals() hack in pipeline.py (plain deferred imports),
   and load all_data once in each orchestrator, passing it into the update_* functions
   instead of each reloading it.
3. T4: process_round_for_all_scores exists in both core/data_loader.py:167 (mutates its
   input, no internal callers) and analysis/data_update.py:103 (the good copy). Keep the
   data_update one, re-export it from core.data_loader and core/__init__.py for
   compatibility, delete the duplicate body. Grep all callers (incl. tests and
   ad_hoc_analysis) first.

Don't touch streamlit/. Done when pytest is green and a simulated cache failure shows
the warning banner. Tick the Chat 3 boxes in REVIEW_PLAN.md and commit.
```

### Chat 4 — Event-loop blocking *(Opus)*
- [x] **W2**: Convert route handlers to sync `def` (FastAPI threadpools them) or wrap
      heavy calls in `run_in_threadpool`; verify HTMX behaviour unchanged.
- [x] **T8 (partial)**: Move the GitHub commit in `finalize_live_round` outside
      `live_round._lock` (staging is already read and status not yet flipped — design the
      ordering carefully).
- [x] Manual concurrency check: poll `/api/live-round/{token}/scores` while a finalize
      runs; pages must stay responsive.
- [x] Review checklist before committing.

*Why alone*: cross-cutting concurrency change; needs Opus-level care and its own
verification pass.

**Chat 4 landed:** every handler in `webapp/routes/*.py` that did no `await` is now a
plain `def`, so FastAPI runs it in its threadpool off the event loop (all GETs, the
Pydantic-body live-round poll/write APIs, and — critically — `admin_live_round_finalize`,
which does the GitHub commit). Handlers that read a **static/list** form were converted to
`def` with `Form(...)` params (whole handler threadpooled, including any ctx-builder I/O);
the six that read **dynamic-keyed** forms (roster `playing__{code}`, hole `par__{h}`, the
edit grid's `score-{h}-{p}` / `cell__{r}__{c}`) stay `async def` and wrap only their heavy
save/commit call in `starlette.concurrency.run_in_threadpool`. HTMX behaviour and response
types are unchanged (same templates, same 303/200/409/422 codes). For **T8**,
`finalize_live_round` now holds `_lock` only for the read-validate phase and the terminal
status flip; `execute_data_update`'s GitHub commit runs *outside* the lock, gated by an
in-process `_finalizing` set so a write arriving mid-commit is rejected (409) rather than
appended to staging and silently excluded from the already-built frame — a commit failure
rolls the set back and leaves Status `active` to retry (no half-finalized state persisted;
ordering documented in the docstring). New tests:
`test_write_during_finalize_commit_is_rejected`,
`test_failed_finalize_commit_rolls_back_and_reopens_writes`. Concurrency verified against
the real ASGI app: 12 polls stayed at ~8–10 ms while a mocked 4 s finalize was committing.
Threading: `deps.py` lru_caches are thread-safe; `_extra_cache_clearers` is mutated only at
import time; `core.players` and `live_round` caches carry their own locks. Full suite green
(256 passed, 4 skipped); `streamlit/` untouched.

**Starter prompt:**
```text
Read REVIEW_PLAN.md (findings W2, T8 / Chat 4) for full context. Every webapp route is
`async def` but does blocking sync work (pandas recompute, volume/CSV reads, and — in
admin_live_round_finalize — a GitHub commit), so it all runs on the event loop and one
slow request stalls every other request. This bites hardest during live rounds: phones
poll /api/live-round/{token}/scores every few seconds while finalize blocks for seconds.

1. W2: Convert route handlers across webapp/routes/*.py from `async def` to plain `def`
   so FastAPI runs them in its threadpool. Keep `async def` only where a handler
   genuinely awaits (e.g. `await request.form()` — for those, either keep async and wrap
   the heavy sync call in `starlette.concurrency.run_in_threadpool`, or read the form
   differently). Confirm HTMX behaviour and response types are unchanged.
2. T8 (partial): In teg_analysis/analysis/live_round.py, finalize_live_round holds the
   module-wide `_lock` through execute_data_update (network I/O to GitHub), blocking all
   live-round writes for every token. Restructure so the lock covers only the
   staging/registry read-validate phase and the final status flip, not the GitHub
   commit — think through what happens if a write arrives mid-finalize and document the
   chosen ordering in the docstring.
3. Verify: `pytest tests/ -v` green, then run the app locally and poll the scores API
   in a loop while triggering a (mocked-slow) finalize — polls must keep responding.

Threading note: the in-process lru_caches in webapp/deps.py will now be hit from
threadpool workers — confirm that's safe (lru_cache is thread-safe; check anything else
with shared mutable state, e.g. register_cache_clearer). Tick the Chat 4 boxes in
REVIEW_PLAN.md and commit.
```

### Chat 5 — webapp dedup + caching batch *(Sonnet)*
- [x] **W3**: One shared escaping `df_to_html` (new `webapp/tables.py`); delete the 7
      copies; keep per-page class hooks via parameters.
- [x] **W4**: `logger.exception(...)` in every `except Exception` context builder
      (keep the user-facing message).
- [x] **W5 + W7**: Add `deps.cached_winners()` and `deps.cached_streaks_data()`
      (registered with `clear_all_data_caches`); point `/honours`, `/player`,
      `/latest-*`, `/scoring/streaks` at them; retire player.py's private winners cache.
- [x] **W6**: Player-profile cleanup — compute `_metric_specs` once per request, use the
      cached streaks instead of `build_streaks`, drop unused `theme` params.
- [x] **W9**: Small tidies — one TEG-label parse helper; named constant for the
      fallback TEG.
- [ ] Review gate (Opus).

**Chat 5 landed:** new `webapp/tables.py` exposes one escaping `df_to_html(df,
table_class=, col_class=, cell_classes=, link_players=, highlight_col=,
highlight_val=)` covering every variant the 7 copies needed (plain, first-col/rest
positional classing, per-cell class overrides, player-name links, row highlighting).
All 7 copies deleted; `scoring.py`, `eclectic.py`, `scorecards.py`, `performance.py`
import it directly as `_df_to_html`/`_df_to_html`(aliased), `history.py` uses it
directly (its `link_players` signature matched exactly), `latest.py` keeps a
2-line `_df_to_html` wrapper (first-col-left positional classing is page-specific),
and `player.py`'s `_build_simple_table_html` + `_build_teg_results_table_html` both
now delegate to it via a shared `_col_class` helper. No caller currently passes
pre-built HTML into a cell (verified by trace), so no raw/markup opt-in was added --
every cell is escaped. `except Exception as e:` blocks across scoring.py, latest.py,
history.py, performance.py, eclectic.py (31 sites) now `logger.exception(...)`
before returning/rendering the existing user-facing message; each file gained
`import logging` + a module `logger` where missing. `deps.cached_winners()` and
`deps.cached_streaks_data()` added (both `lru_cache(maxsize=1)`, both wired into
`clear_all_data_caches()`); `history.py` (`_honours_tab_context`), `latest.py`
(4 streak-tab sites), `scoring.py` (`_streak_detail_context`) and `player.py` all
point at them. `player.py`'s private `_get_winners_data` lru_cache and its
`register_cache_clearer` registration are deleted entirely -- `deps.cached_winners()`
replaces it at all 4 call sites. `player.py`'s `_build_records_context` streaks
section now reads `deps.cached_streaks_data()` instead of calling
`build_streaks(all_data)` fresh (same underlying data -- `data/streaks.parquet` is
exactly `build_streaks(all_data)`'s output, kept in sync by the pipeline).
`_metric_specs(all_data, rd_data, winners)` is now computed once in
`_build_overview_context` and passed into both `_build_overview_metrics` and
`_build_trophy_section` (both signatures changed to accept it) instead of each
recomputing it independently. The unused `theme: str` parameter is dropped from
`_build_overview_context` and `_build_scoring_context` (and their 3 call sites in
`player_page`/`player_tab`) -- confirmed unused in both bodies before removing.
`webapp/deps.py` gained `parse_teg_label(label)` (handles `"TEG 18"` and bare `18`)
and a named `FALLBACK_TEG_NUM = 18` constant, replacing the ad-hoc parses at
`latest.py` (`latest_round_page`) and `scoring.py` (`_streak_detail_context`'s sort
key) and the bare `18` fallback in `get_default_teg_num`.

Files touched (for the Opus review gate): `webapp/tables.py` (new),
`webapp/deps.py`, `webapp/routes/scoring.py`, `webapp/routes/latest.py`,
`webapp/routes/history.py`, `webapp/routes/performance.py`,
`webapp/routes/eclectic.py`, `webapp/routes/scorecards.py`,
`webapp/routes/player.py`, `tests/test_deps_cache.py` (updated -- the old test
asserted `player._get_winners_data` existed, which this chat retired; replaced with
an equivalent check that `clear_all_data_caches()` invalidates `deps.cached_winners()`),
`webapp/README.md` (file-structure listing). Full suite green (256 passed, 4
skipped); `check_pandas_compat.py` 0 errors, 21 warnings (same baseline, all
pre-existing/verified-safe); manually smoke-tested every touched page via
`TestClient` (200s, no error banners) plus a direct escaping test on `df_to_html`
with `<script>`/`&` payloads. `streamlit/` untouched.

*Why together*: these interlock (the same route files are touched by W3/W4/W5/W7);
doing them in one chat avoids repeated conflicts across sessions.

**Starter prompt:**
```text
Read REVIEW_PLAN.md (findings W3, W4, W5, W6, W7, W9 / Chat 5) for full context. One
batch because these all touch the same webapp route files.

1. W3: _df_to_html is copy-pasted 7x (scoring.py:49, latest.py:65, history.py:95,
   performance.py:25, eclectic.py:30, scorecards.py:20, and player.py's
   _build_simple_table_html which is the only one that escapes). Create one shared
   helper (new webapp/tables.py) that escapes every cell via markupsafe and supports the
   variants the copies need (table class, first-col alignment, per-cell classes, player
   links). Delete the copies. Where a caller deliberately passes pre-built HTML
   fragments, give the helper an explicit raw/markup opt-in rather than dropping
   escaping silently.
2. W4: every `except Exception as e: return {"error": str(e)}` context builder in
   scoring.py, latest.py, history.py, performance.py, eclectic.py gets a
   logger.exception(...) before returning (keep the user-facing message).
3. W5+W7: add deps.cached_winners() and deps.cached_streaks_data() (lru_cache, cleared
   by clear_all_data_caches). Point /honours (history.py:307), /latest-* streak/record
   tabs (latest.py:378,428,587,602) and /scoring/streaks (scoring.py:158) at them.
   Retire player.py's private _get_winners_data lru cache in favour of the deps one.
4. W6: in webapp/routes/player.py — compute _metric_specs once per request and share it
   between _build_overview_metrics and _build_trophy_section; replace the
   build_streaks(all_data) call at ~line 1049 with the cached streaks data; delete the
   unused `theme` parameters.
5. W9: one helper for parsing "TEG N" labels (replaces the ad-hoc parses at
   latest.py:449 and scoring.py:164); name the hardcoded fallback TEG 18 in
   deps.get_default_teg_num as a constant.

Behaviour must be unchanged page-for-page (only new escaping of genuinely dangerous
characters). pytest green. Tick the Chat 5 boxes in REVIEW_PLAN.md, commit, and hand to
the Opus review gate — this is the biggest diff of the plan, so list the files touched
for the reviewer.
```

### Chat 6 — `aggregate_data` fixed schema *(Opus)*
- [x] **T5**: Replace `list_fields_by_aggregation_level` dynamic discovery with a fixed
      level→columns map; make grouping/sort order deterministic. **Output must be
      column-for-column identical** — snapshot current outputs for each accessor first
      and diff after. Files: `teg_analysis/analysis/aggregation.py` + caller audit.
- [x] Review checklist before committing.

*Why alone*: every page sits downstream of this function; regression surface is the
whole site.

*Outcome*: `aggregate_data` now uses the fixed `_AGGREGATION_LEVEL_FIELDS` map (no
`groupby().nunique()` per call). Data output is byte-identical for all accessors
(snapshot-diffed). Column/row order was previously nondeterministic (`list(set(...))`
wobbled run-to-run); it is now a deterministic documented order. Audited the only two
internal callers (`webapp/routes/scoring.py` `/scoring/by-teg`,
`teg_analysis/display/html_tables.py`) — both select columns by name via `pivot_table`,
neither depends on position or row order. `list_fields_by_aggregation_level` retained
for ad-hoc use. New test: `tests/test_aggregation.py`.

**Starter prompt:**
```text
Read REVIEW_PLAN.md (finding T5 / Chat 6) for full context. aggregate_data in
teg_analysis/analysis/aggregation.py calls list_fields_by_aggregation_level on every
invocation — a groupby().nunique() over every column at up to 4 levels — to rediscover
a schema that is fixed in practice, and `list(set(group_columns))` (line 126) makes
column and sort order nondeterministic.

1. FIRST, snapshot current outputs: call get_complete_teg_data, get_round_data,
   get_9_data, get_Pl_data and aggregate_data(all_data, 'TEG', measures=['GrossVP'])
   against the repo's real data/ files and save the frames (columns, dtypes, sorted
   values) to the scratchpad.
2. Replace the dynamic discovery with an explicit level -> group-columns map that
   reproduces exactly what discovery finds today (derive it from the snapshot). Keep
   list_fields_by_aggregation_level available if anything else imports it, but
   aggregate_data must not call it per-invocation. Preserve a deterministic, documented
   column order (no set()).
3. Handle additional_group_fields and the missing-columns ValueError exactly as before.
4. AFTER, regenerate the same outputs and diff against the snapshots —
   they must be identical (column order may only change if you deliberately fix the
   set() nondeterminism; if so, say so and check no caller depends on position, e.g.
   iloc users in webapp routes and display formatters).
5. Add a unit test pinning the group columns per level on a small fixture.

pytest green + snapshot diff clean before committing. Tick the Chat 6 box in
REVIEW_PLAN.md.
```

### Chat 7 — Owner-decision items + docs *(Haiku — after answers)* ⚠️
- [x] **W8**: Delete or admin-gate the prototype routers per decision.
- [x] **T6**: Align the Stableford gate to `get_net_competition_measure` **or** name the
      constant with a comment explaining TEG 6, per decision.
- [x] **T11**: Resolve the CLAUDE.md ↔ `DATA_STORAGE_INGESTION_PLAN.md` contradiction
      per decision; consolidate `reporting/reporting-to-do.md` into `reporting/STATUS.md`.
- [ ] Review gate (Opus).

**Starter prompt** (fill in the `<<answers>>` from the owner-decisions section first):
```text
Read REVIEW_PLAN.md (findings W8, T6, T11 / Chat 7) for full context. Jon has decided:
- Prototype routes (charts_proto, width_test, title_preview, showcase, smoke_test,
  placeholder): delete all of these
- Stableford >= 6 gate in aggregation.py comeback functions: bug — align to get_net_competition_measure (TEG 8+)
- DATA_STORAGE_INGESTION_PLAN.md: keep — fix the CLAUDE.md sentence saying it was
  deleted

Apply exactly those decisions:
1. W8: update webapp/app.py imports/includes and delete or gate the route files per the
   decision (admin-gating = is_authed redirect like admin.py). Update webapp/README.md
   if it mentions any removed page.
2. T6: implement the Stableford-gate decision at aggregation.py:433,500,605,740 (one
   named constant, four uses).
3. T11: implement the docs decision, and consolidate
   teg_analysis/reporting/reporting-to-do.md into reporting/STATUS.md (STATUS.md is the
   single to-do list for that area — update the TODOS.md link too).

Docs rule: no content duplicated in two files; update the folder guide in README.md if
any file is added/removed. pytest green. Tick the Chat 7 boxes in REVIEW_PLAN.md,
commit, then hand to the Opus review gate.
```

### Chat 8 — Test back-fill *(Sonnet)*
- [x] **W10**: Webapp smoke tests — TestClient GET for every `NAV_SECTIONS` page,
      `/player/{code}` all tabs, `/latest-round` + `/latest-teg` all tabs; assert 200
      and no `"error"` key in rendered context. Files: `tests/test_webapp_pages.py`.
- [x] **T10**: Seed tests for untested recent features — pure-stage reporting units
      (event scoring, markdown render, lint parsing; no API key needed) and the four
      comeback/collapse functions on a small fixture. Files:
      `tests/test_reporting_core.py`, `tests/test_comebacks.py`.
- [ ] Review gate (Opus).

**Chat 8 landed:** three new test files, 82 new tests, all green (`pytest tests/` now
349 passed, 4 skipped, ~120s — no measurable runtime increase over the 267-test
baseline). `tests/test_comebacks.py` hand-builds a 2-player/1-TEG fixture (a blown
15-shot/12-point lead after R3, a comeback win in R4) and pins exact output rows for
`calculate_final_round_differentials`, `calculate_biggest_leads_lost_after_r3`,
`calculate_biggest_leads_lost_in_r4`, `calculate_biggest_comebacks`, for both GrossVP
and Stableford. `tests/test_reporting_core.py` covers only the pure/LLM-free stages of
`teg_analysis/reporting`: the small helpers in `events.py` (`result_label`,
`hole_evidence`, `_ord`, `_proper`, `_maximal_runs`), the axis-weighting/ranking in
`scoring.py` (`cap`, `total_score`, `finalise` across modes), `render_events_markdown`,
and the CSS-class/markdown transforms in `render.py` (`_add_report_title_class`,
`_add_round_classes`, `_build_at_a_glance` incl. win-count ordinal suffixes,
`apply_styling` idempotency, both `_inject_standings` branches, `_dedup_entries`) — all
built from minimal in-memory inputs, nothing from `llm.py` imported or exercised.
`tests/test_webapp_pages.py` GETs every `NAV_SECTIONS` page plus `/player`,
`/player/{code}` and its 4 tab partials (using real code `DM`), `/latest-round` +
`/latest-teg` and their tab partials, and `/results` + `/honours` plus one tab each,
all against the repo's real `data/` files (no auth needed — only `/admin/*` is
gated). The "error-context marker" checked for is the shared idiom every context
builder's `except Exception` path renders: `>Error: ` (the `{% if error %}Error:
{{ error }}` block used by ~20 partials) or the `error-box` class (used by a handful
of chart/table partials) — both checked, neither found on any page.

No product bugs found while writing these (in scope: tests only, no fixes).

**Environment note for future sessions in this container:** this remote environment
ships without `pandas`/`pytest` pre-installed for the interpreter `python3` resolves
to (`/usr/local/bin/python` -> system Python 3.11); `pip install -r requirements.txt`
alone lands in a different site-packages than the pre-installed `pytest` binary
(`/root/.local/bin/pytest`, a `uv tool` isolated venv). Fix: `pip install -r
requirements.txt` then `pip install pytest` (or just always invoke `python -m pytest`,
which fixed both) before running the suite.

*Why last among code chats*: tests should lock in post-fix behaviour, not pre-fix.

**Starter prompt:**
```text
Read REVIEW_PLAN.md (findings W10, T10 / Chat 8) for full context. Back-fill tests for
the areas the review found uncovered. Tests only — if you find a product bug while
writing them, report it, don't fix it in this batch.

1. W10 — webapp smoke tests (new tests/test_webapp_pages.py), using
   fastapi.testclient.TestClient against the repo's real data/ files (pattern:
   tests/test_admin_routes.py):
   - GET every page URL in webapp/nav.py NAV_SECTIONS -> assert 200 and that the body
     does not contain the error-context marker the templates render.
   - GET /player and /player/{code} for one real code, plus all four
     /player/{code}/tab/{tab} partials.
   - GET /latest-round and /latest-teg pages plus each tab partial with default params.
   - GET /results and /honours plus one tab each.
2. T10 — teg_analysis units:
   - tests/test_comebacks.py: the four functions in analysis/aggregation.py
     (calculate_final_round_differentials, calculate_biggest_leads_lost_after_r3,
     calculate_biggest_leads_lost_in_r4, calculate_biggest_comebacks) on a small
     hand-built fixture with a known blown lead and a known comeback; assert the ranked
     rows for both GrossVP and Stableford.
   - tests/test_reporting_core.py: pure stages of teg_analysis/reporting only — no
     ANTHROPIC_API_KEY, no network, mock nothing that would call llm.py. Cover at least
     event/beat scoring in events.py and the markdown/CSS-class rendering in render.py
     on minimal inputs.
3. Keep total runtime reasonable (<~1 min added); session-scope any expensive fixture.

pytest green. Tick the Chat 8 boxes in REVIEW_PLAN.md, commit, then the Opus review
gate.
```

### Chat 9 — Final review pass *(Opus)*
- [ ] Re-read every file changed across Chats 1–8; grep old names for orphaned callers.
- [ ] `pytest tests/ -v` (the T3 fix means the streamlit-import guard now actually
      guards) and `python scripts/check_pandas_compat.py`.
- [ ] Confirm `streamlit/` untouched across the whole effort.
- [ ] Fold anything of lasting value from this file into the relevant READMEs /
      CLAUDE.md "Current state", then **delete `REVIEW_PLAN.md`**.

**Starter prompt:**
```text
Read REVIEW_PLAN.md end-to-end — this is Chat 9, the closing Opus review pass for the
whole remediation effort (Chats 1-8 should all be ticked; stop and say so if any
aren't).

1. List every file changed since the review baseline (git diff --stat against the
   commit that added REVIEW_PLAN.md) and read each changed file end-to-end.
2. Grep for the names retired during the effort (per-route _df_to_html,
   _build_simple_table_html, _get_winners_data, _get_deps, the duplicated
   process_round_for_all_scores body, list_fields_by_aggregation_level call sites) —
   no orphaned callers, no dead leftovers.
3. Confirm nothing under streamlit/ changed at any point.
4. Run pytest tests/ -v (the streamlit-import guard is now a real assert) and
   python scripts/check_pandas_compat.py — both must be clean (env-only altair failure
   excepted).
5. Spot-check the app: run uvicorn webapp.app:app, load a few pages including a player
   profile and the live-round entry page.
6. Update CLAUDE.md "Current state & next steps" with a short summary of the
   remediation; remove the REVIEW_PLAN.md pointer from TODOS.md; fold anything of
   lasting value from REVIEW_PLAN.md into the relevant README, then delete
   REVIEW_PLAN.md (docs Rule 3 — temporary working doc).
7. Fix directly anything small you find; flag anything structural back instead of
   improvising. Commit.
```

---

## Explicitly deferred (no action planned)

- **T9** `commentary.py:797-799` — verified safe, numeric-only use.
- Per-poll CSV reads in live_round (**T8** beyond the lock scope) — fine at this group
  size; revisit only if polling scales.
- Streamlit findings surfaced by the compat checker — `streamlit/` is frozen legacy.
