# TEG v2

Golf tournament analysis for the TEG (The El Golfo) group. TEG is both the name of the group and each annual tournament event — so "TEG 17" means the 17th tournament. Tracks scores, records, streaks, and standings across 17+ annual tournaments with 7 players.

## Architecture: old vs new

The project has evolved through two phases:

**Phase 1 — Streamlit (original, stable):** All analysis and UI live together in the `streamlit/` folder. This is deployed on Railway and working. It is intentionally self-contained — changes to the rest of the codebase do not affect it, and it will not be migrated.

**Phase 2 — Decoupled (current direction):** Analysis logic has been extracted into `teg_analysis/`, a UI-agnostic Python package. This is the source of truth for all analytical work — it can be called from a webapp, a REST API, a Jupyter notebook, or any other frontend. The new `webapp/` frontend is being built on top of it.

The key principle: **`teg_analysis/` owns the analysis; frontends are interchangeable.**

## What's here

1. **`streamlit/`** -- The original Streamlit dashboard, deployed on Railway. Self-contained; not changing.

2. **`teg_analysis/`** -- The UI-agnostic analysis package. The canonical source for all TEG data, scoring, records, and statistics. Use this for any new analytical work.

3. **`webapp/`** -- New frontend (FastAPI + HTMX + Jinja2). Calls `teg_analysis/` for all data. **Now deployed on Railway from `main`** (replacing the Streamlit app), with `railway.toml` running `uvicorn webapp.app:app`.

## Quick start

```bash
# Install dependencies
pip install pandas numpy pyarrow plotly PyGithub

# Verify the analysis package works
python -c "
from teg_analysis.core.data_loader import load_all_data
df = load_all_data()
print(f'{len(df)} rows, {df.TEGNum.nunique()} TEGs, {df.Player.nunique()} players')
"

# Run the Streamlit app (needs: pip install -r requirements.txt)
streamlit run streamlit/nav.py

# Run the webapp (needs: pip install fastapi uvicorn jinja2)
uvicorn webapp.app:app --reload
# Then visit http://localhost:8000

# Open the ad-hoc analysis quickstart notebook (needs: pip install jupyter)
jupyter notebook ad_hoc_analysis/quickstart.ipynb
```

## Development reference

```bash
# View outstanding to-dos across the project
python todos.py          # outstanding items only
python todos.py --all    # include completed items too
```

See [TODOS.md](TODOS.md) for the central to-do index. Each area (`webapp/`, `streamlit/`, `teg_analysis/`) has its own `TODOS.md` file for working details.

## Shared CLI recovery

Claude Code and Codex share `AGENTS.md` → `CLAUDE.md`. Project hooks save requests,
recent tool outcomes and Git state automatically in `.agent-handoff/state.json`.
Agents keep goals, decisions, check results and the next action in `.current_session.md`.
Both files are local and ignored by Git. Startup loads recovery context without
replacing the previous agent's checkpoint, including when no final reply exists.

```bash
# Install hooks and improved zsh shortcuts once; keep a ~/.zshrc backup
python3 scripts/agent_handoff.py install --shell

# Inspect recovery context without changing it
python3 scripts/agent_handoff.py show
```

