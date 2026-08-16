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

## How to test and iterate on each element

One recipe per thing you might want to change. **Run everything from the repo root.** The free ones
need nothing at all.

**The costs quoted below are API prices**, which is what you pay by default (and needs
`ANTHROPIC_API_KEY`). Add `--plan` to a backfill run — or `llm.use_provider("agent")` around a
call — and the prompt hands off to a Claude Code session or a browser tab instead, drawing on
claude.ai plan usage: read the columns as *relative* expense in that case, because the cash cost
is zero. See [README.md](README.md) → *Who answers the prompts*.

**The rule that saves the most money:** never test a cheap change by re-running the expensive
stages. Freeze what you aren't changing.

| Element | Edit | Cost | Recipe |
|---|---|---|---|
| Which events get detected | `events.py` detectors | **free** | ① below |
| What makes the cut (weights) | `scoring.MODE_WEIGHTS` | **free** | ② |
| What the LLM actually sees | *(inspect only)* | **free** | ③ |
| The frame / structure / beats chosen | hand-edit ① *or* `story_plan.SYSTEM_PROMPT` | **free** / ~$0.28 | ④ |
| Dry-draft detail level | `DRY_DRAFT_SYSTEM_DETAILED`, `dry_draft_style=` | ~$0.37 | ⑤ |
| **Voice — which register do I want?** | *(two prompt strings)* | ~$0.10 each | ⑦ (start here) |
| **Voice — does the writer hit it from scratch?** | *(a voice string; no code edit)* | ~$0.17 | ⑥ |
| **Voice — promote one to the house voice** | `authoring.WRITER_VOICE` | ~$0.17 | ⑥, step 5 |
| Faithfulness rules | `authoring.WRITER_FAITHFULNESS` | ~$0.17 | ⑧ |
| Mechanical fault checks | `verify.py` | **free** | ⑨ |
| Standings / records / CSS hooks | `render.py` | **free** | ⑩ |
| Visual design | `webapp/static/teg_reports.css` | **free** | ⑪ |

---

### ① Which events get detected — free

Every beat, ranked, with its three sub-scores and hole evidence:

```python
from teg_analysis.reporting import build_notable_events, render_events_markdown
events = build_notable_events(17)
print(render_events_markdown(events, 17, top=25))
```

*Did it work?* The beat you added appears with a sensible score, and the count hasn't exploded
(a detector firing 50 times per TEG is spam, not a signal).

### ② What makes the cut — free

```bash
python scripts/weight_profiler.py
```

Sweeps the live default against three alternatives over TEGs 9–18: type mix, tone balance,
coverage, mandatory survival, and churn against the pre-2026-08-11 baseline. The live setting is
read from `scoring.MODE_WEIGHTS`, so it always profiles what the pipeline actually uses.

*Did it work?* `big_blowup` share moved in the direction you wanted and mandatory survival stayed
at 100%.

### ③ What the LLM actually sees — free

```python
from teg_analysis.reporting import build_story_plan
build_story_plan(17, dry_run=True)   # writes teg_17_story_plan_prompt.md, no API call
```

The full system prompt plus the assembled bundle, exactly as sent. Read this before paying for a
generation you suspect will be wrong — most "the report missed X" problems are visible here.

### ④ The frame, structure and chosen beats

**Free option — hand-edit the plan.** ① is just JSON, and this is what archive mode is for. Change
`prominent_vehicle`, `narrative_structure`, `must_include_beat_ids`, a `chosen_headline`, whatever:

```bash
$EDITOR data/commentary/teg_17_story_plan.json
```

Then see the effect for ~$0.17 by re-running the writer only (⑥) — the dry draft does not read the
framing fields, so it needs no regeneration.

**Paid option — let the editor choose again** (~$0.28 plan, ~$0.65 for the full chain):

```python
from teg_analysis.reporting import build_story_plan
out = build_story_plan(17)
out["warnings"]          # [] means the close-finish rule and mandatory coverage are satisfied
out["plan"].prominent_vehicle
```

*Did it work?* `warnings` is empty, and `prominent_vehicle` is a **frame** (`counterfactual`,
`hero_arc`) while `prominent_palette` is **context material** (`cross_teg_career`, `records`).
Anything else is a schema error and will now be rejected outright.

### ⑤ Dry-draft detail level — ~$0.37

