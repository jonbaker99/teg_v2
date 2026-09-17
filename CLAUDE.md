# CLAUDE.md

Guidance for Claude Code and Codex CLI when working in this repository.

> **Freshness:** last reviewed **2026-08-19**. See [Keeping this file current](#keeping-this-file-current) at the bottom — it is an instruction, not a note.

## Working rules

1. **Ask when the answer changes the work.** Inspect available context first. Ask about choices that materially affect scope, behaviour, architecture or irreversible actions. Resolve routine implementation details independently. Record consequential assumptions briefly.
2. **Flag uncertainty explicitly.** If unsure, say so. Where useful, run a small, localised, low-risk experiment and bring the hypothesis and result back for discussion. Confidence without certainty does more damage than admitting a gap.
3. **Simplest thing that works.** Ask "what's the smallest change that solves this?" first. Reuse existing patterns and components. Add complexity only when it's needed now, not when it might be. Prefer focused changes over rewrites — unless a rewrite meaningfully simplifies the codebase, in which case propose it.
4. **Don't touch unrelated code** — but do surface bad code and design smells you find, as a separate item.
5. **Suggest better approaches.** Strategic alternatives welcome, not just tactical fixes.
6. **Documentation is part of the change**, not an afterthought. See [Documentation](#documentation).

## Model and delegation

Use a multi-model workflow by default. Skip it only when it is
clearly unnecessary for the task or the user requests another approach.

- **Plan:** A strong reasoning model inspects the project and defines
  the approach, acceptance criteria and relevant checks.
- **Implement:** Delegate scoped work to cheaper subagents. Use a
  balanced coding model for ordinary implementation and a fast,
  economical model for mechanical edits. Keep difficult or ambiguous
  work with a stronger model.
- **Review:** Use a strong model in a fresh review context to check
  the combined diff. The lead resolves findings and verifies completion.

Give workers clear scope, relevant context and file ownership.
Parallelise independent work; sequence dependent work.
Subagents must not overwrite the lead's session or recovery notes.

Choose models by capability and cost from currently available options.
Avoid version-specific model names in repository instructions or agent
configuration. Use supported tier aliases where available; otherwise
select an explicit worker model from the current available model list.

Do not require the user to request delegation or approve routine model
selection. Briefly report models used when completing delegated work,
not on every turn. If suitable models or delegation are unavailable,
state the limitation and use the best available approach.

### Claude Code-specific

Use `/model opusplan` for the lead workflow and
`.claude/agents/*.md` frontmatter for worker models.
Prefer tier aliases such as `opus`, `sonnet` and `haiku`.

### Codex-specific

Keep a strong model selected for the lead task.
Explicitly select cheaper models when spawning implementation subagents;
workers otherwise inherit the lead's model.
These instructions do not change the lead task's selected model.

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
- For copyable Markdown, use one source line per paragraph or bullet. Do not hard-wrap prose; let the editor wrap it visually.

When writing longer documents or reports, follow the focus-style skill.

## Project overview

TEG v2 is a golf tournament analysis project with two architectural layers: a legacy self-contained Streamlit app (frozen reference) and the current decoupled architecture — a UI-agnostic `teg_analysis/` package plus a `webapp/` FastAPI frontend, which is the site deployed on Railway from `main`. **All new analytical work belongs in `teg_analysis/`.**

## Domain knowledge

- A **TEG** is an annual golf tournament. Each consists of several rounds (usually 4), each 18 holes, split into front 9 (1–9) and back 9 (10–18).
- Two competitions per TEG: **gross** and **net**. Up to TEG 7, net was total net vs par; from TEG 8 onwards it is total Stableford points (`STABLEFORD_ERA_TEG = 8`).

## Where state lives

| Question | File |
|---|---|
| What's the current state / what shipped recently? | `STATUS.md` |
| What's outstanding? | `TODOS.md` (root index → per-area `TODOS.md`) |
| Full data pipeline (storage → I/O → loader → aggregation → webapp) | `DATA_FLOW.md` |
| **How a report gets from scores to the page** (both pipelines, one path) | `DATA_FLOW.md` → §10 *Report build* |
| Webapp stack, themes, design principles | `webapp/README.md` |
| Analysis package API | `teg_analysis/README.md` |
| Report/commentary pipeline | `teg_analysis/reporting/README.md` + `STATUS.md` |
| **Picking up report work in a new chat** | `teg_analysis/reporting/STATUS.md` → **START HERE** (goals, what changed and why, open workstreams) |
| How do I test/iterate on a report-pipeline element (voice, weights, structure)? | `teg_analysis/reporting/ARTEFACTS.md` |
| **How do I regenerate a report, or just part of one?** (which stages, what each costs, plan usage vs API) | `teg_analysis/reporting/README.md` → *Running only the stages you need* |
| Running reports on plan usage vs API billing; model comparisons | `teg_analysis/reporting/README.md` → *Who answers the prompts* |
| Streamlit internals (frozen) | `streamlit/README.md` |

Use this table as a lookup. Read only sources relevant to the current task; do not load every listed document at startup. Read more when dependencies or uncertainty justify it.

**Do not read or reference `to_do_jon.md`** unless explicitly asked. It is personal draft notes, not project documentation.

When a to-do surfaces mid-conversation, add it to the right area's `TODOS.md` before ending the session.

## Isolate agent work in task worktrees

- Every agent task that changes repository files must use a dedicated branch and Git worktree, including small code or documentation changes. Read-only work may inspect the existing checkout.
- Reserve the primary checkout for the user's manual work. Never edit files or switch branches there unless the user explicitly requests that exception.
- Before editing, establish the task's worktree, verify its absolute path and branch, and report both briefly. Run all edits, tests and Git commands from that worktree.
- Continue an existing task in its existing worktree. Start unrelated work in a new worktree. Switching between Claude Code and Codex does not create a new task.
- One lead agent owns each task worktree. Subagents receive its absolute path, branch and non-overlapping file assignments. They must verify their location before editing.
- Only the lead updates shared task notes, coordinates shared writes and performs Git mutations. Preserve unrelated dirty and untracked files.
- Never switch branches, reset, clean or remove another task's worktree. Do not merge into the primary checkout while the user is changing it; coordinate integration first.
- If relevant starting changes are uncommitted, preserve them and clarify which belong in the task. A new worktree does not automatically include them.

Worktree recovery setup and limitations: `README.md` → *Shared CLI recovery*.

## Active Context Tracking

- At startup, read `.current_session.md` and the recovery context supplied by project hooks. For a continuation request, inspect relevant diffs and continue the recorded next action. A new request takes precedence.
- Maintain concise task notes in `.current_session.md`: goal/scope and acceptance criteria, decisions and constraints, owned files, exact checks/results, unresolved issues, permissions already granted and immediate next action. Update at task start, after meaningful edits/tests or decisions, before lengthy work, and before ending. Record failures too; don't wait for a requested handoff.
- Hooks automatically save user requests, recent tool outcomes and Git state in `.agent-handoff/state.json`. These facts supplement task notes; they cannot infer decisions or prove completion. Unknown exit codes are not passing checks.
- Concurrent app instances use different ports. Worktrees do not isolate external services or writable data stores; inspect configuration and coordinate shared writes before running both.

## Development commands

```bash
python todos.py                      # outstanding to-dos (--all includes completed)
python3 scripts/agent_handoff.py install  # install shared CLI recovery hooks once
python3 scripts/agent_handoff.py show     # inspect recovery state without changing it
uvicorn webapp.app:app --reload      # run the webapp (the deployed app)
pip install -r requirements.txt      # install deps
python -m pytest tests/ -v           # run the test suite
streamlit run streamlit/nav.py       # legacy Streamlit app — frozen, rarely needed

pip install -r requirements-dev.txt          # dev-only extras (Playwright, for the PDF build)
python scripts/build_report_pdfs.py --all    # rebuild the downloadable report PDFs
python scripts/build_report_pdfs.py --check --all  # exit 1 if any PDF is out of date
```

The report PDFs (`data/commentary/pdfs/`) are a build artefact of the report
markdown **and** `webapp/static/newspaper_preview.css`. Change either and they
are stale — `--check` is what tells you. Rendering needs headless Chromium, so
`playwright` lives in `requirements-dev.txt` and must never be added to
`requirements.txt`, which drives the Railway build.

Report generation commands, stage selection, billing and mailbox hand-off: [Reporting README](teg_analysis/reporting/README.md#running-only-the-stages-you-need----from-and---to).

On the Claude-Code-on-the-web container, install pytest into the same interpreter as the deps: `pip install -r requirements.txt && pip install pytest` — bare `pytest` there is a `uv`-isolated binary that cannot see pip-installed deps.

## Architecture

Two distinct phases. **Streamlit is the original architecture** — self-contained, no longer deployed, not changing. **The decoupled architecture is the current direction.** Never conflate them: changes to `teg_analysis/` or `webapp/` must never touch `streamlit/`.

1. **`teg_analysis/`** — canonical, UI-agnostic analysis package. All new analytical work goes here. No frontend imports at module level.
   - `constants.py` — file paths, tournament metadata (see [Player identity](#player-identity) for the players caveat)
   - `io/` — file I/O (`read_file`/`write_file`), GitHub API (`GITHUB_TOKEN`), Railway volume management
   - `core/` — data loading (`load_all_data`) and transformation
   - `analysis/` — scoring, rankings, aggregation, streaks, records, eclectic, handicaps, commentary, pipeline, data_update, history, performance, leaderboards, bestball, live_round, round_setup, round_wizard
   - `display/` — formatting, HTML tables, scorecards, nav utilities. Returns HTML strings; never calls `st.write`
   - `reporting/` — LLM-powered tournament reports, plus a free, non-LLM PDF-rendering stage (`report_pdf.py`)
   - `api/` — placeholder for the REST API layer

2. **`streamlit/`** — the original app, self-contained via its own `utils.py`. **Dead code kept for reference only**: not deployed, not maintained, not migrated, and nothing else in the repo depends on it. Slated for deletion. Never modify it, and don't use it as a model for new work.

3. **`webapp/`** — FastAPI + HTMX + Jinja2 + Tailwind. Deployed on Railway from `main` via `railway.toml` → `uvicorn webapp.app:app`. `requirements.txt` is webapp-only (includes `pyarrow`). Needs `GITHUB_TOKEN` and a volume at `/mnt/data_repo`; `ANTHROPIC_API_KEY` for reports (`TEG_ANTHROPIC_API_KEY` is accepted as an alias), `GOOGLE_*` for data-update ingestion. The webapp only *reads* finished reports; it never generates them.

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

### Local Python can outrun Railway's

Keep the local interpreter in sync with the repo's `.python-version`. Before pushing Python changes, run `python scripts/check_python_compat.py`; it reads the pin and requires a matching interpreter on PATH. If the pin changes, verify the Python version actually installed in Railway's deploy log. Incident history and setup: [Webapp local environment](webapp/README.md#local-environment).

### Pandas strict dtypes

`requirements.txt` pins `pandas>=3.0,<4.0`. Three patterns have caused production errors — all fixed, but avoid reintroducing them (re-verified 2026-08-13 on 3.0.5, identical to 2.x behaviour).

**1. `DataFrame.applymap` is removed.** Use `.map(fn)`. Check: `grep -rn "\.applymap(" .`

**2. Assigning strings into an `int64`/`float64` column.** The leaderboard tied-rank pattern (`Rank` int + `=` suffix) raises even when the mask is all-False. Build the column as `str` from the start and guard with `.any()`: `df['Rank'] = df['Total'].rank(...).astype(int).astype(str)`, then `df.loc[dupes, 'Rank'] += '='` only when `dupes.any()` (webapp pattern, `webapp/deps.py`). On 3.x this comes back as Arrow-backed `str`, not `object` — don't assert `== object` on it.

**3. Assigning strings via `.iloc`/`.loc` positional setitem.** Both enforce the existing column dtype. Use named-column assignment instead: `df[col] = df[col].apply(fmt)`, not `df.iloc[:, 2] = ...`.

Check: `python scripts/check_pandas_compat.py` (detects `iloc-col-assign`). Fixed live-code sites: `teg_analysis/analysis/scoring.py`, `webapp/deps.py`.

> Change the pandas pin → re-verify these three and update this section. Pin lives in `requirements.txt`; leaving pandas unpinned is what let the deploy drift onto a new major line unnoticed, so keep the ceiling.

## Definition of done

Not a gate to run mechanically — a checklist to think against before calling work complete.

- Docs updated per the [table below](#documentation), same session.
- `STATUS.md` updated if the change is user-visible or shifts direction.
- Callers of any renamed or removed function checked; back-compat alias considered explicitly rather than by default.
- No frontend imports in `teg_analysis/`; no `streamlit/` file touched.
- **Run only the tests the change could plausibly break.** The full suite takes ~4 minutes; running it by reflex wastes the session and replaces thinking about blast radius.
  - **Nothing** for docs, comments, to-dos or `--help` text — running the command once is the test. **The relevant test file** for a module- or prompt-scoped change, picked by what imports the code you touched.
  - **The full suite only for a genuinely wide blast radius**: a shared/core module (`io/`, `core/`, `analysis/pipeline.py`, `deps.py`), a cross-module signature or schema, a dependency bump, or a merge touching code you also changed. **Merging alone is not a reason.** In doubt, ask — a line costs less than four minutes.
  - Say what you ran and why. Never re-run to feel sure. Suite: `python -m pytest tests/ -v` (web-container pytest caveat: see Development commands).

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


## Keeping this file current

This file has drifted before. Actively resist it. **On every session where you touch this file's subject matter:** if you find an instruction here that contradicts what the code actually does, **say so and propose the fix** rather than silently working around it. A stale instruction is a bug.

**Explicitly flag it when:**

- A capability change makes an instruction here unnecessary or inefficient — e.g. a workaround the tool now handles natively, or a manual ritual now automated.
- A pinned version, model name, or tool behaviour referenced here no longer matches reality.
- A section describes state (what's done, what's next) rather than durable instruction. State belongs in `STATUS.md`.
- Repeated rules, incident narratives or specialised recipes make this file harder to follow. Consolidate repetition and move detail into existing reference documents, keeping actionable rules here.
- The freshness date at the top is more than 6 months old.

**Quarterly (or when the above fires), run a review:** ask Claude to check each section of this file against the codebase and against current Claude Code capabilities, and report contradictions, dead references and obsolete workarounds. Update the freshness date when done.
