# streamlit/pages/Commentary Viewer.py
import streamlit as st
from pathlib import Path
import importlib.util
from utils import load_teg_reports_css
from streamlit.components.v1 import html as st_html


st.set_page_config(page_title="Tournament Commentary", page_icon="📰")
st.title("📰 Tournament Commentary")

# --- Locate commentary folder ---
here = Path(__file__).resolve()
candidates = [
    here.parent.parent.parent / "data" / "commentary",    # .../teg_v2/data/commentary (from streamlit folder)
    here.parent.parent / "data" / "commentary",           # .../data/commentary (from root)
]
commentary_dir = next((p for p in candidates if p.exists()), None)
if commentary_dir is None:
    st.error("Couldn't find commentary folder at `data/commentary`.")
    st.stop()

# --- Fixed parameters ---
teg_num = 17
report_key = "main_report"   # "main_report" = full report
filename = f"teg_{teg_num}_{report_key}.md"
md_path = commentary_dir / filename

# --- Styles ---
load_teg_reports_css()

# --- Loader ---
@st.cache_data(show_spinner=False)
def load_markdown(p: Path) -> str:
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

# --- Load and display the report ---
if md_path.exists():
    md_text = load_markdown(md_path)
    render_report(md_text)

    # # show with a copy button
    # st.write("---")
    # st.subheader("HTML output")
    # full_html = render_report(md_text, return_html = True)
    # st.code(full_html, language="html")  # ← has a copy icon
else:
    st.error(f"Report not found: `{filename}`")
