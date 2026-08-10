# Reporting — Experiment log

Running list. Each entry: what was tried, how it was tested, what the verdict was. Settled entries
are kept (briefly) so we don't re-run them; open entries are the live agenda.

**Regen anchor for style experiments: TEG 14.** Tight 2-point finish, multiple courses — the case
that most tempts the writer into fabrication, so regressions show there first. TEG 18 (blowout with
a Jacket-leader → Spoon-winner subplot) is the useful second read.

---

## OPEN

### H8. Humour dial — 3 vs 6 vs 8 vs 8b *(the live decision)*

**Goal:** the published reports sit at roughly 3/10 humour — deadpan gravitas, very dry. Test whether
dialling up lands better with the insider audience, and which added register works.

**What was run** (`scripts/humour_dial.py` — takes a finished report and rewrites at a higher level):

| Variant | Register added on top of the Ronay/Peck/Armstrong/Iannucci baseline | Outputs |
|---|---|---|
| baseline ≈3/10 | — | `teg_{14,18}_report_styled.md` (**what the site shows today**) |
| `humour6` | ≈6/10 | TEG 14, TEG 18 |
| `humour8` | ≈8/10 | TEG 14, TEG 18 |
| `humour8b` | ≈8/10 **Brooker-only** — drops Clive James and the literary-comparison register, adds Marina Hyde. Physical/contemporary comparisons (broken household objects, malfunctioning tech, bodily indignity) instead of literary ones; short sentences; running jokes that accumulate; punch not flourish | TEG 14 only |
| `humour8bb` | Brooker-only retry on TEG 18 | **never produced** — connection reset mid-run |

**How to settle it:** read `teg_14_report_styled.md` against the three TEG 14 variants side by side,
then the TEG 18 pair. Score on: does it still read as faithful; does the added humour land or strain;
would the players enjoy it more. Then fold the winning register into `WRITER_SYSTEM` and record the
verdict here.

**Notes:**
- Nothing was published. `scripts/humour_dial.py` is still pointed at `TEGS = [18]` mid-retry.
- This blocks the regeneration work — don't regenerate the stale reports until the voice is locked.

**Verdict:** _(open)_

---

### 2b. Embed actual scorecards (HTML) inside reports

**Goal:** if a scorecard is visible inline, the writer can stop spelling out per-hole sequences and
focus on what those sequences *mean*. Heavy lifting moves to a deterministic block; prose carries
interpretation.

**How to test:** build a `build_round_scorecard_html(teg, round)` helper emitting a styled HTML table
(hole / par / each player's gross). Inject it into the report. Regen one round under a writer prompt
told "the scorecard is rendered inline, do NOT enumerate; reference holes by number, comment on what
the score means."

**Notes:**
- **Not built.** No `build_round_scorecard_html` exists.
- Partially superseded: `render.build_round_scores()` already puts a deterministic round-scores block
  at the top of every round report, and the records appendix covers PBs/records. The open part is the
  *hole-by-hole* table.
- Open question: at top of report (with the round-scores block), or after the prose as a data appendix?
- Open question: does the styled output need CSS additions to render the table on both surfaces?

**Verdict:** _(open — lower priority than H8)_

---

## SETTLED

### 1. Style principles for the dry / satirical / humorous voice → **LANDED**

**Was:** make the voice deliberate rather than accidental — build a named list of principles and test
which combinations produce the voice we want.

**Outcome:** landed as the **"Named principles"** block in `WRITER_SYSTEM` (and mirrored in
`ROUND_WRITER_SYSTEM` and `ENRICH_SYSTEM`). Eight principles, built on an explicit core mechanism —
**subverted gravitas**: treat trivial stakes with the solemnity of a geopolitical crisis; the humour
lives in the gap; never wink at the camera. The principles cover: doomed seriousness rendered
honestly; bathos as the engine; trust the reader; balance ledger against emotional landscape; no
scoring redundancy; precise and earned over generic; trace the player arc within the round;
achievements get the same solemnity as disasters.

A separate voice-ladder A/B (`v0_existing` → `v1_baseline` → `v2_restraint` → `v3_economy` →
`v4_observer` → `v5_gravitas`, run on TEG 10 tournament + R2) fed this. *Inferred, not recorded:*
the ladder's final rung is `gravitas` and "subverted gravitas" is what ended up in `WRITER_SYSTEM`,
so gravitas appears to have won — but no verdict was written down at the time. The six variants are
still on disk at `teg_10_tournament_v{0..5}_*.md` and `teg_10_round_2_v{0..5}_*.md` if the comparison
needs redoing.

### 2. Writing must add value beyond the scorecard → **LANDED**

**Was:** the deterministic blocks already show what each player shot; the prose should do what a
scorecard can't — tournament context, historical context, PB flagging, cross-round threads,
cross-player comparisons, venue context, causal explanation.

**Outcome:** landed as the **PALETTE** block in `WRITER_SYSTEM` — seven named context vehicles, with
a hard rule that **at least one must be prominent** (featured in the opener *and* threaded through
the body):

(a) cross-TEG career storylines · (b) per-course player history · (c) course/venue character ·
(d) decisive-moment framing + counterfactual · (e) player-thread continuity within the tournament ·
(f) records and rare feats woven into prose · (g) foreshadow/payoff threads

Backed by real code, not just prompt exhortation: `history_context.py` (career storylines),
`course_history.py` (per-course history + new course records, which become mandatory beats),
`tournament_shape.py` (decisive/close-finish signal), and `StoryPlan.payoffs[]` (every foreshadow
seed must be paid off in a named section — this was the single most common thinness).

### 3. Verbal succinctness → **LANDED**

**Was:** strip redundancy. "A quintuple bogey 10 on the par-5 12th" carries the same number three
times — only two of {result name, raw score, par} are needed.

**Outcome:** landed twice over —

1. **Principle 5** in `WRITER_SYSTEM`: never use gross score, relation to par, and par of the hole
   all at once. Two is enough.
2. The **ECONOMY** block — 11 construction rules: em-dash ceiling of two per paragraph;
   subordinate-clause budget; no "particular kind of X" preambles; no subject-burying preambles;
   plain word over inflated phrasing; split run-on factual lists; two equal facts = two sentences;
   one aside form per sentence; compressed rhythmic lists and bogey shorthand ("quad, triple, double");
   punchline isolation; one dominant idea per paragraph.

**Design decision:** these were deliberately baked into `WRITER_SYSTEM` so the writer constructs tight
on the *first* pass, rather than relying on a fix-up pass. The standalone `tighten_prose()` /
`TIGHTEN_SYSTEM` lever still exists (same 11 rules) and was used to produce the `*_report_tightened.md`
references, but is **not** in the default chain. Snapshots before/after are at
`teg_{9,10,11,13,14,18}_report_pretighten.md`.

The lint pass (Haiku) stayed narrow — repeated/over-used words only. It does not collapse the
redundant-trio pattern; that is the writer's job.
