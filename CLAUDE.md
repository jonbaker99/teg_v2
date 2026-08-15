# CLAUDE.md

Guidance for Claude Code when working in this repository.

> **Freshness:** last reviewed **2026-08-11**. See [Keeping this file current](#keeping-this-file-current) at the bottom — it is an instruction, not a note.

## Working rules

1. **Ask, don't assume.** If intent, architecture or requirements are unclear, ask before writing code. Running unattended: pick the most reasonable interpretation, proceed, and record the assumption where the work is reported.
2. **Flag uncertainty explicitly.** If unsure, say so. Where useful, run a small, localised, low-risk experiment and bring the hypothesis and result back for discussion. Confidence without certainty does more damage than admitting a gap.
3. **Simplest thing that works.** Ask "what's the smallest change that solves this?" first. Reuse existing patterns and components. Add complexity only when it's needed now, not when it might be. Prefer focused changes over rewrites — unless a rewrite meaningfully simplifies the codebase, in which case propose it.
4. **Don't touch unrelated code** — but do surface bad code and design smells you find, as a separate item.
5. **Suggest better approaches.** Strategic alternatives welcome, not just tactical fixes.
6. **Documentation is part of the change**, not an afterthought. See [Documentation](#documentation).

## Response style

- **Lead with the answer**. No preamble, no restating the question.
- **Default to under 150 words** unless I ask for depth.
- **Sentences under 20 words**. Short words over long ones.
- **One idea per paragraph**, max three lines.
- **Bullets for parallel items, prose for connected reasoning.** Don't bullet everything.
- Bold only conclusions or labels, never whole sentences.
- **Headings state the point**, not the category.
- A closing summary is welcome when it adds a decision or next step. Not when it just repeats.
- Cut: "Great question", stacked hedges, unsolicited offers of further help.
Never cut a fact to hit a word count. Accuracy beats brevity.

When writing longer documents or reports, follow the focus-style skill.

## Project overview

TEG v2 is a golf tournament analysis project with two architectural layers: a legacy self-contained Streamlit app (frozen reference) and the current decoupled architecture — a UI-agnostic `teg_analysis/` package plus a `webapp/` FastAPI frontend, which is the site deployed on Railway from `main`. **All new analytical work belongs in `teg_analysis/`.**

## Domain knowledge

- A **TEG** is an annual golf tournament. Each consists of several rounds (usually 4), each 18 holes, split into front 9 (1–9) and back 9 (10–18).
- Two competitions per TEG: **gross** and **net**. Up to TEG 7, net was total net vs par; from TEG 8 onwards it is total Stableford points (`STABLEFORD_ERA_TEG = 8`).

## Where state lives — read these, don't duplicate them here

| Question | File |
|---|---|
| What's the current state / what shipped recently? | `STATUS.md` |
| What's outstanding? | `TODOS.md` (root index → per-area `TODOS.md`) |
| Full data pipeline (storage → I/O → loader → aggregation → webapp) | `DATA_FLOW.md` |
| Webapp stack, themes, design principles | `webapp/README.md` |
| Analysis package API | `teg_analysis/README.md` |
| Report/commentary pipeline | `teg_analysis/reporting/README.md` + `STATUS.md` |
| **Picking up report work in a new chat** | `teg_analysis/reporting/STATUS.md` → **START HERE** (goals, what changed and why, open workstreams) |
| How do I test/iterate on a report-pipeline element (voice, weights, structure)? | `teg_analysis/reporting/ARTEFACTS.md` |
| Moving report generation off API billing onto claude.ai plan usage | `teg_analysis/reporting/API_TO_PLAN_USAGE.md` |
| Streamlit internals (frozen) | `streamlit/README.md` |

**Do not read or reference `to_do_jon.md`** unless explicitly asked. It is personal draft notes, not project documentation.

When a to-do surfaces mid-conversation, add it to the right area's `TODOS.md` before ending the session.

## Development commands

```bash
python todos.py                      # outstanding to-dos (--all includes completed)
uvicorn webapp.app:app --reload      # run the webapp (the deployed app)
pip install -r requirements.txt      # install deps
python -m pytest tests/ -v           # run the test suite
streamlit run streamlit/nav.py       # legacy Streamlit app — frozen, rarely needed
```

> On the Claude-Code-on-the-web container, install pytest into the same interpreter as the deps: `pip install -r requirements.txt && pip install pytest`.

## Architecture

Two distinct phases. **Streamlit is the original architecture** — self-contained, no longer deployed, not changing. **The decoupled architecture is the current direction.** Never conflate them: changes to `teg_analysis/` or `webapp/` must never touch `streamlit/`.

1. **`teg_analysis/`** — canonical, UI-agnostic analysis package. All new analytical work goes here. No frontend imports at module level.
   - `constants.py` — file paths, tournament metadata (see [Player identity](#player-identity) for the players caveat)
   - `io/` — file I/O (`read_file`/`write_file`), GitHub API (`GITHUB_TOKEN`), Railway volume management
   - `core/` — data loading (`load_all_data`) and transformation
   - `analysis/` — scoring, rankings, aggregation, streaks, records, eclectic, handicaps, commentary, pipeline, data_update, history, performance, leaderboards, bestball, live_round, round_setup, round_wizard
   - `display/` — formatting, HTML tables, scorecards, nav utilities. Returns HTML strings; never calls `st.write`
   - `reporting/` — LLM-powered tournament reports
   - `api/` — placeholder for the REST API layer

2. **`streamlit/`** — the original app, self-contained via its own `utils.py`. **Dead code kept for reference only**: not deployed, not maintained, not migrated, and nothing else in the repo depends on it. Slated for deletion. Never modify it, and don't use it as a model for new work.

3. **`webapp/`** — FastAPI + HTMX + Jinja2 + Tailwind. Deployed on Railway from `main` via `railway.toml` → `uvicorn webapp.app:app`. `requirements.txt` is webapp-only (includes `pyarrow`). Needs `GITHUB_TOKEN` and a volume at `/mnt/data_repo`; `ANTHROPIC_API_KEY` for reports (`TEG_ANTHROPIC_API_KEY` is accepted as an alias), `GOOGLE_*` for data-update ingestion. **Report generation currently bills per API call, separately from any claude.ai plan** — moving it onto plan usage is an open workstream, see `teg_analysis/reporting/API_TO_PLAN_USAGE.md`.

4. **`ad_hoc_analysis/`** — Jupyter notebooks calling `teg_analysis/` directly. Start at `quickstart.ipynb`.

**Data storage decision (2026-07-07):** Railway volume + GitHub-commit-as-sync-of-record is kept deliberately (not a database) — at this dataset size it gives atomic-commit audit trail, off-host durability and local-Mac sync for free. `all-data.parquet`/`all-scores.parquet` are master → derived, not two independent sources; the redundant `all-data.csv` mirror was retired — **don't reintroduce it.** Rationale and phased plan: `DATA_STORAGE_INGESTION_PLAN.md`.

## Codebase invariants

Rules that hold regardless of what you're working on. Breaking any of these has caused a production incident.

### Player identity

`data/players.csv` (Code, Name) is the **writable source of truth** for who exists. `constants.PLAYER_DICT` is only a legacy seed/fallback — **never read it directly in new code.** All code→name lookups go through `teg_analysis.core.players.get_player_dict()` (cached; call `clear_player_cache()` after writes — `webapp.deps.clear_all_data_caches` does this). New players are added via `/admin/teg-setup`, which appends to `players.csv`; their `handicaps.csv` column is created the first time they're saved onto a TEG roster.

### No frontend imports in `teg_analysis/`

Enforced by a test guard. `teg_analysis/` must import cleanly with no UI package installed.

### Pipelines fail loudly

`update_*_cache` functions take `all_data` and raise on failure; orchestrators collect them into a `cache_errors` field via `_run_cache_step` and surface an admin warning banner (`analysis/data_update.py`, `analysis/pipeline.py`). Never report a stale cache as success.

`process_round_for_all_scores` has exactly one implementation — canonical in `data_update.py`, thin re-export in `core/data_loader.py`. Don't fork it.

### Live-round writes are validated server-side

`apply_score_writes` / `apply_admin_edits` validate score range (`MAX_SCORE = 20`), hole 1–18 and roster membership. The server — never a client clock — assigns write order. Don't add a write path that bypasses these.

### Webapp route handlers are sync `def`

FastAPI threadpools them. `async def` handlers doing blocking work stall every polling phone. Use `async def` only to read a dynamic-keyed form, and wrap the heavy call in `run_in_threadpool`. See `webapp/README.md` → "Sync `def` handlers".

### Pandas strict dtypes

`requirements.txt` pins `pandas>=3.0,<4.0`. Three patterns have caused production errors — all fixed, but avoid reintroducing them. All three behave **identically on 3.x as on 2.x** (re-verified 2026-08-13 on 3.0.5), so the guidance below is unchanged by the pin; only the version label was wrong.

**1. `DataFrame.applymap` is removed.** Use `.map(fn)`. Check: `grep -rn "\.applymap(" .`

**2. Assigning strings into an `int64`/`float64` column.** The leaderboard tied-rank pattern (`Rank` int + `=` suffix) raises even when the mask is all-False. Convert to `object` first, or build the column as `str` from the start and guard with `.any()`. Both still work on 3.x; note that on 3.x the string-first column comes back as the new Arrow-backed `str` dtype rather than `object`, which is fine here but means **don't assert `== object` on a string column**:

```python
# object-first
df['Rank'] = df['Total'].rank(method='min', ascending=asc).astype(int).astype(object)
df.loc[dupes, 'Rank'] = df.loc[dupes, 'Rank'].astype(str) + '='

# string-first (webapp pattern, see webapp/deps.py)
df['Rank'] = df['Total'].rank(method='min', ascending=asc).astype(int).astype(str)
if dupes.any():
    df.loc[dupes, 'Rank'] = df.loc[dupes, 'Rank'] + '='
```

**3. Assigning strings via `.iloc`/`.loc` positional setitem.** Both enforce the existing column dtype. Use named-column assignment, which replaces the column wholesale:

```python
col = df.columns[2]                      # not df.iloc[:, 2] = ...
df[col] = df[col].apply(fmt)
```

Check: `python scripts/check_pandas_compat.py` (detects the `iloc-col-assign` pattern). Live-code sites previously fixed: `teg_analysis/analysis/scoring.py`, `webapp/deps.py` (already uses string-first). The rest of the historical fixes were in frozen `streamlit/` files.

> If you change the pandas pin, re-verify these three and update this section — don't leave guidance for a version you no longer run. The pin lives in `requirements.txt`; **leaving pandas unpinned is what let the deploy drift onto a new major line unnoticed**, so keep the ceiling.

## Definition of done

Not a gate to run mechanically — a checklist to think against before calling work complete.

- Docs updated per the [table below](#documentation), same session.
- `STATUS.md` updated if the change is user-visible or shifts direction.
- Callers of any renamed or removed function checked; back-compat alias considered explicitly rather than by default.
- No frontend imports in `teg_analysis/`; no `streamlit/` file touched.
- Tests run where the change plausibly affects behaviour — your judgement on when that's warranted. Test suite: `python -m pytest tests/ -v` (bare `pytest` fails on the Claude-Code-on-the-web container, where it's a `uv`-isolated binary that can't see pip-installed deps).

## Documentation

**Rule 1 — always maintain documentation.** When you add, rename or remove a data file, function, module or layer, update the relevant doc in the same session. Never leave docs describing something that no longer exists.

**Rule 2 — each file has one role; content lives in exactly one place.**

| File | Owns | Does not contain |
|---|---|---|
| `README.md` | Public entry point — what it is, how to run, folder map | Deep detail; current state beyond one line |
| `CLAUDE.md` | Durable instructions for Claude — architecture, invariants, conventions | Subfolder detail; current state; changelog |
| `STATUS.md` | Current state, recent work, next priorities | Instructions or architecture |
| `DATA_FLOW.md` | Full data pipeline reference | Per-subfolder loading patterns |
| `teg_analysis/README.md` | Package API — functions, data levels, constraints | Pipeline or webapp detail |
| `streamlit/README.md` | Streamlit internals | Anything outside `streamlit/` |
| `webapp/README.md` | Webapp stack, themes, design principles | Anything outside `webapp/` |

Root docs cover the whole project; L1 subfolder READMEs cover only that subfolder.

**Rule 3 — new `.md` files** only when the content is genuinely too large or specialised for an existing README, or it's a temporary working doc (plan, spike notes) — which must be deleted or consolidated when the work is done. Prefer a new section over a new file. Permanent new files go in the `README.md` folder guide. Split files that grow unwieldy; one clear topic per file.

**When to update which file**

| Change | Update |
|---|---|
| New module or layer in `teg_analysis/` | This file's Architecture + `teg_analysis/README.md` |
| New webapp page area or pattern | `webapp/README.md` |
| Data file added, renamed or removed | `DATA_FLOW.md` Storage Layer |
| New development command | This file's Development commands + `README.md` |
| Architecture decision | This file's Architecture |
| Work completed / priorities changed | `STATUS.md` |

## Model and delegation

Model selection is handled by `/model opusplan` and by `.claude/agents/*.md` frontmatter — **not by instructions in this file.** Two rules only:

- **Never pin a model version string** anywhere in this repo's docs or config. Use aliases (`opus`, `sonnet`, `haiku`, `default`), which track the current model for each tier.
- **Prefer delegating to a subagent over switching models** — especially for broad searches where only the conclusion is needed, and for reviewing work you just did (fresh context, not a continuation).

If a task turns out to be a poor fit for the current model, say so in one line rather than pressing on. Don't emit a model-check block on every turn.

## Keeping this file current

This file has drifted before. Actively resist it.

**On every session where you touch this file's subject matter:** if you find an instruction here that contradicts what the code actually does, **say so and propose the fix** rather than silently working around it. A stale instruction is a bug.

**Explicitly flag it when:**

- A capability change makes an instruction here unnecessary or inefficient — e.g. a workaround the tool now handles natively, or a manual ritual now automated.
- A pinned version, model name, or tool behaviour referenced here no longer matches reality.
- A section describes state (what's done, what's next) rather than durable instruction. State belongs in `STATUS.md`.
- This file exceeds ~200 lines. That's the point where adherence degrades. Move something out.
- The freshness date at the top is more than 6 months old.

**Quarterly (or when the above fires), run a review:** ask Claude to check each section of this file against the codebase and against current Claude Code capabilities, and report contradictions, dead references and obsolete workarounds. Update the freshness date when done.