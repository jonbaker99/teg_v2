I want you to create a Streamlit page for [describe what the page should do].

To understand the codebase:

1. READ docs/FUNCTION_REFERENCE.md - Focus on the "I Want To..." section to find 
   functions you need. All 235+ available functions are documented here.

2. READ docs/USAGE_GUIDE.md - Section "Streamlit (Existing - No Changes Needed)" 
   shows how to import and use functions in Streamlit pages.

3. EXAMINE these existing pages for patterns:
   - streamlit/pages/102TEG Results.py (for filtering examples)
   - streamlit/pages/300TEG Records.py (for aggregation examples)
   - streamlit/pages/latest_leaderboard.py (for real-time data)

Key points:
- Import functions from teg_analysis package directly OR via utils.py wrappers (both work)
- Use @st.cache_data for expensive operations
- Common pattern: load_all_data() → filter → aggregate → display
- Main data columns: TEGNum, Round, Hole, Player, GrossVP, NetVP, Stableford, etc.

[Then describe what your prototype page should do]