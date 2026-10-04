# Jev (TypeSafe AI) reference

Built 2026-10-04 from TypeSafe's public docs and launch post. Every claim comes from a fetched page, cited per section.
Vendor claims are marked **(vendor claim)**: we have not tested them.

Sources fetched:

- Docs index: https://docs.typesafe.ai/llms.txt
- Blog: https://typesafe.ai/blog/introducing-system-one-models-and-jev (dated Sep 15, 2026)
- Docs pages, all under `https://docs.typesafe.ai/`: `introduction`, `introduction/quickstart`, `introduction/coding-agents`, `introduction/machine-learning-primer`, `concepts/system-one`, `concepts/state`, `concepts/how-to-build-with-system-one`, `primitives`, `primitives/choice`, `primitives/score`, `primitives/noul`, `primitives/advanced`, `confidence`, `patterns` (+ `fan-out`, `confidence-routing`, `composite-scoring`, `intent-routing`), `models`, `api`, `model-jaggedness/jev-1.13`, `sdk`, `sdk/python` (+ `usage`, `api/retries`, `api/constants`, `api/exceptions`, `api/types/questions`, `api/types/responses`), `sdk/javascript`, `agent-skill`, `legal`, `cookbooks/parallel_questions`.

Not fetched: the other cookbooks (only Parallel questions was read), the JS SDK class reference, the demos, the manifesto, and the external "workflow evals" site.

## 1. What Jev is and isn't

Jev is TypeSafe's flagship model and the first "System One" model. You send a `state` (text, a JSON object, or an array of text) and typed `questions`. It returns typed answers with probabilities, in one request, with no text generation. It is not a chat, code or text-generating LLM, and it cannot replace the model behind a coding agent. It reads text only, takes no per-customer fine-tuning, and is built for quick judgments (route, score, check a statement), not multi-step reasoning, arithmetic, counting or date maths. TypeSafe describes it as a "frontier-intelligence function call" and says it "can't hallucinate", meaning answers are constrained to the options you supply, not that they are always right.

Sources: https://docs.typesafe.ai/introduction, https://docs.typesafe.ai/concepts/system-one, https://docs.typesafe.ai/introduction/coding-agents, https://docs.typesafe.ai/models, blog post.

## 2. Request and response shapes

One endpoint: `POST https://api.typesafe.ai/v1/systemone`, header `Authorization: Bearer <API_KEY>`. Keys come from https://console.typesafe.ai/keys. A browser Playground is at https://console.typesafe.ai/playground.

Request fields (all required):

- `state`: string, object or array.
- `model`: e.g. `"jev-latest"`.
- `questions`: map of your chosen id to a question object. The id is never sent to the model.

Response fields:

- `model`: the versioned id that answered, e.g. `jev-1.13.0`.
- `answers`: same keys as `questions`.
- `usage`: `{input_tokens, output_tokens}`.

Errors:

- `401`: bad key.
- `422`: validation failure.
- `429`: rate limit.
- `529`: overloaded. Retry with exponential backoff.

Minimal Python example (SDK `typesafe-sdk`, Python >= 3.10, reads `TYPESAFE_API_KEY`):

```python
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

client = TypeSafeClient()  # defaults to model "jev-latest"
response = client.system_one(
    state="Hi, my Stripe integration has failed for 3 days. Please help ASAP.",
    questions={
        "department": Choice(
            instructions="Which team should handle this",
            criteria={"billing": "Payment issues", "technical": "Bugs or integrations"},
        ),
        "frustration": Score(
            instructions="How frustrated the customer appears",
            criteria=["Calm", "Frustrated but civil", "Very angry"],
        ),
        "is_urgent": Noul(instructions="The message conveys urgency"),
    },
)
response.answers["department"].choice   # "technical"
response.answers["frustration"].score   # e.g. 1.0
response.answers["is_urgent"].noul      # e.g. 1.0
```

Other SDK facts:

