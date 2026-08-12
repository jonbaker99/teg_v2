# Reporting pipeline — chat onboarding

5-stage LLM pipeline that generates newspaper-style TEG tournament reports (plus per-round reports).
Cost: ~$0.65/report (Opus-tier). Output: `data/commentary/teg_N_report_styled.md` → rendered by the
webapp at `/teg-reports` and the Report tab on `/results`.

---

## File reading order

Read in this order; stop when you have enough for the task:

1. **`STATUS.md`** — the pick-up ledger: what's published, which reports are on which pipeline
   vintage, the open decisions, known issues. **Read this first, always.**
2. **`README.md`** — pipeline architecture (stages 1–5, the context modules, how they connect,
   design rules)
3. **`ARTEFACTS.md`** — the operational guide: the pipeline in one table, which file is which, and
   **a runnable recipe for testing each element**. **Read before changing anything** — the voice
   loop costs ~$0.17 from the right restart point and ~$0.65 from the wrong one, and several
   elements can be inspected for free before you spend at all
4. **`EXPERIMENTS.md`** — what's been tried on voice/structure, what the verdicts were, what's open
5. **`story_plan.py`** — `StoryPlan` Pydantic schema + editor system prompt (incl. the narrative-vehicle
   menu) + `assemble_bundle()`; the editorial brain, and the most compressed description of what the
   LLM is asked to do
6. **`authoring.py`** — Stage 4 orchestration and every system prompt (`WRITER_SYSTEM`,
   `WRITER_VOICE` / `WRITER_FAITHFULNESS`, `DRY_DRAFT_SYSTEM_*`, `LINT_SYSTEM`, `TIGHTEN_SYSTEM`)
7. **`events.py`** — beat detection and 3-axis scoring; only load if the work touches beat
   generation (900 lines)
8. **`round_report.py`** — per-round pipeline; only load if working on round reports

---

## Current state snapshot

*(Verified 2026-08-10. Update this section when phases complete or known issues are fixed —
the detail lives in STATUS.md, this is just the headline.)*

- **All stages built.** Phases A–G closed; an unlogged **Phase H** (narrative vehicles, setup→payoff
  pairs, close-finish rule, economy/tightening, cross-TEG + course history, faithfulness hardening)
  landed after them.
- **Tournament coverage complete** — TEGs 2–18 all published. (There is no TEG 1 in the data;
  TEG 2 has 3 rounds, every other TEG has 4.)
- **Round reports published for TEGs 8/9/10 (all rounds), 11 (R1–R2), 14 (R1, R4), 18 (R3).**
  17 of 67 — **50 outstanding** for full coverage.
- **The library is not one vintage.** TEGs 2–8, 15, 16 predate Phase H; 9 is partial; 10–14, 17, 18
  are current. All round reports predate Phase H. Vintage is fingerprinted from
  `teg_N_story_plan.json` — `payoffs` / `narrative_vehicles` present ⇒ current.
- **Work stopped mid-experiment** on a humour-dial A/B (3 → 6 → 8 → 8b) run on TEGs 14 and 18.
  Outputs are on disk, unpublished, **no verdict recorded**. That decision is the first pick-up item.
- **Known issues:** see STATUS.md — the register was cleared on 2026-08-11 (D3 verification
  built; era leak, shared-vocabulary schema, arc weighting and model pin all fixed). What
  remains is two judgement calls (humour dial, selection weights) and prose-wording faults
  in older reports that regeneration clears. Historic note:
  `enrich_report_with_history()` was deleted; `backfill.py` doesn't call the tighten
  passes; `RoundStoryPlan` is a generation behind; TEG 10 R3 arithmetic error
  ("fourteen-point swing" should be sixteen); `teg_reports.css` duplicated across
  `streamlit/styles/` and `webapp/static/`; Python 3.14 has a jinja2/starlette template-cache bug so
  webapp visual checks need 3.12/3.13.

---

## Key constraints — the LLM must never violate

- **No countback / tiebreak / playoff in TEG** — never invent one
- Honour `outright` vs `level` lead changes exactly as supplied in the bundle
- **Stableford vs Gross is ordinary handicapping**, never a paradox or "unique double"
- **The Trophy metric is era-dependent** — Stableford for TEG 8+, net-vs-par (lower is better) for
  TEGs 1–7
- **Relationships only from `player_relationships`** — shared surnames prove nothing
- **Weekdays only verbatim from `venue.rounds[i].weekday`**, and only in that round's opener; a TEG
  is four days, never "a week"
- Only players who actually played this TEG may appear
- Arithmetic must be exact against the per-hole evidence
- Audience = the players themselves (insiders who catch errors) → **faithfulness over flair**
- Voice: Ronay / Peck / Armstrong / Iannucci — subverted gravitas; never zany, never wink at the camera
- Use **only** data in the supplied bundle — never invent facts or hole details

---

## Common entry points

```python
# Full tournament report for TEG N
from teg_analysis.reporting import build_story_plan
from teg_analysis.reporting.authoring import generate_dry_draft, report_around_draft, repetition_lint
from teg_analysis.reporting.render import style_report

plan = build_story_plan(teg_num)["plan"]
dry = generate_dry_draft(teg_num, plan)
rpt = report_around_draft(teg_num, plan, dry["text"])
linted, _ = repetition_lint(rpt["text"])
open(f"data/commentary/teg_{teg_num}_report_final.md", "w").write(linted)
style_report(teg_num)  # → teg_N_report_styled.md

# Batch across TEGs (this exact chain, cached per TEG)
from teg_analysis.reporting.backfill import backfill_all
backfill_all([12, 13], scope="tournament", force=True)

# Per-round report
from teg_analysis.reporting.round_report import generate_round_report
generate_round_report(teg_num, round_num)

# Test bundle assembly without an LLM call
build_story_plan(teg_num, dry_run=True)   # writes teg_N_story_plan_prompt.md
```

Run from the repo root with `venv/bin/python`. API key: `ANTHROPIC_API_KEY`, else
`.streamlit/secrets.toml` at the repo root.

---

## Output file naming

| File | Stage | Description |
|------|-------|-------------|
| `teg_N_story_plan.json` | 3 | Editorial plan (LLM structured output) |
| `teg_N_dry_draft.md` | 4a | Faithful, plain scaffold (QA check) |
| `teg_N_report_A_around_draft.md` | 4b | Entertaining report, pre-lint |
| `teg_N_report_final.md` | 4b + lint | Linted report |
| `teg_N_report_styled.md` | 5 | **The live file** — CSS-class annotated, standings + records injected |
| `teg_N_round_R_*` | — | Same set, round level |

Anything else in `data/commentary/` is experiment output or an archived generation — see the naming
conventions table in [README.md](README.md#artefacts-per-teg-under-datacommentary).
