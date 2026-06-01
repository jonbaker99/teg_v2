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
- **Narrative structure freedom (Step 1)**: `StoryPlan` carries `narrative_structure` (`chronological` / `in_medias_res` / `theme_led`) and `opening_hook` fields; `WRITER_SYSTEM` has a STRUCTURE rule granting reorder licence. TEG 14 under Step 1 opens *in medias res* on Mullin's R4 quad and resolves the "same hole / different course" temptation explicitly. Baselines preserved at `teg_14_report_baseline.md` (chronological) and `teg_14_report_step1.md` (Step 1 only).
- **Dry-draft density A/B (Step 2)**: `DRY_DRAFT_SYSTEM` was lightened to be narrative-structure-aware and selective with hole detail. Tested across TEGs 9, 14, 18 → user verdict: **detailed wins**. Detailed floors the worst case (TEG 14 light was materially drier); light occasionally edges on voice but loses hole-level specificity the insider audience wants. **Default flipped to `dry_draft_style="detailed"`** in `generate_dry_draft`; light remains available as a kwarg (useful for fast/post-round mode). Investigation outputs preserved at `data/commentary/teg_{9,14,18}_report_{detailed,light,pre_detailed_baseline}.md`.

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

## Active agenda — pre-backfill (current focus)

Four sequenced phases before bulk backfill:

| Phase | What | Estimated |
|---|---|---|
| **A. Easy cost levers** | Lint on Haiku 4.5 (`model="claude-haiku-4-5"` on `repetition_lint`). Bundle trim to top-N beats with `top_n=50` arg on `story_plan.assemble_bundle`, **always preserving `must_include` ids and `competition_arcs`**. | ~30 min dev; saves ~$0.12/report. |
| **B. Per-round standings + player closing** | (1) New `build_round_standings(teg)` in `render.py` returning per-round Trophy / Green Jacket standings markdown using `create_round_summary`; `apply_styling` injects each block before the next `## ` heading. Deterministic — no LLM. (2) Add non-negotiable closing rule to `WRITER_SYSTEM`'s STRUCTURE block requiring 4–6 player-by-player bullets. | ~45 min dev; zero new LLM calls. |
| **C. Round-report prototype on TEG 14 R1** | New `round_report.py` with `RoundStoryPlan` schema and round-focused `ROUND_PLAN_SYSTEM` / `ROUND_DRY_DRAFT_SYSTEM` / `ROUND_WRITER_SYSTEM` prompts. Reuse `build_notable_events(teg)` filtered to `round`. Decision: does it need round-level scoring weights? Standalone-readable? | ~1–2 h dev + ~$0.40. |
| **D. Unified backfill** | `dry_draft_style` switch DONE (default = `"detailed"` after the 9/14/18 A/B). Generate one tournament report per TEG for 11 post-8 TEGs (8–18, refreshing 9/14/18). If (C) clean, also 4 round reports/TEG. | ~$5.50 tournament only; ~$20 with rounds. ~30 min – 2 h run. |

## Deferred (after the active agenda)

| Item | Notes |
|---|---|
| **5b — Strict round-by-round tournament variant** | Different from C: a *tournament* report rendered strictly chronologically (no theme weaving) — alternative format from the same story plan. |
| **5c — Modes (fast vs archive)** | `mode='fast'` skips the dry draft and uses single-pass authoring (approach B) — cheaper for post-round write-ups. `mode='archive'` = current full chain. Add as a `mode=` arg to a top-level orchestrator. |
| **5d — Batch API wrapper** | Use Anthropic's Batch API (50% off, 24h SLA, identical output) for any future archive runs. Bigger saver than the easy levers but ~1–2 h of staged-batch wrapper code. |
| **Pre-TEG-8 net-vs-par Trophy metric** | The Trophy was total net-vs-par for TEGs 1–7 (Stableford only from TEG 8). The pipeline currently hardcodes Stableford as the Trophy metric everywhere (`events.py` arcs + scoring). Pre-8 reports would misrepresent the Trophy standings — **must be fixed before any pre-8 backfill.** |
| **Light faithfulness-check pass** | Optional final guard that programmatically verifies prose claims against the data. Two writer-drift incidents to date — critique-revise fabricated "countback"; around-draft fabricated a "same hole across courses" rhyme on TEG 14 (now blocked by per-beat `course` + a prompt rule, but a verifier would catch the next class of drift). Useful insurance for scale. |

## Known issues / gotchas
- **Pre-TEG-8 Trophy is on the wrong metric** until net-vs-par handling is added. The "Done" reports above (TEGs 9, 14, 18) are all post-8 so this doesn't affect them.
- **The isolated `venv/` (Python 3.14) hits a jinja2/starlette template-cache bug** (`TypeError: cannot use 'tuple' as a dict key`) on every templated route. Visual webapp verification needs Python 3.12/3.13, or wait for a fixed jinja2/starlette release.
- **MCP/CSS coupling between streamlit and webapp**: `teg_reports.css` is duplicated in `streamlit/styles/` and `webapp/static/`. Edits must be kept in sync (or, later, consolidated into a shared location). Streamlit is deferred but still wired.

## How to pick up in a clean session
1. Read this file (top to bottom) — five minutes.
2. Skim [README.md](README.md) for the architecture refresher — five more.
3. **The active agenda above is the next work** — sequenced A → B → C → D. Start at whatever phase isn't ticked off yet; the table is intentionally linear.
4. Sanity-test any change by regenerating **TEG 14** — it's the trickiest validated case (tight finish, multiple courses, the kind of pattern the writer wants to fabricate into a "rhyme") and any regression there will show. Baselines preserved at `data/commentary/teg_14_report_baseline.md` and `..._step1.md` for comparison.
