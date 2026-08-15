# Running the report pipeline on claude.ai plan usage instead of the API

> **Working doc.** Captures the problem, the constraints and what already exists, so the design can
> start in a fresh chat without re-deriving any of it. **Consolidate into `README.md` and delete this
> file once the work lands** (see the repo's documentation rules in `CLAUDE.md`).
>
> Status: **not started.** Raised 2026-08-14.

## The problem

`teg_analysis/reporting/llm.py` calls the Anthropic API directly with an API key. **That billing is
separate from a claude.ai subscription** — API calls are charged per token and draw nothing from
plan usage. Every report generated this way costs money on top of a plan that is already paid for.

The goal is to run **the same prompts** through claude.ai (Claude Code / Cowork), so report
generation draws on plan usage instead. The API path must remain available and easy to switch back
to.

Jon's constraint, verbatim: *a switch or two parallel workflows so I can easily change between the
API and the claude.ai usage. But in a way that is not overly engineered. Keep it simple.*

## What already exists that helps

- **`llm.py` is a thin, single-purpose wrapper.** Two functions carry every call in the pipeline:
  - `generate_structured(system, user, schema, ...)` → a Pydantic-validated object (the story plan,
    the round plan).
  - `generate_text(system, user, ...)` → free prose (dry draft, the report, the repetition lint).

  Everything else goes through those two. That is the seam.
- **`dry_run=True` already writes the assembled prompt + bundle to disk without calling the API.**
  `build_story_plan(teg, dry_run=True)` is the existing precedent for "produce the inputs, stop
  short of the call". This is most of the mechanism for a file-based hand-off.
- **The key is resolved in one place**, `llm.get_api_key()` — env `ANTHROPIC_API_KEY`, then
  `TEG_ANTHROPIC_API_KEY`, then a gitignored `secrets.toml`.
- **`llm.DEFAULT_MODEL`** is the single model pin.

## What makes it non-trivial

- **Structured output.** The API path uses `messages.parse` with a Pydantic schema and gets
  validation for free. Any non-API path has to produce JSON that satisfies `StoryPlan` (which has
  required enum fields and required strings) and be validated on the way back in. The schema can be
  written out alongside the prompt — `StoryPlan.model_json_schema()` — so whatever produces the
  answer has it.
- **Call volume per report.** One tournament report is four calls in sequence: story plan → dry
  draft → report-around-draft → repetition lint. Each depends on the previous one's output, so this
  is a pipeline, not a batch.
- **Prompt caching only exists on the API path.** The system prompts are large and stable and are
  cached there; a plan-usage path will not have that, which changes the cost/latency profile.
- **Automation vs. interactivity.** `backfill_all` runs unattended over 17 TEGs. Whatever replaces
  the API call has to work in that loop, or the loop has to change shape.

## Sketch of the obvious approach (not a decision)

A provider switch in `llm.py` — `api` (today) and something like `agent` — where the non-API
provider writes `{system, user, schema}` to a known path and reads the response back from another,
and a Claude Code skill or command does the middle bit. Files on disk, no daemon, no queue.

The open questions a design needs to answer: where the hand-off files live and how a run is
identified; how the loop waits (or whether it stops and resumes); how schema validation failures are
retried; and whether the switch is an env var, a parameter, or a mode.

## Related

- `README.md` → **Configuration → API key** for how the key is resolved today.
- `README.md` → **Model selection** for the model pin.
- Cost context: a full 17-TEG tournament regeneration is ~90 minutes and 68 API calls.
