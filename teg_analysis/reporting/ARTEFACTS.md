# Artefacts — which file is which, and which one to touch

**Lookup reference.** What every file in `data/commentary/` is, what made it, and which one you
restart from for a given kind of change. Architecture is in [README.md](README.md); state is in
[STATUS.md](STATUS.md).

---

## The whole pipeline in one table

Read this and you have it. Every stage, what it does, what it reads, what it writes.

| Stage | What it does, in plain terms | Reads | Writes | Cost |
|---|---|---|---|---|
| **1–2** | Loads the data; finds and scores the notable events ("beats") | `data/*.parquet` | *(memory)* | free |
| **–** | Packs beats + arcs + venue + history into **the bundle** | beats + context | *(memory)* | free |
| **3** | **Decides the story** — theme, shape, frame, which beats must appear | the bundle | ① `story_plan.json` | ~$0.28 |
| **4a** | **States the facts plainly** — correct and complete, deliberately boring | ① + bundle | ② `dry_draft.md` | ~$0.20 |
| **4b** | **Applies the voice** — rewrites ② in the house style | ① + ② | ③ `report_A_around_draft.md` | ~$0.10 |
| **lint** | Removes repeated words. Nothing else | ③ | ④ `report_final.md` | ~$0.07 |
| **D3** | **Checks the prose against the data**, reports faults | ④ + data | *(findings)* | free |
| **5** | Adds standings tables, records appendix, CSS hooks | ④ | ⑤ `report_styled.md` | free |
| | | | **total** | **~$0.65** |

Two things that follow:

- **4b can only use facts already in ②.** That is the whole reason 4a exists — the writer cannot
  invent while reaching for a good line, because it is rewriting, not composing from data.
- **④ is the canonical text; ⑤ is what the site serves.** ⑤ is regenerated from ④ every time, so
  editing ⑤ is pointless.

### Other names for the same thing

Three vocabularies exist for this one pipeline. They are not competing models — they are different
cuts, and this is the mapping:

| Vocabulary | What it's for | Where |
|---|---|---|
| **Stages 1–5** | *how a report is built* — the runtime sequence above | this table; README |
| **Themes A–E** | *what you can change* — grouped by cost to iterate | [README.md](README.md) → Components |
| **Files ①–⑤** | *what's on disk* — the artefacts | this doc |

Roughly: **A** = stages 1–2, **B** = stage 3, **C** = stages 4a/4b, **D** = the faithfulness rules
plus D3 plus the injected blocks, **E** = stage 5.

---

## The five files on disk

| # | File | What it is | Made by | Read by |
|---|---|---|---|---|
| ① | `teg_N_story_plan.json` | **The editorial plan.** Theme, per-round angles, chosen headlines, which beats must appear, the frame. No prose. | Stage 3 (LLM) | 4a, 4b, 5 |
| ② | `teg_N_dry_draft.md` | **The facts in plain prose.** Correct, complete, deliberately boring. No jokes, no voice. | Stage 4a (LLM) | 4b |
| ③ | `teg_N_report_A_around_draft.md` | **First pass with the voice on.** ② rewritten in the house style. | Stage 4b (LLM) | the lint |
| ④ | `teg_N_report_final.md` | **The finished prose.** ③ after a word-repetition clean-up. **The canonical text.** | lint (Haiku) | Stage 5, D3 |
| ⑤ | `teg_N_report_styled.md` | **What the site serves.** ④ plus CSS hooks, standings, records, at-a-glance box. | Stage 5 (code) | the webapp |

Everything else in `data/commentary/` is a snapshot or an experiment — see the decoder near the end.

Round reports use the same five names with a `round_R_` infix:
`teg_18_round_3_report_final.md`.

### "The bundle" is not a file

This trips people up. **The bundle is in-memory only** — the ~26k-token blob of scored beats,
competition arcs, venue and player history handed to the LLM. It is assembled fresh on every run by
`assemble_bundle()`, and it is what stages 3 and 4a both read.

Dump it to disk to inspect it, for free:

```python
from teg_analysis.reporting import build_story_plan
build_story_plan(14, dry_run=True)   # writes teg_14_story_plan_prompt.md, no API call
```

That file is a debugging artefact, not part of the chain.

---

## Where the story arc is decided, and where it first bites

Worth knowing before you tune anything, because the two points are **not** the same stage.

