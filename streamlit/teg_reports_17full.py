# streamlit/pages/Commentary Viewer.py
import streamlit as st
from pathlib import Path
import importlib.util
from utils import load_teg_reports_css

st.set_page_config(page_title="Tournament Commentary", page_icon="📰")
st.title("📰 Tournament Commentary")

# --- Locate commentary folder ---
here = Path(__file__).resolve()
candidates = [
    here.parent.parent.parent / "data" / "commentary" / "drafts",  # .../teg_v2/data/commentary/drafts (from streamlit folder)
    here.parent.parent / "data" / "commentary" / "drafts",         # .../data/commentary/drafts (from root)
]
commentary_dir = next((p for p in candidates if p.exists()), None)
if commentary_dir is None:
    st.error("Couldn't find commentary folder at `data/commentary/drafts`.")
    st.stop()

# --- UI controls ---
col1, col2 = st.columns([1, 3])
with col1:
    teg_num = st.selectbox("TEG", options=list(range(3, 18)), index=7)  # default 10
with col2:
    report_key = "main_report"  # keep fixed for now; change here if you add more variants

# --- Resolve file path ---
filename = f"teg_{teg_num}_{report_key}.md"
md_path = commentary_dir / filename

# --- Styles ---
load_teg_reports_css()

# --- Loader ---
def load_markdown(p: Path) -> str:
    # No caching: ensures changes on disk show up immediately upon widget change / page reload
    return p.read_text(encoding="utf-8")

# --- Renderer ---
def render_report(md_text: str, return_html: bool = False):
    has_markdown = importlib.util.find_spec("markdown") is not None
    if has_markdown:
        import markdown as md
        html_body = md.markdown(md_text, extensions=["extra", "sane_lists", "smarty", "toc"])
        full_html = f"<div class='teg-report'>{html_body}</div>"
        st.markdown(full_html, unsafe_allow_html=True)
        if return_html:
            return full_html
    else:
        # Fallback to plain markdown if python-markdown isn't installed
        st.markdown(md_text)

# --- Load and display the report ---
st.caption(f"Looking for: `data/commentary/drafts/{filename}`")
if md_path.exists():
    md_text = load_markdown(md_path)
    render_report(md_text)
else:
    st.error(f"Report not found: `{filename}`")
