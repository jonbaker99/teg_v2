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
5. **`prompts.py`** — **the shared prompt blocks, and the only place the voice is defined**
   (`VOICE_CORE`, `NAMED_PRINCIPLES`, `HOUSE_VOICE_SUMMARY`, `SHARED_FAITHFULNESS`,
   `STROKE_INDEX_RULE`, `OUTPUT_RULE`). All four prompts import from here. Short, and it is where any
   voice or faithfulness change belongs — read it before `authoring.py`
6. **`story_plan.py`** — `StoryPlan` Pydantic schema + editor system prompt (incl. the narrative-vehicle
   menu) + `assemble_bundle()`; the editorial brain, and the most compressed description of what the
   LLM is asked to do
7. **`authoring.py`** — Stage 4 orchestration and the tournament-only prompts (`WRITER_SYSTEM`,
   composed by `build_writer_system()` from `WRITER_CONTRACT` + `WRITER_VOICE` +
   `WRITER_FAITHFULNESS` + `WRITER_OUTPUT_RULE`, where the voice slot is swappable per call;
   `DRY_DRAFT_SYSTEM_*`, `LINT_SYSTEM`, `TIGHTEN_SYSTEM`)
8. **`events.py`** — beat detection and 3-axis scoring; only load if the work touches beat
   generation (900 lines). `impact.py` (counterfactual importance) and `win_anatomy.py` (why the
   champion won) go with it
9. **`round_report.py`** — per-round pipeline; only load if working on round reports
10. **`mailbox.py`** — the prompt hand-off behind `--plan` / `--paste`; only load if a run is stuck

---

## Current state snapshot

*(Verified 2026-08-17. Update this section when phases complete or known issues are fixed —
the detail lives in STATUS.md, this is just the headline.)*

- **All stages built**, including D3 verification (`verify.py`, 8 checks, auto-run by `backfill.py`) and
  a provider switch that runs the same prompts on claude.ai plan usage instead of the API.
- **Tournament coverage complete and now one vintage** — TEGs 2–18 all published, all regenerated on
  2026-08-13, all with a complete artefact chain (plan, dry draft, final, styled). Five (4, 8, 12, 14, 18)
  also carry the 2026-08-14 counterfactual/`win_anatomy` rework. (There is no TEG 1 in the data;
  TEG 2 has 3 rounds, every other TEG has 4.)
- **Round reports: TEGs 8/9/10 (all rounds), 11 (R1–R2), 14 (R1, R2, R4), 18 (R3).** 18 of 67 —
  **49 outstanding**. All 18 are two generations behind the round code, which is itself untested on real
  output.
- ⚠️ **What the site serves is not what was generated.** The 2026-08-13 run used `style=False`, so **16
  of 17 `*_report_styled.md` files still hold pre-regeneration prose.** Re-styling is free; it hasn't
  been done. Check before concluding anything from reading the site.
- **Voice is settled and unvalidated.** The humour dial closed on 2026-08-15 at `humour6`, with em-dashes
  banned outright and a ~15-word sentence average, all in `prompts.VOICE_CORE`. **No report on disk was
  generated under it** — 566 em-dash warnings library-wide say so. One cold generation is the first
  pick-up item.
- **Known issues:** see STATUS.md. The 2026-08-11 register is almost entirely cleared, and the 81
  prose-wording faults cleared with the regeneration (D3 now reports **0 errors on all 17 tournament
  reports**; the only 4 left are in round reports). Still open: `TIGHTEN_SYSTEM` contradicts the em-dash
  ban (dormant, nothing calls it); raw `SI n` leaking into prose; a stray tracked `reply.txt` at the repo
  root; `output_config.effort` never set; `teg_reports.css` duplicated across `streamlit/styles/` and
  `webapp/static/`; Python 3.14 has a jinja2/starlette template-cache bug so webapp visual checks need
  3.12/3.13.

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
- Voice: Herron / Ronay / Armstrong / Iannucci — subverted gravitas; never zany, never wink at the
  camera. **Defined once in `prompts.py` → `VOICE_CORE`; every prompt imports it. Never re-inline it.**
  The register is the one part of the writer prompt that is *meant* to be replaceable: everything
  else lives in `WRITER_CONTRACT` or `WRITER_FAITHFULNESS`, which a `voice=` swap cannot shed
- **No em-dashes at all** (banned outright 2026-08-15, not a ceiling), sentences averaging ~15 words with
  a hard stop around 25, and 5–7 landed comic moments per report. D3 checks the em-dash rule
- **The report is the winner's story** — `why_the_champion_won` is a required plan field. Hard on the
  champion's golf, never on the achievement, and delivered elevated rather than flat
- **Translate stroke index, never quote it** — "the hardest hole on the course", not "SI 1"
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

# Try a voice without editing any source: replaces WRITER_VOICE for one call
from teg_analysis.reporting import write_from_dry
write_from_dry(17, "VOICE: a plain broadsheet match report.", "plain")
```

```bash
# Same job outside the pipeline (Cowork, a browser tab, another model): exports
# the prompt constants and the frozen inputs as files. Generate, never hand-copy.
python -m scripts.export_cowork_kit --tegs 4,14,17 --out ~/cowork/teg
```

Run from the repo root with `venv/bin/python`.

**These calls hit the Anthropic API by default**, which needs `ANTHROPIC_API_KEY` (else a
gitignored `secrets.toml` at the repo root). To run the same prompts on claude.ai plan usage
instead — no key, no per-token cost — add `--plan` to the backfill CLI or wrap the call in
`llm.use_provider("agent")`; each prompt is then written to `data/llm_mailbox/` and waits for
the `teg-report-respond` skill (or you) to answer it.
Full detail: [README.md](README.md) → *Who answers the prompts*.

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

Anything else in `data/commentary/` is experiment output, a variant directory or an archived
generation — see the decoder in [ARTEFACTS.md](ARTEFACTS.md#everything-else-in-the-folder).
