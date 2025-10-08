Generate Round Reports Locally
Method 1: Command Line (Recommended)
From your project root directory:

## Single Report Generation

```bash
# Generate a round report for TEG 17, Round 1
python streamlit/commentary/generate_round_report.py --teg 17 --round 1

# Backwards compatible syntax (deprecated)
python streamlit/commentary/generate_round_report.py 17 1
```

## Batch Processing (with prompt caching optimization)

```bash
# Generate all rounds for a single TEG (both phases)
python streamlit/commentary/generate_round_report.py --teg 17 --round 1-4

# Generate multiple rounds across multiple TEGs
python streamlit/commentary/generate_round_report.py --teg 15-17 --round 1-4

# Only generate story notes (Phase 1 only)
python streamlit/commentary/generate_round_report.py --teg 17 --round 1-4 --story-notes-only

# Only generate reports from existing story notes (Phase 2 only)
python streamlit/commentary/generate_round_report.py --teg 17 --round 1-4 --reports-only

# Test without making LLM calls (dry-run mode)
python streamlit/commentary/generate_round_report.py --teg 17 --round 2 --dry-run
```

### Arguments

- `--teg`: TEG number or range (e.g., "17" or "15-17")
- `--round`: Round number or range (e.g., "2" or "1-4")
- `--story-notes-only`: Only generate story notes (skip report generation)
- `--reports-only`: Only generate reports (requires existing story notes files)
- `--dry-run`: Skip LLM calls for testing

### Batch Processing Notes

- When processing multiple reports, the script uses a two-phase approach:
  1. Phase 1: Generate all story notes (maximizes prompt cache hits)
  2. Phase 2: Generate all narrative reports (maximizes prompt cache hits)
- You can run phases separately using `--story-notes-only` and `--reports-only`
- This approach significantly reduces API costs and processing time
- Invalid TEG/round combinations are automatically skipped with warnings

## Output

Saves to data/commentary/round_reports/teg_{TEG}_round_{ROUND}_report.md
Shows progress in terminal with DEBUG output

## Method 2: Via Streamlit UI

Run the Streamlit app locally and use the Report Generation page:

```bash
streamlit run streamlit/nav.py
```

Then navigate to Data > Report generation and use the "Round Reports" section.

## Requirements

Make sure you have:

- ✅ Your Anthropic API key in .streamlit/secrets.toml:
  - `ANTHROPIC_API_KEY = "sk-ant-..."`
- ✅ All dependencies installed: anthropic, pandas, streamlit, etc.
- ✅ All commentary cache files exist in data/ (run data update if needed)

## Example Output

```text
============================================================
GENERATING ROUND REPORT: TEG 17, Round 1
============================================================

Generating story notes for TEG 17, Round 1...
  > Loaded round summary (5 players)
  > Loaded hole-by-hole data (90 holes)
  > Story notes complete

Generating narrative report...
  > Narrative report complete

============================================================
ROUND REPORT COMPLETE
============================================================
Saved to: data/commentary/round_reports/teg_17_round_1_report.md
```

The command line method is faster and gives you more control!