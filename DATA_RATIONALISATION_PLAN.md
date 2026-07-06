# Data file rationalisation — investigation plan

**Status: not started.** Temporary working document (CLAUDE.md Documentation Rule 3):
when the investigation is done, fold the outcome into `DATA_FLOW.md` (and
`file_catalog.py` if descriptions change) and delete this file.

**The question** (from `DATA_FLOW.md` §1 and CLAUDE.md "To investigate"):
`all-data.parquet` (53 cols) and `all-scores.parquet` (17 cols) are both
hole-level data at identical granularity. Should they be rationalised into a
single source?

**This is an investigation, not an implementation.** The deliverable is a
findings-and-recommendation write-up for Jon to decide on. No data file, no
pipeline code, and nothing in `streamlit/` changes until the decision gate at
the end (Phase 4 is a sketch only, executed in a later session after sign-off).

---

## 1. Facts already established (do not re-derive)

Verified against the code on 2026-07-06. Trust these; spot-check only if
something contradicts them.

### The relationship is master → derived

- **`all-scores.parquet`** is the **raw master**. The add/delete flows in
  `teg_analysis/analysis/data_update.py` write it directly
  (`execute_data_update` ~line 456, `execute_data_deletion` ~line 637). Its
  columns are produced by `process_round_for_all_scores`
  (`data_update.py:92`): TEGNum, Round, Hole, PAR, SI, Pl, Sc, TEG, HC,
  HoleID, FrontBack, Player, HCStrokes, GrossVP, Net, NetVP, Stableford.
- **`all-data.parquet`** is **entirely regenerated from all-scores** on every
  add/delete by `update_all_data()` (`teg_analysis/analysis/pipeline.py:452`):
  read all-scores → `add_round_info` (merges Date + Course from
  `round_info.csv`) → add `TEG-Round` → `add_cumulative_scores` →
  `add_rankings_and_gaps` → add `Year` → write parquet **and**
  `data/all-data.csv` (`ALL_DATA_CSV_MIRROR`, a "manual review" copy — a
  third copy of the same data).
- `teg_analysis/io/file_catalog.py` already documents this framing
  (all-scores = "Source data", importance 1; all-data = "Processed data",
  importance 2, "Regenerated from all-scores").

### Consumer census (file level)

- **`all-data.parquet`**: read by `load_all_data()`
  (`teg_analysis/core/data_loader.py`) — the single entry point for all of
  `teg_analysis`, the webapp (via `webapp/deps.py` lru_cache wrappers), and
  the reporting pipeline (`reporting/events.py`, `history_context.py`,
  `course_history.py`, `story_plan.py` all go through `load_all_data`).
  Streamlit's `utils.py` also references `ALL_DATA_PARQUET`.
- **`all-scores.parquet`**: read/written as master by the
  `teg_analysis` add/edit/delete flows and their legacy Streamlit
  equivalents (`helpers/data_update_processing.py`,
  `helpers/data_deletion_processing.py`); read directly by frozen Streamlit
  commentary code (`commentary/round_data_loader.py`,
  `unified_round_data_loader.py`, `pattern_analysis.py`,
  `1001Report Generation.py`).
- **Nothing in `webapp/` or `teg_analysis` analysis/display code reads
  all-scores directly** — modern reads all go through `load_all_data` →
  all-data.

### Constraints

1. **`streamlit/` is feature-frozen and must not be modified** (CLAUDE.md).
   It reads *both* files, so any option that deletes or renames either file
   breaks the legacy reference app. "Breaks the frozen reference" may be an
   acceptable cost — but that is Jon's call, and the recommendation must
   price it in explicitly.
2. **Both files are load-bearing in production** (Railway volume + GitHub
   store, synced via `teg_analysis/io/sync.py`; catalogued in
   `file_catalog.py`; backed up by the delete flow). Any rename/removal
   touches: `constants.py`, `file_catalog.py`, sync/backup paths,
   `DATA_FLOW.md`, admin pages, and the GitHub copy of `data/`.
