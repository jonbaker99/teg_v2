# Reporting pipeline — chat onboarding

5-stage LLM pipeline that generates newspaper-style TEG tournament reports.
Cost: ~$0.65/report (Opus 4.7). Output: `data/commentary/teg_N_*.md`.
Round-level reports also available via `round_report.py`.

---

## File reading order

Read in this order; stop when you have enough for the task:

1. **`README.md`** — pipeline architecture (stages 1–5, how they connect, design rules)
2. **`STATUS.md`** — what's done, what's next, known issues; read this to understand current state
3. **`story_plan.py`** — `StoryPlan`/`RoundPlan` Pydantic schema + system prompt + `assemble_bundle()`; the editorial brain of the pipeline and the most compressed description of what the LLM is asked to do
4. **`authoring.py`** — Stage 4 orchestration: `generate_dry_draft`, `report_around_draft`, `repetition_lint`, `enrich_report_with_history`; contains all system prompts (`WRITER_SYSTEM`, `DRY_DRAFT_SYSTEM_*`, `LINT_SYSTEM`, `ENRICH_SYSTEM`)
5. **`events.py`** — beat detection and 3-axis scoring; only load if the work touches beat generation (800 lines)
6. **`round_report.py`** — per-round report pipeline; only load if working on round reports

---

## Current state snapshot

*(Update this section when phases complete or known issues are fixed.)*

- **Phases A–E**: complete
- **Phase F** (backfill TEGs 8–18): TEGs 8–11 done; ~16 tournament + round reports outstanding; on hold pending layout experiments
- **Known issues:**
  - TEG 10 R3 arithmetic error: "fourteen-point swing" should be "sixteen"
  - `teg_reports.css` duplicated in `streamlit/styles/` and `webapp/static/` — edits need sync in both places
  - Python 3.14 has a jinja2/starlette template-cache bug; use Python 3.12/3.13 for webapp visual verification

---

## Key constraints — LLM must never violate

- **No countback / tiebreak / playoff in TEG** — never invent one
- Honour `outright` vs `level` lead changes exactly as supplied in the bundle
- Audience = the players themselves (insiders who catch errors) → **faithfulness over flair**
- Voice: Barney Ronay / Tom Peck — witty, grounded, tongue-in-cheek; never zany or over-the-top
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

# Batch backfill across multiple TEGs → see backfill.py
# Per-round reports → see round_report.py
# Test bundle assembly without an LLM call → build_story_plan(teg_num, dry_run=True)
```

---

## Output file naming

| File | Stage | Description |
|------|-------|-------------|
| `teg_N_story_plan.json` | 3 | Editorial plan (LLM structured output) |
| `teg_N_dry_draft.md` | 4a | Faithful, plain scaffold (QA check) |
| `teg_N_report_final.md` | 4b | Linted, entertaining report |
| `teg_N_report_styled.md` | 5 | CSS-class annotated for UI rendering |
| `teg_N_rN_story_plan.json` | 3 | Round-level story plan |
| `teg_N_rN_report_final.md` | 4b | Round-level report |
