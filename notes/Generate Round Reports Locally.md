Generate Round Reports Locally
Method 1: Command Line (Recommended)
From your project root directory:
# Generate a round report for TEG 17, Round 1
python streamlit/commentary/generate_round_report.py 17 1

# Generate for TEG 17, Round 2
python streamlit/commentary/generate_round_report.py 17 2

# Test without making LLM calls (dry-run mode)
python streamlit/commentary/generate_round_report.py 17 1 --dry-run
Arguments:
First argument: TEG number
Second argument: Round number
Optional --dry-run flag: Skip LLM calls for testing
Output:
Saves to data/commentary/round_reports/teg_{TEG}_round_{ROUND}_report.md
Shows progress in terminal with DEBUG output
Method 2: Via Streamlit UI
Run the Streamlit app locally and use the Report Generation page:
streamlit run streamlit/nav.py
Then navigate to Data > Report generation and use the "Round Reports" section.
Requirements
Make sure you have:
✅ Your Anthropic API key in .streamlit/secrets.toml:
ANTHROPIC_API_KEY = "sk-ant-..."
✅ All dependencies installed: anthropic, pandas, streamlit, etc.
✅ All commentary cache files exist in data/ (run data update if needed)
Example Output
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
The command line method is faster and gives you more control!