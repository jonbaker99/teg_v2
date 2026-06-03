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

## Active agenda — phases A–G

Phases A → G build the canonical post-8 pipeline and an era-aware pre-8 path. Phases A–E and G's code are complete; Phase F's backfill is partial; Phase G's backfill is deferred.

| Phase | What | Status |
|---|---|---|
| **A. Easy cost levers** | Haiku 4.5 lint; bundle trim to top-N=50 (preserves mandatory beats). | DONE. |
| **B. Per-round standings + player closing** | Deterministic `build_round_standings` injection; non-negotiable closing rule for tournament reports. | DONE. |
| **C. Round-report prototype on TEG 14 R1** | `round_report.py` pipeline (RoundStoryPlan, ROUND_* prompts, single-round bundle). | DONE. |
| **D. Pre-Phase-F shape fixes** | Folded into Phase E. | DONE. |
| **E. Round-report shape fixes (E1–E5)** | Round-scores block at top; auto-injected standings + LLM change-commentary; drop men-in-brief from round reports; default chronological/player_by_player; final-round awareness. Plus: anti-countback rule, arithmetic-faithfulness rule, mandatory-beats coverage guarantee, deterministic "PBs and TEG records" appendix. | DONE. |
| **F. Unified backfill (TEGs 8–18)** | PARTIAL. Force-regen kicked off, stopped after TEGs 8–10 fully complete and TEG 11 tournament + R1 + R2. Remaining for full coverage: TEG 11 R3–R4, then TEGs 12, 13, 15, 16, 17 (tournament + 4 rounds each), then TEGs 14 + 18 (re-refresh under latest prompts). ~16 reports outstanding; ~$8 to finish. **On hold** at user request — experimenting with guidelines/rules/layouts before resuming. Partial outputs verified (see notes below). | PARTIAL. |
| **G. Pre-TEG-8 era-aware Trophy + backfill** | CODE COMPLETE (commits `13db3c4`, `5709cc0`). `era.trophy_metric` helper; `commentary.py` extended with NetVP columns + `_add_rank_netvp_teg`; `events.py` era-aware throughout via `_trophy_cols(metric)`; `story_plan.py`, `authoring.py`, `round_report.py`, `render.py` all era-aware. Smoke tests passed on TEG 3 (NetVP framing) and TEG 14 (Stableford unchanged). Pre-8 backfill (TEGs 1–7, ~$15.75, ~30 min) **deferred** — to be run after the layout/rules experiments are settled, so pre-8 inherits them. | CODE DONE; backfill deferred. |

## Deferred (after the active agenda)

| Item | Notes |
|---|---|
| **5b — Strict round-by-round tournament variant** | Different from C: a *tournament* report rendered strictly chronologically (no theme weaving) — alternative format from the same story plan. |
| **5c — Modes (fast vs archive)** | `mode='fast'` skips the dry draft and uses single-pass authoring (approach B) — cheaper for post-round write-ups. `mode='archive'` = current full chain. Add as a `mode=` arg to a top-level orchestrator. |
| **5d — Batch API wrapper** | Use Anthropic's Batch API (50% off, 24h SLA, identical output) for any future archive runs. Bigger saver than the easy levers but ~1–2 h of staged-batch wrapper code. |
| **Pre-TEG-8 net-vs-par Trophy metric** | The Trophy was total net-vs-par for TEGs 1–7 (Stableford only from TEG 8). The pipeline currently hardcodes Stableford as the Trophy metric everywhere (`events.py` arcs + scoring). Pre-8 reports would misrepresent the Trophy standings — **must be fixed before any pre-8 backfill.** |
| **Light faithfulness-check pass** | Optional final guard that programmatically verifies prose claims against the data. Two writer-drift incidents to date — critique-revise fabricated "countback"; around-draft fabricated a "same hole across courses" rhyme on TEG 14 (now blocked by per-beat `course` + a prompt rule, but a verifier would catch the next class of drift). Useful insurance for scale. |

## Phase F partial verification (2026-06-02)

Reports verified: TEGs 8, 9, 10 (tournament + all rounds), TEG 11 (tournament + R1 + R2). Older anchors TEG 14 (tournament + R1 + R4) and TEG 18 (tournament + R3) also checked.

**Sanity-grep pass** — no hits in any `_final` report for: `schizophrenic`, `unique double`, `countback`, `tiebreak`, `playoff`. All "same hole" references are within-round comparisons (not cross-course fabrications). ✅

**Spot-reads:**
- TEG 8 tournament — faithful, dry, correct arithmetic throughout. ✅
- TEG 9 tournament — anchor holds. PB/record claims consistent with prior validation. ✅
- TEG 10 tournament — faithful. Baker's TEG-record 51 and 184 aggregate framed correctly. ✅
- TEG 11 tournament — faithful, good in_medias_res structure. Mullin Jacket-and-Spoon parlay correctly handled. ✅
- TEG 14 R4 — final-round coronation framing is correct. ✅
- TEG 18 tournament — anchor holds. ✅

**One arithmetic error found:** `teg_10_round_3_report_final.md` — opening para claims "a fourteen-point swing" (Mullin: 5 clear → 11 adrift). Correct figure is sixteen (5 + 11 = 16). The dry draft has the correct raw numbers; the writer miscalculated the summary. Not re-generated — the error is noted here; it can be fixed when/if TEG 10 R3 is re-generated as part of the experiment phase.

**Structure checks:**
- All round styled reports: round-scores block ✅, end-of-round standings ✅, records block ✅.
- All tournament styled reports: final standings ✅, records block ✅ (uses `class="records"`, not `pbs-and-records`).

## Known issues / gotchas
- **Pre-TEG-8 Trophy is on the wrong metric** until net-vs-par handling is added. The "Done" reports above (TEGs 9, 14, 18) are all post-8 so this doesn't affect them.
- **TEG 10 R3 arithmetic error**: "fourteen-point swing" should be "sixteen". Will fix on re-gen.
- **The isolated `venv/` (Python 3.14) hits a jinja2/starlette template-cache bug** (`TypeError: cannot use 'tuple' as a dict key`) on every templated route. Visual webapp verification needs Python 3.12/3.13, or wait for a fixed jinja2/starlette release.
- **MCP/CSS coupling between streamlit and webapp**: `teg_reports.css` is duplicated in `streamlit/styles/` and `webapp/static/`. Edits must be kept in sync (or, later, consolidated into a shared location). Streamlit is deferred but still wired.

## How to pick up in a clean session
1. Read this file (top to bottom) — five minutes.
2. Skim [README.md](README.md) for the architecture refresher — five more.
3. **The active agenda above is the next work** — sequenced A → B → C → D. Start at whatever phase isn't ticked off yet; the table is intentionally linear.
4. Sanity-test any change by regenerating **TEG 14** — it's the trickiest validated case (tight finish, multiple courses, the kind of pattern the writer wants to fabricate into a "rhyme") and any regression there will show. Baselines preserved at `data/commentary/teg_14_report_baseline.md` and `..._step1.md` for comparison.
