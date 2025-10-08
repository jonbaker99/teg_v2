# Batch API Implementation Summary

## What Was Added

I've implemented Anthropic Batch API support for bulk report regeneration with **50% cost savings**.

### New Files

1. **[batch_api.py](batch_api.py)** - Core batch API wrapper module
   - Create batch requests
   - Submit batches to Anthropic
   - Poll for completion
   - Retrieve results

2. **[BATCH_API_USAGE.md](BATCH_API_USAGE.md)** - Complete usage guide
   - When to use batch API
   - Cost comparisons
   - Examples and workflows
   - Troubleshooting

### Modified Files

1. **[generate_round_report.py](generate_round_report.py)**
   - Added `--use-batch` flag
   - New function: `generate_batch_reports_via_api()`
   - Handles round reports (story notes + narratives)

2. **[generate_tournament_commentary_v2.py](generate_tournament_commentary_v2.py)**
   - Added `--use-batch` flag
   - New function: `generate_reports_via_batch_api()`
   - Handles tournament reports (main + brief summary)

## Key Features

### ✅ Opt-In Design
- **Batch API is NOT default behavior**
- Requires explicit `--use-batch` flag
- Standard real-time API remains default

### ✅ Cost Savings
- **50% cheaper** than standard API
- Sonnet 4.5: $1.50/MTok input, $7.50/MTok output (vs $3/$15)
- Example: $10 job → $5 with batch API

### ✅ Automatic Processing
- Builds batch requests from your data
- Submits to Anthropic
- Polls every 60s until complete
- Retrieves and saves results
- Creates git commits

### ✅ Complete Workflows
Supports all existing generation modes:
- Story notes only
- Reports only
- Full pipeline (story notes + reports)
- Range processing (multiple TEGs/rounds)

## Usage Examples

### Round Reports (Bulk Regeneration)

```bash
# Regenerate all round reports for TEG 10-17
python streamlit/commentary/generate_round_report.py \
  --teg 10-17 --round 1-4 --use-batch

# Story notes only, then reports later
python streamlit/commentary/generate_round_report.py \
  --teg 10-17 --round 1-4 --story-notes-only --use-batch

python streamlit/commentary/generate_round_report.py \
  --teg 10-17 --round 1-4 --reports-only --use-batch
```

### Tournament Reports (Bulk Regeneration)

```bash
# Regenerate both main reports and summaries for TEG 10-17
python streamlit/commentary/generate_tournament_commentary_v2.py \
  --range 10 17 --batch-reports --use-batch --generate-reports

# Main reports only
python streamlit/commentary/generate_tournament_commentary_v2.py \
  --range 10 17 --batch-reports --use-batch --main-report-only
```

### Live/Current Tournament (Standard API)

```bash
# DON'T use --use-batch for live tournaments
python streamlit/commentary/generate_round_report.py --teg 17 --round 4

# Real-time API is default (no flag needed)
```

## Processing Time

- **Most batches complete in 1 hour**
- Maximum: 24 hours
- Script automatically polls and waits
- Can leave running overnight

## Output Structure

```
streamlit/commentary/
├── batch_api.py                     # NEW: Core module
├── BATCH_API_USAGE.md              # NEW: Usage guide
├── BATCH_API_SUMMARY.md            # NEW: This file
│
├── batch_requests/                 # NEW: Request files
│   ├── story_notes_TIMESTAMP.jsonl
│   └── narrative_reports_TIMESTAMP.jsonl
│
└── batch_results/                  # NEW: Results tracking
    ├── batch_ID_info.json          # Batch metadata
    └── batch_ID_summary.json       # Results summary

# Reports saved to normal locations:
data/commentary/
├── round_reports/                  # Round reports
│   ├── TEG17_R1_story_notes.md
│   └── TEG17_R1_report.md
│
└── drafts/                        # Tournament reports
    ├── teg_17_main_report.md
    └── teg_17_brief_summary.md
```

## Decision Matrix

| Scenario | Use Batch API? | Command |
|----------|----------------|---------|
| Regenerate 10+ old tournaments | ✅ YES | `--use-batch` |
| Cost >$10 | ✅ YES | `--use-batch` |
| Bulk refresh of all reports | ✅ YES | `--use-batch` |
| Can wait 1-24 hours | ✅ YES | `--use-batch` |
| **Live/current tournament** | ❌ NO | (default) |
| **Need results immediately** | ❌ NO | (default) |
| **Only 1-2 reports** | ❌ NO | (default) |

## Cost Estimate

For your bulk regeneration task:

Assuming:
- 8 TEGs × 4 rounds = 32 round reports
- 8 tournament reports (main + brief) = 16 reports
- **Total: 48 reports**

Estimated tokens (conservative):
- Round story notes: ~30k input, ~1k output each
- Round narratives: ~10k input, ~2k output each
- Tournament reports: ~50k input, ~4k output each

**Total estimated:**
- Input: ~2.5M tokens
- Output: ~0.3M tokens

**Cost comparison:**
- Standard API: ~$12
- Batch API: ~$6
- **Savings: ~$6** 💰

## Next Steps

1. **Test with small batch first:**
   ```bash
   python streamlit/commentary/generate_round_report.py \
     --teg 16-17 --round 1-4 --use-batch
   ```

2. **Monitor progress** (script does this automatically)

3. **Verify results** in data directories

4. **Run full batch** when ready:
   ```bash
   # All round reports
   python streamlit/commentary/generate_round_report.py \
     --teg 10-17 --round 1-4 --use-batch

   # All tournament reports
   python streamlit/commentary/generate_tournament_commentary_v2.py \
     --range 10 17 --batch-reports --use-batch --generate-reports
   ```

## Important Notes

⚠️ **Batch API is OPT-IN:**
- Default behavior unchanged
- Must explicitly add `--use-batch` flag
- Standard real-time API used by default

✅ **Safe to commit:**
- No breaking changes
- Existing scripts work as before
- New functionality is additive only

📊 **Track your spend:**
- Monitor at https://console.anthropic.com/settings/usage
- Batch API costs appear as "Batch" requests

## Questions?

See [BATCH_API_USAGE.md](BATCH_API_USAGE.md) for detailed guide.
