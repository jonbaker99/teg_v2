# Round Report System - Usage Guide

## Overview

The Round Report System generates narrative reports for individual rounds during live tournaments. It provides forward-looking analysis ("What's At Stake") to keep readers engaged throughout multi-round competitions.

## Quick Start

### Generate a Single Round Report

```bash
# From project root directory
cd "c:\Users\jonba\Documents\Projects - not on onedrive\teg_v2"

# Generate report for TEG 17, Round 2
python streamlit/commentary/generate_round_report.py 17 2
```

### Test Without LLM (Dry Run)

```bash
python streamlit/commentary/generate_round_report.py 17 2 --dry-run
```

## Command-Line Interface

```bash
python streamlit/commentary/generate_round_report.py <TEG_NUM> <ROUND_NUM> [OPTIONS]

Arguments:
  TEG_NUM           Tournament number (e.g., 17)
  ROUND_NUM         Round number (e.g., 2)

Options:
  --dry-run         Test data pipeline without making LLM calls
  --help            Show help message
```

## Examples

```bash
# Generate Round 1 report for TEG 17
python streamlit/commentary/generate_round_report.py 17 1

# Generate Round 2 report for TEG 17
python streamlit/commentary/generate_round_report.py 17 2

# Test Round 3 without using LLM
python streamlit/commentary/generate_round_report.py 17 3 --dry-run
```

## Output

Reports are saved to: `data/commentary/round_reports/`

Filename format: `teg_{TEG_NUM}_round_{ROUND_NUM}_report.md`

Example: `data/commentary/round_reports/teg_17_round_2_report.md`

## Report Structure

Each report contains:

1. **Story Notes** (Structured bullets)
   - Round summary
   - Key moments
   - Position changes
   - Round breakdown (6-hole segments)
   - Player notes

2. **Narrative Report** (Full prose)
   - Round summary (what happened)
   - How it unfolded (chronological, 6-hole segments)
   - Standings tables (Trophy & Jacket)
   - **What's At Stake** (forward-looking analysis)
   - Round highlights
   - Player summaries

## Data Sources

The system automatically loads and analyzes:

### Round Data
- Round scores (Stableford, Gross, vs Par)
- Standings before/after round
- Gaps to leader
- Front 9 / Back 9 splits
- Six-hole splits (1-6, 7-12, 13-18)

### Hole-by-Hole
- Every hole's scoring
- Position changes through the round
- Hole difficulty statistics

### Events & Patterns
- Eagles, disasters, key moments
- Streaks (birdie runs, bogey-free, disasters)
- Lead changes
- Momentum shifts

### Forward-Looking
- Rounds remaining
- Gap analysis (catchable vs insurmountable)
- What each player needs to win
- Tournament projections

## Requirements

### Python Packages
```bash
pip install anthropic pandas numpy
```

### API Key
Set your Anthropic API key:

**Option 1: Environment Variable**
```bash
export ANTHROPIC_API_KEY="your-key-here"  # Mac/Linux
set ANTHROPIC_API_KEY=your-key-here       # Windows
```

**Option 2: Streamlit Secrets**
Add to `.streamlit/secrets.toml`:
```toml
ANTHROPIC_API_KEY = "your-key-here"
```

## Data Files Required

The system expects these files in the `data/` directory:
- `all-scores.parquet` - Hole-by-hole scoring
- `commentary_round_summary.parquet` - Round summaries
- `commentary_round_events.parquet` - Events
- `commentary_round_streaks.parquet` - Streaks
- `round_info.csv` - Course metadata

## Workflow for Live Tournaments

1. **After each round completes**, run the generator:
   ```bash
   python streamlit/commentary/generate_round_report.py 17 1  # After Round 1
   python streamlit/commentary/generate_round_report.py 17 2  # After Round 2
   # etc.
   ```

2. **Review the output** in `data/commentary/round_reports/`

3. **Share or publish** the markdown report

## Troubleshooting

### "No data found for TEG X, Round Y"
- Ensure the round data has been uploaded to the system
- Check that `commentary_round_summary.parquet` contains data for this TEG/Round

### "ANTHROPIC_API_KEY not found"
- Set the API key as environment variable or in Streamlit secrets
- Verify the key is valid

### "anthropic package not available"
- Install: `pip install anthropic`

### Testing Without LLM
- Use `--dry-run` flag to test the data pipeline
- This verifies all data loads correctly without using API credits

## Architecture

The system follows a two-pass LLM architecture:

**Pass 1: Story Notes Generation**
- Data → LLM → Structured bullets identifying key storylines

**Pass 2: Report Generation**
- Story Notes → LLM → Full narrative with forward-looking analysis

This mirrors the proven tournament report system architecture.

## Related Files

- `streamlit/commentary/round_data_loader.py` - Data assembly
- `streamlit/commentary/round_pattern_analysis.py` - Pattern detection
- `streamlit/commentary/generate_round_report.py` - Main generator
- `streamlit/commentary/prompts.py` - LLM prompts
- `ROUND_REPORT_TODO.md` - Implementation tracking

## Support

For issues or questions:
1. Check `ROUND_REPORT_TODO.md` for implementation notes
2. Review test output with `--dry-run` flag
3. Examine data files to verify completeness
