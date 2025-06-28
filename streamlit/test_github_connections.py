import streamlit as st
import os
from github import Github, Auth, UnknownObjectException
import pandas as pd
from io import StringIO, BytesIO
import base64
import logging

# Configure logger for the test file
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

st.set_page_config(layout="wide")
st.title("GitHub Connection & File Content Test")

def get_github_token():
    """Get GitHub token from environment variables or Streamlit secrets"""
    # Try environment variable first (for Railway)
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    
    # Try Streamlit secrets (for local development)
    try:
        token = st.secrets["GITHUB_TOKEN"]
        if token:
            return token
    except (KeyError, AttributeError):
        pass
    
    # Try alternative secrets access method
    try:
        token = st.secrets.get("GITHUB_TOKEN")
        if token:
            return token
    except (AttributeError, TypeError):
        pass
    
    return None

# ## Debug token access
# st.write("**Debug: Token sources**")
# st.write(f"Environment variable: {os.environ.get('GITHUB_TOKEN') is not None}")

# try:
#     st.write(f"Secrets available: {hasattr(st, 'secrets')}")
#     if hasattr(st, 'secrets'):
#         st.write(f"Secrets keys: {list(st.secrets.keys()) if hasattr(st.secrets, 'keys') else 'No keys method'}")
#         st.write(f"GITHUB_TOKEN in secrets: {'GITHUB_TOKEN' in st.secrets}")
# except Exception as e:
#     st.write(f"Error accessing secrets: {e}")

# Get GitHub token
github_token = get_github_token()

if not github_token:
    st.error("GITHUB_TOKEN not found!")
    st.info("Please ensure GITHUB_TOKEN is set in your Railway environment variables or in .streamlit/secrets.toml for local testing.")
    st.stop()

st.success("GITHUB_TOKEN found!")

# Attempt to import constants from utils.py
try:
    from utils import (
        GITHUB_REPO, GITHUB_BRANCH,
        PARQUET_FILE, ALL_SCORES_FILE, HANDICAPS_FILE,
        ROUND_INFO_FILE, CSV_OUTPUT_FILE
    )
    logger.info("Successfully imported file constants from utils.py")
except ImportError:
    st.warning(
        "Could not import constants from utils.py. Using default paths for testing. "
        "Ensure utils.py is in the Python path or define constants directly in this test file if issues persist."
    )
    # Fallback definitions
    GITHUB_REPO = "jonbaker99/teg_v2"
    GITHUB_BRANCH = "railway-deployment"
    DATA_DIR_GITHUB = "data"
    PARQUET_FILE = f"{DATA_DIR_GITHUB}/all-data.parquet"
    ALL_SCORES_FILE = f"{DATA_DIR_GITHUB}/all-scores.csv"
    HANDICAPS_FILE = f"{DATA_DIR_GITHUB}/handicaps.csv"
    ROUND_INFO_FILE = f"{DATA_DIR_GITHUB}/round_info.csv"
    CSV_OUTPUT_FILE = f"{DATA_DIR_GITHUB}/all-data.csv"

