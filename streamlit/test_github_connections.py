import streamlit as st
import os
from github import Github
from github import Auth
from utils import GITHUB_REPO, GITHUB_BRANCH

# These should be set in your Railway environment variables or directly here for a quick test
# (but environment variables are better for production)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_NAME = GITHUB_REPO
BRANCH_NAME = GITHUB_BRANCH

st.title("GitHub Connection Test")

if not GITHUB_TOKEN:
    st.error("GITHUB_TOKEN environment variable not found!")
else:
    st.success("GITHUB_TOKEN found!")
    try:
        auth = Auth.Token(GITHUB_TOKEN)
        g = Github(auth=auth)
        user = g.get_user()
        st.write(f"Authenticated GitHub User: {user.login}")

        repo = g.get_repo(REPO_NAME)
        st.success(f"Successfully accessed repository: {repo.full_name}")

        st.write(f"Looking for branch: {BRANCH_NAME}")
        try:
            branch = repo.get_branch(branch=BRANCH_NAME)
            st.success(f"Successfully found branch: {branch.name}")

            # Try to list some contents from the root of this branch
            st.write(f"Contents of the '{BRANCH_NAME}' branch (root directory):")
            contents = repo.get_contents("", ref=BRANCH_NAME)
            if contents:
                for content_file in contents:
                    st.write(f"- {content_file.path} ({content_file.type})")
            else:
                st.write("No content found in the root directory of the branch.")
            
            # Test reading a specific small file (e.g., your requirements.txt from that branch)
            try:
                file_content = repo.get_contents("requirements.txt", ref=BRANCH_NAME)
                st.success(f"Successfully read 'requirements.txt' from branch '{BRANCH_NAME}'.")
                st.text_area("requirements.txt content (decoded)", file_content.decoded_content.decode(), height=150)
            except Exception as e:
                st.error(f"Could not read 'requirements.txt' from branch '{BRANCH_NAME}': {e}")

        except Exception as e:
            st.error(f"Could not access branch '{BRANCH_NAME}': {e}")
            st.info(f"Make sure the branch '{BRANCH_NAME}' exists in the repository '{REPO_NAME}'.")


    except Exception as e:
        st.error(f"An error occurred during GitHub interaction: {e}")
        st.info("Check your GITHUB_TOKEN permissions and repository/branch names.")