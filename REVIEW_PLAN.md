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
2. Paste the chat's **scope block** below as the kickoff prompt.
3. On completion, tick the checkboxes here, update the "Current state" section of
   CLAUDE.md if the change is architectural, and run the **review gate** (below).
4. Chats marked ⚠️ **owner decision** need an answer from Jon before starting.

**Review gate (end of every Sonnet/Haiku chat, and Chat 8 in full):** on Opus —
re-read every changed file end-to-end; grep for old function names to catch orphaned
callers; confirm nothing under `streamlit/` changed; run `pytest tests/ -v` and
`python scripts/check_pandas_compat.py`; then commit.

---

## Owner decisions needed (blocking Chat 7)

- [ ] **Prototype routes**: `charts_proto`, `width_test`, `title_preview`, `showcase`,
      `smoke_test`, `placeholder` are publicly served on the production site
      (`webapp/app.py:59-74`). Delete, or gate behind admin auth? Which are still used?
- [ ] **Stableford era gate**: comeback/collapse analysis filters Stableford to
      `TEGNum >= 6` (`teg_analysis/analysis/aggregation.py:433,500,605,740`) but the
      domain rule (`get_net_competition_measure`) says Stableford from TEG 8.
      Is 6 intentional (Stableford *recorded* from TEG 6) or a bug?
- [ ] **Docs contradiction**: CLAUDE.md says the live-round planning doc was deleted,
      but `DATA_STORAGE_INGESTION_PLAN.md` exists and is referenced from
      `webapp/routes/admin_live_round.py:5` and `teg_analysis/analysis/live_round.py`.
      TODOS.md says it's "kept as a historical/reference record", so the likely fix is
      correcting CLAUDE.md — confirm, or delete-and-fold instead?

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

---

## Execution plan — batched into chats

Each chat = one session, one coherent scope, sized to stay reviewable. Order matters.

### Chat 1 — Make the suite green and the guards real *(Sonnet)*
- [ ] **T1**: Seed `handicaps.csv` in the live-round test fixtures; add a test asserting
      the unconfirmed-roster refusal path. Files: `tests/test_live_round.py`.
- [ ] **T3**: Convert `test_no_streamlit_imports` to `assert not imports, ...`
      (keep script mode working). Files: `tests/test_no_streamlit_imports.py`.
- [ ] Review gate (Opus).

*Why together*: both are test-infrastructure fixes; tiny; everything else depends on a
trustworthy green suite.

### Chat 2 — Live-round server-side validation *(Sonnet)*
- [ ] **W1**: Add `MAX_SCORE = 20` (+ hole 1–18, player-in-roster checks) inside
      `apply_score_writes` and `apply_admin_edits`; make the admin route and the entry
      template consume the same constant (template gets it via context). Reject invalid
      cells with a clear error rather than dropping them silently. Tests for each
      rejection. Files: `teg_analysis/analysis/live_round.py`,
      `webapp/routes/live_round.py`, `webapp/routes/admin_live_round.py`,
      `webapp/templates/live_round_entry.html`, `tests/test_live_round*.py`.
- [ ] Review gate (Opus).

*Why alone*: highest user-facing data-integrity risk; touches the API contract, so keep
the diff focused and well-tested.

### Chat 3 — Data-pipeline hygiene: no silent failures *(Opus)*
- [ ] **T2**: Make the `update_*_cache` functions raise (or return typed error markers);
      `execute_data_update`/`execute_data_deletion` collect failures into a
      `cache_errors` field in the result; admin result templates render a warning banner
      when present. Files: `teg_analysis/analysis/pipeline.py`,
      `teg_analysis/analysis/data_update.py`,
      `webapp/templates/partials/admin_update_result.html`,
      `webapp/templates/partials/admin_live_round_finalize_result.html`, tests.
- [ ] **T7**: Replace `_get_deps()`/`locals()` with plain deferred imports; load
      `all_data` once in the orchestrators and pass it into the `update_*` functions.
- [ ] **T4**: De-duplicate `process_round_for_all_scores` — keep the data_update
      version, re-export from `core.data_loader`/`core.__init__`, delete the mutating
      copy (grep all callers incl. tests first).
- [ ] Review gate = the chat itself is Opus; still run the checklist before committing.

*Why together*: all three live in `pipeline.py`/`data_update.py`/`core`; one coherent
"the update pipeline fails loudly and has one copy of the math" change.

