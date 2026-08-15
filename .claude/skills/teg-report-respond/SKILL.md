---
name: teg-report-respond
description: Answer TEG report-generation prompts so they run on claude.ai plan usage instead of the Anthropic API. Use when the user is running `python -m teg_analysis.reporting.backfill` (or any report pipeline call) with the default `agent` provider and prompts are waiting in `data/llm_mailbox`. Trigger on "respond to the report mailbox", "run the report on plan usage", "answer the TEG prompts", or when a backfill run says it is waiting for a response.
---

# Answer TEG report prompts from the mailbox

The report pipeline is running in another terminal with `TEG_LLM_PROVIDER=agent`
(the default). Instead of calling the Anthropic API, it writes each prompt to a
file and waits. **You are the model it is waiting for.** Answering here draws on
plan usage rather than per-token API billing, which is the entire point.

Run from the repo root — every path is cwd-relative.

## The loop

Repeat until the run finishes:

1. **Wait for work.**
   ```bash
   python -m teg_analysis.reporting.mailbox wait
   ```
   It blocks and prints one of:
   - a request directory path → answer it (step 2)
   - `DONE` → the pipeline finished, or its process died; stop and report back
   - `NONE` → timed out with nothing pending after 15 minutes. The pipeline is
     still alive but slow (bundle assembly is the heavy pure-Python step). Run it
     again rather than assuming it failed.

2. **Read the request.** `Read` the `request.md` in that directory. It is
   self-contained: a system prompt, a user message, and — for structured calls —
   a JSON Schema.

3. **Answer it as the model.** Follow the system prompt exactly. You are not
   summarising or reviewing the prompt; you are producing the output it asks for,
   in full, as if you were the API call it replaces.

4. **Write the answer** with the `Write` tool, to the path named in the request's
   "What to do" section — `response.md` for prose, `response.json` for structured
   output, in the same directory.

5. Go back to step 1. The pipeline picks the answer up within a second or two and
   moves to the next call by itself.

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

## Batch runs: use a subagent per request

A full backfill is ~68 calls with large prompts. Answering them all in this
session will exhaust context long before the run finishes.

**If the run is more than one report** (the pipeline prints how many TEGs at
startup), do not answer inline. For each request, spawn a subagent with the
`Agent` tool and give it exactly this task:

> Read `<request directory>/request.md`. Follow its instructions precisely and
> write your answer to the response path it names, using the `Write` tool. Output
> only what the prompt asks for — no preamble, no commentary. Do not modify any
> other file. Reply to me with just the path you wrote.

Each subagent starts cold, so your own context stays flat across the whole
backfill. Wait for it to finish, then loop.

For a single report (four or five calls), answering inline is fine and faster.

## Checking on things

```bash
python -m teg_analysis.reporting.mailbox status   # active run + what is pending
python -m teg_analysis.reporting.mailbox show     # print the next pending request
```

## When it ends

Report back with: how many requests you answered, which TEGs, and anything that
needed a retry. If the run stopped early, the pipeline's terminal has the error —
say so rather than guessing at the cause.