```python
from teg_analysis.reporting.authoring import load_story_plan, generate_dry_draft
plan = load_story_plan(17)                                    # frozen ①
dry  = generate_dry_draft(17, plan, dry_draft_style="light")  # or "detailed" (default)
```

*Did it work?* Every must-include beat still appears, and hole-level specifics survive. `detailed`
won the original A/B because `light` lost hole detail the insider audience wants.

### ⑥ and ⑦ — which voice recipe do I want?

They answer different questions, and you will usually want **both, in this order**:

| Your question | Recipe | Cost | Why |
|---|---|---|---|
| *"Brooker or Herron? Which register do I even want?"* | **⑦** | ~$0.10 each | Rewrites a **finished** report, so the facts and structure are literally identical between the two. Pure voice comparison, no code editing — just two strings. |
| *"I've picked one. Does the writer hit it from scratch?"* | **⑥** | ~$0.17 | Re-runs the real writer from the dry draft in a voice you pass as a string. This is the one that proves the pipeline produces the voice, rather than a rewrite reaching it. |

**Use ⑦ to choose, ⑥ to confirm.** Comparing registers with ⑥ works — neither needs a code edit
since 2026-08-16 — but it costs more and re-rolls the writer's structural execution each time, so
some of what you see is sampling noise rather than voice. Run a house-voice control alongside any ⑥
comparison.

#### Worked example — Brooker vs Herron

```python
from teg_analysis.reporting import restyle_voice

BROOKER = """VOICE TARGET: Charlie Brooker. Contemporary, vicious, specific, physical.
Comparisons drawn from broken household objects and malfunctioning tech, never literary.
Short sentences. Speaking voice. Escalation through specificity."""

HERRON = """VOICE TARGET: Mick Herron. Dry, wry, understated. Comedy from precise
characterisation and the gap between how people see themselves and how they perform.
Longer sentences that turn at the last clause. Never cruel for its own sake."""

for label, prompt in (("brooker", BROOKER), ("herron", HERRON)):
    out = restyle_voice(17, prompt, label)
    print(label, "->", out["styled_path"], out["new_findings"] or "clean")
```

**$0.20 for the pair.** Then read three files side by side:

```
data/commentary/teg_17_report_styled.md            <- the current house voice
data/commentary/teg_17_report_brooker_styled.md
data/commentary/teg_17_report_herron_styled.md
```

Same facts, same structure, same headings, same standings. Only the prose differs.

Then run ⑥ once to confirm the writer reaches the winning register from the dry draft rather than
only by rewriting, and fold it into `WRITER_VOICE` after that confirms.

> **Which TEG to test on.** Use one with a `report_final.md` — **17 or 12** are the current-vintage
> ones. The two natural anchors are unavailable by default: **TEGs 14 and 18 have no
> `report_final.md`** (past experiments consumed it), so pass
> `source_label="A_around_draft"` for those. The error message lists the alternatives if you forget.
>
> **Test on two TEGs before committing**, as the original A/B did: one tight finish, one blowout.
> A register that works on a close finish can fall flat on a procession.

### ⑥ Tone of voice — ~$0.17 · confirming the chosen register

Runs the **real writer** over the frozen dry draft in a voice you pass as a string. Same function
the production chain calls, same prompt assembly — the only difference is that you supply the middle
slot instead of letting it default to the house voice.

**Write the voice as a complete description, not a change.** `write_from_dry` REPLACES
`WRITER_VOICE`; it does not modify it. "Drier, shorter sentences" is the wrong shape of input here —
there is no baseline for it to be drier *than*, so the model invents one. Describe the register from
scratch, at whatever level of detail you want to test.

**Step 1 — write the voice.** No code edit. A string in a notebook is enough:

```python
PLAIN = """VOICE: a plain broadsheet match report. British English. Report what happened,
in order, clearly. No jokes, no metaphor, no authorial personality. Short declarative
sentences. The reader wants the facts and the shape of the contest, nothing else."""
```

**Step 2 — run it.**

```python
from teg_analysis.reporting import write_from_dry
out = write_from_dry(17, PLAIN, "plain")        # ~$0.17 incl. lint
out["styled_path"]      # data/commentary/teg_17_report_plain_styled.md
out["findings"]         # [] is what you want
```

It loads the frozen plan and dry draft, writes, lints, styles and runs the D3 checks. It refuses
labels that would overwrite `report_final`, `report_styled` or the chain's own `A_around_draft`, so
the live report is never at risk.