### Chat 4 — Event-loop blocking *(Opus)*
- [ ] **W2**: Convert route handlers to sync `def` (FastAPI threadpools them) or wrap
      heavy calls in `run_in_threadpool`; verify HTMX behaviour unchanged.
- [ ] **T8 (partial)**: Move the GitHub commit in `finalize_live_round` outside
      `live_round._lock` (staging is already read and status not yet flipped — design the
      ordering carefully).
- [ ] Manual concurrency check: poll `/api/live-round/{token}/scores` while a finalize
      runs; pages must stay responsive.
- [ ] Review checklist before committing.

*Why alone*: cross-cutting concurrency change; needs Opus-level care and its own
verification pass.

### Chat 5 — webapp dedup + caching batch *(Sonnet)*
- [ ] **W3**: One shared escaping `df_to_html` (new `webapp/tables.py`); delete the 7
      copies; keep per-page class hooks via parameters.
- [ ] **W4**: `logger.exception(...)` in every `except Exception` context builder
      (keep the user-facing message).
- [ ] **W5 + W7**: Add `deps.cached_winners()` and `deps.cached_streaks_data()`
      (registered with `clear_all_data_caches`); point `/honours`, `/player`,
      `/latest-*`, `/scoring/streaks` at them; retire player.py's private winners cache.
- [ ] **W6**: Player-profile cleanup — compute `_metric_specs` once per request, use the
      cached streaks instead of `build_streaks`, drop unused `theme` params.
- [ ] **W9**: Small tidies — one TEG-label parse helper; named constant for the
      fallback TEG.
- [ ] Review gate (Opus).

*Why together*: these interlock (the same route files are touched by W3/W4/W5/W7);
doing them in one chat avoids repeated conflicts across sessions.

### Chat 6 — `aggregate_data` fixed schema *(Opus)*
- [ ] **T5**: Replace `list_fields_by_aggregation_level` dynamic discovery with a fixed
      level→columns map; make grouping/sort order deterministic. **Output must be
      column-for-column identical** — snapshot current outputs for each accessor first
      and diff after. Files: `teg_analysis/analysis/aggregation.py` + caller audit.
- [ ] Review checklist before committing.

*Why alone*: every page sits downstream of this function; regression surface is the
whole site.

### Chat 7 — Owner-decision items + docs *(Haiku — after answers)* ⚠️
- [ ] **W8**: Delete or admin-gate the prototype routers per decision.
- [ ] **T6**: Align the Stableford gate to `get_net_competition_measure` **or** name the
      constant with a comment explaining TEG 6, per decision.
- [ ] **T11**: Resolve the CLAUDE.md ↔ `DATA_STORAGE_INGESTION_PLAN.md` contradiction
      per decision; consolidate `reporting/reporting-to-do.md` into `reporting/STATUS.md`.
- [ ] Review gate (Opus).

### Chat 8 — Test back-fill *(Sonnet)*
- [ ] **W10**: Webapp smoke tests — TestClient GET for every `NAV_SECTIONS` page,
      `/player/{code}` all tabs, `/latest-round` + `/latest-teg` all tabs; assert 200
      and no `"error"` key in rendered context. Files: `tests/test_webapp_pages.py`.
- [ ] **T10**: Seed tests for untested recent features — pure-stage reporting units
      (event scoring, markdown render, lint parsing; no API key needed) and the four
      comeback/collapse functions on a small fixture. Files:
      `tests/test_reporting_core.py`, `tests/test_comebacks.py`.
- [ ] Review gate (Opus).

*Why last among code chats*: tests should lock in post-fix behaviour, not pre-fix.

### Chat 9 — Final review pass *(Opus)*
- [ ] Re-read every file changed across Chats 1–8; grep old names for orphaned callers.
- [ ] `pytest tests/ -v` (the T3 fix means the streamlit-import guard now actually
      guards) and `python scripts/check_pandas_compat.py`.
- [ ] Confirm `streamlit/` untouched across the whole effort.
- [ ] Fold anything of lasting value from this file into the relevant READMEs /
      CLAUDE.md "Current state", then **delete `REVIEW_PLAN.md`**.

---

## Explicitly deferred (no action planned)

- **T9** `commentary.py:797-799` — verified safe, numeric-only use.
- Per-poll CSV reads in live_round (**T8** beyond the lock scope) — fine at this group
  size; revisit only if polling scales.
- Streamlit findings surfaced by the compat checker — `streamlit/` is frozen legacy.