try:
    auth = Auth.Token(github_token)
    g = Github(auth=auth)
    user = g.get_user()
    st.write(f"Authenticated GitHub User: **{user.login}**")

    repo = g.get_repo(GITHUB_REPO)
    st.success(f"Successfully accessed repository: **{repo.full_name}**")

    st.info(f"Attempting to access branch: **{GITHUB_BRANCH}**")
    try:
        branch = repo.get_branch(branch=GITHUB_BRANCH)
        st.success(f"Successfully found branch: **{branch.name}** (Commit SHA: {branch.commit.sha})")

        # Test individual files
        files_to_test = [
            {"path": PARQUET_FILE, "type": "parquet"},
            {"path": ALL_SCORES_FILE, "type": "csv"},
            {"path": HANDICAPS_FILE, "type": "csv"},
            {"path": ROUND_INFO_FILE, "type": "csv"},
            {"path": CSV_OUTPUT_FILE, "type": "csv", "problematic": True}
        ]

        for file_info in files_to_test:
            file_path = file_info["path"]
            file_type = file_info["type"]
            is_problematic = file_info.get("problematic", False)
            
            st.markdown("---")
            st.subheader(f"Testing File: `{file_path}` ({file_type.upper()}) {'🔴' if is_problematic else ''}")
            
            decoded_content = None
            raw_bytes_for_parquet = None

            try:
                logger.info(f"Fetching {file_path} from branch {GITHUB_BRANCH}...")
                file_content_obj = repo.get_contents(file_path, ref=GITHUB_BRANCH)
                st.info(f"Successfully fetched metadata for: `{file_path}` (SHA: {file_content_obj.sha}, Size: {file_content_obj.size} bytes)")

                if file_content_obj.size == 0:
                    st.error(f"File `{file_path}` is reported as 0 bytes by GitHub.")
                    decoded_content = ""
                elif file_content_obj.encoding == 'base64':
                    if isinstance(file_content_obj.content, str):
                        raw_bytes_for_parquet = base64.b64decode(file_content_obj.content)
                        try:
                            decoded_content = raw_bytes_for_parquet.decode('utf-8')
                        except UnicodeDecodeError as ude:
                            st.error(f"UnicodeDecodeError for `{file_path}`: {ude}. Trying 'latin-1'.")
                            decoded_content = raw_bytes_for_parquet.decode('latin-1', errors='replace')
                    else:
                        st.warning(f"Content for `{file_path}` is not a base64 string but encoding is '{file_content_obj.encoding}'. Type: {type(file_content_obj.content)}")
                        raw_bytes_for_parquet = file_content_obj.content
                        decoded_content = raw_bytes_for_parquet.decode('utf-8', errors='replace')
                elif file_content_obj.content is not None:
                     decoded_content = file_content_obj.content
                     raw_bytes_for_parquet = decoded_content.encode('utf-8')
                else:
                    st.error(f"No 'content' attribute or content is None for `{file_path}`. Encoding: {file_content_obj.encoding}")
                    decoded_content = ""

                if is_problematic or st.checkbox(f"Show content details for {file_path}?", key=f"details_{file_path}"):
                    st.text_area(f"First 500 chars of DECODED content for `{file_path}`:", (decoded_content or "")[:500], height=100)
                    st.write(f"Total length of DECODED content for `{file_path}`: {len(decoded_content or '')}")
                    st.write(f"Content starts with: {repr((decoded_content or '')[:20])}")
                    st.write(f"Content ends with: {repr((decoded_content or '')[-20:])}")

                if not decoded_content or not decoded_content.strip():
                    st.error(f"Content of `{file_path}` is EMPTY or effectively whitespace after decoding and stripping.")
                    continue

                # Attempt to parse
                try:
                    if file_type == 'csv':
                        if is_problematic:
                            st.info(f"Attempting lenient CSV parse for `{file_path}`...")
                            df = pd.read_csv(StringIO(decoded_content), skip_blank_lines=True, on_bad_lines='warn')
                        else:
                            df = pd.read_csv(StringIO(decoded_content))
                        st.success(f"Successfully parsed `{file_path}` as CSV. Shape: {df.shape}")
                        if df.empty:
                            st.warning(f"`{file_path}` parsed as CSV but resulted in an empty DataFrame (no data rows).")
                    
                    elif file_type == 'parquet':
                        if not raw_bytes_for_parquet:
                            st.error(f"Cannot parse Parquet for `{file_path}`: raw bytes not available.")
                            continue
                        df = pd.read_parquet(BytesIO(raw_bytes_for_parquet))
                        st.success(f"Successfully parsed `{file_path}` as Parquet. Shape: {df.shape}")
                        if df.empty:
                            st.warning(f"`{file_path}` parsed as Parquet but resulted in an empty DataFrame.")
                    
                    if not df.empty and st.checkbox(f"Show head for {file_path}", key=f"head_{file_path}"):
                        st.dataframe(df.head(3))

                except pd.errors.EmptyDataError:
                    st.error(f"Pandas `EmptyDataError` for `{file_path}`: No columns to parse. The file content is likely empty or has no data rows after headers.")
                except Exception as parse_e:
                    st.error(f"Error PARSING `{file_path}` (type: {file_type}): {parse_e}")
                    logger.error(f"Parsing error for {file_path}:", exc_info=True)

            except UnknownObjectException:
                st.error(f"File NOT FOUND on GitHub: `{file_path}` on branch `{GITHUB_BRANCH}`")
                logger.warning(f"File not found: {file_path} on branch {GITHUB_BRANCH}")
            except Exception as fetch_e:
                st.error(f"Error FETCHING or processing `{file_path}` from GitHub: {fetch_e}")
                logger.error(f"Fetching/processing error for {file_path}:", exc_info=True)

    except Exception as branch_e:
        st.error(f"Could not access branch '{GITHUB_BRANCH}': {branch_e}")
        st.info(f"Make sure the branch '{GITHUB_BRANCH}' exists in the repository '{GITHUB_REPO}'.")
        logger.error(f"Branch access error for {GITHUB_BRANCH}:", exc_info=True)

except Exception as e:
    st.error(f"An error occurred during GitHub initial interaction: {e}")
    st.info("Check your GITHUB_TOKEN permissions and repository/branch names.")
    logger.error("GitHub initial interaction error:", exc_info=True)


