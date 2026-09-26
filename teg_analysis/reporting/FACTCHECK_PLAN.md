# Fact-check upgrade — plan (approved 2026-09-26; WP1–4 + 7 built AND run 2026-09-26)

**Temporary working doc.** Delete it, or fold it into `STATUS.md` / `ARTEFACTS.md`, once WP5–6 ship too.

**WP1–4 + 7 status: built, tested, and run for real against TEG 18.** 0 regressions, full suite
genuinely all-green (see below). WP5 (repair the 85 reports) and WP6 (missed-fact detection) remain
open — see [STATUS.md](STATUS.md)'s START HERE entry for the session summary and `ARTEFACTS.md`
⑨/⑨b for the rebuilt component detail.

**The real TEG 18 extraction run found 4 errors + 1 warning** — one exactly matching item 1, one
matching item 4, one a different manifestation of item 2's round/weekday ambiguity, and **two
genuinely new, previously undiagnosed errors** (see [Real extraction run](#real-extraction-run-teg-18-2026-09-26)
below). Getting a trustworthy result took three environment fixes and three rounds of prompt/checker
hardening after the first two extraction attempts failed outright.

**TEG 18's 3 confirmed errors were then repaired in place** (item 2's finding turned out to be a
misextraction, not a real error — see below) and the fix was committed to
`teg_18_report_storylinefirst.md`; `_styled.md` regenerated; the PDF is flagged stale (`playwright`
not installed in the build session — rebuild with `scripts/build_report_pdfs.py --tegs 18` when it is).

**Then the full 85-report sweep ran three times**, each round fixing systemic extractor/checker bugs
the previous round's real output surfaced — see
[Full-corpus sweep](#full-corpus-sweep-2026-09-26-not-finished) below for the complete account,
the two fixes still needed, and the 5 new genuine errors already found and verified against real
data, ready to repair.

**Goal:** no factual error or ambiguous claim in a report can ship silently. Code decides what is true; a model only lists the claims and rewrites flagged sentences.

**Chosen path: "A".** Build the checker, fix the causes upstream, then check and repair the 85 existing storyline-first reports **in place** (17 tournament, 68 round). Nothing is regenerated, so the approved stories and headlines are kept.

## Why — the TEG 18 diagnosis

Every item below was checked against the parquet data.

| # | Report says | Truth | Verdict | Introduced by |
|---|---|---|---|---|
| 1 | Jon Baker's "six" at the R2 7th handed the Jacket lead to Williams; the Jacket story says Williams "drew level at the 13th" | He made an **8**; the 6 was Williams's. The lead changed hands at R2 H6/7/9/10/12/13/14 and R3 H2. | Real error, plus an omission | **Code:** the `long_lead_lost` beat (`events.py` ~l.399) attaches the new leader's hole. The Jacket plan didn't cite beats b87/b88/b90. |
| 2 | Patterson "added another [8] at the 4th on Sunday" | Sunday = R2, and he did make an 8 at the R2 4th. The paragraph is about R1. | Ambiguous | Draft: the "rounds not weekdays" rule is missing from the draft prompt |
| 3 | Alex Baker's double at the 17th "ended the run of par or better" | Gross 14–16 was par, birdie, par, so this is true. The previous sentence covers 8–12 (three bogeys). | Ambiguous (span) | Draft |
| 4 | Patterson was "comfortably the better player over four rounds" | Trophy: AB 169, JP 161. True only on gross (JP 383 vs AB 412). | Real error | Plan subject, hardened by the voice pass |
| 5 | Mullin went "from second to the bottom" of the Spoon race | Before the 15th he was tied 2nd with two others, 1 point off the bottom | Misleading | **Code:** `spoon_change` rank fields hide ties; rank 1 = best, which reads backwards in the Spoon race |
| 6 | (not mentioned) Williams's R4 84 equals Mullin's R3 84 Stadium record | True | Missed | **Code:** `course_history.detect_course_records` uses strict `<` and compares with prior TEGs only |

Related: Williams's R4 84 "eight better than his previous best there" ignores his 85 in R3 of the same TEG (`build_player_course_history`'s "prior" excludes this TEG).

