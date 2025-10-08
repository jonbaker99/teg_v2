# Laptop-Safe Batch API Workflow

## Quick Start: Submit and Close Your Laptop 💻🔒

This workflow lets you submit batch jobs and **safely close your laptop** while Anthropic processes them on their servers.

### Step 1: Submit Batch (Takes ~30 seconds)

**For Round Reports:**
```bash
python streamlit/commentary/generate_round_report.py \
  --teg 10-17 --round 1-4 --use-batch --submit-only
```

**For Tournament Story Notes:**
```bash
python streamlit/commentary/generate_tournament_commentary_v2.py \
  --range 3 17 --batch-reports --use-batch --submit-only
```

**Output:**
```
============================================================
BATCH SUBMITTED - YOU CAN NOW CLOSE THIS WINDOW
============================================================
Story notes batch ID: msgbatch_01ABC123...
Narrative reports batch ID: msgbatch_01XYZ789...

To retrieve results later, run:
  python generate_round_report.py --retrieve-batch msgbatch_01ABC123...
  python generate_round_report.py --retrieve-batch msgbatch_01XYZ789...

Batch info saved to:
  streamlit/commentary/batch_results/batch_msgbatch_01ABC123_info.json
============================================================
```

### Step 2: Close Your Laptop ✅

- **You can now close Python**
- **You can shut down your laptop**
- **Batches continue processing on Anthropic's servers**
- Most complete in 1-4 hours

### Step 3: Check Status Later (Anytime)

**For Round Reports:**
```bash
python streamlit/commentary/generate_round_report.py --list-batches
```

**For Tournament Story Notes:**
```bash
python streamlit/commentary/generate_tournament_commentary_v2.py --list-batches
```

**Output:**
```
RECENT BATCH SUBMISSIONS
============================================================

1. Batch ID: msgbatch_01ABC123...
   Type: round_story_notes
   Created: 2025-01-08T14:30:52
   Status: ended ✓
   Progress: {'succeeded': 32, 'errored': 0}
   To retrieve: python generate_round_report.py --retrieve-batch msgbatch_01ABC123...

2. Batch ID: msgbatch_01XYZ789...
   Type: round_narrative_reports
   Created: 2025-01-08T14:32:15
   Status: in_progress ⏳
   Progress: {'processing': 8, 'succeeded': 24, 'errored': 0}
```

### Step 4: Retrieve Results (When Complete)

**For Round Reports:**
```bash
python streamlit/commentary/generate_round_report.py \
  --retrieve-batch msgbatch_01ABC123...
```

**For Tournament Story Notes:**
```bash
python streamlit/commentary/generate_tournament_commentary_v2.py \
  --retrieve-batch msgbatch_01ABC123...
```

**Output:**
```
RETRIEVING BATCH RESULTS: msgbatch_01ABC123...
============================================================
Checking batch status...
  Status: ended
  Request counts: {'succeeded': 32, 'errored': 0}
  Batch type: round_story_notes

Retrieving results...
Saved 32 batch requests to streamlit/commentary/batch_results

Saving results to files...
  ✓ Saved: data/commentary/round_reports/TEG10_R1_story_notes.md
  ✓ Saved: data/commentary/round_reports/TEG10_R2_story_notes.md
  ...
  ✓ Saved: data/commentary/round_reports/TEG17_R4_story_notes.md

BATCH RETRIEVAL COMPLETE
============================================================
Retrieved: 32/32 successful
```

## Common Scenarios

### Scenario 1: Overnight Processing

```bash
# Evening: Submit batch
python generate_round_report.py --teg 10-17 --round 1-4 --use-batch --submit-only

# Close laptop, go to sleep 💤

# Morning: Check status
python generate_round_report.py --list-batches

# Morning: Retrieve results
python generate_round_report.py --retrieve-batch msgbatch_01ABC...
```

### Scenario 2: Forgot Batch ID

```bash
# List all recent batches (sorted by date, newest first)
python generate_round_report.py --list-batches

# Copy the batch_id from output and retrieve
python generate_round_report.py --retrieve-batch <batch_id>
```

### Scenario 3: Batch Still Processing

```bash
# Check status
python generate_round_report.py --list-batches

# If status is 'in_progress', wait and check again later
# Most batches complete in 1-4 hours
```

### Scenario 4: Multiple Batches

```bash
# Submit story notes
python generate_round_report.py --teg 10-17 --round 1-4 --story-notes-only --use-batch --submit-only

# Submit narrative reports (after story notes complete)
python generate_round_report.py --teg 10-17 --round 1-4 --reports-only --use-batch --submit-only

# Retrieve both when complete
python generate_round_report.py --list-batches
python generate_round_report.py --retrieve-batch <story_notes_batch_id>
python generate_round_report.py --retrieve-batch <narrative_batch_id>
```

## What Happens If...

### ❓ My laptop battery dies?
✅ **No problem.** Batch continues on Anthropic's servers. Retrieve results later with `--retrieve-batch`.

### ❓ Python crashes?
✅ **No problem.** Batch is already submitted. Retrieve results later with `--retrieve-batch`.

### ❓ I close the terminal?
✅ **No problem.** Use `--list-batches` to find your batch_id, then `--retrieve-batch`.

### ❓ I forget the batch ID?
✅ **No problem.** Run `--list-batches` to see all recent submissions (sorted by date).

### ❓ Batch fails?
⚠️ Check `--list-batches` for error counts. Failed requests are logged in the results summary.

### ❓ I need results urgently?
❌ Batch API can take up to 24 hours. Use standard API (without `--use-batch`) for immediate results.

## Files Created

```
streamlit/commentary/
├── batch_requests/
│   ├── story_notes_20250108_143052.jsonl       # Your requests (for reference)
│   └── narrative_reports_20250108_143052.jsonl
│
└── batch_results/
    ├── batch_msgbatch_01ABC_info.json          # Batch metadata (includes batch_id)
    └── batch_msgbatch_01ABC_summary.json       # Results summary

# Reports saved to normal locations:
data/commentary/round_reports/
├── TEG10_R1_story_notes.md
├── TEG10_R1_report.md
└── ...
```

## Commands Reference

```bash
# Submit and exit immediately (RECOMMENDED for laptops)
python generate_round_report.py --teg 10-17 --round 1-4 --use-batch --submit-only

# List all recent batches with status
python generate_round_report.py --list-batches

# Retrieve results from completed batch
python generate_round_report.py --retrieve-batch <batch_id>

# Submit and wait (keeps Python running - for desktops)
python generate_round_report.py --teg 10-17 --round 1-4 --use-batch
```

## Cost Savings

Using `--use-batch` (with or without `--submit-only`) gives you:
- **50% cost reduction** vs standard API
- Same quality results
- Processing time: 1-24 hours (most complete in 1-4 hours)

## Summary

✅ **Safe to close laptop** after `--submit-only`
✅ **Processing continues** on Anthropic's servers
✅ **Retrieve anytime** with `--retrieve-batch`
✅ **Find batch IDs** with `--list-batches`
✅ **50% cheaper** than standard API

For immediate results, use standard API (omit `--use-batch` flag).
