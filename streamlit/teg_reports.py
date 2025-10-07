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
    here.parent.parent.parent / "data" / "commentary",    # .../teg_v2/data/commentary (from streamlit folder)
    here.parent.parent / "data" / "commentary",           # .../data/commentary (from root)
]
commentary_dir = next((p for p in candidates if p.exists()), None)
if commentary_dir is None:
    st.error("Couldn't find commentary folder at `data/commentary`.")
    st.stop()

# --- Controls ---
col1, col2 = st.columns([1, 2])
with col1:
    teg_num = st.selectbox("Tournament number", options=list(range(2, 18)), index=0)

report_label_to_key = {
    "Summary": "brief_summary",
    "Full report": "main_report",
    "Player-by-player": "player_profiles",
}
with col2:
    try:
        report_label = st.segmented_control(
            "Report type", options=list(report_label_to_key.keys()), default="Summary"
        )
    except Exception:
        report_label = st.radio(
            "Report type", options=list(report_label_to_key.keys()), index=0, horizontal=True
        )

report_key = report_label_to_key[report_label]
filename = f"teg_{teg_num}_{report_key}.md"
md_path = commentary_dir / filename

# --- Styles ---
load_teg_reports_css()

# --- Loader ---
@st.cache_data(show_spinner=False)
def load_markdown(p: Path) -> str:
    return p.read_text(encoding="utf-8")

# --- Renderer (MD -> HTML -> single wrapped block) ---
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
        # Fallback: no wrapper styling, but renders content
        st.markdown(md_text, unsafe_allow_html=False)
        st.info("Tip: add `markdown>=3.4` to requirements.txt for full styling.")

# --- Display ---



if md_path.exists():
    md_text = load_markdown(md_path)
    render_report(md_text)
    full_html = render_report(md_text, return_html=True)

    # show with a copy button
    st.write("---")
    st.subheader("HTML output")
    st.code(full_html, language="html")  # ← has a copy icon


else:
    st.warning(f"Report not found: `{filename}`")
    with st.expander("Show available files in data/commentary/"):
        files = sorted(p.name for p in commentary_dir.glob("*.md"))
        st.code("\n".join(files) or "(none found)")

