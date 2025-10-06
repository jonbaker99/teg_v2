# streamlit/pages/Commentary Runner.py
import os
from pathlib import Path
import time
import streamlit as st

# === Page config ===
st.set_page_config(page_title="Tournament Commentary Runner", page_icon="📝", layout="centered")
st.title("📝 Tournament Commentary Runner")

# === Import generator + utils ===
# Path-based import to avoid clashing with the installed 'streamlit' package
import importlib.util, sys
from pathlib import Path

# Make sure data is available at ./data
def ensure_data_symlink():
    if os.getenv("RAILWAY_ENVIRONMENT"):
        src = Path("/mnt/data_repo/data")
        dst = Path("data")
        if src.exists() and not dst.exists():
            try:
                dst.symlink_to(src, target_is_directory=True)
            except Exception:
                # fallback: create local folder and let Option A copy into it
                dst.mkdir(parents=True, exist_ok=True)

ensure_data_symlink()

def _find_generator():
    here = Path(__file__).resolve()
    candidates = [
        # runner in streamlit/ → streamlit/commentary/...
        here.parent / "commentary" / "generate_tournament_commentary_v2.py",
        # runner in streamlit/pages/ → streamlit/commentary/...
        here.parent.parent / "commentary" / "generate_tournament_commentary_v2.py",
        # fallback: cwd/streamlit/commentary/...
        Path.cwd() / "streamlit" / "commentary" / "generate_tournament_commentary_v2.py",
    ]
    # also try the nearest parent actually named "streamlit"
    for p in here.parents:
        if p.name == "streamlit":
            candidates.append(p / "commentary" / "generate_tournament_commentary_v2.py")
            break

    for cand in candidates:
        if cand.exists():
            return cand

    raise FileNotFoundError(
        "Could not find generate_tournament_commentary_v2.py. Tried:\n" +
        "\n".join(str(c) for c in candidates)
    )

_gen_path = _find_generator()
_gen_dir = _gen_path.parent               # .../streamlit/commentary
_streamlit_base = _gen_dir.parent         # .../streamlit

# Ensure sibling imports like `import pattern_analysis` resolve
for p in (str(_gen_dir), str(_streamlit_base)):
    if p not in sys.path:
        sys.path.insert(0, p)

# Load the generator module
_spec = importlib.util.spec_from_file_location("teg_commentary_gen", _gen_path)
gen = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = gen
_spec.loader.exec_module(gen)

# Optional sanity check
assert hasattr(gen, "generate_complete_story_notes"), f"Generator functions not found in {_gen_path}"



try:
    # Imported as requested; not used for .md (current impl supports csv/parquet only)
    from utils import write_file  # noqa: F401
except Exception:
    write_file = None  # keep page functional if utils isn't importable here

# === Constants from your repo behavior ===
REPO_OUTPUTS = Path("streamlit/commentary/outputs")
# Module writes here, e.g. teg_17_story_notes.md / _main_report.md / _brief_summary.md

# Railway volume mount convention used by your utils: /mnt/data_repo/<file_path>
# We'll mirror that for markdown saving.
VOLUME_ROOT = Path(os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "/mnt/data_repo"))
VOLUME_COMMENTARY = VOLUME_ROOT / "commentary"
VOLUME_COMMENTARY.mkdir(parents=True, exist_ok=True)

