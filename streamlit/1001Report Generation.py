"""Report Generation Page

This page allows generating tournament reports directly from the Railway environment.
Supports multiple report types:
- TEG Reports: Story Notes, Full Reports, Brief Summaries, Player by Player
- Round Reports: For in-progress tournaments

Also includes prompt editing functionality for customizing report generation.
"""

import streamlit as st
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from utils import read_text_file, write_text_file, read_file, get_teg_rounds
import pandas as pd

# Import report generation functions
sys.path.append(os.path.join(os.path.dirname(__file__), 'commentary'))

try:
    from commentary.generate_tournament_commentary_v2 import (
        generate_complete_story_notes,
        generate_main_report,
        generate_brief_summary,
        DRY_RUN as CURRENT_DRY_RUN_STATE
    )
    from commentary.generate_round_report import generate_complete_round_report
    from commentary.prompts import (
        MAIN_REPORT_PROMPT,
        BRIEF_SUMMARY_PROMPT,
        PLAYER_PROFILES_PROMPT,
        ROUND_STORY_NOTES_PROMPT,
        ROUND_REPORT_PROMPT,
        TOURNAMENT_SYNTHESIS_PROMPT,
        ROUND_STORY_PROMPT
    )
    GENERATION_AVAILABLE = True
except ImportError as e:
    GENERATION_AVAILABLE = False
    import_error = str(e)

# ============================================
# PAGE CONFIGURATION
# ============================================

st.title("🤖 Report Generation")

if not GENERATION_AVAILABLE:
    st.error(f"❌ Report generation modules not available: {import_error}")
    st.info("This page requires the commentary generation modules to be present.")
    st.stop()

# Initialize session state
if 'generated_reports' not in st.session_state:
    st.session_state.generated_reports = {}

if 'show_prompt_editor' not in st.session_state:
    st.session_state.show_prompt_editor = False

# ============================================
# HELPER FUNCTIONS
# ============================================

def get_available_tegs():
    """Get list of available TEGs from data."""
    try:
        df = read_file('data/all-scores.parquet')
        tegs = sorted(df['TEGNum'].unique())
        return tegs
    except Exception as e:
        st.error(f"Error loading TEG list: {e}")
        return []

def get_prompt_info():
    """Returns information about available prompts."""
    return {
        "Story Notes (Round)": {
            "name": "ROUND_STORY_PROMPT",
            "content": ROUND_STORY_PROMPT,
            "description": "Generates structured story notes for individual rounds"
        },
        "Story Notes (Tournament)": {
            "name": "TOURNAMENT_SYNTHESIS_PROMPT",
            "content": TOURNAMENT_SYNTHESIS_PROMPT,
            "description": "Synthesizes tournament-level story notes from round notes"
        },
        "Main Report": {
            "name": "MAIN_REPORT_PROMPT",
            "content": MAIN_REPORT_PROMPT,
            "description": "Generates full narrative tournament reports"
        },
        "Brief Summary": {
            "name": "BRIEF_SUMMARY_PROMPT",
            "content": BRIEF_SUMMARY_PROMPT,
            "description": "Generates concise 2-3 paragraph summaries"
        },
        "Player Profiles": {
            "name": "PLAYER_PROFILES_PROMPT",
            "content": PLAYER_PROFILES_PROMPT,
            "description": "Generates individual player summaries"
        },
        "Round Story Notes": {
            "name": "ROUND_STORY_NOTES_PROMPT",
            "content": ROUND_STORY_NOTES_PROMPT,
            "description": "Generates story notes for live round analysis"
        },
        "Round Report": {
            "name": "ROUND_REPORT_PROMPT",
            "content": ROUND_REPORT_PROMPT,
            "description": "Generates narrative round reports for in-progress TEGs"
        }
    }

def save_generated_report(teg_num, report_type, content):
    """Save generated report to session state and optionally to file."""
    key = f"TEG{teg_num}_{report_type}"
    st.session_state.generated_reports[key] = {
        'teg': teg_num,
        'type': report_type,
        'content': content,
        'timestamp': pd.Timestamp.now()
    }

# ============================================
# REPORT GENERATION SECTION
# ============================================

st.write("## Generate Reports")

# Report type selection
report_category = st.radio(
    "Select report category:",
    ["TEG Reports", "Round Reports"],
    horizontal=True
)

if report_category == "TEG Reports":
    st.write("### TEG Report Generation")

    # TEG selection
    available_tegs = get_available_tegs()
    selected_tegs = st.multiselect(
        "Select TEG(s):",
        options=available_tegs,
        default=[max(available_tegs)] if available_tegs else []
    )

    # Report type selection
    teg_report_type = st.selectbox(
        "Select report type:",
        ["Story Notes", "Full Report", "Brief Summary"]
    )

    # Generation button
    if st.button("🚀 Generate Report", type="primary", disabled=not selected_tegs):
        for teg_num in selected_tegs:
            with st.spinner(f"Generating {teg_report_type} for TEG {teg_num}..."):
                try:
                    if teg_report_type == "Story Notes":
                        result = generate_complete_story_notes(teg_num)
                        st.success(f"✅ Story notes generated for TEG {teg_num}")
                        save_generated_report(teg_num, "story_notes", result)

                    elif teg_report_type == "Full Report":
                        result = generate_main_report(teg_num)
                        st.success(f"✅ Full report generated for TEG {teg_num}")
                        save_generated_report(teg_num, "full_report", result)

                    elif teg_report_type == "Brief Summary":
                        result = generate_brief_summary(teg_num)
                        st.success(f"✅ Brief summary generated for TEG {teg_num}")
                        save_generated_report(teg_num, "brief_summary", result)

                except Exception as e:
                    st.error(f"❌ Error generating report for TEG {teg_num}: {e}")

