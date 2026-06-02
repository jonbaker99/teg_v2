# Reporting — Experiments to try

Working list. Each entry: what to try, how to test, notes. Delete entries (or roll into prompts / STATUS) once the experiment settles.

A short / interesting TEG to use as a regen anchor for style experiments: TBD — pick one from TEGs 8–11 (we have fresh outputs for these). TEG 11 has the smallest field for that era and is partially regenerated; TEG 8 is the closest to "blowups + spoon drama" which gives the prose plenty to work with.

---

## 1. Style principles for the dry / satirical / humorous voice

**Goal:** make the voice deliberate rather than accidental. Build a short list of named principles (e.g. "wry observation > broad joke", "specific image > generic adjective", "the comma is doing the work", "let one short sentence land the point") and see which combinations produce the voice we want.

**How to test:** pick one short report (one round, ideally). Regenerate it 3–5 times with different principle stacks layered into `ROUND_WRITER_SYSTEM`'s VOICE block. Read side-by-side. Score on: faithful, dry, observational, lands without trying. Lock in the keepers.

**Notes:**
- _(empty — to fill in as we run)_

---

## 2. Writing must add value beyond the scorecard

**Goal:** the deterministic round-scores block already shows what each player shot. The prose should do the things a scorecard can't:

- Tournament-level context for the round ("the eight-shot cushion has gone to two")
- Historical context (TEG records, this is the Nth time X has happened, all-time best/worst)
- Personal-best / personal-worst flagging
- Threads across rounds (foreshadowing, payoffs)
- Cross-player comparisons (same hole, different outcomes; matched scores; rivalries)
- Course / venue context (the hole's reputation, weather, what makes it hard)
- Causal explanation (this stretch is what made the difference, not just what happened)

**How to test:** read the existing TEG 8–11 outputs and grade each round-report paragraph as: (a) restates scorecard, (b) adds context not visible from the scorecard, or (c) wastes words. Look for the dominant failure mode. Then sharpen the writer prompt with rules that prevent the failure mode, regen the same report, compare.

**Notes:**
- _(empty)_

### 2b. Embed actual scorecards (HTML) inside reports

**Goal:** if a scorecard is visible inline, the writer can stop spelling out per-hole sequences and focus on what those sequences mean. Heavy lifting moves to a deterministic block; prose carries interpretation.

**How to test:** build a `build_round_scorecard_html(teg, round)` helper that emits a styled HTML table — hole / par / each player's gross — for the round. Inject above (or below?) the prose. Regen one round under a writer prompt told "the scorecard is rendered inline, do NOT enumerate; reference holes by number, comment on what the score means."

**Notes:**
- Open question: at top of report (with round-scores block), or after main prose (data appendix)?
- Open question: does the styled output need any CSS additions to render the table nicely in the webapp + streamlit surfaces?

---

## 3. Verbal succinctness

**Goal:** strip redundancy. "A quintuple bogey 10 on the par-5 12th" carries the same number three times — only two of {quintuple, 10, par-5} are needed. Aim for one form per reference.

**Specific rules to consider:**
- Pick **two of three** when describing a score: {result name, raw score, par}. The third is derivable.
- Abbreviate result names in casual prose: `quint`, `quad`, `sext`, `trip` (or `triple`). Reserve full forms for the very first appearance in a report, or for emphasis.
- Drop adjectives that don't earn their place: "a stunning 10", "a remarkable bogey".
- Remove ceremonial phrasings the dry draft tends to inherit: "the trouble was…", "the day's defining number…", "what made all this matter…".

**How to test:** word-count + readability check on a regen. The same beats, but tighter. Compare against the current TEG 8–11 outputs.

**Notes:**
- The lint pass (Haiku) currently kills repeated dramatic words; extend it to also collapse the redundant-trio pattern? Or keep it in the writer prompt so the lint stays narrow?
