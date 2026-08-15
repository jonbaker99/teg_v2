---
name: teg-report-respond
description: Answer TEG report-generation prompts so they run on claude.ai plan usage instead of the Anthropic API. Use when the user has started `python -m teg_analysis.reporting.backfill --plan` (or any report pipeline call under the `agent` provider) and prompts are waiting in `data/llm_mailbox`. Trigger on "respond to the report mailbox", "run the report on plan usage", "answer the TEG prompts", or when a backfill run says it is waiting for a response.
---

# Answer TEG report prompts from the mailbox

The report pipeline is running in another terminal with `TEG_LLM_PROVIDER=agent`
(the default). Instead of calling the Anthropic API, it writes each prompt to a
file and waits. **You are the model it is waiting for.** Answering here draws on
plan usage rather than per-token API billing, which is the entire point.

Run from the repo root — every path is cwd-relative.

## Before you start: which run?

```bash
python -m teg_analysis.reporting.mailbox status
```

Usually there is one live run and you can ignore this. If **more than one** is
listed, every command below needs `--run <id>` — ask the user which one they want
served rather than picking. A second run is often a deliberate paste experiment
aimed at a different model.

Runs marked `responder=manual` are **not yours**. They are prompts the user is
pasting into ChatGPT or Gemini by hand, and answering them here would put
Claude-written prose into a directory labelled as another model's work. The
commands below skip them automatically; do not override that with `--run` unless
the user explicitly asks.

## The loop

Repeat until the run finishes:

1. **Wait for work.**
   ```bash
   python -m teg_analysis.reporting.mailbox wait          # add --run <id> if several are live
   ```
   It blocks and prints one of:
   - a request directory path → answer it (step 2)
   - `DONE` → the pipeline finished, or its process died; stop and report back
   - `NONE` → timed out with nothing pending after 15 minutes. The pipeline is
     still alive but slow (bundle assembly is the heavy pure-Python step). Run it
     again rather than assuming it failed.

2. **Hand it to a fresh subagent.** Do not read the request yourself. Spawn a
   subagent with the `Agent` tool and give it exactly this task, substituting the
   directory `wait` printed:

   > Read `<request directory>/request.md`. Follow its instructions precisely and
   > write your answer to the response path it names, using the `Write` tool.
   > Output only what the prompt asks for — no preamble, no commentary. Read the
   > whole prompt before answering. Do not modify any other file. Reply to me
   > with just the path you wrote.

3. **Wait for it to finish**, then go back to step 1. The pipeline picks the
   answer up within a second or two and moves to the next call by itself.

**Always a subagent — including for a single report.** This is not a
context-budget optimisation, it is what makes the answer correct. Two reasons:

- **Size.** One tournament report is ~76k tokens of prompt and answer across four
  calls, and prompts 1 and 2 carry the same ~20k-token evidence bundle. Answered
  in this conversation it compacts mid-report, and a compacted responder is
  working from a summary of the data rather than the data.
- **Contamination, which is worse.** A responder that has already seen the bundle
  in prompt 1 will notice prompt 2 repeating it and start skimming — "I can reuse
  what I already extracted rather than re-reading everything." That is the
  opposite of what it is standing in for. The API call it replaces has no memory
  and reads every token of every prompt. A cold subagent does the same; a warm
  conversation does not, and the resulting report is quietly worse in ways
  nothing downstream will catch.

## Rules that matter

**Output only the artefact.** No preamble, no "here is the report", no summary of
what you did, no markdown fence wrapping the whole thing. The file contents become
the report — anything else you add ends up in it.

**For `response.json`, emit a single JSON object that validates against the
schema in the request.** Every `required` field must be present, and any field
with an `enum` must use one of the listed values exactly. If it fails validation
the pipeline re-asks with the error attached, up to three attempts, then gives up
and the run dies — so read the schema properly the first time.

**Do not shorten the work.** A tournament report prompt asks for a full report.
Length and specificity are the product; a tidy abbreviated version is a failure.

**Do not edit anything else in the repo** while responding. Your only writes are
response files inside `data/llm_mailbox/`.

## Your job is dispatch, not authorship

You are the loop, not the writer. Across a whole backfill your context should
stay roughly flat: a `wait` result and a path per call, nothing more. If you find
yourself reading a `request.md`, holding a story plan in mind, or comparing one
prompt to a previous one, you have taken over the subagent's job and the run is
already degraded.

The one exception is diagnosis — if a subagent fails, read the request to work
out why, then dispatch a fresh one.

## Checking on things

```bash
python -m teg_analysis.reporting.mailbox status   # live runs + what is pending
python -m teg_analysis.reporting.mailbox show     # print the next pending request
```

Both take `--run <id>` when several runs are live.

## When it ends

Report back with: how many requests you answered, which TEGs, and anything that
needed a retry. If the run stopped early, the pipeline's terminal has the error —
say so rather than guessing at the cause.
