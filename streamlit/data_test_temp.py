import streamlit as st
from pathlib import Path
import datetime

# Point to your volume
DATA_DIR = Path("/mnt/data_repo")

# Ensure directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

test_file = DATA_DIR / "volume_test.txt"

if st.button("Write test file"):
    now = datetime.datetime.now().isoformat()
    test_file.write_text(f"Hello from Railway at {now}\n")
    st.success(f"Wrote file with timestamp {now}")

if st.button("Read test file"):
    if test_file.exists():
        content = test_file.read_text()
        st.info(f"File contents:\n{content}")
    else:
        st.error("Test file not found!")

st.caption("Try: Write → Restart service → Read. The file should still be there.")