- The Python SDK also exposes `response.nouls`, `.choices` and `.scores` maps.
- The SDK has sync and async clients, with an optional `http2` extra.
- The JS/TS SDK is `@typesafe-ai/sdk` (Node 20+), using `choice()`, `noul()` and `score()` helpers.
- Python SDK defaults: `base_url` `https://api.typesafe.ai`, model `jev-latest`, timeout 10 s per HTTP operation.
- Environment variables: `TYPESAFE_API_KEY`, `TYPESAFE_BASE_URL`, `TYPESAFE_DEFAULT_MODEL`, `TYPESAFE_LOG_LEVEL`.
- `GET /v1/models` lists model names the account can use.

Sources: https://docs.typesafe.ai/api, https://docs.typesafe.ai/introduction/quickstart, https://docs.typesafe.ai/sdk/python, https://docs.typesafe.ai/sdk/javascript, https://docs.typesafe.ai/sdk/python/api/constants, https://docs.typesafe.ai/models.

State rules:

- A string works for simple cases. Docs recommend an object with named fields for most requests.
- Questions can point at parts of the state by path, in backticks, e.g. `` `ticket.messages[0].text` ``.
- Instructions and criteria can themselves be JSON (string, object, array or null).

Sources: https://docs.typesafe.ai/concepts/state, https://docs.typesafe.ai/primitives, https://docs.typesafe.ai/primitives/advanced.

## 3. Primitives

All questions in one request see the same state. They are evaluated in parallel and independently. One answer never becomes context for another. Questions that depend on an earlier answer need a second request.

Sources: https://docs.typesafe.ai/primitives, https://docs.typesafe.ai/introduction.

### Choice

- **Purpose:** pick one option from an unordered set (routing, classification).
- **Inputs:** `type: "choice"`, `instructions`, and `criteria`, a map of option to description (`null` allowed).
- **Outputs:** `choice` (top option), `probabilities` (every option, sums to 1), `confidence` (0 to 1).
- **Limits:** at most 255 options.
- **Advice from the docs:**
  - Give the full option list.
  - Add an `other` or `none of the above` option.
  - Option names and descriptions are both sent to the model, so write descriptions that separate the options.
  - Option order can bias the answer toward the first option (see section 7).

Source: https://docs.typesafe.ai/primitives/choice, https://docs.typesafe.ai/api.

### Score

- **Purpose:** place the state on an ordered scale you describe (severity, frustration, skill).
- **Inputs:** `type: "score"`, `instructions`, and `criteria`, an ordered array of level descriptions. Levels are numbered from 0 by position.
- **Outputs:** `score` (probability-weighted, can fall between levels), `legend`, `probabilities` per level, `confidence`.
- **Limits:** at least 2 levels, at most 10.
- **Notes:**
  - The model does not see level numbers or neighbouring levels. Numbers in descriptions or instructions do not help.
  - Use as many levels as you can describe distinctly.
  - Do not interpolate between levels to recover an exact number: score levels are "weak in numerical calibration". Thresholding the score is fine.

Sources: https://docs.typesafe.ai/primitives/score, https://docs.typesafe.ai/api, https://docs.typesafe.ai/model-jaggedness/jev-1.13.

### Noul

- **Purpose:** yes/no. The answer is the probability that the answer is yes.
- **Inputs:** `type: "noul"`, `instructions` (a question or a statement to judge), optional `criteria` with `true` and `false` descriptions.
- **Outputs:** `noul` (0 to 1). No `confidence` field. A value near 0.5 is the model being unsure.
- **Limits:** none stated on the page.
- **Notes:**
  - `noul` is a probability of yes, not a degree. 0.5 does not mean "medium". Use Score for degree.
  - Example values recorded on `jev-1.13.0`: 0.02 for "Thanks, that fixed it!" and 0.99 for an explicit request for a person. Borderline messages came out at 0.26 and 0.40, so thresholds matter.
  - Docs suggest confidence-like use of `|2p - 1|`.

Sources: https://docs.typesafe.ai/primitives/noul, https://docs.typesafe.ai/confidence.

## 4. Confidence

Meaning:

- `confidence` is a 0 to 1 number computed from the answer's own `probabilities`. It is 1 when all probability sits on one outcome and 0 when it is spread evenly. It exists on Choice and Score, not Noul.
- Calibration is claimed across groups of predictions, not for any single answer. For example, outcomes given 0.8 should occur about 80% of the time.