3. **Known smell to weigh, not fix yet:** enrichment is split inconsistently —
   `Area` is merged from `round_info.csv` at *load* time inside
   `load_all_data`, while Date/Course/cumulatives are baked in at *write*
   time by `update_all_data`. Any recommendation should say where enrichment
   should live, once.

### Guardrails for every phase

- **Read-only.** Never write to `data/`, never call `write_file`,
  `execute_data_update`, `execute_data_deletion`, or `update_all_data`
  against real paths. All generated output goes to a scratch directory or
  `investigation_out/` (git-ignored, deleted at the end).
- Work locally against the checked-in `data/` copies. Do not touch the
  Railway volume or push data commits to GitHub.
- Do not modify anything under `streamlit/`.

---

## 2. Phase 1 — Fact base (Haiku, or Sonnet if scripting wobbles)

Mechanical inventory work. Output: `investigation_out/findings.md` sections
F1–F3, each a table plus two or three sentences of commentary.

### T1.1 — Column inventory (F1)

Write a throwaway script (scratch dir) that loads both parquets with pandas
and emits, per file: column name, dtype, null count, and 3 sample values.
Then produce a three-way classification:

- columns in **both** (expected: the 17, minus any renames),
- columns **only in all-data** (the derived ~36: Date, Course, TEG-Round,
  Year, `*Cum*`, `*Avg*`, ranking/gap cols, Career Count …),
- columns **only in all-scores** (expected: none — **if any exist, flag
  loudly**, because it breaks the "all-data is a superset" assumption and
  changes the options appraisal).

### T1.2 — Value-identity check on shared columns (F2)

Join the two frames on the natural key (HoleID + Pl; verify uniqueness of
that key in both files first) and assert shared columns are value-identical.
Report row counts of each file, rows present in one but not the other, and
any cell-level mismatches (list them exhaustively if < 50, else summarise).

### T1.3 — Column-usage census (F3)

For each of the 53 all-data columns, grep the modern codebase
(`teg_analysis/`, `webapp/`) for usage (quoted column name; check bracket
access and `.get`). Classify: **used / used-only-via-aggregation /
apparently dead**. Do the same for all-scores' 17 columns across
`teg_analysis/analysis/data_update.py` and (read-only census, no edits)
`streamlit/`. Dead columns are candidates for dropping regardless of which
option wins — list them separately.

**Acceptance for Phase 1:** findings.md has F1–F3 filled in; every
"unexpected" result (extra all-scores columns, key collisions, value
mismatches, dead columns) is in a highlighted *Anomalies* list.

---

## 3. Phase 2 — Experiments (Sonnet)

Three small, isolated, read-only experiments. Output: findings.md sections
F4–F6 with method, numbers, and a one-paragraph interpretation each.

### T2.1 — Regeneration fidelity (F4)

Replicate `update_all_data`'s transform chain in a scratch script — call the
same functions it calls (`add_round_info`, `add_cumulative_scores`,
`add_rankings_and_gaps`, the Year derivation) on a frame read from
`data/all-scores.parquet`, **writing only to the scratch dir**. Diff the
result against the committed `data/all-data.parquet`: same shape, same
columns, value-equal (allow dtype-level tolerance, e.g. Int64 vs int64;
report any). This proves (or disproves) that all-data carries **zero
information not derivable** from all-scores + round_info + handicaps.
If the diff is not clean, characterise exactly what differs and why —
this is the single most decision-relevant fact in the investigation.

### T2.2 — Cost of deriving at load time (F5)

Time (a) `pd.read_parquet` of all-data as today, vs (b) read all-scores +
run the transform chain from T2.1 in memory. Report medians over ≥5 runs,
plus peak memory if easy. The dataset is ~6.4k rows, so the expectation is
that (b) is well under a second — but get the number; it decides whether
"derive on load" is free or needs a startup cache. Also note the webapp
already wraps `load_all_data` in `@lru_cache(maxsize=1)`
(`webapp/deps.py`), so the cost would be paid once per process/cache-clear.

