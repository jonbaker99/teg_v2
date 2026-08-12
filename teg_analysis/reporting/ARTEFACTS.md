# Artefacts — which file is which, and which one to touch

**Lookup reference.** What every file in `data/commentary/` is, what made it, and which one you
restart from for a given kind of change. Architecture is in [README.md](README.md); state is in
[STATUS.md](STATUS.md).

---

## Start here: only five files matter

Everything else in the folder is a snapshot or an experiment. The live chain is five files, made in
this order:

| # | File | What it is | Made by | Read by |
|---|---|---|---|---|
| 1 | `teg_N_story_plan.json` | **The editorial plan.** Theme, per-round angles, chosen headlines, which beats must appear, the frame. No prose. | Stage 3 (LLM) | Stages 4a, 4b, 5 |
| 2 | `teg_N_dry_draft.md` | **The facts in plain prose.** Correct, complete, deliberately boring. No jokes, no voice. | Stage 4a (LLM) | Stage 4b |
| 3 | `teg_N_report_A_around_draft.md` | **First pass with the voice on.** The dry draft rewritten in the house style. | Stage 4b (LLM) | the lint |
| 4 | `teg_N_report_final.md` | **The finished prose.** Same as ③ after a word-repetition clean-up. **This is the canonical text.** | lint (Haiku) | Stage 5, D3 |
| 5 | `teg_N_report_styled.md` | **What the site serves.** ④ plus CSS hooks, standings tables, records appendix, at-a-glance box. | Stage 5 (code, free) | the webapp |

Round reports use the same five names with a `round_R_` infix:
`teg_18_round_3_report_final.md`.

### "The bundle" is not a file

This trips people up. **The bundle is in-memory only** — the ~26k-token blob of scored beats,
competition arcs, venue and player history that gets handed to the LLM. It is assembled fresh on
every run by `assemble_bundle()`.

You can dump it to disk to inspect it, for free:

```python
from teg_analysis.reporting import build_story_plan
build_story_plan(14, dry_run=True)   # writes teg_14_story_plan_prompt.md, no API call
```

That file (`story_plan_prompt.md`) is a debugging artefact, not part of the chain.

---

## The flow, in one line each

```
data (parquet)
   └─► beats + arcs + context ──────────► THE BUNDLE (memory, ~26k tokens)
                                             │
   ①  story_plan.json      ◄── Stage 3 ──────┤   "what story do we tell?"        ~$0.28
                                             │
   ②  dry_draft.md         ◄── Stage 4a ─────┘   "say it plainly and correctly"  ~$0.20
                │
   ③  report_A_around_draft.md ◄─ Stage 4b       "now say it well"               ~$0.10
                │
   ④  report_final.md          ◄─ lint          "remove repeated words"          ~$0.07
                │                                 ← D3 verification runs here
   ⑤  report_styled.md         ◄─ Stage 5        "add tables + CSS hooks"        FREE
                │
             the webapp
```

**Why 4a and 4b are separate.** The dry draft is a correctness checkpoint. Stage 4b can only use
facts already in it, which is what stops the writer inventing things while reaching for a good line.
Splitting them is the main reason the reports stay faithful.

---

## Which file do I restart from?

The whole point of keeping intermediate files is that you don't re-run — and re-pay for — stages you
aren't changing.

| I want to change… | Edit | Restart from | Re-runs | Cost |
|---|---|---|---|---|
| **Tone of voice, humour level** | `authoring.WRITER_VOICE` | ① plan + ② dry draft (both frozen) | 4b + lint | **~$0.17** |
| Faithfulness rules | `authoring.WRITER_FAITHFULNESS` | ① + ② frozen | 4b + lint | ~$0.17 |
| How much hole detail the draft carries | `DRY_DRAFT_SYSTEM_DETAILED`, or `dry_draft_style=` | ① plan frozen | 4a → lint | ~$0.37 |
| The frame, structure, which beats feature | `story_plan.SYSTEM_PROMPT` | the bundle | everything | ~$0.65 |
| Which beats exist at all | `scoring.MODE_WEIGHTS`, `events.py` | the data | everything | ~$0.65 |
| Standings/records blocks, CSS hooks | `render.py` | ④ final | Stage 5 only | **free** |
| Visual design | `webapp/static/teg_reports.css` | ⑤ styled | nothing | **free** |

### The voice loop, concretely