Formulas (exact, so you can recompute or use your own measure):

- **Choice:** `(p_max - 1/n) / (1 - 1/n)`. Only the top probability counts.
- **Score:** `max(0, 1 - sum_i p_i*|i - m| / MAD_unif)`, where `m` is the most likely level and `MAD_unif = (1/n) * sum_i |i - (n-1)/2|`. Mass on neighbouring levels costs less than mass on distant levels.
- **Noul:** no field. Use `p` directly, or `|2p - 1|`.
- Docs suggest two alternatives for Choice: top probability `p_max` (set its threshold per question, since 0.5 means different things among 2 and 10 options) and the top-to-second ratio.

How to use it:

- Split into three bands. High: act automatically. Medium: confirm, flag or gather more. Low: do not act. Route to a human, ask for clarification, or fall back to another system.
- Scale thresholds with risk. Docs' example: below 0.5 go to a human, a read-only action proceeds above that, and a destructive action needs more than 0.9. The routing pattern page uses a 0.6 floor and over 0.85 for transfers.
- Docs say to start conservative and tune on your own data. The numbers above are illustrations, not recommendations.

Sources: https://docs.typesafe.ai/confidence, https://docs.typesafe.ai/patterns/confidence-routing, https://docs.typesafe.ai/introduction/machine-learning-primer.

## 5. Recommended patterns and anti-patterns

Recommended:

- **Atomic questions.** Ask one narrow judgment per question, the kind an expert makes in seconds.
- **Compose in code.** Split a complex judgment into factors, then combine with your own weights (composite scoring). Changing priorities means changing a coefficient, not a prompt.
- **Speculative fan-out.** Send every question you might need in one call, then ignore the irrelevant answers in code. The docs say extra questions cost "only the tokens for the extra questions".
- **Confidence-gated routing.** Use the answer for what and confidence for whether to act.
- **Intent routing.** Use Jev as a cheap classifier in front of deterministic code, an LLM, or a human.
- **Closed answer sets for extraction.** Turn extraction into a Choice over candidates (found by regex or another model), with an explicit "not stated" option.
- **Filter state first.** Retrieve in code and send only what the question needs. A Noul can pre-filter irrelevant passages.
- **Cascade.** Jev for cheap first-pass decisions, escalating low-confidence cases to a reasoning model or a person.
- **Pin versions.** If thresholds were tuned on one version, pin its id (e.g. `jev-1.13.0`), not an alias.

Anti-patterns (from the Jev 1.13 jaggedness page, last reviewed 2026-10-02 per the page):

- **Literal reading.** It answers the words written, not the intent. State exact conditions and put boundary cases in the criteria. Contradictory instructions and criteria hurt accuracy.
- **Maths and counting.** It is not a calculator and does not count reliably. Count in code (one Noul per item, then sum). Hex or RGB values are worse than named colours.
- **Date and time comparison.** Extract the parts with Choices and compare in code.
- **Indirection.** Double negatives and multi-hop questions are less reliable.
- **Large, noisy state.** Accuracy falls as unrelated content grows ("context rot").
- **Adversarial content.** State is not treated as hostile by default, and injected instructions can move answers. Test edge cases before launch.
- **Choice option order.** It can lean toward the first option. Reorder options and check that the answer holds.
- **Generation.** It does not write text. Chaining choices to force it is "very slow" and does not work well.
- **Several judgments hidden in one question.**

Sources: https://docs.typesafe.ai/patterns and its four child pages, https://docs.typesafe.ai/concepts/how-to-build-with-system-one, https://docs.typesafe.ai/model-jaggedness/jev-1.13, https://docs.typesafe.ai/primitives/advanced, https://docs.typesafe.ai/models.

## 6. Pricing, latency, rate limits, access

Model `jev-1.13.0` (the current model per the Models page):

| Item | Value |
| - | - |
| Price | $0.042 per million input tokens ($42 per billion). Output tokens free. |
| Rate limit | 100K tokens/s and 80 requests/s. Over either returns `429`. |
| Context | 64k tokens per request. 32k for `state` plus the longest question. |
| Input | Text only. |
| Aliases | `jev-latest` and `jev-preview` both resolve to `jev-1.13.0`. No preview build exists now. |

