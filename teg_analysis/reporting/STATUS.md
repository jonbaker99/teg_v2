# Reporting — Status & Next Steps

**Pick-up ledger.** Read this first when resuming work in a fresh session. The how-it-works architecture is in [README.md](README.md); the full design rationale (interviews, A/B decisions, stress tests) lives in the user's plan file at `~/.claude/plans/i-want-to-review-peaceful-pie.md`.

## Done — production-ready

### Stages 1–5 all built and validated

| | Stage | Module / function |
|---|---|---|
| ✅ | 1 — record | reuses `teg_analysis.core.data_loader.load_all_data` |
| ✅ | 2 — notable-event detection + 3-axis scoring | `events.py`, `scoring.py` |
| ✅ | 2 — competition arcs (Trophy / Jacket / Spoon) | `events._competition_arcs` |
| ✅ | 2 — venue context | `venue.py` + `data/course_info.csv` |
| ✅ | 3 — story plan (LLM, structured) | `story_plan.py`, `llm.py` |
| ✅ | 4a — dry storyline draft | `authoring.generate_dry_draft` |
| ✅ | 4b — entertaining report (around-draft) | `authoring.report_around_draft` |
| ✅ | 4b — repetition lint | `authoring.repetition_lint` |
| ✅ | 5 — CSS-class styling renderer | `render.apply_styling` / `render.style_report` |

### Validated production reports
- **TEG 9** — procession with R4 brief jeopardy (initial validation case)
- **TEG 14** — tight 2-pt finish, multi-course (stress test for tight finishes + cross-course holes)
- **TEG 18** — most recent, blowout with Jacket-leader → Spoon-winner subplot

All three live at `data/commentary/teg_{9,14,18}_report_final.md` (clean MD) and `..._report_styled.md` (with CSS hooks).

### Editorial fixes already applied at source
- Player names proper-cased when assembling beats (no all-caps surnames in prose).
- `Outright` vs `level` lead-change distinction (per-hole rank-1 count check); level changes downweighted in scoring.
- Each `NotableEvent` carries its `course`; prompt guards in `WRITER_SYSTEM` and `DRY_DRAFT_SYSTEM` forbid "same hole" across rounds.
- Early-round lead changes downweighted; prompts state "opening jockeying is routine, not chaos".
- Winner margins computed against the runner-up (the legacy `Margin_*` column was 0 for the winner, which produced a factual error in the old report).

### A/B decision (TEG-9 prototype)
- **Chosen**: A — around-draft + repetition lint. Most faithful (bounded by the validated dry draft), still reads well.
- *Rejected — single-pass (B)*: good but slightly more freewheeling; loses the QA scaffold.
- *Rejected — critique-revise (C)*: best polish, but the extra pass fabricated a "countback" detail. Too risky for an insider audience.

### UI wiring (both surfaces)
- **Webapp (user's preferred surface)**: `/teg-reports` page + `/results` Report tab — `webapp/routes/reports.py`, `webapp/templates/teg_reports.html`, `webapp/static/teg_reports.css`, plus the `_results_context()` "report" branch in `webapp/routes/history.py`.
- **Streamlit (legacy, still works)**: `streamlit/teg_reports.py` prefers the new styled MD, falls back to `teg_N_main_report.md`. Nav re-enabled in `streamlit/page_config.py`.

### Cost & environment
- ~**$0.65 per report** on Opus 4.7. The story-plan call (~$0.28) dominates because the ~19k-token beats bundle is user-message-side and can't be cached.
- API key: `ANTHROPIC_API_KEY` env var, else `.streamlit/secrets.toml` at the repo root.
- Run with `venv/bin/python` — has anthropic + markdown + (now) fastapi/uvicorn/jinja2/starlette/httpx.

## Deferred / next work

| Item | Notes |
|---|---|
| **5b — Strict round-by-round variant** | Second renderer/prompt that emits a chronological per-round version from the same story plan (no theme weaving). Uses the existing Stage-5 styling pipeline. |
| **5c — Modes (fast vs archive)** | `mode='fast'` skips the dry draft and uses single-pass authoring (approach B) — cheaper, faster, for post-round write-ups. `mode='archive'` is the current default (full chain) — pauses to let a human edit the story plan if desired. Add as a `mode=` argument to a top-level orchestrator function. |
| **5d — Scale to all TEGs** | Use Anthropic's Batch API (50% off, 24h SLA, identical output) for the archive backfill. Pair with bundle trim (send only top-N scored beats to the story-plan call) as the headline cost-saving lever. |
| **Pre-TEG-8 net-vs-par Trophy metric** | The Trophy was total net-vs-par for TEGs 1–7 (Stableford only from TEG 8). The pipeline currently hardcodes Stableford as the Trophy metric everywhere (`events.py` arcs + scoring). Pre-8 reports would misrepresent the Trophy standings — **must be fixed before any pre-8 backfill.** |
| **Light faithfulness-check pass** | Optional final guard that programmatically verifies prose claims against the data. Two writer-drift incidents to date — critique-revise fabricated "countback"; around-draft fabricated a "same hole across courses" rhyme on TEG 14 (now blocked by per-beat `course` + a prompt rule, but a verifier would catch the next class of drift). Useful insurance for scale. |

## Known issues / gotchas
- **Pre-TEG-8 Trophy is on the wrong metric** until net-vs-par handling is added. The "Done" reports above (TEGs 9, 14, 18) are all post-8 so this doesn't affect them.
- **The isolated `venv/` (Python 3.14) hits a jinja2/starlette template-cache bug** (`TypeError: cannot use 'tuple' as a dict key`) on every templated route. Visual webapp verification needs Python 3.12/3.13, or wait for a fixed jinja2/starlette release.
- **MCP/CSS coupling between streamlit and webapp**: `teg_reports.css` is duplicated in `streamlit/styles/` and `webapp/static/`. Edits must be kept in sync (or, later, consolidated into a shared location). Streamlit is deferred but still wired.

## How to pick up in a clean session
1. Read this file (top to bottom) — five minutes.
2. Skim [README.md](README.md) for the architecture refresher — five more.
3. Decide which deferred item to start on. Suggested order: **5b** (round-by-round, easy) → **5c** (modes, easy) → **pre-8 net-vs-par metric** (medium, needed before pre-8 backfill) → **5d** (scale + Batch API).
4. Sanity-test any change by regenerating **TEG 14** — it's the trickiest validated case (tight finish, multiple courses, the kind of pattern the writer wants to fabricate into a "rhyme") and any regression there will show.
