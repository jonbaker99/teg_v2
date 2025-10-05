# streamlit/pages/Commentary Viewer.py
import streamlit as st
from pathlib import Path
import importlib.util

st.set_page_config(page_title="Tournament Commentary", page_icon="📰")
st.title("📰 Tournament Commentary")

# --- Locate commentary folder ---
here = Path(__file__).resolve()
candidates = [
    here.parent / "commentary" / "outputs",           # .../streamlit/pages/commentary/outputs
    here.parent.parent / "commentary" / "outputs",    # .../streamlit/commentary/outputs
]
commentary_dir = next((p for p in candidates if p.exists()), None)
if commentary_dir is None:
    st.error("Couldn't find commentary folder at `streamlit/commentary/outputs`.")
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
st.markdown("""
<style>
.teg-report {
    max-width: 960px;
    margin: 2rem auto;
    padding: 1.5rem 2rem;
    font-family: "Lora", "Georgia", "Times New Roman", serif;
    line-height: 1.7;
    text-align: justify;
    color: #222;
    background: #fdfcf8;
    border-radius: 8px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
    column-count: 2;
    column-gap: 2.5rem;
}
.teg-report h1:first-of-type {
    column-span: all;
    text-align: center;
    font-size: clamp(1.8rem, 3.4vw, 2.6rem);
    line-height: 1.2;
    letter-spacing: 0.5px;
    margin: 0 0 0.75rem 0;
    font-weight: 700;
}
.teg-report h1:first-of-type + p::first-letter,
.teg-report > p:first-of-type::first-letter {
    float: left;
    font-size: 3.4rem;
    line-height: 1;
    margin-right: 0.25rem;
    font-weight: 700;
    color: #a00;
}
.teg-report h2, .teg-report h3 {
    column-span: all;
    text-align: center;
    margin-top: 1.2rem;
}
.teg-report blockquote {
    column-span: all;
    font-style: italic;
    margin: 1rem 2rem;
    padding-left: 1rem;
    border-left: 3px solid #ccc;
}
.teg-report hr {
    column-span: all;
    border: none;
    border-top: 1px solid #ccc;
    margin: 2rem 0;
}
@media (max-width: 900px) {
    .teg-report { column-count: 1; padding: 1rem; }
}
</style>
""", unsafe_allow_html=True)

# --- Loader ---
@st.cache_data(show_spinner=False)
def load_markdown(p: Path) -> str:
    return p.read_text(encoding="utf-8")

# --- Renderer (MD -> HTML -> single wrapped block) ---
def render_report(md_text: str):
    has_markdown = importlib.util.find_spec("markdown") is not None
    if has_markdown:
        import markdown as md
        html_body = md.markdown(md_text, extensions=["extra", "sane_lists", "smarty", "toc"])
        st.markdown(f"<div class='teg-report'>{html_body}</div>", unsafe_allow_html=True)
    else:
        # Fallback: no wrapper styling, but renders content
        st.markdown(md_text, unsafe_allow_html=False)
        st.info("Tip: add `markdown>=3.4` to requirements.txt for full styling.")

# --- Display ---
if md_path.exists():
    md_text = load_markdown(md_path)
    render_report(md_text)
else:
    st.warning(f"Report not found: `{filename}`")
    with st.expander("Show available files in commentary/outputs/"):
        files = sorted(p.name for p in commentary_dir.glob("*.md"))
        st.code("\n".join(files) or "(none found)")