**What each safeguard missed today:**
- **D1:** `DRAFT_WRITER_SYSTEM` (`scripts/storyline_full_report_experiment.py`) carries only RANKING/NAMING/DOUBLE — not `SHARED_FAITHFULNESS`. The voice pass has the rules but sees no data.
- **D2:** fine (standings, results box, records appendix).
- **D3:** `verify --all` globs `teg_*_report_final.md`, which was archived on 2026-09-11, so it checks nothing. The eight checks are word-level only.
- **Baseline today** over the 85 storyline-first files: 3 errors, 33 warnings.

## Work packages (in order)

### 1. Point D3 at the current reports — free — **done**
- `verify.py`: `--all` and `load_context` resolve `teg_N[_round_R]_report_storylinefirst.md` by default; legacy `report_final.md` is reachable via `--label final` or `text=`.
- Findings persist next to the report (`{stem}_verify.json`), written by the CLI and by `restyle_voice`/`apply_corrections` — previously stdout-only.
- **Re-baselined (2026-09-26):** 85/85 files found (0 under the old glob). **3 errors, 33 warnings** — identical to the pre-existing "baseline today" figure above, confirming the fix surfaces the real count rather than a new one.

### 2. Upstream fixes — free, no new LLM calls — **done**
- `events.py` `long_lead_lost`: attaches **both** players' hole evidence, each labelled, plus flat `taken_at_hole`/`lost_at_hole`.
- Lead/Spoon beats: `tied_with` / `tie_size` added; Spoon beats now use `spoon_rank_before/after` + `position_label` (e.g. "T2 of 5, 1 pt above last") instead of the Trophy-direction rank columns. "Took Lead" now fires on a recapture from a tie — root cause was a boolean-`shift()` → object-dtype `~` bug in `commentary.create_round_events`'s new outright-tracking columns, not just a missing condition; TEG 18 R2 H7/H12/H14 (Jacket) now fire, matching the diagnosis exactly.
- **Adjacent bug found and fixed:** the Jacket's `lead_change` beat context read the *Trophy's* rank_before/after columns unconditionally, not the Gross ones — same defect class as the Spoon bug, not one of the six original items.
- `course_history.detect_course_records`: emits `course_record_equalled` / `course_record_high_equalled`; walks each TEG's rounds on a course chronologically against a running best, so a same-TEG round is compared with an earlier same-TEG round. TEG 18's Williams R4 84 now correctly equals Mullin's R3 84 at the Stadium course.
- `build_player_course_history`: exposes `best_earlier_this_teg` / `best_earlier_this_teg_round`.
- `DRAFT_WRITER_SYSTEM` (and the round equivalent): both now carry `prompts.SHARED_FAITHFULNESS` + a newly-extracted `prompts.WEEKDAY_RULE` (pulled out of `_WRITER_FAITHFULNESS_TOURNAMENT`, byte-identical, imported not retyped).
- All of `tests/test_reporting_prompts.py`, `tests/test_round_storyline.py`, `tests/test_reporting_schema_and_era.py` pass unchanged in behaviour (new assertions added, none removed).

### 3. Settled facts for the writer — free — **done**
New `teg_analysis/reporting/settled_facts.py`, wired into both draft writers' `_context_for` as `context.settled_facts`:
- **Round→day map** (`R2 = Sunday`) — leak-safe via `through_round`.
- **Lead timeline** per competition (Trophy, Jacket, Spoon), tie-aware — records only OUTRIGHT leader identity changes, matching `long_lead_lost`'s tenure semantics (a tie doesn't count as losing the lead).
- **Final totals** per competition (Jacket in raw gross strokes, matching how players actually read it) plus `decisive_metric`.
- **Tie-aware rank snapshots**, scoped to the holes referenced in `lead_timeline` (not every hole — that would be ~72 holes of noise).

