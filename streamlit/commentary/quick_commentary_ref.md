# TEG Commentary Generation - Quick Reference

**Last Updated:** 2025-01-06

---

## Command Prompts for TEG Commentary Generation

### 1. Create Story Notes for a TEG

**Basic Command (Complete Tournament):**
```bash
cd streamlit/commentary
python generate_tournament_commentary_v2.py 17
```

**For Partial Tournament (e.g., first 2 rounds completed):**
```bash
cd streamlit/commentary
python generate_tournament_commentary_v2.py 17 --partial 2
```

**What This Does:**
- Runs Level 1: Data Processing (7 passes - Python, free)
- Runs Level 2: Round Story Generation (4 LLM calls for 4 rounds)
- Runs Level 2: Tournament Synthesis (1 LLM call)
- Appends factual sections (venue, records, PBs) directly
- **Output:** `streamlit/commentary/outputs/teg_17_story_notes.md`

---

### 2. Create Final Reports from Story Notes

**Option A: Both Reports (Main Report + Brief Summary):**
```bash
cd streamlit/commentary
python generate_tournament_commentary_v2.py 17 --generate-reports
```

**Option B: Main Report Only:**
```bash
cd streamlit/commentary
python generate_tournament_commentary_v2.py 17 --main-report-only
```

**Option C: Brief Summary Only:**
```bash
cd streamlit/commentary
python generate_tournament_commentary_v2.py 17 --brief-summary-only
```

**What This Does:**
- Reads existing `teg_17_story_notes.md` file
- Passes to LLM with report generation prompts
- **Outputs:**
  - Main Report: `streamlit/commentary/outputs/teg_17_main_report.md`
  - Brief Summary: `streamlit/commentary/outputs/teg_17_brief_summary.md`

**Prerequisites:** Story notes must already exist (run step 1 first)

---

### 3. Full Pipeline (Story Notes + Reports in One Go)

```bash
cd streamlit/commentary
python generate_tournament_commentary_v2.py 17 --full-pipeline
```

**What This Does:**
- Generates story notes (5 LLM calls)
- Then generates both reports (2 more LLM calls)
- **Total:** 7 LLM calls
- **Outputs:** All 3 files (story_notes, main_report, brief_summary)

---

### 4. Batch Processing Multiple TEGs

```bash
cd streamlit/commentary
python generate_tournament_commentary_v2.py --range 10 17
```

**Optional Flags:**
- `--stop-on-error` - Stop on first failure
- `--pause-between 5` - Wait 5 seconds between TEGs

---

## Quick Reference Card

| Task | Command |
|------|---------|
| **Story notes for TEG 17** | `python generate_tournament_commentary_v2.py 17` |
| **Both reports for TEG 17** | `python generate_tournament_commentary_v2.py 17 --generate-reports` |
| **Everything for TEG 17** | `python generate_tournament_commentary_v2.py 17 --full-pipeline` |
| **Batch TEGs 10-17** | `python generate_tournament_commentary_v2.py --range 10 17` |

---

## File Locations

All outputs go to: `streamlit/commentary/outputs/`

- Story Notes: `teg_17_story_notes.md`
- Main Report: `teg_17_main_report.md`
- Brief Summary: `teg_17_brief_summary.md`

---

## Important Configuration

### Before Running:

1. **Working Directory:** Always run from `streamlit/commentary/` directory
2. **DRY_RUN Mode:** Set to `False` in script (line 29) to actually call LLM
   ```python
   DRY_RUN = False   # set to False when you're ready to actually call the LLM
   ```
3. **API Key:** Must be in environment variables or Streamlit secrets
4. **Feature Toggles:**
   - `DEBUG = True` - Show detailed output
   - `INCLUDE_STREAKS = True` - Include streak data (when implemented)

### Prerequisites:

- **For Report Generation:** Story notes must exist first (unless using `--full-pipeline`)
- **For Batch Processing:** All TEGs in range must have data available

---

## Recent Enhancements (2025-01-06)

 **Token Optimization** - Factual data (venue, records, PBs) added directly, saving ~2500-4500 tokens/tournament

 **Career Context** - Recent finishes + position counts added to synthesis (PRE-TOURNAMENT only)

 **Feature Toggle** - INCLUDE_STREAKS switch for easy testing

---

## Troubleshooting

**Error: "Story notes not found"**
- Run story note generation first (step 1)
- Check file exists in `streamlit/commentary/outputs/`

**Error: "ANTHROPIC_API_KEY not found"**
- Set environment variable or add to Streamlit secrets

**No LLM calls happening:**
- Check `DRY_RUN = False` in script (line 29)

**Want to test without API calls:**
- Set `DRY_RUN = True` to test prompt building

---

## See Also

- [IMPLEMENTATION_PLAN_FINAL.md](IMPLEMENTATION_PLAN_FINAL.md) - Complete architecture
- [RECENT_CHANGES.md](RECENT_CHANGES.md) - Latest updates and changes
- [prompts.py](prompts.py) - All LLM prompts