Restart the CLIs after setup. In Codex, open `/hooks` and trust the new project
hooks once; changed hook definitions need review again. Untrusted hooks are
skipped. Claude project hooks require the usual trusted workspace. Existing
global sound/notification hooks remain in place.
[Codex hook trust](https://learn.chatgpt.com/docs/hooks),
[Claude hook configuration](https://code.claude.com/docs/en/hooks).

Run `install --shell` from the durable checkout, not a disposable task worktree.
The optional `--shell` setup loads `scripts/agent_handoff.zsh` last in `~/.zshrc`,
overriding the old shortcut functions. It preserves existing setup and saves
`.zshrc.teg-agent-handoff.bak` before its first change. Open a new shell or source
`scripts/agent_handoff.zsh` to load the replacements into an existing shell.
Without `--shell`, only project hooks are installed. `install --dry-run --shell`
lists proposed configuration targets without writing them.
Symlinked configuration files are rejected so managed dotfile targets stay intact.

Run `to-codex` or `to-claude` from the task worktree to continue unfinished work.
Commit the recovery scripts, shared rules and project hook configuration before
creating new worktrees: a worktree created from a commit does not include this
checkout's uncommitted setup. Review/trust hooks in each new workspace as needed.
Ordinary CLI startups also receive recovery context; a new user request takes
precedence over old notes. Use one writer per worktree. The JSON lock protects
checkpoint writes, not application files. Keep the original worktree: snapshots
record state but do not back up contents or transfer work to another machine.

Recovery uses no model calls. It saves after local tool events and captures Claude
API failures through `StopFailure`; Codex recovery uses the checkpoint already
saved before an error. Abrupt termination can lose events not yet delivered.
Agents must save decisions during work. Checks remain historical until assessed
against relevant diffs; unknown exit codes never mean success. Switching CLIs
remains manual. Automatic quota-triggered launching is a separate backlog item.

The isolated recovery checks use only Python's standard library:
`python3 -m unittest tests.test_agent_handoff -v`.

Inside the analysis package (the top-level map is the [folder guide](#folder-guide) below):

```
teg_analysis/
  constants.py       File paths, tournament metadata
  io/                File I/O, GitHub API, Railway volume management
  core/              Data loading and transformation
  analysis/          Scoring, rankings, aggregation, streaks, records, handicaps,
                     eclectic, pipeline, data update, live round, leaderboards
  display/           Formatting, HTML tables, scorecards, navigation utilities
  reporting/         LLM-powered tournament reports
  api/               (Placeholder for REST API endpoints)
```

## Folder guide

| Directory / File | Purpose |
|---|---|
| `teg_analysis/` | Standalone analysis package — io, core, analysis, display, api layers. See `teg_analysis/README.md` |
| `webapp/` | FastAPI + HTMX frontend — **the deployed site** (Railway, from `main`). See `webapp/README.md` |
| `streamlit/` | Legacy Streamlit app — **frozen reference, no longer deployed.** See `streamlit/README.md` |
| `data/` | Tournament data files (parquet, CSV) + generated reports in `data/commentary/` — see `teg_analysis/reporting/ARTEFACTS.md` for what each report file is |
| `ad_hoc_analysis/` | Jupyter notebooks for exploratory / one-off analysis |
| `scripts/` | Standalone maintenance and experiment scripts. `export_cowork_kit.py` (report-writing kit for rewriting outside the pipeline), `humour_dial.py`, `check_pandas_compat.py` |
| `scripts/agent_handoff.py`, `scripts/agent_handoff.zsh` | Shared Claude/Codex CLI recovery hooks, installer and continuation shortcuts |
| `tests/` | Test suite for `teg_analysis` |
| `examples/` | FastAPI proof-of-concept |
| `prompts/` | Saved prompt text for one-off work. Not read by any code |
| `reference/` | Reference material, including report images |
| `CLAUDE.md`, `AGENTS.md` | Shared development rules for Claude Code and Codex; `AGENTS.md` symlinks to `CLAUDE.md` |
| `DATA_FLOW.md` | Data pipeline reference guide |

## Current status

The `webapp/` (FastAPI) is **deployed on Railway from `main`** and has replaced the Streamlit app as the live site; `railway.toml` runs `uvicorn webapp.app:app` and `requirements.txt` is webapp-only (with `pyarrow` for the parquet reads). The Streamlit app remains in `streamlit/` as the stable legacy reference but is no longer the deployed site. The `teg_analysis` package powers the webapp and is gaining a headless data-update pipeline (`teg_analysis/analysis/data_update.py`) so data management is no longer Streamlit-only.

See [CLAUDE.md](CLAUDE.md) for current work priorities and architecture decisions. See folder-level READMEs (`teg_analysis/README.md`, `webapp/README.md`, `streamlit/README.md`) for each component.