This is the one you'll use most. It costs ~$0.17 and changes **only** the voice, because the plan
and the facts are held fixed:

```python
from teg_analysis.reporting.authoring import (
    load_story_plan, load_dry_draft, report_around_draft, repetition_lint)
from teg_analysis.reporting.render import style_report

teg = 17
plan = load_story_plan(teg)      # frozen ①
dry  = load_dry_draft(teg)       # frozen ②
rpt  = report_around_draft(teg, plan, dry)          # ~$0.10
linted, _ = repetition_lint(rpt["text"])            # ~$0.07

open(f"data/commentary/teg_{teg}_report_final.md", "w").write(linted)
style_report(teg)                                    # free
```

> **Save a copy before you overwrite.** `report_around_draft` and the write above replace ③ and ④.
> If you're comparing voices, write to a variant name first (see the naming convention below) and
> only promote the winner to `report_final.md`.

**Never test a voice change by regenerating the story plan.** You'd move two variables at once and
learn nothing — and pay 4× for the privilege.

---

## Which TEGs can I iterate voice on?

The voice loop needs ① *and* ② on disk. Verified 2026-08-11:

| Ready (11) | Not ready |
|---|---|
| 2, 3, 4, 5, 6, 7, 8, 9, 12, 15, 16, 17 | **10** — `report_final` missing<br>**11, 13, 14, 18** — `dry_draft` + `report_final` missing |

**TEG 14 is the standing anchor case** (2-point finish, multiple courses — the case that most tempts
fabrication) **and it is not currently usable for the voice loop.** The humour experiments consumed
its intermediate files into variant filenames. One full regeneration rebuilds them. Until then use
**TEG 17 or 12** — both current-vintage with complete chains.

---

## Everything else in the folder

Decoder for the ~40 other files. None of these are read by anything; they're history.

| Pattern | What it is |
|---|---|
| `..._report_styled.md` | **the live report** — what the site renders |
| `..._report_pre{X}.md` | a snapshot of the report **before** change X landed. `prevehicles`, `prepayoff`, `preclose`, `pretighten`, `pre_detailed_baseline`, `pre_phaseA` |
| `..._report_humour{6,8,8b}.md` | the **unsettled humour-dial A/B** (TEGs 14 and 18). `8b` is the Brooker-only variant. Read these against `report_styled.md` to settle it |
| `..._report_{detailed,light}.md` | the dry-draft density A/B. **Settled: detailed won** |
| `..._report_{tightened,step1,baseline,buggy}.md` | one-off experiment outputs |
| `..._report_{B_single_pass,C_critique_revise}.md` | the rejected authoring alternatives. C fabricated a "countback" — that's why the around-draft route won |
| `..._tournament_v{0..5}_*.md` | the voice ladder (`existing` → `baseline` → `restraint` → `economy` → `observer` → `gravitas`). Gravitas won |
| `..._story_plan_prompt.md` | dry-run dump of the assembled prompt + bundle. Free to regenerate |
| `..._notable_events.md`, `..._venue_context.md` | inspection dumps of Stage 2. Free |
| `archive 2026 v1/`, `archive 2026 v2/` | full snapshots of two earlier generations of the library |
| `archive 2025/`, `drafts/`, `round_reports/` | the pre-pipeline 2025 system. Still the webapp's fallback read paths |

**Naming a new variant:** `teg_N_report_{yourlabel}.md`, and `_styled` on the end for the rendered
version. Anything that isn't exactly `report_final.md` / `report_styled.md` is invisible to the site
and safe to create.

---

## Two things that will bite you

**1. Editing `report_styled.md` is pointless.** It's regenerated from `report_final.md` every time
`style_report()` runs. Edit ④, then re-style.

**2. Changing a file here does not change the website.** Railway serves from a volume. Merging to
`main` updates GitHub; the site keeps serving its cached copy until you hit **"Sync all reports from
GitHub"** on `/admin/volume-sync`.

---

## Check your work

D3 runs automatically inside `backfill.py`, but run it by hand after any manual edit:

```bash
python -m teg_analysis.reporting.verify 17          # one TEG
python -m teg_analysis.reporting.verify --all --rounds
```

It checks the finished prose against the data: beat IDs leaking into prose, invented
countback/playoff, "a week" (a TEG is 3–4 consecutive days), non-participants, invented weekdays,
impossible over-par totals, and mis-stated swings. Clean output is `✓`.
