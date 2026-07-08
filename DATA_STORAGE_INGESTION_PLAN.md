# Data storage & score ingestion — architecture review and implementation plan

**COMPLETE — kept as a historical/reference record, not deleted.** Every phase (0 through
4.1) shipped; 4.2 is an intentionally-open, human-gated decision (see bottom). This file was
originally a temporary working document per CLAUDE.md's documentation rules, and its outcome
*is* folded into `CLAUDE.md`, `DATA_FLOW.md`, and `webapp/README.md` — but a genuine amount of
narrative and rationale here (Fable's architecture + design reviews, the phase-by-phase design
decisions, the specific bugs found and why) isn't fully duplicated there, and a number of
permanent docs and code comments now correctly point back to specific sections of this file.
Deleting it would trade real information loss + broken cross-references for a marginal tidiness
gain, so it stays — **consolidated in place** rather than deleted, which CLAUDE.md's own rule
on temporary working documents explicitly allows ("must be deleted *or consolidated*").

**Status (2026-07-07): Phase 0 complete (see [findings](#phase-0-findings)). Phase 1
complete** (1.1-1.5 all done: backups on add, `backup_file()` volume-copy fix, concurrency
lock, CSV mirrors retired, docs swept, `DATA_RATIONALISATION_PLAN.md` deleted). **Phase 2
complete, revised** (`course_pars.csv` now defaults every course to its most-recently-played
round, not majority vote — all 26 courses populated). **Phase 2.5 complete** (new: pre-round
setup — `round_pars.csv` + the `/admin/round-setup` page — so Par/SI is confirmed by an
admin before a round is played, never by whoever's entering scores). **[Decisions needed for
Jon](#decisions-needed-for-jon) — both resolved, nothing outstanding.** **Phase 3.1 + 3.2 +
3.2b complete** (four interactive mockups at `/mockups/` — grid/wizard/player-column/flow —
with par-relative keypads and voice entry layered on). **Phase 3.3 complete:** Pattern A
(`round_entry_grid.html`) chosen as the final design, refined with a fixed 2–8 keypad, bigger
buttons, and an all-players/single-player view toggle — see "Phase 3.3 decision" below.
Second refinement pass added a keypad-mode toggle, a player-group chip picker, and a cross-tab
sync demo; Fable's design/performance review found and fixed one real bug (players hiding their
own chip) plus smaller issues — see that section. Jon's call: ship the mockup's current design
as-is (both keypad modes, voice entry, everything) — no further mockup changes pending.
**Phase 3.4 complete:** the real, data-writing round-entry page + live multi-device sync
backend are built, tested (unit + a real end-to-end test that drives actual HTTP requests
through two simulated devices, including a genuine conflict and finalize into
`all-scores.parquet`), and manually verified against a running server — see "Phase 3.4 design"
below for the model and "Phase 3.4 built" for what shipped and two real bugs it caught.
**Nothing outstanding — every phase in this plan is done.** Temporary working document (CLAUDE.md
Documentation Rule 3). When Phase 4 is complete, fold the outcome into `DATA_FLOW.md`,
`webapp/README.md`, `teg_analysis/README.md`, and CLAUDE.md's "Current state & next steps",
then delete this file (see the wrap-up note at the very end).

## Decisions needed for Jon

**Both items below are now resolved — nothing outstanding.** Kept as a record so neither
gets re-litigated. (Superseded history: item 1 was originally an open decision about
Estoril; Phase 2.5's methodology change — most-recent-round instead of majority vote —
resolved it as a side effect, and Jon separately said not to investigate further.)

### 1. Estoril Par/SI — RESOLVED by the Phase 2.5 methodology change (not a manual decision)

Only 2 rounds have ever been played at Estoril (TEG 15 Round 1, 2022; TEG 16 Round 4,
2023), and they disagree on Par and/or SI for 15 of 18 holes — e.g. Hole 5: TEG 15 says
Par 3/SI 3, TEG 16 says Par 5/SI 17. With only one round on each side there was no majority
to lean on for the original majority-vote approach.

**Resolved:** `course_pars.csv` now defaults every course to its most recently played round
(Phase 2.5), which naturally covers Estoril — it uses TEG 16 (2023), the more recent of the
two, same as every other course gets its most-recent-round default. Jon: "just leave
Estoril" — not investigating which historical entry was more accurate; if the TEG 16 default
turns out wrong when Estoril is next played, it's a one-round edit on the Round Setup page,
same as any other course.

### 2. Two apparent Par/SI "conflicts" — RESOLVED, not data errors (Jon, 2026-07-07)

While backfilling `course_pars.csv`, majority-vote resolution flagged two rounds that
disagree with every other round ever played at their course on **all 18 holes
simultaneously**: **TEG 2 Round 3** (Boavista, 18/05/2009) and **TEG 7 Round 1** (Praia
D'El Rey, 02/10/2014). Before assuming these were data-entry errors, computed the actual
impact of "correcting" them (recomputing GrossVP/HCStrokes/Net/NetVP/Stableford under the
majority Par/SI and comparing to what's recorded) — see the full breakdown in git history
(commit `e1b6331`) if useful context is ever needed. Headline: gross scores/rankings and
TEG-level trophy/spoon standings are mathematically unaffected either way (net totals are
provably invariant to which Par/SI permutation is used); the only real effect would be on
career eagle counts and the all-time single-round Stableford record for Praia D'El Rey
specifically.

**Then Jon corrected the premise: Praia D'El Rey is genuinely, legitimately sometimes
played back-9-first — this is not a data error.** TEG 7 Round 1's recorded Par/SI is very
likely *correct as entered* for however that round was actually played that day; the
"conflict" is real course variation, not a mistake. Decision, final:

- **`all-scores.parquet` is not touched, for either round.** No correction was or will be
  applied. Current eagle count (4, one each for David M/John P/Jon B/Stuart N) and the
  all-time single-round Stableford record (51, HM, TEG 7 Round 2) stand as-is.
- **Praia D'El Rey is permanently excluded from `course_pars.csv`'s per-hole Par/SI
  backfill** (`scripts/backfill_course_pars.py`'s `KNOWN_VARIABLE_ROUTING`) — there is no
  single canonical Par/SI-by-hole-number for this course, so there's nothing to prefill.
  Future round-entry (Phase 3+) will need manual Par/SI entry for this course; a
  two-routing-variant prefill would be a nice later enhancement but is out of scope now.
- **Boavista's SI difference is not being investigated further** (Jon: "just ignore the
  Boavista SI diffs") — the majority-vote value already in `course_pars.csv` (SI only;
  Par already matched) stands as a reasonable, low-stakes default. Nothing else to do here.

**If this ever resurfaces:** it isn't a bug and doesn't need re-investigating. Praia D'El
Rey's Par/SI genuinely varies by which nine was played first that day — check
`round_info.csv`/course notes for that specific TEG+Round if the routing for a given visit
ever needs to be known, rather than assuming one of the two recorded variants is "wrong."

---

**Supersedes `DATA_RATIONALISATION_PLAN.md`'s open investigation.** That file's Phase 3
options appraisal (Option 3: keep both parquets, drop the CSV mirror) is adopted directly
by Phase 1.4 below, on lighter evidence (this review's own file-size/derivation checks)
rather than its full column-census investigation — justified because that investigation's
main reason for rigour, "streamlit/ must not break," is no longer a constraint (Jon,
2026-07-07: "It's ok to break streamlit now"). `DATA_RATIONALISATION_PLAN.md` should be
deleted once Phase 1.5 lands (see that step).

**Origin:** a full architecture review by Fable (2026-07-07), commissioned to answer two
questions — is a Railway volume the right storage foundation, and is there a better way to
capture/ingest new round scores, in particular from a phone immediately after a round.
Budget ceiling: ~$10/month on top of existing Railway hosting. Streamlit compatibility is
explicitly not a constraint.

---

## Facts verified directly (do not re-derive; trust these)

- **Sizes:** `all-scores.parquet` 37 KB; `all-data.parquet` 541 KB; the `all-data.csv`
  mirror **2.5 MB** (committed to GitHub on every update — dominates commit weight); full
  git pack 16 MB; volume ~4 MB total.
- **`all-data` is fully derived from `all-scores`** — `update_all_data()`
  (`teg_analysis/analysis/pipeline.py:452`) regenerates it wholesale on every add/delete.
- **The add flow takes no backups.** Only `execute_data_deletion` calls
  `create_timestamped_backups()`; `execute_data_update` with `overwrite=True` can replace
  existing hole scores with nothing recoverable on `/admin/backups`.
- **`backup_file()` on Railway backs up the GitHub copy, not the volume copy**
  (`teg_analysis/io/file_operations.py:261-264`) — snapshots last committed state, not
  current state; its "backups branch" comment doesn't match what it actually does (commits
  to the same branch).
- **No concurrency guard** around `execute_data_update`/`execute_data_deletion` — a
  double-tapped phone submit could interleave two full read-modify-write cycles.
- **Hole-level Par/SI exist only in the Google Sheet today.** `course_info.csv` is
  course-level prose only. A native entry form needs a new `course_pars.csv`, backfillable
  from `all-scores` (which carries PAR/SI per hole) joined to `round_info.csv`.
- **`process_google_sheets_data` silently drops any player-round with ≠18 holes** — capture
  (in-progress) and ingestion (complete round) must be separate states.
- **`update_commentary_caches` is deterministic pandas, not an LLM call** — full derived-cache
  regen on add/delete is cheap compute, safe to trigger synchronously from a phone (pending
  Phase 0.1's actual timing).

---

## Question 1: Is the Railway volume + GitHub the right storage foundation?

**Recommendation: keep it.** Do not migrate to a database. Harden the write path instead. Cost: $0/month.

At this scale (~37 KB of canonical data, growing ~4 KB/year, single writer, ~30 writes/year)
storage technology barely matters — what matters is integrity, recoverability, and the local-Mac
story. GitHub-as-system-of-record already gives an atomic-commit audit trail, off-host
durability, and the Mac workflow (`git pull`) as side effects of the existing design. The
volume is correctly positioned as a self-healing cache, not a source of truth. A database
migration would have to rebuild all three properties this design gets for free, while
rewriting ~1,400 lines of working `teg_analysis/io` + admin tooling.

**Considered and rejected:** managed Postgres (loses the versioned/diffable/self-healing
properties, requires rewriting the io layer and the notebook workflow, worse backup story
on a $5 tier than "every state is a git commit"); SQLite on the volume (solves no current
problem, binary diffs are useless); object storage (versionless by default, new credential,
duplicates what GitHub already gives free); GitHub-only/no volume (every cold read becomes
an API call); a separate data-only repo (16 MB repo doesn't justify the churn yet — dropping
the CSV mirror removes ~75% of per-update commit weight anyway).

**Harden instead** — see Phase 1: backups on add, fix `backup_file()`, add a concurrency
lock, drop the dead CSV mirror.

## Question 2: Score capture and ingestion

**Recommendation:** build a mobile-first round-entry page in the webapp, backed by
server-side drafts, that produces the *same wide-format frame* the Google Sheet does — so
`process_google_sheets_data`, duplicate-checking, the preview/confirm step, and
`execute_data_update` are all reused untouched. Google Sheets becomes a one-season fallback,
then gets removed if unused. Ingestion stays an explicit confirm tap (the preview step is a
real integrity gate, not friction to remove) but happens on the same screen as entry, not a
separate admin flow.

The Sheet is the actual friction — typing into a spreadsheet grid on a phone — not the
ingestion trigger (already ~3 taps behind a 30-day cookie). Automating ingestion further
(webhooks/polling on the sheet) would fix the easy half and leave the hard half. **This is
also where Jon wants prototyping**: before locking in one interaction pattern, build 2-3
throwaway mobile mockups and try them on a real phone (Phase 3, steps 3.1-3.3).

**Considered and rejected:** sheet + webhook auto-ingest (fixes the wrong half); a Google
Form (still Google-shaped, no duplicate preview, no offline story); multi-user live scoring
with per-player logins (different product; single-admin entry matches the actual
requirement); a native/PWA offline-first app (overkill — `localStorage` + server drafts
covers the realistic failure modes, e.g. phone dies mid-round).

---

# Phased implementation plan

Ordering rule: Phase 1 (backups on add) ships before Phase 3's implementation steps — the
new entry flow raises the chance of a fat-fingered overwrite and must inherit the safety
net first. Phase 3.1-3.3 (prototyping) has no such dependency and can run any time after
Phase 0.

Each phase below ends with a **kick-off prompt** — copy it as-is to start a fresh session/agent
on that step. Prompts are self-contained: they point at this file for full context rather than
repeating it, so keep this file intact until the final wrap-up.

## Phase 0 findings

Run 2026-07-07, all read-only / against a scratch copy of `data/` (real repo `data/` was
never touched — verified by monkeypatching `teg_analysis.io.volume_operations._REPO_ROOT`
to a throwaway directory rather than running in place).

### 0.1 — Full pipeline timing: **16.5s median — over the ~15s synchronous threshold**

A full `execute_data_update` dry run (synthetic 18-hole round, 7 players, TEG 50 sandbox),
median of 5 runs: **16.52s** (range 16.23s–17.14s). Breakdown by sub-step:

| Step | Time | Share |
|---|---|---|
| `update_commentary_caches` | 9.61s | 59% |
| `update_bestball_cache` | 5.00s | 30% |
| `update_all_data` | 1.34s | 8% |
| everything else (read/write all-scores, duplicate check, handicap merge, status, streaks) | <0.15s combined | ~1% |

**Root cause:** both `update_commentary_caches` and `update_bestball_cache`
(`teg_analysis/analysis/pipeline.py`) call `load_all_data(exclude_teg_50=True,
exclude_incomplete_tegs=False)` and recompute their outputs **from the entire historical
dataset** on every single add/delete — not incrementally from the changed round. Cost is
O(full history), currently ~17 TEGs, and will keep growing every year.

**Caveat:** this ran in the dev sandbox container, whose CPU may not match Railway's
production container — treat the absolute number as indicative, not exact. The *relative*
breakdown (commentary + bestball dominate, everything else is noise) is the reliable part
and doesn't depend on hardware.

**Verdict for Phase 3:** this **does not clear** the synchronous-submit assumption. A naive
mobile submit button would hang for ~15-20s (worse on a flaky course/clubhouse connection).
Two paths, both worth putting to Opus at Phase 3.4 rather than deciding here:
1. **Background-task pattern** — submit returns immediately, UI polls/HTMX-polls for
   completion, as the original plan anticipated for this scenario.
2. **Make the two caches incremental** — a more invasive change to
   `update_commentary_caches`/`update_bestball_cache` (recompute only affected
   TEG/rounds, not full history), which would likely bring the whole pipeline back under
   ~2s and remove the need for a background-task UX at all. Not scoped or estimated here;
   flag as an option for Phase 3.4 to weigh, since it's a bigger change than a UI pattern
   swap but fixes the actual growth problem (today's ~15s only gets worse every TEG).

### 0.2 — Par/SI consistency: 23/26 courses clean, 3 need manual resolution

See full breakdown above (Boavista: SI re-rated at some point, PAR stable; Estoril: mixed
PAR+SI conflicts on most holes; Praia D'El Rey: front/back 9 conflict pattern mirrors
exactly, suggesting a routing swap between visits, not noise). **Verdict for Phase 2:** the
backfill script must surface these three for manual resolution as designed — do not
auto-resolve. No course has fewer than 18 holes represented; no orphaned rows.

**Update from Phase 2's deeper TEG+Round breakdown:** Boavista's "conflict" was a *single
outlier round* disagreeing with every other round on all 18 holes — resolved by majority
vote (see Phase 2 below). **Praia D'El Rey's original hypothesis above was right** — Jon
confirmed the course is genuinely sometimes played back-9-first; it's excluded from
`course_pars.csv` entirely rather than "resolved," since there's no single correct
per-hole Par/SI to backfill. Only Estoril is a true, unresolvable tie. See
[Decisions needed for Jon](#decisions-needed-for-jon).

### 0.3 — CSV mirror readers: clear outside Streamlit

`data/all-data.csv` is actively **written** by `teg_analysis/analysis/data_update.py` and by
Streamlit's parallel pipeline, but **read by nothing** (webapp, scripts, ad_hoc_analysis,
tests all clean). `data/all-scores.csv` is fully dead — no live code reads or writes it;
the only references are stale docstring/log text in `teg_analysis/core/data_transforms.py`
and `streamlit/utils.py`, whose one real caller (`streamlit/1000Data update.py`) actually
passes the **parquet** paths, not the CSV. **Verdict for Phase 1.4:** clear to proceed —
nothing outside Streamlit reads either mirror file.

**Minor aside (not a Phase 0 deliverable, noted for later):** `check_for_complete_and_duplicate_data`
exists as two different functions with different signatures in
`teg_analysis/core/data_transforms.py` (path-based, Streamlit-oriented) and
`teg_analysis/io/file_operations.py` (DataFrame-based) — a naming collision worth a
cleanup pass sometime, unrelated to this plan.

---

## Phase 0 — Verification spikes (no production changes)

| # | Step | Model | Why this tier |
|---|------|-------|----------------|
| 0.1 | Time a full local `execute_data_update` dry run against a **scratch copy** of `data/`. Confirm end-to-end regen (streaks + commentary + bestball + status) is seconds, not minutes — decides whether the Phase 3 phone submit can be synchronous. If >~15s, flag for Opus at 3.4 — a background-task pattern would be needed. | Sonnet | Throwaway script + measurement; no design judgement unless the number is bad. |
| 0.2 | Par/SI history census: script joining `all-scores.parquet` to `round_info.csv`, reporting per course whether hole-level Par/SI are self-consistent across all plays. Output: clean vs. conflicted courses, with the conflicting values listed. | Sonnet | Data-quality scripting against a clear spec. |
| 0.3 | Reader census for `data/all-data.csv` and `data/all-scores.csv`: grep `teg_analysis/`, `webapp/`, `scripts/`, `ad_hoc_analysis/` (and separately note, without acting on, any `streamlit/` hits) for both filenames and `ALL_DATA_CSV_MIRROR`. | Haiku | Mechanical grep + tabulation. |
| 0.4 | **Manual (Jon):** confirm on Railway whether the volume persists across deploys as assumed and whether the plan tier includes volume snapshots (likely not — fine, GitHub is the durable copy, but should be a known fact); confirm `RAILWAY_GIT_BRANCH` is set (`github_operations._get_github_branch()` assumes it); sanity-check the GitHub token is a fine-grained PAT with an expiry reminder somewhere. | — | Ops facts, not code. |

> **Kick-off prompt — Phase 0 (Sonnet + Haiku, steps 0.1-0.3):**
> "Read `DATA_STORAGE_INGESTION_PLAN.md` in full for context, then run Phase 0's three
> verification spikes read-only, no production changes: (0.1) copy `data/` to a scratch
> directory, run a full `execute_data_update` dry run against the copy, and time the whole
> pipeline including cache regeneration (streaks/commentary/bestball/status) over a few
> runs — report the median; (0.2) write a script joining `data/all-scores.parquet` to
> `data/round_info.csv` and report, per course, whether hole-level Par/SI are consistent
> across every historical play, listing any conflicts found; (0.3) grep `teg_analysis/`,
> `webapp/`, `scripts/`, `ad_hoc_analysis/` for references to `all-data.csv`,
> `all-scores.csv`, and `ALL_DATA_CSV_MIRROR`, and separately list (don't act on) any hits
> under `streamlit/`. Do not modify anything in `data/` in place. Report all three findings
> plainly, and call out explicitly whether they clear Phase 1.4 (mirror retirement) and
> Phase 3.4/3.6 (synchronous phone submit) to proceed."

## Phase 1 — Harden the existing foundation (keep volume + GitHub)

| # | Step | Model | Why | Risk / rollback |
|---|------|-------|-----|-------------------|
| 1.1 | Add timestamped backups to the **add** flow: in `execute_data_update` (`teg_analysis/analysis/data_update.py`), call `create_timestamped_backups()` before any write whenever `overwrite=True` or duplicates exist. Return backup paths in the summary dict; surface in `partials/admin_update_result.html`. | Sonnet | Single-file change reusing an existing function. | Additive; no data at risk. Verify: run an overwrite update locally, confirm the backup appears on `/admin/backups` and restores. |
| 1.2 | Fix `backup_file()` (`teg_analysis/io/file_operations.py:251`): on Railway, copy the **volume** file to the backup path, falling back to GitHub only if the volume copy is absent. Fix the stale "backups branch" comment. | Sonnet | Known-bug fix, clear intended behaviour. | Behaviour change in a safety mechanism — add a test asserting the volume copy wins. Rollback: revert the function. |
| 1.3 | Concurrency/double-submit guard: module-level `threading.Lock` in `data_update.py` acquired (non-blocking) by `execute_data_update`/`execute_data_deletion`; raise a clear "update already in progress" error on contention. Disable the submit button on first click in the templates. | Sonnet | Small, well-specified mechanism; routes already have error-render paths. | None; purely protective. |
| 1.4 | Retire the CSV mirrors (gated on 0.3 showing no live modern readers): remove the `ALL_DATA_CSV_MIRROR` write from `update_all_data()` (`pipeline.py:452`) and its call-sites; remove the constant; delete `data/all-data.csv` and `data/all-scores.csv` from the volume (via `/admin/volume` browser, which backs up before delete) and from GitHub. This breaks Streamlit's reader — accepted per brief; note it in the commit message. | Sonnet (code), then Haiku (constant removal + deletion) | Code change touches the core update path → Sonnet with tests; deletion/cleanup is mechanical. | **Data-change step.** Both files are derived/regenerable; volume-delete auto-backs-up; GitHub history retains them regardless. Rollback: restore from backup or `git checkout` the blobs. Verify: local dry-run update; full page sweep; `pytest tests/`. |
| 1.5 | Documentation: update `DATA_FLOW.md` §1-2 (mirror gone, master→derived made explicit — resolves the "Unresolved" note), `teg_analysis/io/file_catalog.py`, CLAUDE.md's "To investigate" entry. Fold the outcome into `DATA_RATIONALISATION_PLAN.md`'s own §6 wrap-up, then **delete `DATA_RATIONALISATION_PLAN.md`** — its open question is now resolved (Option 3) without needing its full column-census investigation. | Haiku | Pure doc maintenance per the repo's own rules. | None. |

> **Kick-off prompt — Phase 1 code (Sonnet, steps 1.1-1.4a):**
> "Read `DATA_STORAGE_INGESTION_PLAN.md` in full, in particular Phase 0's findings if they
> exist yet (check for a Phase 0 findings note; if step 0.3 hasn't run, do a quick grep
> yourself first for `all-data.csv`/`all-scores.csv`/`ALL_DATA_CSV_MIRROR` outside
> `streamlit/` before touching 1.4). Implement Phase 1 steps 1.1-1.4: (1.1) add timestamped
> backups to `execute_data_update` in `teg_analysis/analysis/data_update.py`, matching the
> pattern `execute_data_deletion` already uses, surfaced in
> `partials/admin_update_result.html`; (1.2) fix `backup_file()` in
> `teg_analysis/io/file_operations.py` to snapshot the volume copy on Railway, falling back
> to GitHub only if absent, and correct the misleading comment; (1.3) add a non-blocking
> `threading.Lock` around `execute_data_update`/`execute_data_deletion` with a clear
> in-progress error, and disable the submit button on first click in the relevant
> templates; (1.4, code half) remove the `ALL_DATA_CSV_MIRROR` write from `update_all_data`
> in `teg_analysis/analysis/pipeline.py` and its call-sites. Add/extend tests in
> `tests/test_data_update.py` for each change. Run `pytest tests/ -v` before finishing. Do
> not touch anything under `streamlit/`."

> **Kick-off prompt — Phase 1 cleanup + docs (Haiku, steps 1.4b-1.5):**
> "Phase 1's code changes (1.1-1.4a) are done — read `DATA_STORAGE_INGESTION_PLAN.md` for
> context. Finish step 1.4: remove the now-unused `ALL_DATA_CSV_MIRROR` constant, and
> delete `data/all-data.csv` and `data/all-scores.csv` — locally via git, and in production
> via the `/admin/volume` browser (which backs up before deleting) plus the GitHub copy.
> Then do step 1.5's doc sweep: update `DATA_FLOW.md` §1-2 to remove the CSV mirror and make
> the master→derived relationship explicit; update `teg_analysis/io/file_catalog.py`; remove
> the resolved 'To investigate' entry in `CLAUDE.md` and add a one-line note under
> Architecture recording the decision; fold the outcome into `DATA_RATIONALISATION_PLAN.md`
> §6, then delete that file."

## Phase 2 — Course par data (prerequisite for the entry form)

Depends on Phase 0.2. Schema is finalised alongside Phase 3.4; implementation can start once
0.2's findings exist.

| # | Step | Model | Why |
|---|------|-------|-----|
| 2.1 | Backfill script (`scripts/`): generate `data/course_pars.csv` (`Course, Hole, Par, SI`) from `all-scores` + `round_info`, writing to a scratch dir. Where 0.2 found conflicts, emit both variants and stop for manual resolution. Jon reviews the output; it then enters the store via the existing `/admin/volume-sync` push. | Sonnet | Clearly specified derivation with a human review gate. |
| 2.2 | Register the file: add to `EDITABLE_DATA_FILES` in `data_update.py` (so new courses are maintained on `/admin/edit-data`), `DATA_FILE_CATALOG` in `file_catalog.py`, and a constant in `constants.py`. | Sonnet | Three small, pattern-following registry edits. |
| 2.3 | Docs: `DATA_FLOW.md` storage-layer entry. | Haiku | Mechanical. |

> **Kick-off prompt — Phase 2 (Sonnet):**
> "Read `DATA_STORAGE_INGESTION_PLAN.md` Phase 2 and Phase 0.2's findings (par/SI
> consistency census). Write a backfill script under `scripts/` that generates
> `data/course_pars.csv` (columns: `Course, Hole, Par, SI`) by joining
> `data/all-scores.parquet` to `data/round_info.csv` on TEG/Round to get Course per hole.
> Write output to a scratch directory, not `data/`, for review. Where the 0.2 census found
> a course with inconsistent historical Par/SI, emit all conflicting variants clearly
> labelled rather than picking one, and stop there for manual resolution — do not guess.
> Once Jon has reviewed and approved the output, register the new file: add it to
> `EDITABLE_DATA_FILES` in `teg_analysis/analysis/data_update.py`, add an entry to
> `DATA_FILE_CATALOG` in `teg_analysis/io/file_catalog.py`, and add a path constant in
> `teg_analysis/constants.py`, following the existing patterns for `round_info.csv`/
> `handicaps.csv` exactly. Add a short entry to `DATA_FLOW.md`'s storage layer section."

## Phase 2.5 — Pre-round setup (built, 2026-07-07, added mid-plan by Jon)

Not in the original plan — added when the `course_pars.csv` work made it obvious that
**someone** has to confirm a round's Par/SI before it's played, and it must not be whoever's
entering scores from a phone afterwards (Jon: "Players shouldn't be doing that"). Split the
concept in two:

- **`course_pars.csv`** (Phase 2, revised) — a *course-level default*, backfilled from the
  most recently played round at each course (not majority vote — see the revision below).
- **`round_pars.csv`** (new) — the *confirmed* Par/SI for one specific TEG+Round, set up by
  an admin ahead of play via the new **Round setup** page. Phase 3's round entry (whenever
  it's built) reads Par/SI from here, read-only — a player sees it like it's printed on a
  scorecard, but pre-round setup is the only place it's edited.

**Revised `course_pars.csv` methodology:** switched from majority-vote to **most recently
played round at each course**. Recency beats historical agreement — a course can be
legitimately re-rated over time (this is *why* Boavista's SI differed for one old round),
so "what actually happened most recently" is a better default, and it naturally covers
courses with too little history for a majority (Estoril, resolved as a side effect — no
further action needed, per Jon: "just leave Estoril"). All 26 courses now populated
(`scripts/backfill_course_pars.py`, rewritten). Praia D'El Rey still gets a default (its
most recent round) but is flagged in `constants.KNOWN_VARIABLE_ROUTING` so pre-round setup
prompts a double-check rather than silently trusting it.

**Built:**
- `teg_analysis/analysis/round_setup.py` — `get_rounds_status()` (upcoming rounds needing
  setup — scoped to `round_info.csv` entries with **no scores yet in `all-scores.parquet`**,
  so this doesn't list 18 TEGs of already-played history), `get_round_setup_form()`
  (prefill logic: confirmed `round_pars.csv` → `course_pars.csv` default → blank, with the
  variable-routing flag), `save_round_setup()` (upsert into `round_pars.csv`).
- `webapp/routes/admin_round_setup.py` + `admin_round_setup.html` /
  `admin_round_setup_form.html` / `partials/admin_round_setup_result.html` — the
  `/admin/round-setup` list page and `/admin/round-setup/{teg}/{round}` 18-hole confirm
  form, nav-linked as **Round setup**. Manually verified end-to-end via Playwright
  (screenshots: list empty-state, unflagged form, flagged form) — no page errors, no real
  data touched during testing.
- `round_pars.csv` and `course_pars.csv` both registered in `EDITABLE_DATA_FILES` /
  `DATA_FILE_CATALOG` as usual, so they're also editable via the generic `/admin/edit-data`
  grid as a fallback.
- Tests: `tests/test_round_setup.py` (9 unit tests) + additions to
  `tests/test_admin_routes.py` (7 route tests) — prefill precedence, variable-routing flag,
  the already-played filter, save upsert semantics, incomplete-form rejection.

**Consequence for Phase 3.4+:** the round-entry draft schema no longer needs a "Par/SI
overrides" field — pre-round setup already owns that. Round entry should read Par/SI from
`round_pars.csv` (via `round_setup.get_round_setup_form` or similar) and guard on it existing
(link to `/admin/round-setup/{teg}/{round}` if not), the same way it already guards on
`round_info.csv` existing. Updated in the Phase 3.4/3.5/3.6 rows below.

---

## Phase 3 — Mobile round entry (the core build)

### 3.1-3.3 — Prototype before committing to a design

Jon's explicit ask: consider phone-entry ergonomics carefully, prototype a couple of
approaches, and try them for real before writing production code.

| # | Step | Model | Why |
|---|------|-------|-----|
| 3.1 | Propose 2-3 candidate mobile score-entry interaction patterns, grounded in the real usage moment (single admin, typically entering scores after the round has finished — clubhouse or course — from memory or a paper/phone scorecard, often under time or social pressure). For each: a short brief covering the interaction flow, the usage moment it's optimised for, and its primary weakness. Append as a new `## Phase 3.1 prototypes` section in this file. | Opus | Getting the candidate patterns wrong wastes real prototyping effort; this is genuine UX/product judgement about what's worth building, same reasoning as 3.4's design note. |
| 3.2 | Build each brief from 3.1 as a static, standalone HTML mockup under `webapp/mobile_mockups/` (served at `/mockups/`), following the existing conventions in that folder exactly: pure-CSS light/dark toggle via `:has()`, Lora + Roboto Mono + forestgreen identity, no backend calls, no JS framework, phone-viewport sized. Populate with a fake in-progress round (a handful of fake players, 18 holes) so it's actually tappable/testable, not just a static image. Add each to `webapp/mobile_mockups/index.html`'s chooser page with its brief as the description. | Sonnet | Frontend implementation against an existing, well-established convention — no design judgement of its own. |
| 3.3 | **Manual (Jon):** open each prototype on an actual phone (via `/mockups/`), ideally simulating real conditions — standing, one-handed, outdoor screen glare if possible — and tap through entering a fake round. Pick a direction (or note a hybrid). Record the decision and the reasoning in a short note appended under `## Phase 3.3 decision` in this file. | — | Only Jon can judge the actual feel on a real device. |

> **Kick-off prompt — Phase 3.1 (Opus):**
> "Read `DATA_STORAGE_INGESTION_PLAN.md` Question 2's recommendation for context. Propose
> 2-3 candidate interaction patterns for entering golf scores on a phone in this app,
> grounded in the actual usage moment: a single admin entering a just-finished round's
> scores, typically in the clubhouse or on the course, from memory or a scorecard, possibly
> in a hurry. Think through real alternatives — e.g. a touch-optimised grid (18 holes ×
> players, like the current Google Sheet but redesigned for a small screen), a sequential
> hole-by-hole wizard matching how the round is actually played, a player-by-player
> scrollable entry list — and pick the 2-3 most worth prototyping, not necessarily those
> three verbatim if you see a better option. For each, write a concise brief (~1 short
> paragraph: interaction flow, the usage moment it best fits, its main weakness). Append
> them as a new `## Phase 3.1 prototypes` section at the end of
> `DATA_STORAGE_INGESTION_PLAN.md` — edit that file directly, don't create a new one."

> **Kick-off prompt — Phase 3.2 (Sonnet):**
> "Read the `## Phase 3.1 prototypes` section of `DATA_STORAGE_INGESTION_PLAN.md` (added by
> the previous step) and look at a couple of existing files in `webapp/mobile_mockups/`
> (e.g. `scorecard_field_app.html`, `index.html`) to match their conventions exactly: single
> self-contained HTML file, pure-CSS light/dark toggle via a `:has(#mode:checked)` pattern
> (no JS required to view), Lora + Roboto Mono fonts + forestgreen accent, phone-width
> layout, no backend calls or real data — everything hardcoded. Build one standalone mockup
> per Phase 3.1 brief under `webapp/mobile_mockups/` (suggested naming:
> `round_entry_<short-name>.html`), populated with a fake in-progress round (4-5 fake
> players, 18 holes, plausible golf scores) so each pattern is genuinely tappable and
> testable on a phone, not just a static image. Add an entry for each to
> `webapp/mobile_mockups/index.html`'s chooser page, using the corresponding brief as the
> description, in the same visual style as the existing entries there. These are throwaway
> prototypes — do not wire them to any backend route, any real data file, or any Python
> code."

*(Step 3.3 is manual — no kick-off prompt; it's Jon trying the mockups from 3.2 on a phone
via `/mockups/` and recording a decision in this file.)*

### 3.4-3.10 — Build the real thing (gated on 3.3's decision + Phase 1 complete)

| # | Step | Model | Why | Risk / rollback |
|---|------|-------|-----|-------------------|
| 3.4 | **Design note** (temporary .md per CLAUDE.md rule 3) covering: the chosen interaction pattern from 3.3; **the submit UX given Phase 0.1's finding that the full pipeline is ~16.5s median, not the hoped-for <15s** — decide between a background-task/poll pattern or scoping in the incremental-cache-regen option (see [0.1 findings](#phase-0-findings)) as a prerequisite; draft JSON schema (TEGNum, Round, Course, per-player-per-hole scores, updated-at — **no Par/SI overrides needed**: pre-round setup, already built, owns that via `round_pars.csv`, and round entry only ever reads it read-only); draft lifecycle (create → autosave → submit → archive/delete; one active draft per TEG+Round); the wide-frame builder contract (must byte-match the layout `process_google_sheets_data` consumes — pull Par/SI from `round_pars.csv`, not from player input); route surface (`GET /admin/enter-round`, `.../autosave`, `.../preview`, `.../submit`, draft list/delete); offline strategy (server draft = source of truth, `localStorage` mirror replayed on reconnect, last-write-wins is fine for a single admin); how preview/submit reuse existing partials; failure UX (regen error mid-submit, lock contention from 1.3, **no `round_pars.csv` entry yet for this TEG+Round** — link to `/admin/round-setup`). Module placement: draft store + builder in new `teg_analysis/analysis/round_entry.py` (UI-agnostic), routes in new `webapp/routes/admin_entry.py` (`admin.py` is already 842 lines). | **Opus** | New module + API design feeding the highest-value data path; a wrong call here (drafts entangled with the canonical store, or a builder diverging from the sheet contract) is expensive to unwind — now compounded by a real submit-latency decision to make. | — |
| 3.5 | Implement `teg_analysis/analysis/round_entry.py`: draft save/load/list/delete under `data/drafts/` (volume on Railway, `data/` locally; excluded from GitHub sync), `build_wide_frame(draft) -> pd.DataFrame` (Par/SI sourced from `round_setup`'s `round_pars.csv` reads, not the draft itself), validation helpers (score bounds, completeness per player). | Sonnet | New functions to a written spec, following existing io patterns. | Drafts are ephemeral; no canonical data touched. |
| 3.6 | Routes (`webapp/routes/admin_entry.py`, registered in `webapp/app.py`): form page prefilled from `in_progress_tegs.csv`/`round_info.csv`, guarded on `round_pars.csv` having an entry for this TEG+Round (link to `/admin/round-setup/{teg}/{round}` if not — pre-round setup, not the entry page, is where Par/SI gets confirmed); HTMX autosave; preview posts the built frame through `process_google_sheets_data` → duplicate analysis → existing `partials/admin_update_preview.html`; submit → `execute_data_update` (with 1.1 backups + 1.3 lock) → `deps.clear_all_data_caches()` → existing result partial. `find_tegs_missing_round_info` guard links to `/admin/edit-data`. | Sonnet | Straightforward new endpoints copying `admin.py`'s established auth/ctx/partial patterns; hard logic lives in already-designed functions. | Submit path writes canonical data — but only via the identical, now-backed-up pipeline. |
| 3.7 | Template + styling for the chosen pattern from 3.3: `admin_enter_round.html`, mobile-first per `webapp/MOBILE_PLAN.md`/`static/mobile.css` conventions (≤640px, desktop untouched); `localStorage` mirror + replay script; disabled-submit while in flight. Build directly on the winning `webapp/mobile_mockups/round_entry_*.html` prototype rather than starting fresh. | Sonnet | Frontend work with an already-chosen, already-prototyped design to follow. | None. |
| 3.8 | Tests: draft roundtrip; builder output accepted by `process_google_sheets_data` and equivalent to a sheet-shaped fixture; incomplete-round rejection; duplicate/overwrite paths; route auth. Extend `tests/test_admin_routes.py` + new `tests/test_round_entry.py`. | Sonnet | Test writing against a fixed spec. | — |
| 3.9 | **Opus review gate** (per CLAUDE.md): read modified files end-to-end, run `pytest tests/ -v`, then a real-device end-to-end test: enter a fake round (confirm the TEG-50 sandbox convention with Jon first), airplane-mode mid-entry, resume, submit, verify site pages update, verify a backup exists, delete via `/admin/delete-data`. | **Opus** | Repo-mandated review gate; also the data-integrity sign-off before this becomes the primary ingestion path. | E2E test writes real data — use the TEG-50 sandbox and delete afterwards; both directions are backed up (Phase 1.1/1.2). |
| 3.10 | Docs: `DATA_FLOW.md` (new ingestion path + drafts), `webapp/README.md`, CLAUDE.md current-state, `file_catalog.py`; delete the 3.4 design note. | Haiku | Mechanical doc sweep. | — |

> **Kick-off prompt — Phase 3.4 (Opus):**
> "Read `DATA_STORAGE_INGESTION_PLAN.md` in full, including the `## Phase 3.3 decision`
> section (the chosen interaction pattern — if it's not there yet, stop and ask Jon before
> proceeding). Write a design note as a new temporary file
> `webapp/ROUND_ENTRY_DESIGN.md` covering: the chosen interaction pattern; the draft JSON
> schema; the draft lifecycle (create/autosave/submit/archive/delete, one active draft per
> TEG+Round); the exact wide-format frame contract the builder must produce — inspect
> `teg_analysis/analysis/pipeline.py`'s `get_google_sheet`/`reshape_round_data` and
> `teg_analysis/analysis/data_update.py`'s `process_google_sheets_data` to pin this down
> precisely, since 3.5/3.6 depend on it matching exactly; the new route surface under
> `/admin/enter-round`; the offline/autosave strategy (server draft as source of truth,
> `localStorage` mirror, last-write-wins); how preview/submit reuse
> `partials/admin_update_preview.html` and the existing result partial; failure UX for a
> mid-submit error or a lock-contention error from Phase 1.3. Confirm module placement: new
> `teg_analysis/analysis/round_entry.py` for the UI-agnostic draft store + builder, new
> `webapp/routes/admin_entry.py` for routes (do not add to `admin.py`, which is already
> large). This is a design note only — no implementation."

> **Kick-off prompt — Phase 3.5-3.8 (Sonnet):**
> "Read `webapp/ROUND_ENTRY_DESIGN.md` (from Phase 3.4) in full — implement exactly to that
> spec, and read `DATA_STORAGE_INGESTION_PLAN.md` for surrounding context if anything is
> ambiguous. Implement in order: (3.5) `teg_analysis/analysis/round_entry.py` — draft
> save/load/list/delete under the store's `data/drafts/` path (use the existing
> `teg_analysis/io` volume/local path conventions; this folder must NOT be synced to
> GitHub), `build_wide_frame(draft) -> pd.DataFrame` matching the design note's frame
> contract exactly, and score/completeness validation helpers; (3.6)
> `webapp/routes/admin_entry.py`, registered in `webapp/app.py`, following the auth/context/
> partial-rendering patterns already established in `webapp/routes/admin.py` — the form
> page, autosave endpoint, a preview endpoint that runs the built frame through
> `process_google_sheets_data` and reuses `partials/admin_update_preview.html`, and a submit
> endpoint that calls `execute_data_update` (relying on the Phase 1.1 backups and Phase 1.3
> lock already in place) then `deps.clear_all_data_caches()`; (3.7) the entry template,
> built directly on the winning prototype from `webapp/mobile_mockups/` (see
> `## Phase 3.3 decision` in the plan file for which one), wired to real data and following
> `webapp/MOBILE_PLAN.md`/`static/mobile.css` conventions — mobile-only styling behind the
> existing `≤640px` breakpoint, desktop untouched; (3.8) tests in
> `tests/test_round_entry.py` and additions to `tests/test_admin_routes.py` covering draft
> roundtrip, frame-builder output being accepted by `process_google_sheets_data`,
> incomplete-round rejection, duplicate/overwrite handling, and route auth. Run
> `pytest tests/ -v` before finishing."

> **Kick-off prompt — Phase 3.9 (Opus):**
> "This is the CLAUDE.md-mandated Opus review gate for the round-entry feature (Phases
> 3.4-3.8). Read every file touched by those phases end-to-end (`git diff` against the base
> branch for the file list). Run `pytest tests/ -v`. Then do a real end-to-end pass: confirm
> with Jon which TEG number is safe to use as a sandbox (the codebase has a TEG-50
> convention for this — verify it's still current), enter a full fake round through the new
> `/admin/enter-round` flow on an actual phone, deliberately go into airplane mode partway
> through and resume to prove the draft survives, submit, verify the site's other pages
> reflect the new data, verify a timestamped backup was created (`/admin/backups`), then
> delete the sandbox round via the existing `/admin/delete-data` flow and confirm the site
> returns to its prior state. Report pass/fail on each of these checks plus anything you'd
> flag before this becomes the primary ingestion path."

> **Kick-off prompt — Phase 3.10 (Haiku):**
> "Phase 3 (mobile round entry) is implemented and reviewed. Update `DATA_FLOW.md` to
> document the new ingestion path (drafts → wide-frame builder → existing
> `process_google_sheets_data`/`execute_data_update` pipeline), `webapp/README.md`,
> CLAUDE.md's 'Current state & next steps', and `teg_analysis/io/file_catalog.py` for the
> new `course_pars.csv` and drafts folder if not already covered. Delete
> `webapp/ROUND_ENTRY_DESIGN.md` (its content is now folded into `DATA_FLOW.md`)."

## Phase 4 — Demote Google Sheets, then decide

| # | Step | Model | Why |
|---|------|-------|-----|
| 4.1 | Relabel the existing `/admin/data-update` page as "Import from Google Sheet (fallback)"; link both flows from a small admin index; keep it fully functional for one TEG season. | Haiku | Copy/nav changes only. |
| 4.2 | **Decision gate (human, after next TEG):** if the native form was used and the sheet wasn't missed, remove the sheet path (`get_google_sheet`, `GOOGLE_*` env vars, `gspread`/`google-auth` deps, old page). Until then, no code removal. | Haiku (when triggered) | Deleting dead code and docs. |

**4.1 done.** The Google Sheet import page (`admin_data_update.html`, route unchanged at
`/admin/data-update`) is relabeled "Import from Google Sheet (fallback)" with a note pointing
to Live round as the primary path; the admin nav (`partials/admin_nav.html`, already the
"small index linking both flows" — no separate page needed) now reads "Sheet import
(fallback)". No Sheet-related code touched.

*(Step 4.2 triggers after a season of real use — no kick-off prompt yet; revisit this file
when Jon says Live round has proven itself.)*

---

## Assumptions to verify before committing (consolidated)

1. ~~Full derived-cache regen time~~ — **resolved (0.1): 16.5s median in the dev sandbox,
   dominated by full-history recompute in `update_commentary_caches`/`update_bestball_cache`.
   Exceeds the synchronous threshold; Phase 3.4 must pick background-task vs
   incremental-regen.** Still worth a quick real-Railway timing check once deployed, since
   the dev sandbox's CPU may not match production.
2. Railway volume persistence/snapshot behaviour and `RAILWAY_GIT_BRANCH` presence (0.4).
3. Par/SI historical consistency per course (0.2) — sizes the Phase 2 backfill effort.
4. No non-Streamlit readers of the CSV mirrors (0.3) — gates Phase 1.4.
5. GitHub PAT type/expiry and rate budget (0.4) — near-certain fine, but ingestion now
   depends on it at a moment (clubhouse) where failure is annoying; the volume-first write
   order already means a GitHub outage loses nothing (data lands on the volume; a later
   manual push via `/admin/volume-sync` recovers — worth confirming that recovery path once,
   manually).

**Budget outcome:** $0/month added, against a ~$10/month ceiling. Nothing in this design
improves by paying for it.

## Critical files for implementation

*(Original plan sketch below; superseded by what actually got built — see "Phase 3.4 built"
above for the real file list. Left as-is for history rather than silently rewritten: the
module ended up named `live_round.py` not `round_entry.py`, and everything landed as one
Phase 3.4 pass rather than the originally-sketched 3.4-3.7 sub-steps.)*

- `teg_analysis/analysis/data_update.py` — add-flow backups, lock, mirror retirement, editable-files registry
- `teg_analysis/analysis/pipeline.py` — `update_all_data` mirror removal; the sheet contract (`get_google_sheet`, `reshape_round_data`) the new builder must match
- `webapp/routes/admin.py` — patterns (auth, preview/confirm partials, cache clearing) the new entry routes replicate
- `teg_analysis/io/file_operations.py` — `backup_file` fix; store-path conventions for the draft store
- `teg_analysis/analysis/round_entry.py` — new module (draft store + wide-frame builder), designed in Phase 3.4
- `webapp/mobile_mockups/` — Phase 3.1-3.2 prototypes live here before becoming the real template in 3.7
- `teg_analysis/analysis/round_setup.py` — **built** (pre-round setup, see below): `get_round_setup_form`/`save_round_setup` are what Phase 3.4-3.6 should read Par/SI from, not reinvent
- `webapp/routes/admin_round_setup.py`, `webapp/templates/admin_round_setup*.html` — **built**: the `/admin/round-setup` pre-round Par/SI confirmation page

---

## Wrap-up (done)

- ✅ Folded this file's outcome into `DATA_FLOW.md` (Storage Layer: `live_rounds.csv` +
  `live_rounds/{token}.csv`), `webapp/README.md` (Live round admin + player-facing sections,
  Sheet-import relabel), and `CLAUDE.md`'s "Current state & next steps". `teg_analysis/README.md`
  got the three new `analysis/` modules (`round_setup.py`, `teg_setup.py`, `live_round.py`).
- ✅ Confirmed `DATA_RATIONALISATION_PLAN.md` was deleted at Phase 1.5.
- ✅ Replaced the root `TODOS.md` "Data updates" entry with the Phase 4.2 decision-gate
  reminder (still outstanding — see below).
- **Not deleted, deliberately** — see the "COMPLETE — kept as a historical/reference record"
  note at the very top for why.

---

## Phase 3.1 prototypes

Three candidate interaction patterns for a single admin entering a just-finished round
(up to 7 players × 18 holes ≈ 126 gross scores) on a phone, usually transcribing from a
completed paper/phone scorecard in the clubhouse or on the course, one-handed, possibly
under glare and time pressure. The dominant cost in this moment is raw numeric-entry speed
and error rate while copying an existing grid — so all three keep a big custom number pad
(not the OS keyboard), an always-visible running total per player as a live sanity check,
and clear "holes remaining" progress. They differ in how the cursor moves through the 126
cells, which is the real variable to test on a phone. Prototype all three (Phase 3.2), then
pick on feel (Phase 3.3).

### A. Sticky-keypad grid (redesigned scorecard grid)
A compact holes-as-rows × players-as-columns grid — the same mental model as the paper card
Jon is copying from — with a number pad pinned to the bottom of the screen. Tapping a cell
highlights it; the keypad fills it and the cursor auto-advances to the next cell in a chosen
traversal (down a column, or across a row, toggglable), so most of the round is entered
without ever re-aiming at a target. The grid scrolls under the fixed keypad, with column
totals and a per-hole "everyone entered?" tick giving constant overview. **Best fits:** the
common case — transcribing a complete paper card end-to-end, where seeing the whole grid
mirrors the source and makes gaps and fat-finger outliers obvious at a glance. **Main
weakness:** even redesigned, 7 columns on a phone means small cells and horizontal scrolling;
the highlighted-cursor + auto-advance is the whole bet, and if a mis-tap moves the cursor
unnoticed, errors cascade down a column before the running total catches them.

### B. Hole-by-hole wizard
One hole per screen: a big card showing hole N (Par/SI for context) with a large tap-target
and number pad for each player's score stacked vertically, then a prominent "Next hole"
advance. Progress is a 1→18 stepper; back/next jumps let you fix any hole. **Best fits:**
entering live or incrementally as the round is played, or reconstructing from memory where
you naturally replay the round hole by hole; also the most glare- and one-hand-friendly —
biggest targets, least on screen, hardest to mis-tap. **Main weakness:** worst fit for the
actual common case (bulk-transcribing a finished card): 18 screen advances is a lot of taps,
you lose the whole-round overview, and spotting "did everyone play hole 12?" or an entry
transposed between two players is harder when you only ever see one hole at a time.

### C. Player-by-player column
Pick one player and enter all 18 of their holes in a single fast vertical run — one mental
context ("this is JB's card"), one column of the source scorecard, number pad fixed, cursor
auto-advancing hole 1→18 — then move to the next player. A player-selector strip along the
top shows who's done (with their total) and who's left. **Best fits:** the "finish one card
completely, then the next" transcription style, and the fact that Jon knows his own round
cold — fastest sustained numeric entry because nothing changes context between taps. **Main
weakness:** you re-read/traverse the source card up to 7 times, cross-player checks (did
everyone score hole 7? is a hole accidentally shifted by one row for one player?) are
invisible until every column is done, and the repetitive middle players are where attention
(and accuracy) lapses.

*Recommended prototyping priority:* A first (best fit for the most likely moment — copying a
completed card — and the sticky-keypad/auto-advance mechanic is the least proven), then C
(the speed play), then B (the safe, low-error fallback and the only one that also suits live
entry).

## Phase 3.2 mockups (built)

All three built as standalone, fully interactive HTML files under `webapp/mobile_mockups/`,
served at `/mockups/` (see the "Round entry — pick one" section on the mockups index page).
Populated with a fake TEG 50 · Round 1, the real 7-player roster (DM, GW, HM, JP, JB, SN,
AB), and a plausible 18-hole par sequence — nothing is saved, this is throwaway. Verified
with Playwright (cell/row activation, keypad fill, auto-advance in both traversal modes,
running totals, hole/player completion) — no JS errors from the mockups themselves (the
only console noise is the same external Google-Fonts CDN calls every other mockup in this
folder already makes, which just need a live network to render icons/fonts — same as
opening any other file in this folder).

- `round_entry_grid.html` — Pattern A, sticky-keypad grid. Includes a Column/Row traversal
  toggle so both cursor directions from the brief are actually testable.
- `round_entry_wizard.html` — Pattern B, hole-by-hole wizard. Dot-strip progress, "Next
  hole" only enables once all 7 players are filled for the current hole.
- `round_entry_player.html` — Pattern C, player-by-player column. Player chips show
  progress/done state; completing a player's 18th hole auto-advances to the next
  incomplete player.

## Phase 3.2b — voice entry, par-relative keypads, and a fourth pattern (built)

Second prototyping pass, layered onto the 3.2 mockups (edited in place) plus one new
mockup. All still throwaway, nothing persisted, same conventions. Verified with Playwright
(keypad taps per par, dictation-string parsing/preview/fill on each voice-enabled page, no
mockup JS console errors).

**Par-relative keypad (all four mockups).** The flat 1–12 pad wasted prime thumb space on
numbers that never get tapped. Replaced with six prominent buttons spanning **par−1 to
par+4** for the active hole, labelled number-first with a small golf term underneath
(birdie/par/bogey/+2…), plus a quieter one-tap outlier row for the rest of 1–12 so nothing
is unreachable. The range was picked from the data, not intuition: across all 6,390
recorded holes, par−1..par+4 covers 97.8% of scores, while eagles are 0.06% (4 ever) and
par+4 alone is 3.7% — so the window skews high rather than the symmetric par−2..par+3
(94.0%). Par always sits at the fixed 2nd position, so muscle memory holds across par 3/4/5.
Trade-off: the six primary buttons show different numbers per hole, so you must glance
before tapping — the fixed par position and the term labels are the mitigation.

**Voice entry (grid, player-column, and the new flow mockup).** A mic button opens a bottom
sheet with a plain textarea — deliberately *not* the Web Speech API, which iOS Safari
doesn't reliably support; the invitation is to tap the field and use the iOS keyboard's
built-in dictation mic, then parse whatever text lands. The parser handles digits, number
words (zero–twenty, so mis-sizes are caught rather than mangled), common dictation mishears
("for/fore"→4, "to/too"→2, "tree/free"→3, "won"→1, "ate"→8), separators from natural
pauses, and glued digit runs ("three four ten" arriving as "3410" — split digit-wise,
reading 1 followed by 0–2 as 10–12 since a blow-up is far likelier than an ace). Nothing
commits without review: a live chip preview maps each parsed value to its target cell
("H3 DM 7"), unknown words or out-of-range values disable Apply outright (a dropped token
mid-run would silently shift every later score onto the wrong hole), and filling resumes
from the current cursor, not hole 1. The wizard didn't get voice — its per-hole,
across-players frame doesn't match dictating a column of one player's card.

**D. Rapid-fire flow (`round_entry_flow.html`, new).** Rethinking the brief with voice and
par-relative selection as first-class primitives: the bottleneck in A–C is *aiming* — 126
small tap targets. Flow removes aiming entirely. One huge target card announces the cell
being filled ("DM · Hole 7 · Par 4"); six near-thumb-sized par-relative buttons fill it and
auto-advance to the next *empty* cell in player-major order (never overwriting downstream);
mis-taps are handled by an undo tape of recent entries (tap a chip to jump back, undo
restores the previous value) rather than by careful aiming; a tappable 7×18 dot map gives
the grid's gap-spotting overview and random access; voice fills forward from the cursor
with the same preview gate. Best fit: heads-down transcription at maximum speed, and
glare/one-thumb conditions (biggest targets of the four). Main weakness: you see only one
cell's context at a time, so a transposition against the paper card surfaces via the map
dots and running total, not the entry surface itself — the tape and map are load-bearing,
not decorative.

Index page updated: A and C flagged "+ voice", all descriptions mention the par-relative
pad, D added. The 3.3 decision below should now weigh four patterns, not three.

## Phase 3.3 decision

**Decided: Pattern A (`round_entry_grid.html`, sticky-keypad grid) is the chosen direction.**
Tried all four on a real phone. The voice entry and par-relative keypad were both judged
successes and are being kept; A won over the others for its always-visible grid (gap-spotting
at a glance) combined with a keypad. Refinements made after the on-phone trial, all in
`round_entry_grid.html`:

- **Fixed 2–8 keypad, not par-relative shifting.** The par-relative *range* was right, but
  letting the six primary buttons slide with par (as 3.2b built it) turned out to slow entry
  down in practice — fingers couldn't build muscle memory for "the low-score button" when its
  screen position kept moving. Numbers are now pinned: **2–8 are always the big primary
  buttons**, in the same position on every hole (this range still covers every par-1..par+4
  case for par 3/4/5, i.e. the same 97.8%-of-all-scores window as before); 1 and 9–12 stay
  reachable as a smaller outlier row underneath. Only the *label* under each button
  (birdie/par/bogey/+2…) still moves with par — the position doesn't.
- **Bigger keypad**, sized up to feel closer to the `round_entry_flow.html` big-pad (larger
  buttons, bigger digits), since screen space allowed it once the layout wasn't fighting a
  6-wide single row.
- **All-players / single-player view toggle.** A segmented control above the grid switches
  between showing all 7 columns (the gap-spotting overview) and filtering to just one
  player's column (less visual noise while transcribing one card start-to-finish). Traversal
  in single-player mode is always hole-by-hole for that player; the Column/Row toggle is
  hidden since it's moot with one column. Voice entry respects the same filter.

Not carried forward: Patterns B, C, D remain in `webapp/mobile_mockups/` for reference but
are no longer active candidates. `round_entry_grid.html` is the reference implementation for
Phase 3.4 (building the real, data-writing round-entry page) — that build-out (auth, wiring to
`round_pars.csv`/`all-scores.parquet`, roster awareness, persistence) has not started yet.

### Second refinement pass (multi-device, groups, keypad choice)

Further feedback after living with Pattern A:

- **Keypad style toggle, not a forced choice.** Added a second keypad mode, **relative to
  par** (par−1..par+3, 5 buttons, re-centering on the hole like the original 3.2b design),
  selectable alongside the fixed 2–8 layout via a small toggle inside the keypad. Some players
  think in raw numbers, some in shots-vs-par — this is a genuine preference, not a UX bug to
  resolve one way. Persisted per device (`localStorage`), defaults to fixed.
- **Player group picker, generalized from single/all to any subset.** A round is typically
  played in 2 groups of 2–4, and each player only wants their own group's cells on their
  phone. The all/single toggle became a **chip multi-select** (tap any of the 7 player chips
  on/off, plus an "All" quick-reset) — traversal, voice entry, and column visibility all
  filter to whichever subset is currently chosen. This choice is local to the device (never
  synced) so each player picks independently. `advance()`/voice-targeting were generalized to
  cycle through "whichever players are currently visible" rather than special-casing
  all-vs-one, which also deleted the old single-player branch entirely — one code path instead
  of two.
- **Concurrent multi-device entry.** The real requirement — two-plus people entering scores on
  separate phones for the same round at the same time — needs a backend (shared state +
  polling/websocket) that doesn't exist yet; a static mockup can't provide that literally. What
  it *can* do, and now does: a same-browser cross-tab simulation via `BroadcastChannel` +
  `localStorage`, so opening the mockup in two tabs behaves like two devices on one round for
  testing the interaction pattern — live merge of entries, a "N devices" presence badge (with
  an immediate reply-to-new-peer handshake so discovery isn't up to 4s late), a late-joining
  tab catching up from the `localStorage` snapshot, and per-cell timestamps so a delayed/
  stale message can't clobber a newer edit (last-write-wins). Two bugs caught and fixed during
  Playwright verification: `buildGrid()` was rebuilding cells empty and never repainting from
  a loaded `scores` object (fixed with `renderAllCells()`, called once after `buildGrid()`);
  and presence discovery relied purely on periodic 4s pings until the reply-handshake was
  added. **This does not solve real cross-device sync** — that's Phase 3.4 backend work
  (see the Fable review below for a first pass at that architecture).

### Fable design/performance review (done)

Asked Fable to review `round_entry_grid.html` end-to-end for correctness, design coherence,
performance, and — separately — to sketch the real Phase 3.4 backend architecture, since the
cross-tab sync above is explicitly not that. Full report:
`/tmp/.../scratchpad/fable_round_entry_review.md` (ephemeral session path; key content
preserved here since that file won't persist). Verdict: the core design (grid + always-visible
keypad + auto-advance + group chips) is sound, not cruft; `innerHTML=`-driven re-renders don't
leak listeners; performance is a non-issue at this scale (~5,000 node creations over a 20-30min
session — any phone handles that trivially). Found one real shipping bug and several smaller
ones.

**Fixed immediately** (all verified with Playwright, including a fresh two-tab concurrency
re-check after all fixes):
- **HIGH — chips hid themselves.** `applyPlayerVisibility()` selected `[data-player]`
  document-wide, which also matched the chip buttons themselves (they carry `data-player`
  too) — so deselecting a player hid its own chip, making it unreachable again except via
  "All" (you could shrink the visible set but never selectively regrow it). Scoped the
  selector to `#egrid`/`#totalsbar` only.
- **iOS auto-zoom**: voice textarea was 14px; iOS Safari auto-zooms any focused field under
  16px and ignores `maximum-scale=1.0` for it anyway (also dropped that meta value — it's an
  accessibility anti-pattern with no upside here).
- **scrollIntoView landing under the sticky header/columns** on wrap-around advance — added
  `scroll-margin-top`/`scroll-margin-left` matching the sticky thead/left-column sizes.
- **Hardcoded OUT/IN/TOT pars (36/36/72)** could silently disagree with the `PARS` array —
  now derived (`PARS.slice(0,9).reduce(...)` etc).
- **Dead `zero`/`oh` voice mappings** — both always mapped to 0, which is never a valid score,
  so they could only ever trip the "must be 1-12" error. Removed; they now report as an
  honest "didn't understand" instead.

**Left as open decisions** (not acted on — need Jon's call or on-device testing, not a
clear-cut fix):
- **D1 — keypad mode**: is the fixed/relative toggle worth keeping, or should the real page
  ship fixed-2–8-only (which the file's own comment says already covers 97.8% of every score
  ever recorded)? Fable's lean: keep the toggle for the trip as a live A/B, cut it for the
  real build if nobody defends relative mode after real use.
- **Voice strictness**: any single unrecognized word currently blocks the whole dictated
  batch (`Fix before filling`), and "hole fourteen" gets parsed as a literal score of 14 and
  blocked, since `NUM_WORDS` maps `fourteen:14` and nothing swallows a `hole <n>` pair. Softening
  either is a real behavior change with tradeoffs, not touched.
- **Apply button possibly behind the OS keyboard** during voice dictation (`.vsheet` is
  `position:fixed; bottom:0`) — flagged as needing an actual on-device check before deciding
  a fix, not something to guess at from a read-through.
- **LWW tie divergence** (two devices writing the same cell in the same millisecond can swap
  and permanently diverge) — a real bug in the demo's client-side timestamp approach, but not
  worth patching there: the recommended real backend design below drops client timestamps
  entirely (server-assigned order), which eliminates the whole problem class rather than
  papering over it client-side.
- **Smaller polish, not done**: voice preview doesn't flag when a value would overwrite an
  already-filled cell; `traversal` preference isn't persisted (unlike keypad mode / visible
  players); progress badge counts all 126 cells even when a device is filtered to one group;
  deselecting the last-visible player silently no-ops with no feedback; muted grid-header text
  (`--text-muted` at ~3.2:1 contrast) may be hard to read in direct sunlight — the actual use
  case.

**Real multi-device backend recommendation, for Phase 3.4** (not started — this is a design
sketch to build from, not code): **polling, not WebSockets** (self-healing on flaky course
cellular; ~3-4s interval, back off when the tab's hidden; 7 devices is ~2 req/s worst case) —
`POST .../scores` to write (doubles as a poll response), `GET .../scores?since={seq}` to read
deltas. **Storage**: one JSON file per live round on the existing Railway volume
(`live_rounds/{teg}_r{round}.json`), single `asyncio.Lock`, no new dependency — explicitly a
*staging area*, not the record; "finish round" feeds the existing `data_update.py` pipeline for
one GitHub commit, never per-stroke. **Conflict model**: drop client timestamps, let the server
stamp arrival order (kills LWW ties/clock-skew outright); when two *different* devices write
*different* values to the same cell within ~60s, don't silently pick a winner — flag the cell
(amber ring) and refuse to finalize the round until resolved, since a silently-wrong golf score
lives in the record forever. **Identity**: a `localStorage` UUID + self-declared name behind
the *existing* admin cookie auth (or a per-round shareable link) — no new auth system.
Estimated size: ~150-250 lines of FastAPI; the mockup's `setScore`/`renderCell` split from the
transport layer (`broadcastScore`/`bc.onmessage`) makes swapping in `fetch`-based polling a
clean, contained change when this gets built.

## TEG roster + handicap setup (built)

Companion admin page to Phase 2.5's round setup, addressing the same gap one level up: not
every player plays every TEG, and until now the only handicap-prepopulation logic
(`get_current_handicaps_formatted` / `get_hc` in `teg_analysis/analysis/handicaps.py`) was
wired into a read-only display on the Handicaps page. New module
`teg_analysis/analysis/teg_setup.py` (`get_teg_roster_form`, `save_teg_roster`,
`get_roster_players`, `get_next_teg`) reuses that existing calculation rather than
reimplementing it, and a new `/admin/teg-setup[/{teg_num}]` page (mirroring
`/admin/round-setup`'s structure) lets an admin, ahead of a TEG:

- see all 7 rostered players (the ones with a column in `handicaps.csv`) with a
  playing/not-playing checkbox and a handicap field,
- prefilled from `handicaps.csv` if a row already exists for that TEG ("confirmed"), else
  from the calculated draft ("calculated"), else blank,
- manually override any handicap or roster flag before saving, which upserts the one
  `handicaps.csv` row for that TEG in place (existing row order untouched; a genuinely new
  TEG is appended).

Not-playing is still the 0-in-that-cell convention already used throughout the existing data
(`load_and_prepare_handicap_data` already drops `HC == 0` rows) — no schema change. Scope
note: this only covers the 7 players who already have a `handicaps.csv` column (AB, DM, GW,
HM, JB, JP, SN); Graham Patterson (`GP` in `PLAYER_DICT`) has never played and has no column,
so adding him would need a schema change and is out of scope here. Also noticed in passing,
not touched: `data/handicaps.csv` has a `TEG 50` row wedged between `TEG 18` and `TEG 19`
with odd values (`GW,HM` effectively 0/blank) — looks like stray test data from an earlier
session rather than a real TEG, since real play only goes up to TEG 18/19. Flagged for Jon to
confirm/clean up; not touched here since it predates this session and isn't blocking.

## Phase 3.4 design — the real, data-writing round-entry page

Jon's decision: ship the mockup's current design as-is (both keypad modes, player-group
chips, voice entry) and build the real backend it needs. Auth model decided: **per-round
shareable link**, not the shared admin password — a live round is started by an admin, who
gets a link to share with the group; anyone with the link can enter scores for that round,
no login. This section is the concrete design, written before coding it (matching how every
other phase in this doc was speced first).

### Storage: reuse `read_file`/`write_file`, not a new file type

`teg_analysis/io/file_operations.py` only supports `.csv`/`.parquet` — no JSON. Rather than
add a third file type (and its own volume-caching/GitHub-sync plumbing) for what's a small,
short-lived dataset, live-round state is two new CSVs, read/written through the existing I/O
layer like everything else in `data/`:

- **`data/live_rounds.csv`** (registry, one row per live round ever started): `Token, TEGNum,
  Round, CreatedAt, Status` where `Status` is `active | finalized | cancelled`. Low write
  frequency (only at start/finalize/cancel) — committed to GitHub normally (`defer_github`
  default), so there's an audit trail of every live round.
- **`data/live_rounds/{token}.csv`** (per-round staging, current state per cell, not an
  event log): `Hole, Pl, Score, DeviceId, DeviceName, Seq, Conflict, PrevScore,
  PrevDeviceName`. One row per cell that has ever been written. Written via `write_file(...,
  defer_github=True)` on **every score write** and the returned file-info is always
  discarded — this makes it a volume-only write (fast, no GitHub API call, no commit noise
  during live entry) matching Fable's "staging area, not the record." Deleted (or moved to
  `data/live_rounds/archive/`) once finalized.
- **Concurrency**: a single module-level `threading.Lock()` (mirrors `data_update.py`'s
  `_update_lock`) guards each staging-file read-modify-write cycle. At 7 devices polling
  every few seconds this is negligible contention — no need for a lock-per-token map.

### Server-assigned order, not client timestamps

The mockup's cross-tab demo used client `Date.now()` for last-write-wins, which has a real
tie-divergence bug (documented above) — the fix is architectural, not a bigger clock: the
**server** assigns a monotonic `Seq` (a simple counter stored in the registry row, incremented
per write) to every cell write, in arrival order. No client clock is ever trusted. This alone
eliminates ties and clock-skew entirely.

### Conflict model

On each write: if the cell already has a value, from a **different** `DeviceId`, that
**differs** from the incoming value → set `Conflict=True`, save the old `(Score,
DeviceName)` into `(PrevScore, PrevDeviceName)`, apply the new value anyway (never blocks
entry). A same-device overwrite (self-correction) never flags. Conflicts are visible live
(the poll response includes the flag; the entry page can show an amber ring, reusing the
`remote-flash` visual language already in the mockup) but **don't block entry** — they block
**finalize**. The admin's finalize-review page lists every conflicted cell with both values
and lets the admin pick the correct one; that write clears the flag. `Finalize` is disabled
while any `Conflict=True` row remains.

### Endpoints

Public, token-gated (the token in the URL *is* the auth — no cookie, matches the "trust the
group" model already used elsewhere in this app):
- `GET /live-round/{token}` — the entry page itself (ported from `round_entry_grid.html`).
  Reads the roster from `teg_setup.get_teg_roster_form(teg_num)` (only "playing" players get
  a column) and Par/SI from `round_setup.get_round_setup_form(teg_num, round_num)` (expects
  `source == 'confirmed'` — Phase 2.5's whole point). If the round hasn't been set up, or the
  token is unknown/finalized, the page says so instead of guessing.
- `GET /api/live-round/{token}/scores?since=0` — poll. Returns `{seq, status, cells: [...]}`
  for rows with `Seq > since` (or everything, if `since=0`, for first load / a late-joining
  device). `status` lets the page go read-only once `finalized`.
- `POST /api/live-round/{token}/scores` — write. Body: `{device_id, device_name, cells:
  [{hole, player, value}]}` (a list so one voice-entry Apply is one request, not N). Returns
  `{seq}` so the client can bump its own polling cursor and not immediately re-fetch what it
  just wrote.

Admin, cookie-gated (mirrors `/admin/round-setup`'s pattern exactly):
- `GET /admin/live-round` — list active/recent live rounds, links to start a new one (from a
  round that's already set up) or review an existing one.
- `POST /admin/live-round/start` — body `{teg_num, round_num}`; creates the token + registry
  row + empty staging file, returns the shareable link.
- `GET /admin/live-round/{token}/review` — the finalize screen: full grid (reuses the same
  rendering as the player page, admin variant), conflicted cells highlighted with a resolve
  control, `Finalize` button (disabled while conflicts remain), `Cancel round` (abandons
  without writing to `all-scores`).
- `POST /admin/live-round/{token}/resolve` — admin picks a value for one conflicted cell.
- `POST /admin/live-round/{token}/finalize` — converts the staging CSV into the long-format
  `[TEGNum, Round, Hole, Par, SI, Pl, Score]` frame `execute_data_update` expects (Par/SI
  joined back in from `round_pars.csv`), calls `execute_data_update(long_df,
  new_data_only=True)` (the existing pipeline — one GitHub commit, all derived caches
  regenerated, same as "add a round" today), marks the registry row `finalized`, archives the
  staging file.
- `POST /admin/live-round/{token}/cancel` — marks `cancelled`, deletes the staging file,
  never touches `all-scores`.

### Frontend

`round_entry_grid.html`'s interaction design (grid, both keypad modes, player-group chips,
voice entry) is the reference and is ported close to verbatim into a real Jinja2 template.
The only structural swap is the sync layer: `broadcastScore()`/`bc.onmessage` (BroadcastChannel
+ localStorage) are replaced by `fetch`-based polling against the two endpoints above — the
mockup's existing separation of `setScore()`/`renderCell()` (state + rendering) from
`broadcastScore()` (transport) makes this a contained swap, not a rewrite. `DEVICE_ID`
becomes a `localStorage` UUID; a one-time "what's your name?" prompt on first load supplies
`DeviceName`. Poll interval: 3-4s while the tab is visible, paused on `visibilitychange:
hidden` (matches Fable's recommendation).

### What's explicitly out of scope for this pass

- QR code generation for the shareable link — a plain URL + "copy link" button is enough; no
  new dependency for something the admin can text/WhatsApp directly.

Nothing else changes about `execute_data_update` — finalize calls it exactly as "add a round"
already does.

## Phase 3.4 built

Everything in the design above is implemented and tested, matching the auth decision (per-round
shareable link) and the "ship the mockup as-is" decision from earlier.

- **`teg_analysis/analysis/live_round.py`** — the storage/business-logic module: registry +
  per-round staging CSVs through the existing `read_file`/`write_file` layer,
  `start_live_round`/`apply_score_writes`/`get_scores_since`/`resolve_conflict`/
  `finalize_live_round`/`cancel_live_round`. 18 unit tests
  (`tests/test_live_round.py`), all data mocked.
- **`webapp/routes/admin_live_round.py`** + **`webapp/routes/live_round.py`** — admin
  lifecycle routes (cookie-gated, mirror the round-setup/teg-setup pattern) and the public
  poll/write API + entry page (token-gated, no cookie). Route tests in `test_admin_routes.py`
  and `tests/test_live_round_routes.py`, all `live_round` calls mocked.
- **`webapp/templates/live_round_entry.html`** — the real player-facing page, ported from
  `round_entry_grid.html` (fixed/relative keypad toggle, player-group chips, voice entry, all
  kept as designed) with the sync layer swapped for real polling.
- **`tests/test_live_round_e2e.py`** — a genuine end-to-end test: real HTTP requests (via
  `TestClient`, isolated to a scratch copy of `data/`, never the real repo) through two
  simulated devices, a deliberately triggered conflict, admin resolution, and finalize — checked
  against the actual resulting `all-scores.parquet` row, not a mock. Caught two real bugs unit
  tests (which mock all file I/O) couldn't have:
  1. **`write_file`'s local-dev path never created the parent directory before writing**
     (unlike the Railway path and unlike `write_text_file`, which both already did) — starting
     the first-ever live round crashed writing `data/live_rounds/{token}.csv` since that
     subdirectory didn't exist yet. Fixed in `teg_analysis/io/file_operations.py`, now matches
     `write_text_file`'s existing behaviour; regression test added to `test_file_operations.py`.
  2. **`get_scores_since` returned a raw NaN for `prev_device_name`** on any cell that had never
     conflicted (a `None` written to CSV round-trips back as `NaN`, not `None`, on the next
     read — `prev_value` was already guarded against this, `prev_device_name` wasn't). Starlette's
     `JSONResponse` rejects NaN outright (`allow_nan=False`), so the very first poll response
     containing an unconflicted cell 500'd. Fixed; the `store` fixture in `test_live_round.py`
     was also upgraded to round-trip every write through a real CSV encode/decode (it previously
     stored DataFrames as-is, which is exactly why the unit tests didn't catch this) so this
     whole bug class stays caught going forward.
- **Manually verified against a running server**, pointed at a scratch `data/` copy (never the
  real one): started a live round from the admin UI, entered a score on the real rendered page,
  confirmed a second browser tab (simulating a second device) saw it after a poll cycle and that
  a fresh third page load caught up correctly — Playwright, screenshots kept in the session
  scratchpad.
- Full test suite: 213 passed, 4 skipped, one pre-existing unrelated failure (`altair`, a
  Streamlit-only dependency not in `requirements.txt`).

**Not built, deliberately out of scope for this pass** (all previously flagged, none blocking):
QR code generation for the shareable link (a copyable URL is enough); the "keep both keypad
modes vs. ship fixed-only" and "soften voice-parsing strictness" decisions (still open, low
stakes, easy to revisit after real use); an on-device check for whether the voice sheet's Apply
button sits behind the iOS keyboard while dictating; self-hosting fonts (a pre-existing,
site-wide pattern, not something this feature introduced).