**How much story plan goes in** — `plan_scope=`, the second dial:

| `plan_scope` | What the writer gets besides the dry draft | Use it to |
|---|---|---|
| `"none"` | nothing | Isolate the voice completely. The draft's own chronology is the only structure. |
| `"arc"` *(default)* | `narrative_vehicles`, `prominent_vehicle`, `narrative_structure`, `opening_hook`, `theme`, `foreshadow`, `payoffs`, `why_the_champion_won` | Give the report a shape to follow without the per-round angles and per-player arcs steering the prose. |
| `"full"` | the whole plan | Match production exactly. |

Narrowing the scope adds a note telling the writer which plan fields it actually has, so it does not
hunt for the missing ones and improvise. The structural requirements hold at every scope.

**Full material without preset phrasing** — `bundle_context=True`, the third dial. Every story-plan
field is editorial prose the writer can lift; `rounds[].angle` and `players[].arc` are already
written sentences. The bundle is not: `venue`, `player_history`, `player_course_history`,
`player_relationships` and `win_anatomy` are structured data. So:

```python
write_from_dry(17, PLAIN, "plain_rich", plan_scope="none", bundle_context=True)
```

gives the writer the competition resolutions and hole detail (from the dry draft, which already
carries a full "HOW THE COMPETITIONS WERE DECIDED" section), plus venue character, cross-TEG career
storylines and per-course history — and not one pre-written phrase. Deterministic, no extra LLM
call, so it costs nothing beyond the tokens.

**Step 3 — get a control.** Voice comparisons are worthless without one, because the writer re-rolls
its structural execution on every call and some of what you see is sampling noise:

```python
write_from_dry(17, None, "house_control")   # house voice, same path, same scope
```

**Step 4 — compare.**

```
data/commentary/teg_17_report_house_control_styled.md
data/commentary/teg_17_report_plain_styled.md
```

Check `findings` before you form a view on the prose. A factual fault means the voice pulled the
writer into fabrication, which is a different verdict from "I don't like the tone".

**Step 5 — promote, only if you like it.** This is the deliberate, separate act that makes a trial
voice the house voice. Nothing before this point changes what the pipeline produces:

```python
# 1. paste the winning voice into `authoring.WRITER_VOICE`
# 2. re-run the backfill for the TEGs you want regenerated
```

**If you don't like it,** do nothing. `report_final.md` is untouched and the variant files are
inert — the site never reads them.

> **What ⑥ can't reach.** `write_from_dry` fills the VOICE slot only. The contract above it (who the
> report is for, the winner's-story duty, structure, palette, scoring-redundancy notation, SI) and
> the guardrails below it (faithfulness, output format) are fixed by design — a voice cannot shed
> them. To change those, edit `WRITER_CONTRACT` or `WRITER_FAITHFULNESS` and see ⑧.

### ⑦ Comparing voice registers — ~$0.10 each · choosing the register

When the question is "which register?" rather than "is this prompt better?", rewrite a **finished**
report instead. The input is the finished text, so facts, structure and headings are held literally
constant — the tightest possible A/B.

```python
from teg_analysis.reporting import restyle_voice
out = restyle_voice(17, "VOICE TARGET: drier. Shorter sentences, fewer images.", "drier")
out["new_findings"]     # faults THIS pass introduced — [] is what you want
```

The humour-dial registers are pre-written:

```bash
python scripts/humour_dial.py --list
python scripts/humour_dial.py --teg 14 --variant humour8b
```

**This is an experiment tool, not part of report generation.** Nothing in the pipeline calls it —
`backfill.py` runs plan → dry → around → lint → style → verify and stops. The point is to *find* a
target voice; once found, confirm it with ⑥ and only then fold it into `WRITER_VOICE`. Rewriting
proves a voice is reachable, not that the writer hits it first time from the bundle.

### ⑧ Faithfulness rules — ~$0.17

Edit `authoring.WRITER_FAITHFULNESS`, then run recipe ⑥ — same loop, different constant. Kept
separate from voice precisely so a voice experiment can't disturb a guardrail.

Before removing a rule, check whether ⑨ covers it. Six of the eleven are mechanically checked, but
**belt and braces is deliberate** — prevention and detection are cheap together.

### ⑨ Mechanical fault checks — free

```bash
python -m teg_analysis.reporting.verify 17            # one TEG
python -m teg_analysis.reporting.verify --all --rounds
```

