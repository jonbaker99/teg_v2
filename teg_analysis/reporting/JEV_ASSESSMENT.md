# Jev and the report pipeline — assessment (2026-09-26)

Spike notes. Temporary working doc: fold the verdict into `STATUS.md` and delete this file once the follow-up experiment below is run or dropped.

## Verdict: Jev cannot speed up or cheapen report writing, but it could strengthen checking

Jev cannot generate text. Every stage that costs time or money in our pipeline is text generation. So Jev cannot replace any paid call, and it cannot make a report arrive sooner.

Where it could help is **judgement**: typed yes/no, choice or score answers about text we already have. Our weakest area is exactly that — semantic fact-checking (Theme D) and scoring A/B experiments. Worth one small, measured spike there. Not worth wiring into generation.

**Spike result (2026-09-28): passed on 4 of 4 rules.** Adopt as an optional, advisory check. See *Spike result* below.

## What Jev is

Sources are launch-week articles and third-party tests; nothing below was verified by us.

- **Product.** A "System One" decision model from TypeSafe AI, public since 15 Sep 2026. It does not write text or code.
- **Interface.** Send a *state* (the text or data to judge) plus typed questions. It returns Choice, Score (a level on a described rubric) or yes/no answers, each with a calibrated probability. All questions are answered in one parallel pass.
- **Speed and price.** 70–500 ms per request. About $0.042 per million input tokens; output is free.
- **Limits.** About 32k tokens for the state plus the longest question (64k for state plus all questions). Larger inputs must be chunked.
- **Accuracy.** Independent tests put it roughly level with small LLMs on classification, with very good calibration (AUROC 0.99 in one third-party test). It is not a substitute for frontier-model reasoning.
- **Weaknesses.** Answers move with question wording. Adversarial or self-arguing text can shift a verdict. No written reasoning comes back, only numbers.

## Stage by stage

The live pipeline is **storyline-first** (`/teg-reports`). Legacy five-stage rows are noted only where they still matter. Costs are Opus-tier API; on `--plan` billing the marginal cost is plan usage, not dollars.

| # | Stage | What happens | LLM? | Would Jev help? |
|---|---|---|---|---|
| 1 | **Data load** | `load_all_data()` reads parquet | No | **No.** Deterministic. |
| 2 | **Beat detection + scoring** (`events.py`, `scoring.py`) | Detectors find 43–105 notable events; three axes rank them; top ~50 kept | No, free | **No.** Already free and instant. Swapping code for a model adds noise, not value. |
| 3 | **Context + bundle** (`history_context`, `venue`, `win_anatomy`, `vehicle_fit`, `assemble_bundle`) | Adds history, course, venue, win anatomy; scores narrative vehicles against a baseline | No, free | **Marginal.** `vehicle_fit` has four vehicles with no detector (`motif`, `bookends`, `ensemble`, `theme_led_body`) and four under-detected ones. Jev Score questions could fill those hints. But the hints are advisory, so the gain is small. |
| 4 | **Storyline plan** (`build_storyline_plan`) | Opus picks the 3 mandatory storylines, 0–3 discovered ones, titles, `why_it_matters`, self-scored `compelling_score` / `humour_score` | Yes, 1 call | **No for the plan itself** — it is open-ended writing. **Maybe** an independent re-score of candidate storylines to rank the lead, replacing the editor's self-score. Low priority. |
| 5 | **Structural draft** (`build_storyline_draft`) | One plain-prose section per storyline, fact-isolated to its own beats | Yes, ~5 calls | **No.** Pure generation. |
| 6 | **Voice pass** (`restyle_voice`) | Rewrites the draft in the house voice | Yes, 1 call | **No.** Pure generation. |
| 7 | **Verification** (`verify.py`, D3) | 9 mechanical checks: beat IDs, em-dashes, invented mechanisms, "a week", roster, sibling age order, weekdays, arithmetic, swings | No, free | **Yes — best fit.** See below. |
| 8 | **Styling + edition + PDF** (`render`, `newspaper_edition`, `report_pdf`) | Injects deterministic blocks; parses into a newspaper edition; renders PDFs | No, free | **No.** Deterministic. Descriptor badges could be a Choice question, but the rule-based fix (2026-09-22) already works. |
| — | **Legacy repetition lint** | Haiku replaces overused words | Yes | **No.** Needs rewritten text. |
| — | **A/B experiment judging** (`scripts/storyline_*_experiment.py`) | One blind Opus call scores arms on compellingness, grounding, richness, reads-as-story, with notes | Yes | **Partly.** See below. |

