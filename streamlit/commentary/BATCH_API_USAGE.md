# Batch API Usage Guide

This guide explains how to use the Anthropic Batch API for bulk report generation at **50% cost reduction**.

## When to Use Batch API

✅ **Use Batch API when:**
- Regenerating reports for multiple tournaments/rounds (bulk operations)
- Cost is more important than speed (you can wait 1-24 hours)
- Processing 5+ reports in a single batch
- Budget is >$10 (where 50% savings = $5+ saved)

❌ **Don't use Batch API when:**
- Generating reports for live/current tournaments (use real-time API)
- You need results immediately
- Processing only 1-2 reports (overhead not worth it)

## Cost Comparison

| API Type | Sonnet 4.5 Input | Sonnet 4.5 Output | Processing Time |
|----------|------------------|-------------------|-----------------|
| Standard | $3/MTok | $15/MTok | Real-time |
| **Batch** | **$1.50/MTok** | **$7.50/MTok** | Up to 24 hours |

**Example:** 100 round reports @ ~50k tokens each = 5M tokens
- Standard API: ~$150-200
- Batch API: ~$75-100
- **Savings: $75-100** 💰

## Usage

### Round Reports

Generate round reports using Batch API:

```bash
# Generate story notes + reports for TEG 10-17, all rounds
python streamlit/commentary/generate_round_report.py --teg 10-17 --round 1-4 --use-batch

# Story notes only (faster, then you can run reports separately)
python streamlit/commentary/generate_round_report.py --teg 10-17 --round 1-4 --story-notes-only --use-batch

# Reports only (from existing story notes)
python streamlit/commentary/generate_round_report.py --teg 10-17 --round 1-4 --reports-only --use-batch
```

### Tournament Story Notes

Generate tournament story notes using Batch API:

```bash
# Submit and close: Generate story notes for TEG 3-17 (RECOMMENDED)
python streamlit/commentary/generate_tournament_commentary_v2.py --range 3 17 --batch-reports --use-batch --submit-only

# Retrieve later
python streamlit/commentary/generate_tournament_commentary_v2.py --retrieve-batch msgbatch_01ABC...

# List pending batches
python streamlit/commentary/generate_tournament_commentary_v2.py --list-batches

# Full workflow: Wait for completion (keeps Python running)
python streamlit/commentary/generate_tournament_commentary_v2.py --range 3 17 --batch-reports --use-batch
```

### Tournament Reports

Generate tournament reports (main report + brief summary) using Batch API:

```bash
# Generate both main reports and brief summaries for TEG 10-17
python streamlit/commentary/generate_tournament_commentary_v2.py --range 10 17 --batch-reports --use-batch --generate-reports

# Main reports only
python streamlit/commentary/generate_tournament_commentary_v2.py --range 10 17 --batch-reports --use-batch --main-report-only

# Brief summaries only
python streamlit/commentary/generate_tournament_commentary_v2.py --range 10 17 --batch-reports --use-batch --brief-summary-only
```

## How It Works

### Workflow

1. **Build Batch Requests**
   - Script loads your data and prepares prompts
   - Saves requests to JSONL file in `streamlit/commentary/batch_requests/`

2. **Submit to Anthropic**
   - Uploads batch to Anthropic API
   - Returns batch ID for tracking

3. **Wait for Processing** (automatic polling)
   - Script polls Anthropic every 60 seconds
   - Most batches complete within 1 hour
   - Maximum wait: 24 hours

4. **Retrieve Results**
   - Downloads completed results
   - Saves reports to appropriate directories
   - Creates git commits

### Files Created

```
streamlit/commentary/
├── batch_requests/              # Request files (JSONL)
│   ├── story_notes_20250108_143052.jsonl
│   └── narrative_reports_20250108_143052.jsonl
│
└── batch_results/              # Results and metadata
    ├── batch_msgbatch_123_info.json        # Batch metadata
    ├── batch_msgbatch_123_summary.json     # Results summary
    └── (raw results are processed and saved to data/)
```