Checks the prose against the data: leaked beat IDs, invented countback/playoff, "a week" (a TEG is
3–4 consecutive days), non-participants, invented weekdays, impossible over-par totals, mis-stated
swings. `backfill.py` runs it automatically after every generation.

*Did it work?* `✓`. Use the error count as the acceptance test after a regeneration.

### ⑩ Standings, records, CSS hooks — free

```python
from teg_analysis.reporting.render import style_report
style_report(17)      # re-reads report_final.md, rewrites report_styled.md
```

Idempotent — running it twice produces byte-identical output. Safe to re-run as often as you like.

### ⑪ Visual design — free

Edit `webapp/static/teg_reports.css` and reload. No Python involved.
(There is a second copy under `streamlit/`; it is dead code — see known issue 6.)

---

## Which file do I restart from?

The summary of the above, as a lookup. **"Restart from" means one thing: load that artefact from
disk instead of regenerating it.** When a row lists two artefacts, that is not two separate restarts
— it is one action, loading both into memory before running the stages in the next column. Concretely:

```python
plan = load_story_plan(teg)   # reads ① from disk — free, no API call
dry  = load_dry_draft(teg)    # reads ② from disk — free, no API call
# only NOW does anything in "Then run" actually call the LLM
```

Nothing downstream of the artefact you load gets touched until "Then run" executes. That is the
entire saving: the cost column only counts what's in that column, because everything before it was
loaded, not regenerated.

| I want to change… | Edit | Load from disk (free) | Then run | Cost | Numbered steps |
|---|---|---|---|---|---|
| **Tone of voice, humour level** | a `voice=` string, or `authoring.WRITER_VOICE` to promote it | ① plan **and** ② dry draft | 4b → lint | **~$0.17** | [Recipe ⑥](#-tone-of-voice--017--confirming-the-chosen-register) |
| What the report must be, whatever its voice | `authoring.WRITER_CONTRACT` | ① plan **and** ② dry draft | 4b → lint | ~$0.17 | Recipe ⑥, run it with `voice=None` |
| Faithfulness rules | `authoring.WRITER_FAITHFULNESS` | ① plan **and** ② dry draft | 4b → lint | ~$0.17 | Recipe ⑥, same steps, different constant |
| How much hole detail the draft carries | `DRY_DRAFT_SYSTEM_DETAILED`, or `dry_draft_style=` | ① plan only | 4a → lint | ~$0.37 | [Recipe ⑤](#-dry-draft-detail-level--037) |
| The frame, structure, which beats feature | hand-edit ①, or `story_plan.SYSTEM_PROMPT` | ① (if hand-editing) | 4b only, or everything | **free** → ~$0.65 | [Recipe ④](#-the-frame-structure-and-chosen-beats) |
| Which beats exist at all | `scoring.MODE_WEIGHTS`, `events.py` | *(nothing — recompute from data)* | everything | ~$0.65 | [Recipe ①](#-which-events-get-detected--free) / [②](#-what-makes-the-cut--free) |
| Standings/records blocks, CSS hooks | `render.py` | ④ final | Stage 5 only | **free** | [Recipe ⑩](#-standings-records-css-hooks--free) |
| Visual design | `webapp/static/teg_reports.css` | ⑤ styled | nothing | **free** | [Recipe ⑪](#-visual-design--free) |

**This table is a lookup, not a walkthrough.** It tells you what's frozen and what runs; the actual
runnable steps are in the recipe each row links to.

## Which TEGs can I iterate voice on?

Recipe ⑥ needs ① *and* ② on disk, and **every TEG 2-18 has both** (re-verified 2026-08-16), so any
of them works for a from-scratch voice trial.

Recipe ⑦ additionally needs a finished report to rewrite. Verified 2026-08-11:

| Ready for ⑦ (12) | Not ready for ⑦ |
|---|---|
| 2, 3, 4, 5, 6, 7, 8, 9, 12, 15, 16, 17 | **10, 11, 13, 14, 18** — no `report_final` (pass `source_label="A_around_draft"`) |

**TEG 14 is the standing anchor case** (2-point finish, multiple courses — the case that most tempts
fabrication). It has ① and ② on disk, so **⑥ works on it**; only ⑦ needs the `source_label=`
workaround. **TEG 17 or 12** remain the easiest defaults — both current-vintage with complete chains
including a `report_final`.

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
