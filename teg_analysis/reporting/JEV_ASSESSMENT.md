# Jev and the report pipeline — assessment (2026-09-26)

Spike notes. Temporary working doc: fold the verdict into `STATUS.md` and delete this file once the follow-up experiment below is run or dropped.

## Verdict: Jev cannot speed up or cheapen report writing, but it could strengthen checking

Jev cannot generate text. Every stage that costs time or money in our pipeline is text generation. So Jev cannot replace any paid call, and it cannot make a report arrive sooner.

Where it could help is **judgement**: typed yes/no, choice or score answers about text we already have. Our weakest area is exactly that — semantic fact-checking (Theme D) and scoring A/B experiments. Worth one small, measured spike there. Not worth wiring into generation.

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
| 7 | **Verification** (`verify.py`, D3) | 8 mechanical checks: beat IDs, em-dashes, invented mechanisms, "a week", roster, weekdays, arithmetic, swings | No, free | **Yes — best fit.** See below. |
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

## Recommended next step

One spike, about an hour, no pipeline changes:

1. Hand-label ~40 paragraphs from existing reports for the four semantic rules, including known past faults.
2. Ask Jev each rule as a yes/no per paragraph.
3. Measure precision and recall against the labels.

If it separates the faults cleanly, add it as an optional D3 check behind a flag. If not, drop it and delete this file. Skip the experiment-judge idea unless the spike succeeds.

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