- **Rate limits are unstable.** The docs warn they are "adjusting dynamically" and "can change without notice". Higher limits are offered on custom and enterprise plans (sales@typesafe.ai).
- **Latency (vendor claim).** The launch post says end-to-end response time is 70 ms to 500 ms, and that its published evals were run from a laptop on the US West Coast, where the service is based. It says Jev is 40x to 200x faster than frontier LLMs on System One tasks. The docs state no latency guarantee.
- **Cost and speed claims (vendor claims).**
  - 193.6x faster and 444.6x cheaper on TypeSafe's own workflow evals. The post says these are "on the higher end" of real gains, and that the evals were built by TypeSafe's own team. The reference answers are the average of two other vendors' top models.
  - The Parallel questions cookbook: 12.2x cheaper and 10.0x faster when 13 questions go in one call instead of 13 calls, on a 54,000-character document, with no change in answers.
  - The post says it cannot prove the pricing is not subsidised.
- **Access status.**
  - The launch post (Sep 15, 2026) says Jev is "available today in early access" and that developers are being admitted from a waitlist.
  - The docs describe a self-serve console, a Playground and API keys, but give no signup terms.
  - The Models page says limits may change "as we let in more users".
- **Data handling.** Not trained on customer requests or responses. A Data Processing Agreement and Privacy Policy exist. Zero data retention is offered to enterprise customers.
- **SDK retries.** SDKs retry with backoff by default and honour `retry-after`. The `RetryPolicy` example shows `max_retries=3, timeout=10.0, http_statuses={429, 500, 502, 503, 504}`.

Sources: https://docs.typesafe.ai/models, https://docs.typesafe.ai/api, https://docs.typesafe.ai/legal, https://docs.typesafe.ai/sdk/python/api/retries, https://docs.typesafe.ai/cookbooks/parallel_questions, blog post.

## 7. Known limits and open questions

Known limits, as stated by TypeSafe:

- Text only. No images, audio or video.
- English is strongest. Other languages, including CJK, work with lower accuracy.
- No per-customer fine-tuning. The same weights serve every account. Customise via `state`, `instructions` and `criteria` only.
- The jaggedness list in section 5 applies to `jev-1.13`. TypeSafe says many items "will be fixed in later versions".
- Calibration holds across many predictions, not for one answer.

Open questions. The pages fetched do not answer these:

1. **Access.** Is the waitlist still active? Can a new account get a key today? Is there a free tier or credit? The post says early access, while the Quick start reads as self-serve.
2. **Rate-limit stability.** Is there any SLA or latency guarantee? The docs state none.
3. **Question limits.** What are the maximum questions per request and the maximum size of a single question? Only context (64k/32k), Choice options (255) and Score levels (10) are stated.
4. **Question billing.** The docs say questions cost tokens and that extra questions are "cheap". The tokenizer, and how criteria text is counted, are not described.
5. **Accuracy.** There are no public-benchmark numbers on the pages fetched. The post's FAQ has a "How does Jev perform against public benchmarks?" entry, but its answer was collapsed and not captured. The same applies to "Is Jev just a smaller LLM?" and "Where does our training data come from?".
6. **Workflow evals.** These live on a separate site we did not fetch. They are TypeSafe-authored and compare against other vendors' models.
7. **Version drift.** A cookbook used `jev-1.12` at the same price. How often do versions change, and how long is an old version served? Aliases move without notice.
8. **Retries.** The API page says retry `529`. The `RetryPolicy` example set omits it. Is `529` retried by default?
9. **Determinism.** A cookbook reports std dev 0.0 on most repeats. The docs do not promise identical answers across calls.
10. **Hosting and SLA.** Where is the service hosted (the post says West Coast)? What are the uptime terms? Is there a fallback if the vendor is down?
11. **Prompt injection.** Quantified robustness is not given, only a warning.
12. **Company risk.** The post says pricing may change and that more GPU capacity is still arriving.
13. **Terms.** The Master Customer Agreement, DPA and Acceptable Use Policy were not read.