else:  # Round Reports
    st.write("### Round Report Generation")

    # TEG selection
    available_tegs = get_available_tegs()
    selected_teg = st.selectbox(
        "Select TEG:",
        options=available_tegs,
        index=len(available_tegs)-1 if available_tegs else 0
    )

    # Round selection
    if selected_teg:
        num_rounds = get_teg_rounds(selected_teg)
        selected_round = st.selectbox(
            "Select Round:",
            options=list(range(1, num_rounds + 1))
        )

        # Generation button
        if st.button("🚀 Generate Round Report", type="primary"):
            with st.spinner(f"Generating round report for TEG {selected_teg}, Round {selected_round}..."):
                try:
                    output_path = generate_complete_round_report(selected_teg, selected_round)

                    # Read the generated report
                    report_content = read_text_file(str(output_path))

                    st.success(f"✅ Round report generated for TEG {selected_teg}, Round {selected_round}")
                    save_generated_report(selected_teg, f"round_{selected_round}_report", report_content)

                except Exception as e:
                    st.error(f"❌ Error generating round report: {e}")

# ============================================
# DISPLAY GENERATED REPORTS
# ============================================

if st.session_state.generated_reports:
    st.write("---")
    st.write("## Generated Reports")

    for key, report_data in st.session_state.generated_reports.items():
        with st.expander(f"TEG {report_data['teg']} - {report_data['type']} ({report_data['timestamp'].strftime('%H:%M:%S')})"):
            st.markdown(report_data['content'])

            col1, col2 = st.columns(2)

            with col1:
                # Download button
                st.download_button(
                    label="📥 Download",
                    data=report_data['content'],
                    file_name=f"teg_{report_data['teg']}_{report_data['type']}.md",
                    mime="text/markdown"
                )

            with col2:
                # Save to data directory button
                if st.button(f"💾 Save to data/commentary/", key=f"save_{key}"):
                    try:
                        file_path = f"data/commentary/teg_{report_data['teg']}_{report_data['type']}.md"
                        write_text_file(
                            file_path,
                            report_data['content'],
                            commit_message=f"Add {report_data['type']} for TEG {report_data['teg']}"
                        )
                        st.success(f"Saved to {file_path}")
                    except Exception as e:
                        st.error(f"Error saving: {e}")

# ============================================
# PROMPT EDITOR SECTION
# ============================================

st.write("---")
st.write("## Prompt Management")

if st.button("📝 Edit Prompts"):
    st.session_state.show_prompt_editor = not st.session_state.show_prompt_editor

if st.session_state.show_prompt_editor:
    st.write("### Prompt Editor")

    st.info("⚠️ Editing prompts requires access to the prompts.py file. Changes will be saved to the file.")

    prompt_info = get_prompt_info()

    selected_prompt = st.selectbox(
        "Select prompt to edit:",
        options=list(prompt_info.keys())
    )

    if selected_prompt:
        prompt_data = prompt_info[selected_prompt]

        st.write(f"**{selected_prompt}**")
        st.write(f"*{prompt_data['description']}*")

        # Display current prompt in text area
        edited_prompt = st.text_area(
            "Prompt content:",
            value=prompt_data['content'],
            height=400,
            key=f"edit_{prompt_data['name']}"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("💾 Save Changes", key=f"save_{selected_prompt}"):
                st.warning("⚠️ Direct prompt editing from the UI is not yet implemented.")
                st.info("To edit prompts, modify `streamlit/commentary/prompts.py` directly.")

        with col2:
            if st.button("↩️ Reset", key=f"reset_{selected_prompt}"):
                st.rerun()

# ============================================
# VIEW EXISTING REPORTS
# ============================================

st.write("---")
st.write("## View Existing Reports")

try:
    # List existing reports from data/commentary/
    col1, col2 = st.columns(2)

    with col1:
        view_teg = st.selectbox(
            "Select TEG to view:",
            options=available_tegs,
            key="view_teg"
        )

    with col2:
        report_types = ["main_report", "brief_summary", "story_notes"]
        view_type = st.selectbox(
            "Report type:",
            options=report_types,
            key="view_type"
        )

    if st.button("📖 Load Report"):
        try:
            file_path = f"data/commentary/teg_{view_teg}_{view_type}.md"
            content = read_text_file(file_path)

            with st.expander(f"TEG {view_teg} - {view_type}", expanded=True):
                st.markdown(content)

                st.download_button(
                    label="📥 Download",
                    data=content,
                    file_name=f"teg_{view_teg}_{view_type}.md",
                    mime="text/markdown"
                )
        except Exception as e:
            st.error(f"Could not load report: {e}")

except Exception as e:
    st.error(f"Error in view existing reports section: {e}")

# ============================================
# SYSTEM INFO
# ============================================

st.write("---")
st.write("## System Information")

col1, col2 = st.columns(2)

with col1:
    st.write("**Environment:**")
    is_railway = os.getenv('RAILWAY_ENVIRONMENT') is not None
    st.write(f"- Running on: {'Railway' if is_railway else 'Local'}")
    st.write(f"- Generation available: {GENERATION_AVAILABLE}")

with col2:
    st.write("**Cache:**")
    if st.button("🔄 Clear All Caches"):
        st.cache_data.clear()
        st.success("All caches cleared!")
        st.rerun()