Both draft prompts reference it directly ("check it, do not just copy it" — the existing `round_by_round_status` precedent's wording).

### 4. Claim extraction + code checks — 1 LLM call per report — **done, run for real**
- **Extractor:** `claims.py`, one `llm.generate_structured` call, `claude-sonnet-5`, API billing (confirmed at kick-off), **`thinking=False`** — see [Real extraction run](#real-extraction-run-teg-18-2026-09-26): adaptive thinking reproducibly burns the whole `max_tokens` budget on this call and returns no output. Input: report text only. Output: a list of claims, each with a **verbatim quote**. Claims whose quote isn't in the text are dropped.
- **Claim types implemented:** `hole_score`, `weekday`, `total`, `rank_change`, `lead_event`, `comparison`, `run` — all checked against `settled_facts.py`'s data. `record` is extracted but has no checker yet (reports `severity="unchecked"`).
- **Cache:** `{stem}_claims.json`, keyed by a SHA-256 of the report text. `verify --all --claims` re-extracts only when the text changes.
- **Checker:** `claims.FactBase` (built from `settled_facts.build_hole_timeline` + `build_settled_facts`), one function per claim type.
- **Severity**, confirmed both against hand-written TEG 18 fixtures (`tests/test_reporting_verify.py::TestClaimChecks`, no LLM call) and against the real extraction run:
  - **Error:** item 1 (`hole_score` — the data flatly contradicts the claimed score) — the real run reproduced this exactly, plus found two new ones (see below).
  - **Warning:** item 4 (`comparison`, unqualified — the two competitions disagree on who was "better", exactly the plan's "true only on gross" diagnosis: a genuine ambiguity, not a flat contradiction). The real run reproduced this exactly. Item 2 (`weekday`, wrong round) and item 5 (`rank_change`, hides a tie) are confirmed only against hand-written fixtures — neither's exact sentence shape was independently re-flagged by the real run (see below for what the run found instead).
  - **Unchecked:** `record` claims; any `comparison` with an explicit metric/competition named; a `total` claim naming a specific round rather than the tournament (no per-round total is wired into `FactBase` yet).
  - **Item 3** (a cross-sentence span-redundancy ambiguity — two separate `run` claims referencing adjacent-but-distinct spans) is **not mechanically checkable from a single claim** in this cut; each `run` claim is validated in isolation and both would pass independently. Left as a known gap.

#### Real extraction run, TEG 18 (2026-09-26)

Getting a trustworthy result took three separate fixes, in order:

1. **Environment.** No `ANTHROPIC_API_KEY` reached the worktree (`.env` is gitignored, so `git worktree add` never copies it — untracked files don't propagate to a new worktree) and `anthropic` wasn't installed in the interpreter. Fixed by copying `.env` and installing the SDK; then found `llm.get_api_key()` never called `load_dotenv()` itself (only `webapp/app.py` does), so a bare `teg_analysis.reporting` CLI was blind to `.env` regardless — fixed by adding `load_dotenv()` to `get_api_key()`, mirrored by a test fix (`test_reporting_provider.py`'s "no key" test now patches `dotenv.load_dotenv` to a no-op, since a real `.env` would otherwise silently defeat it).
2. **Adaptive thinking burned the entire budget with zero output**, at 16000, at 20000, and with no `thinking` param at all (the model's own default) — confirmed reproducible and confirmed NOT max-tokens-related by testing the API directly: `thinking={"type": "disabled"}` fixed it outright (88 claims, `end_turn`, zero thinking tokens), while Opus succeeded immediately with thinking on. Added a `thinking: bool` parameter to `generate_structured`/`_api_structured`, mirroring the one `generate_text` already had; `extract_claims` now passes `thinking=False`.
3. **Three checker/prompt bugs**, found by the run itself and fixed before trusting the output — this is the false-alarm sweep doing its job:
   - The extractor invented a `run` basis ("par or better") for sentences that only state a point total for a hole range ("21 points from holes 11 to 16") — no per-hole result was actually stated. Tightened `EXTRACTOR_SYSTEM` to require the text explicitly name the per-hole category for the WHOLE span, and to skip the claim rather than guess.
   - The extractor was **hallucinating raw scores from qualitative descriptors** ("doubles at the 5th, 6th and 10th" → a fabricated `hole_score` claim with a guessed number) — it can't know a hole's par from text alone, so it was guessing. Tightened the prompt to only fill `score` when the text states an explicit number.
   - `_check_total` assumed one unit for the Jacket; the report states it in gross-vs-par ("+66"), `settled_facts.py` stored raw strokes (354) — same number, different units, flagged as a false error. Added `total_vs_par` to the Jacket's `final_totals` entries; the checker now accepts either representation. Also added a guard: a `total` claim naming a specific round is a round score, not the tournament total — unchecked rather than wrongly compared.

**Final result: 4 errors, 1 warning, 49 unchecked.**

| Finding | Matches | Detail |
|---|---|---|
| `claim_hole_score`: Jon Baker scored 8 at R2 H7, claim says 6 | **item 1**, exactly | "…where a six handed the lead to Gregg Williams" — the six was Williams's |
| `claim_comparison`: warning, Patterson/Baker | **item 4**, exactly | Trophy and Jacket disagree on who was better |
| `claim_hole_score`: John Patterson scored 5 at R4 H4, claim says 8 | **item 2's ambiguity**, different shape | The real R2 H4 score (8) got attributed to R4 H4 by the extractor conflating "the 4th" (a hole) with "Sunday" (R2) — the same round/hole/weekday confusion item 2 diagnosed, just caught via `hole_score` rather than `weekday` |
| `claim_run`: Gregg Williams R1 H1 was a par, contradicting "did not make a hole better than bogey" through H14 | **new**, not one of the six | Verified directly against the parquet |
| `claim_run`: Gregg Williams R3 H1 was a bogey, contradicting "four pars opened round three" | **new**, not one of the six | Verified directly against the parquet |

Items 2 (exact weekday shape), 3 and 5 were not independently re-flagged by this run — either the extractor didn't isolate them as separate checkable claims this time (item 5's exact sentence extracted with `round`/`hole` both null, since the sentence itself doesn't restate them — falls to `unchecked`, not a miss of the checker), or (item 3) they're the documented cross-claim gap above. **Two new, previously undiagnosed real errors were found** — a concrete demonstration of the sweep's value beyond re-confirming the six known items.

**The 17-report sweep itself was not run** — one report's worth of iteration was enough to find and fix the systematic issues above; running all 17 now would be re-spending on calls whose failure modes are already fixed. Do that sweep before WP5.

### 5. Repair in place (path A) — 1–2 LLM calls per flagged report
- For each error/warning, send the **flagged sentence + surrounding paragraph + the correct facts computed by code** to a repair call. It returns a replacement sentence only, in house voice (reuse `VOICE_CORE` / `SENTENCE_DISCIPLINE`).
- Splice the replacement in, re-extract and re-check. Stop when clean or after 2 rounds. Anything still flagged → a human queue.
- Show the diff for review. Write to `_storylinefirst.md` only on approval, then re-run the free restyle (`_styled.md`) and the PDF build (`scripts/build_report_pdfs.py --check`).
- Run tournament reports first (17), then round reports (68).

### 6. Missed facts (item 6) — free
Code lists the must-mention facts: records set or equalled, the winner's decisive lead change and personal-worst/best records. Flag any one no claim covers, as a **warning** ("not mentioned"). It uses WP2's detectors and needs no model call.

### 7. Tests and docs
- `tests/test_reporting_verify.py`: hand-written claim fixtures against real TEG 18 data (no LLM) — **done**. Items 1 (error), 2, 4, 5 (warnings) confirmed; item 3 documented as an out-of-cut gap, not force-fitted; item 6 (missed-fact) is WP6, not built. Plus `--all`/`--label` glob tests, `_verify.json` round-trip, and the quote-not-found-drops-the-claim rule.
- `tests/test_reporting_detectors.py` — **done**: WP2's fixes against real TEG 18 data (both players' hole evidence, the exact H6/7/9/10/12/13/14 recapture sequence, Gross-not-Trophy ranks on the Jacket beat, Spoon direction + ties, the same-TEG course-record equal).
- Docs updated same session: `STATUS.md` (START HERE), `ARTEFACTS.md` (⑨ rewritten + new ⑨b), `README.md` D1–D3 table + module table, `DATA_FLOW.md` (new artefacts noted in the Storage Layer section).

## Acceptance
- TEG 18: item 1 is an error (confirmed by the real run); item 4 is a warning (confirmed by the real run); items 2 and 5 are confirmed as errors/warnings only against hand-written fixtures, not independently re-caught by the real run in their exact original shape (see the extraction-run table above for what it caught instead — including two new real errors). Item 3 is a known gap, not force-fitted into a false positive. Item 6 (missed-fact) is WP6, not attempted.
- No new **errors** on `verify --all` beyond real ones confirmed by hand — **re-baselined 2026-09-26: 3 errors, 33 warnings across all 85** (mechanical checks only), unchanged from the pre-fix count, confirming the glob fix surfaces the true count rather than a different one.
- The false-alarm sweep (`--claims` across all 17 tournament reports) is **not yet run** — one report's worth of iteration surfaced and fixed three systematic extractor/checker bugs first; see [Real extraction run](#real-extraction-run-teg-18-2026-09-26). Run the sweep next, before WP5.
- After repair (WP5, not started): every report has 0 errors; any remaining warnings are signed off by a human.
- Tests: targeted reporting suite passes (113+ tests across the affected files), plus a full-suite run (justified — WP2 touches `analysis/commentary.py`, a shared module): genuinely all-green once the environment fixes above landed (the one failure seen mid-session, `test_reporting_provider.py`, was the same missing-`anthropic`-package issue being fixed, not a new regression).

## Cost (rough; API rates Sonnet 5 $2/$10 and Opus 5 $5/$25 per M tokens)

| Item | Per tournament report | 85-report repair run |
|---|---|---|
| Claim extraction (Sonnet) | ~$0.07 (rounds ~half) | ~$4 |
| Repair + re-check, 1–2 rounds | ~$0.10–0.20 | ~$6–10 |
| **Total path A** | | **~$10–15** |

Plan usage: $0 cash, ~170–250 mailbox prompts. That is feasible but mind the weekly cap. Human review: ~2–3 h of diffs.

**Effort:** WP1–4 + 7 ≈ 1–1.5 days of agent work; WP5–6 ≈ another day.

## Decisions confirmed at kick-off (2026-09-26)
- **Extraction model:** Sonnet tier, **API billing** (not plan usage) — `claude-sonnet-5` in `claims.py`.
- **False-alarm sweep:** all 85 reports (not just tournament, not a sample) — **run three times**, see below.
- **Repair model:** Opus — used for TEG 18's 3 repairs; not yet run at scale for WP5.

## Full-corpus sweep (2026-09-26)

`python -m teg_analysis.reporting.verify --all --rounds --claims` run three times against all 85 reports, fixing real systemic bugs the previous round's output surfaced each time. A fourth pass re-checked the cached claims for free after two more checker fixes:

| Sweep | Errors | Fix applied after |
|---|---|---|
| 1 | 230 | Spoon rank direction (`_rank_source_for` used the inverted `_SpoonRank` column — 19 false errors); margin/lead-gap claims misclassified as `total` (~150 false errors); `run` claims invented from aggregate point totals; `hole_score` hallucinated from qualitative descriptors; Jacket total unit mismatch |
| 2 | 133 | "Last"/"bottom" language made the extractor emit `value=1` (a regression from the spoon fix's wording) — tightened to leave `value` null rather than guess; `total` tightened further to explicitly exclude round/partial scores |
| 3 | 65 | Sign-tolerance fix ("18 under" vs stored `-18`); one outdated test assumption fixed (`test_item5_shared_rank_is_warning` was keyed to the old inverted Spoon column) |
| 4 (free re-check of cached claims) | 60 → 52 | 60 = sweep 3's 65 less TEG 18's repaired errors. Net-vs-gross axis + negation in `_check_run`; `rank_change` value=1 with last-place/Spoon language → unchecked. 8 false errors cleared, 0 new |

**How to re-check for free:** the cached `{stem}_claims.json` files hold every report's extracted claims. Load them, build `build_fact_base(teg, round_num=...)`, and call `check_claim_list` — no LLM call unless the report text changes.

### Checker fixes made in sweep 4

1. **Net-vs-gross axis in `_check_run`.** `_run_axis` picks `NetVP` when the quote attaches a per-hole result to the net axis ("without a net par", "pars-or-better against his handicap"), else `GrossVP`; both → unchecked. NetVP is equivalent to Stableford ≥ 2 for "net par or better" and scales the other basis levels. Aggregate net language ("gained five shots on net par", "three shots to par against his handicap") does NOT switch the axis — both were regressions in a first draft.
2. **Dropped negation.** The extractor often turns "without a net par" into basis `par`. `_NEGATED_PAR_RE` flips `par`/`par or better` to `bogey or worse` for "without/never (a) (net) par". Kept tight: "without dropping a shot to par" means the opposite and is not flipped.
3. **`rank_change` value=1 with "last"/"bottom"/"foot of the field" in the quote, or any Wooden Spoon claim** → unchecked. The Spoon condition matters: three of the five TEG 5 R1 false errors ("Meller briefly reclaimed the position") carry no "last" word in the quote itself.

Tests: `tests/test_reporting_verify.py` (six fixtures against real data, no LLM).

### Remaining noise (not fixed)

- **Before/after value confusion in `rank_change`** — "from fourth to last" extracted with `value=4` (the BEFORE rank), checked against the AFTER state. At least 5 of the remaining 9 `rank_change` errors (TEG 4, 5, 13 R3, 15, 9 R1). Cheapest fix: treat "from <ordinal> to …" as unchecked, or add `before`/`after` fields to the extractor.
- **Round misattribution** — the extractor attaches the wrong round to a sentence whose paragraph names it earlier. Both "confirmed" TEG 5 and TEG 16 R2 errors below turned out to be this. No code fix; the rule stays: verify against the paragraph before repairing.
- Residual round-vs-tournament `total` confusion (~11) and span/basis slips in `run` — likely an acceptable floor.

### Repairs — sweep-3 candidates re-verified against paragraph context + parquet

**Not errors (extractor misattribution) — left unchanged:**
- TEG 5 tournament: "16th, 17th and 18th in level par gross" (Neumann). The paragraph opens "Wednesday's move to Palmares" — that is R4 (0, 0, 0 gross; round of 96), not R3.
- TEG 16 R2: "three holes running without a single net par" (Alex Baker). True in round 2 (net +2, +1, +1 at 13-15); the extractor attached round 1.

**Real errors — six repairs drafted, NOT yet written (awaiting approval)** via `claims.repair_report()` on the `agent` provider (Opus, fresh subagent per prompt), mechanical re-verify clean, each new sentence hand-checked against the parquet:

| Report | Was | Now |
|---|---|---|
| TEG 15 R3 | "ran holes 3 to 7 without dropping a gross shot" (Patterson; bogey at the 4th) | "…for just one dropped gross shot, a bogey at the 4th" |
| TEG 15 R3 | "then ran four holes without managing better than a bogey" (Alex Baker; the 5th was a birdie) | "three holes" |
| TEG 15 R3 | "9 points from the closing three holes … bogey-par-bogey" (Neumann; that was 14-16, the closing three scored 5) | "the next three holes" |
| TEG 15 R2 | "extended the run to six holes without a gross shot dropped" (Williams; bogey at the 8th) | bogey at the 8th named; "six pars in seven holes" |
| TEG 13 tournament | "arrived at the tee fourth from bottom" (Mullin; he was 4th of 5) | "second from bottom" |
| TEG 18 R1 | bogey at the 5th moved him "into outright second place" in the Jacket (Jon Baker; it took him into the outright lead) | "into the outright lead" |

The plan's earlier table placed the two TEG 15 Baker/Neumann errors in the tournament report; both are in the R3 round report.

**Known gap in the re-verify:** re-extracting a single repaired paragraph loses the round context, so most re-extracted claims come back `unchecked`. The hand check against the parquet is what actually verified these six.