**Decided: Stage 3, the story plan.** The editor LLM reads the bundle (scored beats, competition
arcs, venue, player history, `tournament_shape`, `recent_vehicle_choices`) and writes into ①:

| Field | What it fixes |
|---|---|
| `theme` | the one-line through-line |
| `narrative_structure` | the sequence — `chronological`, `in_medias_res`, `theme_led`, … |
| `narrative_vehicles` | 1–3 storytelling frames |
| `prominent_vehicle` | **the frame being foregrounded** (e.g. `counterfactual`) |
| `prominent_palette` | **the context material being foregrounded** (e.g. `cross_teg_career`) |
| `opening_hook`, `foreshadow`, `payoffs` | what to plant, and where it resolves |

Two constraints bind the choice: the **close-finish hard rule** (if `tournament_shape.close_finish`
is true, `prominent_vehicle` must be `counterfactual` or `dual_narrative`) and the **soft
anti-repetition rule** (`recent_vehicle_choices` shows the last few TEGs' picks).

> `prominent_vehicle` and `prominent_palette` are **two different axes with disjoint vocabularies.**
> A report is normally *framed* one way and *foregrounds* material from another. Confusing them is
> what caused the close-finish rule to never fire for four TEGs.

**First used: Stage 4b, the writer — not 4a.** The whole plan JSON is passed to both stages, but
only the writer prompt acts on the framing:

| Field | Dry draft 4a (`detailed`, the default) | Dry draft 4a (`light`) | Writer 4b |
|---|---|---|---|
| `theme` | ✓ | ✓ | ✓ |
| `narrative_structure` | **ignored** | ✓ | ✓ |
| `narrative_vehicles` / `prominent_vehicle` | **ignored** | **ignored** | ✓ |
| `opening_hook`, `foreshadow`, `payoffs` | **ignored** | **ignored** | ✓ |

**This is deliberate, and worth understanding.** The default dry draft is *always* a flat
round-by-round fact dump, whatever structure the plan chose. Its job is completeness and accuracy,
not shape — a scaffold you can check the facts against. The framing is applied once, at 4b, when the
prose is written.

Three practical consequences:

1. **A dry draft that reads chronologically is not a bug**, even when the plan says `in_medias_res`.
2. **Changing the vehicle means re-running 4b only** (~$0.17) — the dry draft is unaffected by it, so
   there is no reason to regenerate ②.
3. **Changing the vehicle means regenerating the plan** (~$0.65) if you want the *editor* to pick
   differently. Editing ① by hand is the cheap alternative: it is just JSON, and archive mode exists
   precisely so a human can steer it before authoring runs.

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

### Comparing voices without touching the canonical files

`restyle_voice()` rewrites a **finished report's** voice only. Because the input is the finished
text rather than the bundle, everything else — facts, structure, headings, standings, records — is
held literally constant. One variable, one API call, ~$0.10.

```python
from teg_analysis.reporting import restyle_voice

out = restyle_voice(17, "VOICE TARGET: drier. Fewer jokes, shorter sentences.", "drier")
#   -> data/commentary/teg_17_report_drier.md
#   -> data/commentary/teg_17_report_drier_styled.md   (directly comparable with _styled.md)
out["new_findings"]   # faults THIS pass introduced — [] is what you want
```

The humour-dial registers are already wired up:

```bash
python scripts/humour_dial.py --list
python scripts/humour_dial.py --teg 14 --variant humour8b
```

Three things it does for you:

- **Refuses to write to `final` / `styled` / `A_around_draft`.** Canonical artefacts are safe.
- **Composes the guardrails from `WRITER_FAITHFULNESS`** — the same constant the main writer uses,
  so a voice experiment cannot shed the faithfulness rules or drift out of step with them.
- **Reports what this pass *introduced*, not what it inherited.** A restyle inherits the source's
  existing faults, so a raw finding list is misleading; `new_findings` is the number that matters.

> **Why this is a lever and not a pipeline stage.** The original authoring A/B tested an extra pass
> over finished prose as the *default* (variant C, critique-revise) and rejected it: the extra pass
> fabricated a "countback". Every pass over prose is a fabrication opportunity. What has changed is
> that D3 now exists, so such a pass can be *checked* rather than trusted — which is what
> `new_findings` is. It stays opt-in.
>
> **What it does not prove:** that a voice is reachable *by rewriting* is not the same as the writer
> hitting it first time from the bundle. Fold the winner into `WRITER_VOICE`, then confirm with one
> from-scratch generation before trusting it for a backfill.

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
