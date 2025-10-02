import streamlit as st
from utils import (
    update_streaks_cache,
    update_bestball_cache,
    update_commentary_caches,
    update_teg_status_files,
    clear_all_caches
)
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.title("⚙️ Generate Cache Files")
st.markdown("Use this page to manually generate or refresh all analysis cache files. This is useful after making changes to the calculation logic or to create cache files for the first time.")
st.warning("This can be a slow process as it involves loading and processing all data.")

if st.button("🚀 Generate All Caches", type="primary"):
    with st.spinner("Clearing old caches..."):
        clear_all_caches()
        st.success("♻️ Caches cleared.")

    with st.spinner("📊 Updating TEG status files..."):
        update_teg_status_files()
        st.success("📊 TEG status files updated.")

    with st.spinner("🏁 Updating streaks cache..."):
        update_streaks_cache()
        st.success("🏁 Streaks cache updated.")

    with st.spinner("🏀 Updating bestball cache..."):
        update_bestball_cache()
        st.success("🏀 Bestball cache updated.")

    with st.spinner("📝 Updating commentary caches..."):
        update_commentary_caches()
        st.success("📝 Commentary caches updated.")

    st.balloons()
    st.success("✅ All cache files have been successfully generated!")

if st.button("🚀 Generate Bestball Caches", type="primary"):
    with st.spinner("🏀 Updating bestball cache..."):
        update_bestball_cache()
        st.success("🏀 Bestball cache updated.")