## Monitoring Progress

### Real-time Monitoring

The script automatically polls and displays progress:

```
Polling batch msgbatch_01ABC... (checking every 60s, max 86400s)...
  [60s] Status: in_progress | {'processing': 45, 'succeeded': 23, 'errored': 0}
  [120s] Status: in_progress | {'processing': 12, 'succeeded': 56, 'errored': 0}
  [180s] Status: ended | {'processing': 0, 'succeeded': 68, 'errored': 0}
Batch complete after 180s!
```

### Manual Status Check

If you need to check status later (e.g., script crashed):

```python
from streamlit.commentary.batch_api import check_batch_status, get_api_key

batch_id = "msgbatch_01ABC..."  # From your batch_info.json file
api_key = get_api_key()

status = check_batch_status(batch_id, api_key)
print(status)
```

### Retrieve Results Manually

If you need to retrieve results from a completed batch:

```python
from streamlit.commentary.batch_api import get_batch_results, get_api_key

batch_id = "msgbatch_01ABC..."
api_key = get_api_key()
results_dir = "streamlit/commentary/batch_results"

results = get_batch_results(batch_id, api_key, results_dir)
# Results are saved to results_dir and returned as dict
```

## Best Practices

### 1. Test First with Small Batch
```bash
# Test with just 2 TEGs before running full batch
python streamlit/commentary/generate_round_report.py --teg 16-17 --round 1-4 --use-batch
```

### 2. Run Overnight
- Start batch in evening
- Check results in morning
- Most batches complete in 1-4 hours

### 3. Monitor Costs
Check your Anthropic dashboard to track spend:
- https://console.anthropic.com/settings/usage

### 4. Batch Similar Prompts Together
The scripts already do this automatically:
- All story notes use same system prompt → cached
- All narrative reports use same system prompt → cached
- Maximum cache hit rate = more savings

### 5. Keep Batch Info Files
Save `batch_*_info.json` files in case you need to:
- Check status later
- Retrieve results again
- Debug issues

## Troubleshooting

### Batch Taking Too Long?
- Most complete within 1 hour
- Maximum: 24 hours
- If >24 hours: batch expired, re-submit

### Results Not Appearing?
1. Check batch status: `status['status'] == 'ended'`?
2. Check for errors in results summary
3. Look for error messages in console output

### Rate Limit Errors?
- Batch API has no rate limits during submission
- Only limit is 100,000 requests or 256MB per batch
- If hitting limits, split into multiple batches

### Cost Higher Than Expected?
- Check token counts in batch results summary
- Prompt caching requires identical system prompts
- Verify `use_cache=True` in requests

## Advanced: Custom Batch Processing

For custom workflows, use the `batch_api.py` module directly:

```python
from streamlit.commentary.batch_api import (
    create_batch_request,
    save_batch_requests,
    submit_batch,
    poll_until_complete,
    get_batch_results
)

# 1. Build requests
requests = []
for item in my_data:
    request = create_batch_request(
        custom_id=f"my_task_{item.id}",
        model="claude-sonnet-4-5",
        max_tokens=4000,
        system_prompt="Your system prompt",
        user_message=f"Process: {item.content}",
        use_cache=True
    )
    requests.append(request)

# 2. Save and submit
batch_file = "my_batch.jsonl"
save_batch_requests(requests, batch_file)

api_key = os.getenv('ANTHROPIC_API_KEY')
batch_info = submit_batch(batch_file, api_key)

# 3. Wait for completion
poll_until_complete(batch_info['batch_id'], api_key)

# 4. Get results
results = get_batch_results(batch_info['batch_id'], api_key, "my_results/")
```

## Summary

- **Always use `--use-batch` flag** for bulk regeneration tasks
- **50% cost savings** on all LLM calls
- **Processing time:** 1-24 hours (most complete in 1-4 hours)
- **Best for:** Regenerating 5+ reports at once
- **Not for:** Live/current tournament reporting

For questions or issues, check the batch API module source: [batch_api.py](batch_api.py)