### T2.3 — Load-time vs write-time enrichment map (F6)

Document precisely which enrichments happen where today: write-time
(`update_all_data`: Date, Course, TEG-Round, cumulatives, rankings, Year)
vs load-time (`load_all_data`: Area merge, TEG-50/incomplete filtering).
One table. This feeds the "where should enrichment live" part of the
recommendation and costs almost nothing given T2.1's work.

**Acceptance for Phase 2:** F4 states clean/dirty regeneration with
evidence; F5 has real timings; F6's table is complete.

---

## 4. Phase 3 — Options appraisal & recommendation (Opus)

Read findings F1–F6 end-to-end, then write the *Options* and
*Recommendation* sections of findings.md. Appraise at least these four
end-states (add others if the facts suggest one):

| | Option | Sketch | Key questions the facts must answer |
|---|---|---|---|
| **0** | Document & keep both | No storage change; make master→derived explicit in `DATA_FLOW.md`; optionally rename for clarity later | Is the confusion cost alone worth more than this? |
| **1** | Single stored master (all-scores); derive on load | Delete stored all-data + csv mirror; `load_all_data` runs the transform chain in memory (webapp lru_cache absorbs the cost) | F4 clean? F5 cheap? Breaks Streamlit's all-data reads + admin "View Processed Data" + sync/backup/catalog entries — enumerate every touchpoint |
| **2** | Single stored file (all-data); retire all-scores | Update flows write enriched all-data directly; raw = the 17-col subset | Requires reworking the add/delete/backup pipeline (higher risk than 1); breaks frozen Streamlit commentary loaders; is a stored derived file as master philosophically worse? |
| **3** | Minimal cleanup only | Keep both parquets; delete only the `all-data.csv` mirror (a third redundant copy); fix the Area/load-time inconsistency | Near-zero risk; can be combined with 0; does anything read the csv mirror? (census check) |

For each option: benefit, one-off cost (files/modules touched — name them),
ongoing cost, risk (data loss, prod breakage on Railway, Streamlit
breakage), and reversibility. Then make **one recommendation with
reasoning**, present it to Jon, and stop. Per CLAUDE.md rule 1: if the facts
genuinely don't discriminate, present the top two with a preferred pick —
do not implement anything.

Likely-decisive considerations to address explicitly (not conclusions —
things the write-up must cover): the master/derived split already works and
is documented in the catalog, so the real question is whether *two stored
copies + a csv mirror* earn their keep vs derive-on-load; how much weight to
give the frozen Streamlit app (reference-only vs must-keep-runnable); and
that any option touching stored files must sequence Railway volume +
GitHub store + backups together.

**Acceptance for Phase 3:** findings.md is complete and self-contained
(readable without re-running anything); a recommendation exists; the open
decision for Jon is stated in one sentence at the top.

---

## 5. Phase 4 — Implementation (GATED — do not start)

Only after Jon picks an option, in a fresh session, under a plan of its
own. Expected shape, whatever wins:

1. Sequence: code change → local verification (full webapp page sweep +
   `pytest tests/` — note `tests/test_data_loading.py` exists) → data-store
   change (volume + GitHub together) → doc updates (`DATA_FLOW.md`,
   `file_catalog.py`, `constants.py` docstring, `teg_analysis/README.md`).
2. Take manual timestamped backups of both parquets under `data/backups/`
   before any store change.
3. Model: Opus for pipeline changes (options 1/2 touch the add/delete flow —
   the highest-blast-radius code in the project); Sonnet for option 3 or the
   doc-only option 0.

## 6. Wrap-up (any model, end of Phase 3 or 4)

- Fold the outcome into `DATA_FLOW.md` §1 (replace the "Unresolved" note)
  and update `file_catalog.py` roles if they changed.
- Remove the "To investigate" entry in CLAUDE.md; record the decision in one
  line under Architecture.
- Delete `investigation_out/` and this file.