## Where Jev fits: semantic faithfulness checks (stage 7)

`README.md` → *Why D3 reduces the burden on D1* lists the faithfulness rules no code checks today:

- Same hole number in different rounds is not the same hole.
- A Stableford vs Gross gap is not a paradox.
- Relationships only from `player_relationships`.
- Early lead changes are not "chaos".
- `must_include` beats actually covered (partial).

Each is a narrow yes/no over one paragraph plus a small evidence slice. That is Jev's shape. A paragraph plus its storyline's evidence fits well inside 32k. At ~$0.04 per million tokens, checking all 17 reports costs well under a cent.

A second question per paragraph — "is every factual claim here supported by this evidence?" — would be an entailment check across the whole report. Today only an LLM or a human can do that.

**Why it matters.** Players are the readers and they catch every error. Theme D is the least-built theme and carries the most risk. This is improvement, not speed or cost.

**Caveats.** Calibration on golf-banter prose is unknown. Voice-pass prose is playful and hyperbolic, which may read as "unsupported". Findings would stay advisory, like the rest of D3.

## Where Jev partly fits: scoring A/B experiments

Every settled design choice came from a blind judge call. `STORYLINE_PLAN.md` flags the limit: N=3 TEGs, one judge call each. Jev could score each arm many times, across more rubric items, for almost nothing. That buys statistical power.

It cannot replace the judge. The written notes were repeatedly the most useful output ("what the judge actually flagged is more important"). And taste calls like humour are where a small-model-class judge is least trustworthy. Use it as a cheap second opinion, not the verdict.

## Why cost and speed will not move

- A full storyline-first report is ~7 LLM calls. The documented reference cost is ~$0.65 per report on the API. All seven calls are generation.
- `--plan` already routes those calls to claude.ai plan usage, so per-call dollars can already be near zero.
- The real time cost is human reading and iteration. Jev does not touch that, except by catching errors earlier.

## Costs of adopting it

- A new vendor, 11 days old, and another API key.
- A dev-only dependency. It must never enter `requirements.txt`: the webapp never generates reports.
- Question wording needs tuning and a labelled test set before its numbers mean anything.

## Spike result (2026-09-28): passes on all four rules

**Verdict: adopt Jev as an optional, advisory D3 check.** It met the pre-set bar on 4 of 4 rules; the bar needed 3.

| Rule | Pos / N | Regex P / R | Jev P / R @0.5 | Jev AUROC | Pass? |
|---|---|---|---|---|---|
| same_hole | 4/47 | 0.18 / 0.50 | 1.00 / 0.75 | 0.96 | Yes |
| paradox | 7/47 | 0.56 / 0.71 | 0.58 / 1.00 | 1.00 | Yes, narrowly on precision |
| chaos | 5/47 | 0.50 / 0.60 | 1.00 / 1.00 | 1.00 | Yes |
| relationship | 6/47 | 0.80 / 0.67 | 1.00 / 1.00 | 1.00 | Yes |

Run: 47 requests, median 316 ms, max 624 ms, 41,506 input tokens, $0.00174 in total. Raw answers: `scripts/jev_spike/results.json`.

**Errors at 0.5:**

- **paradox, 5 false alarms** (p 0.54 to 0.85). Two are "same hole" paragraphs, one of which explicitly says "same number, different hole". AUROC 1.00 means a higher threshold would separate them cleanly, but that threshold is picked on the same 47 rows, so it is not yet evidence.
- **same_hole, 1 miss** (`seed:sh1`, p 0.14). The link is implied by day names (Friday on the Tour course, Sunday on the Stadium), with no "same hole" phrase. The request state maps rounds to courses but not days to rounds, so Jev could not resolve it. That is a harness gap, not a clean Jev miss.

**Caveats.** Positives per rule are 4 to 7, so these are directions, not measurements. The labels were written by Claude. Jon reviewed 4 of the 5 paradox false alarms (2026-09-28) and agreed Jev was wrong on all 4; `paradox:7` ("the Spoon paradoxically tightened") is unresolved. The other 42 labels are unreviewed. Paradox precision only just clears the regex.