# === Small helper: save markdown to the volume (UTF-8) ===
def save_markdown_to_volume(rel_path: str, text: str) -> Path:
    """
    Save text to the Railway volume under /mnt/data_repo/<rel_path>.
    Falls back to local path if not on Railway.
    """
    if os.getenv("RAILWAY_ENVIRONMENT"):
        out = VOLUME_ROOT / rel_path
    else:
        # local dev: keep a copy beside the repo for convenience
        out = Path(rel_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return out

# Utility to list volume markdown files

def list_volume_md_files():
    try:
        files = sorted(VOLUME_COMMENTARY.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    except Exception:
        files = []
    return files

# === UI controls ===
report_type = st.radio(
    "What do you want to generate?",
    ["Story notes (only)", "Main report (from notes)", "Brief summary (from notes)"],
    index=0,
)

start_teg, end_teg = st.slider("TEG range (inclusive)", 2, 20, (3, 17), 1)

st.caption("Options")
c1, c2, c3 = st.columns(3)
dry_run = c1.checkbox("Dry run (no LLM calls)", value=False)
debug_mode = c2.checkbox("Debug mode (extra files/logs)", value=False)
stop_on_error = c3.checkbox("Stop on first error", value=False)

c4, c5 = st.columns(2)
ensure_notes = c4.checkbox("Create notes if missing (for Main/Brief)", value=True)
pause_between = c5.number_input("Pause between TEGs (secs)", min_value=0.0, max_value=60.0, value=0.0, step=0.5)

run_btn = st.button("Run", type="primary", use_container_width=True)

# === Wire flags into the generator module ===
def set_module_switches():
    gen.DRY_RUN = dry_run
    gen.DEBUG = debug_mode
    # If the module exposes a limiter object, nudge its flags too
    try:
        gen.TOKEN_LIMITER.dry_run = dry_run
        gen.TOKEN_LIMITER.debug = debug_mode
    except Exception:
        pass

# === Expected local output paths from your generator ===
def local_md_paths(teg: int):
    return {
        "notes": REPO_OUTPUTS / f"teg_{teg}_story_notes.md",
        "main":  REPO_OUTPUTS / f"teg_{teg}_main_report.md",
        "brief": REPO_OUTPUTS / f"teg_{teg}_brief_summary.md",
    }

# === Read a local .md if it exists ===
def read_local(path: Path) -> str | None:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None

# === Core per-TEG execution ===
def run_for_teg(teg: int):
    set_module_switches()
    paths = local_md_paths(teg)
    produced = []

    try:
        if report_type.startswith("Story"):
            gen.generate_complete_story_notes(teg)
            produced.append(("notes", paths["notes"]))

        elif report_type.startswith("Main"):
            if ensure_notes and not paths["notes"].exists():
                gen.generate_complete_story_notes(teg)
            gen.generate_main_report(teg)
            produced.append(("main", paths["main"]))

        elif report_type.startswith("Brief"):
            if ensure_notes and not paths["notes"].exists():
                gen.generate_complete_story_notes(teg)
            gen.generate_brief_summary(teg)
            produced.append(("brief", paths["brief"]))

    except Exception as e:
        return "error", [], str(e)

    # Copy produced files to the volume as markdown
    copies = []
    for kind, local_path in produced:
        text = read_local(local_path)
        if not text:
            copies.append((kind, local_path.name, None, "Local file missing after generation"))
            continue
        # Save to /mnt/data_repo/commentary/<filename>.md (Railway) or local fallback
        vol_rel = f"commentary/{local_path.name}"
        dst = save_markdown_to_volume(vol_rel, text)
        copies.append((kind, local_path.name, dst, None))

    return "ok", copies, None

# === Run button ===
if run_btn:
    tegs = list(range(int(start_teg), int(end_teg) + 1))
    with st.status(f"Running for TEGs {tegs[0]}–{tegs[-1]}…", expanded=True) as status:
        ok_count, fail_count = 0, 0
        for i, teg in enumerate(tegs, 1):
            st.write(f"**TEG {teg}**")
            stat, copies, err = run_for_teg(teg)

            if stat == "ok":
                ok_count += 1
                for kind, fname, dst, warn in copies:
                    if dst:
                        st.success(f"{kind.title()} → {dst}")
                    else:
                        st.warning(f"{kind.title()} → {fname}: {warn or 'not saved'}")
            else:
                fail_count += 1
                st.error(f"Failed: {err}")
                if stop_on_error:
                    status.update(label=f"Stopped on error (TEG {teg})", state="error")
                    break

            if pause_between and i < len(tegs):
                time.sleep(float(pause_between))

        else:
            status.update(label="All TEGs processed", state="complete")

    st.divider()
    st.write(f"Done. ✅ **{ok_count}** succeeded, ❌ **{fail_count}** failed.")

# === Browse / open generated files ===
st.subheader("📁 Commentary folder (Railway volume)")
refresh = st.button("Refresh file list", key="refresh_files")
files = list_volume_md_files()
if not files:
    st.info(f"No markdown files found in {VOLUME_COMMENTARY}")
else:
    for p in files:
        info = p.stat()
        cols = st.columns([3,2,1,1,1])
        cols[0].markdown(f"**{p.name}**  \n`{p}`")
        cols[1].markdown(time.strftime("%Y-%m-%d %H:%M", time.localtime(info.st_mtime)))
        if cols[2].button("👁 View", key=f"view_{p.name}"):
            st.session_state['view_file'] = str(p)
        with p.open('rb') as f:
            data = f.read()
        cols[3].download_button("⬇️ Download", data=data, file_name=p.name, mime="text/markdown", key=f"dl_{p.name}")
        cols[4].markdown(f"[Open link](?view={p.name})")

    # Handle query param 'view'
    try:
        params = st.experimental_get_query_params()
        if 'view' in params:
            candidate = VOLUME_COMMENTARY / params['view'][0]
            if candidate.exists():
                st.session_state['view_file'] = str(candidate)
    except Exception:
        pass

    if 'view_file' in st.session_state:
        vp = Path(st.session_state['view_file'])
        if vp.exists():
            st.markdown("---")
            st.subheader(f"Preview: {vp.name}")
            text = vp.read_text(encoding='utf-8')
            st.markdown(text)
            with st.expander("Show raw Markdown"):
                st.code(text, language="markdown")

# === Footer context ===
with st.expander("Where files go / why this path"):
    st.markdown(
        f"""
- The generator writes **locally** to `streamlit/commentary/outputs/…` (inside the app container).  
- This page then copies each `.md` to your **Railway volume** at:
  ```
  {VOLUME_COMMENTARY}/<filename>.md
  ```
- We follow your utils’ convention that Railway files live under **`/mnt/data_repo/…`**, hence `commentary/` under that root. If you later extend `utils.write_file()` to support text/markdown, we can swap the saver to use it directly.
"""
    )
