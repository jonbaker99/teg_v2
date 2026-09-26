# Fact-check upgrade — plan (approved 2026-09-26, not yet built)

**Temporary working doc.** Delete it, or fold it into `STATUS.md` / `ARTEFACTS.md`, once the work ships.

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

### 1. Point D3 at the current reports — free
- `verify.py`: `--all` and `load_context` resolve `teg_N[_round_R]_report_storylinefirst.md`. Keep reading legacy `report_final.md` only via explicit `text=`.
- Persist findings next to the report (`..._verify.json`) so results survive the run; today `restyle_voice` only prints them.
- Re-baseline and record the counts here.

### 2. Upstream fixes — free, no new LLM calls
- `events.py` `long_lead_lost`: attach the **losing** leader's hole (or both players' holes, each labelled with the player).
- Lead/Spoon beats: add `tied_with` / `tie_size` and a race-direction-safe label (e.g. "T2 of 5, 1 pt above last"). Emit "Took Lead" for recaptures (R2 H12/H14 are missing).
- `course_history.detect_course_records`: emit `course_record_equalled` (ties), and compare later rounds with earlier rounds of the same TEG.
- `build_player_course_history`: expose `best_earlier_this_teg` so "previous best" can't skip a same-TEG round.
- `DRAFT_WRITER_SYSTEM` (and the round equivalent): add `prompts.SHARED_FAITHFULNESS` plus the weekday rule from `WRITER_FAITHFULNESS`. Don't retype them; import them.
- Re-run the tests that pin these prompts (`tests/test_reporting_prompts.py`) and `tests/test_round_storyline.py`.

### 3. Settled facts for the writer — free
Add to the bundle / draft `context`, computed by code:
- **Round→day map** (`R2 = Sunday`).
- **Full lead timeline** per competition (every change, tie-aware).
- **Final totals** in every competition, plus which metric decides each competition.
- **Tie-aware rank snapshots** at each beat.

It helps future generations. For repair (WP5) it is the source of the corrections.

### 4. Claim extraction + code checks — 1 LLM call per report
- **Extractor:** one structured call (`llm.generate_structured`, cheap model, Sonnet tier). Input: report text only. Output: a list of claims, each with a **verbatim quote**. Claims whose quote isn't in the text are dropped.
- **Claim types:** `hole_score`, `lead_event`, `rank_change`, `comparison` (players, span, metric stated or not), `run` (player, round, holes, basis, ended_by), `weekday`, `record` / `personal_best`, `total`.
- **Cache:** `..._claims.json`, keyed by a hash of the report text. `verify --all` stays free and deterministic; the model only re-runs when the text changes.
- **Checker (code):** new `teg_analysis/reporting/claims.py` (or a section of `verify.py`) with one check per type, against `load_all_data` and the existing `teg_analysis` / records functions. Build one hole-by-hole standings timeline (cumulative Gross / Stableford, tie-aware ranks) and reuse it for leads, ranks and totals.
- **Severity:**
  - **Error:** the data contradicts a fully resolved claim (items 1, 4).
  - **Warning:** the claim is ambiguous — tie hidden, gross/net basis unstated where it matters, span unclear, or weekday and paragraph round disagree (items 2, 3, 5).
  - **Unchecked:** the claim type is not covered. Counted and listed, never reported as "passed".
- **Cross-story contradictions** need no separate check: every claim is checked against one timeline.

### 5. Repair in place (path A) — 1–2 LLM calls per flagged report
- For each error/warning, send the **flagged sentence + surrounding paragraph + the correct facts computed by code** to a repair call. It returns a replacement sentence only, in house voice (reuse `VOICE_CORE` / `SENTENCE_DISCIPLINE`).
- Splice the replacement in, re-extract and re-check. Stop when clean or after 2 rounds. Anything still flagged → a human queue.
- Show the diff for review. Write to `_storylinefirst.md` only on approval, then re-run the free restyle (`_styled.md`) and the PDF build (`scripts/build_report_pdfs.py --check`).
- Run tournament reports first (17), then round reports (68).

### 6. Missed facts (item 6) — free
Code lists the must-mention facts: records set or equalled, the winner's decisive lead change and personal-worst/best records. Flag any one no claim covers, as a **warning** ("not mentioned"). It uses WP2's detectors and needs no model call.

### 7. Tests and docs
- `tests/test_reporting_verify.py`: hand-written claim fixtures against real TEG 18 data (no LLM). They flag items 1–5 (1, 4 errors; 2, 3, 5 warnings) and item 6 as a missed-fact warning. Plus tests that the new `--all` glob finds storyline-first files and that a missing quote drops the claim.
- Detector unit tests for WP2.
- Docs: `reporting/STATUS.md` (START HERE entry), `ARTEFACTS.md` (⑨ rewritten; new artefacts `_claims.json` / `_verify.json`), `README.md` D1–D3 table, `DATA_FLOW.md` §10 if the artefact list changes.

## Acceptance
- TEG 18: items 1 and 4 are errors; 2, 3 and 5 are warnings; item 6 is a missed-fact warning.
- No new **errors** on `verify --all` beyond real ones confirmed by hand. Warnings are reviewed on the 17 tournament reports.
- After repair: every report has 0 errors; any remaining warnings are signed off by a human.
- Tests pass (run the reporting test files, not the whole suite, unless WP2 touches shared modules).

## Cost (rough; API rates Sonnet 5 $2/$10 and Opus 5 $5/$25 per M tokens)

| Item | Per tournament report | 85-report repair run |
|---|---|---|
| Claim extraction (Sonnet) | ~$0.07 (rounds ~half) | ~$4 |
| Repair + re-check, 1–2 rounds | ~$0.10–0.20 | ~$6–10 |
| **Total path A** | | **~$10–15** |

Plan usage: $0 cash, ~170–250 mailbox prompts. That is feasible but mind the weekly cap. Human review: ~2–3 h of diffs.

**Effort:** WP1–4 + 7 ≈ 1–1.5 days of agent work; WP5–6 ≈ another day.

## Decisions still open (confirm at kick-off)
- **Extraction model:** Sonnet tier, on plan usage or API?
- **False-alarm sweep:** all 17 tournament reports (recommended) or a sample?
- **Repair model:** Sonnet or Opus (house voice may need Opus)?