**Next steps if adopted:**

1. Add day-to-round mapping to the request state and re-run, so `seed:sh1` is a fair test.
2. Wire Jev into `verify.py` as an opt-in, advisory check. Keep it a dev-only dependency, never in `requirements.txt`.
3. Set the paradox threshold on fresh paragraphs, not these 47.
4. Fold this verdict into `STATUS.md`, then delete `scripts/jev_spike/` and this file.

### Spike setup

**Run it** (needs the key and network access to `api.typesafe.ai`):

```bash
python scripts/jev_spike/run.py --dry-run                 # free: regex baseline and a sample request
TYPESAFE_API_KEY=... python scripts/jev_spike/run.py      # 47 requests, well under a cent
```

It prints the metrics table, latency, input-token cost and every miss or false alarm. Raw answers go to `scripts/jev_spike/results.json`.

**What it does.** Each paragraph is one request with four yes/no questions, one per rule. The request state carries the facts the rules depend on: which course each round was on (from `all-data.parquet`) and `PLAYER_RELATIONSHIPS`. Without those, "same hole" and "relationship" are unanswerable.

**The labelled set** (`scripts/jev_spike/labels.json`, 47 paragraphs, labelled by Claude; see *Caveats* above for what Jon has reviewed):

- 31 real paragraphs from `data/commentary/`, mostly from archived reports. They include the known TEG 10 "same hole" fault and its correct twin (R1 and R4 were both at Boavista).
- 13 seeded paragraphs: violations written *without* the obvious keyword ("bedlam", "a question for the philosophers", "old school friends"), plus correct-framing twins.
- 3 clean paragraphs from served reports.
- Positives per rule: same hole 4, paradox 7, chaos 5, relationship 6. That's small, so treat any result as a direction, not a measurement.

**Baseline to beat: a keyword grep**, the cheap thing we could add to `verify.py` today with no vendor. Its scores are in the regex column of the result table above.

**Pass criteria, set before seeing Jev's answers.** Adopt Jev as an optional D3 check only if, on at least 3 of the 4 rules, AUROC is 0.85 or higher and it beats the regex on both precision and recall at the 0.5 threshold. Otherwise drop it.

**Found while labelling: a real fault class nobody had flagged.** Archived round reports disagree about which Baker brother is older. TEG 10 R1 and TEG 11 R4 say Alex is older; TEG 11 R2, TEG 13 R4 and TEG 18 R1 say he is younger. The data records only that they are brothers, so every one of these claims is invented. None appears in a currently served report: all 10 files are in `data/commentary/archive 2026 v4/round_reports/`. The rule in `authoring.py` already forbids it. **Now caught by `verify.py`'s `no_sibling_order` check (2026-09-26)**: 34 hits across the archived files, none in served reports.


## Sources

- [Tom's Hardware — launch claims (speed, cost)](https://www.tomshardware.com/tech-industry/artificial-intelligence/typesafe-ais-jev-offers-an-alternative-to-llms-that-claims-to-be-193x-faster-and-445x-cheaper-system-one-type-model-is-bespoke-for-probabilistic-decision-making)
- [DataCamp — Jev overview](https://www.datacamp.com/blog/system-one-models-jev)
- [Made with Jev — "LLM writes, Jev decides, code acts"](https://madewithjev.com/what-is-jev-engineering)
- [Layer3 Labs — Jev limits](https://www.layer3labs.io/guides/jev-limits)
- [pydantic/genai-prices — 32k context window PR](https://github.com/pydantic/genai-prices/pull/720)
- [OpenRouter — Jev vs LLM-as-a-Judge](https://openrouter.ai/blog/tutorials/jev-vs-llm-as-a-judge/)
- [HoneyHive — Jev as an LLM judge](https://www.honeyhive.ai/blog/how-to-use-typesafe-ais-jev-as-an-llm-judge)
- [VentureBeat — prompt injection moves verdicts](https://venturebeat.com/security/companies-are-putting-jev-in-charge-of-ai-agent-decisions-and-prompt-injection-can-influence-the-verdict)
- [XenoSpectrum — accuracy swings with how you ask](https://xenospectrum.com/en/jev-typesafe-bert-classifier-decomposition/)
- [AY Automate — independent benchmark vs GPT and Claude](https://www.ayautomate.com/blog/jev-vs-llm-benchmark)
