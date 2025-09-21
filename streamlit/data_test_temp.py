# pages/99_Volume Admin.py
import os
import io
import time
import datetime as dt
from pathlib import Path

import pandas as pd
import streamlit as st

# ====== CONFIG ======
VOLUME_PATH = Path("/mnt/data_repo")          # Railway volume mount
DEFAULT_SUBDIR = Path("data")                 # Where you normally keep CSV/Parquet (optional)
TEST_FILE = VOLUME_PATH / "volume_test.txt"   # Test file location

# ====== HELPERS ======
def ensure_volume():
    VOLUME_PATH.mkdir(parents=True, exist_ok=True)

def human_size(n: int) -> str:
    for unit in ["B","KB","MB","GB","TB"]:
        if n < 1024.0:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"

def safe_join(base: Path, rel: str) -> Path:
    """
    Prevent path traversal: only allow paths inside base.
    """
    target = (base / rel).resolve()
    if not str(target).startswith(str(base.resolve())):
        raise ValueError("Invalid path.")
    return target

def list_files(root: Path):
    for p in sorted(root.rglob("*")):
        if p.is_file():
            stat = p.stat()
            yield {
                "relative": str(p.relative_to(root)),
                "size": stat.st_size,
                "modified": dt.datetime.fromtimestamp(stat.st_mtime),
                "path": p,
            }

def read_preview(p: Path, max_lines=50):
    # Preview small text/CSV/Parquet; otherwise show bytes length
    suffix = p.suffix.lower()
    try:
        if suffix in {".csv", ".txt", ".log"}:
            text = p.read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines()
            head = "\n".join(lines[:max_lines])
            return "text", head, len(lines)
        elif suffix in {".parquet"}:
            df = pd.read_parquet(p)
            return "parquet", df.head(min(len(df), 50)), len(df)
        else:
            data = p.read_bytes()
            return "binary", f"(binary file: {human_size(len(data))})", len(data)
    except Exception as e:
        return "error", str(e), 0

# ====== UI ======
st.title("Volume Admin & Test")
ensure_volume()

st.caption(f"Volume path: `{VOLUME_PATH}`  |  Exists: **{VOLUME_PATH.exists()}**")

# --- Section A: Test file actions ---
st.header("A) Quick volume test")

c1, c2, c3 = st.columns(3)
with c1:
    if st.button("Write test file"):
        now = dt.datetime.now().isoformat(timespec="seconds")
        VOLUME_PATH.mkdir(parents=True, exist_ok=True)
        TEST_FILE.write_text(f"Hello from Railway at {now}\n", encoding="utf-8")
        st.success(f"Wrote {TEST_FILE.name} with timestamp {now}")

with c2:
    if st.button("Read test file"):
        if TEST_FILE.exists():
            st.info(TEST_FILE.read_text(encoding="utf-8"))
        else:
            st.error("Test file not found")

with c3:
    if st.button("Delete test file"):
        if TEST_FILE.exists():
            TEST_FILE.unlink()
            st.success("Deleted test file")
        else:
            st.info("Nothing to delete")

st.divider()

# --- Section B: File browser / actions ---
st.header("B) Browse, preview, download, delete")

root_choice = st.text_input("Relative folder to browse (inside the volume)", str(DEFAULT_SUBDIR))
try:
    browse_root = safe_join(VOLUME_PATH, root_choice) if root_choice.strip() else VOLUME_PATH
except ValueError:
    st.error("Invalid folder path")
    st.stop()

browse_root.mkdir(parents=True, exist_ok=True)
rows = list(list_files(browse_root))
if not rows:
    st.info("No files found in this folder yet.")
else:
    # Lightweight table
    st.subheader("Files")
    data = [
        {
            "File": r["relative"],
            "Size": human_size(r["size"]),
            "Modified": r["modified"].strftime("%Y-%m-%d %H:%M"),
        }
        for r in rows
    ]
    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

    # Select one file to act on
    rel_names = [r["relative"] for r in rows]
    selected_rel = st.selectbox("Select a file", rel_names, index=0)
    selected_path = safe_join(VOLUME_PATH, selected_rel)

    # Preview
    kind, preview, n = read_preview(selected_path)
    st.write(f"**Preview ({kind})** — records/lines: {n}")
    if kind == "parquet" and isinstance(preview, pd.DataFrame):
        st.dataframe(preview, use_container_width=True)
    else:
        st.code(str(preview)[:10_000])  # cap the display

    # Download
    with open(selected_path, "rb") as f:
        st.download_button(
            "Download selected file",
            data=f.read(),
            file_name=selected_path.name,
            mime="application/octet-stream",
            use_container_width=True,
        )

    # Delete (with confirmation)
    st.checkbox("Confirm delete", key="confirm_delete")
    if st.button("Delete selected file", type="secondary"):
        if st.session_state.get("confirm_delete"):
            try:
                selected_path.unlink()
                st.success("File deleted.")
                st.rerun()
            except Exception as e:
                st.error(f"Delete failed: {e}")
        else:
            st.warning("Tick 'Confirm delete' first.")

st.divider()

# --- Section C: Upload into the volume ---
st.header("C) Upload a file into the volume")
upload_col1, upload_col2 = st.columns([2,1])
with upload_col1:
    target_rel = st.text_input(
        "Target relative path (e.g. data/new_file.csv)",
        value=str(DEFAULT_SUBDIR / "uploaded.csv"),
        help="Where to save inside the volume",
    )
file_up = st.file_uploader("Choose a file to upload", type=None)
if st.button("Upload now", disabled=(file_up is None or not target_rel.strip())):
    try:
        target = safe_join(VOLUME_PATH, target_rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = file_up.read()
        target.write_bytes(data)
        st.success(f"Uploaded to {target_rel} ({human_size(len(data))})")
    except Exception as e:
        st.error(f"Upload failed: {e}")

st.caption("Tip: keep GitHub as the source of truth. Use this volume as a fast local copy.")
