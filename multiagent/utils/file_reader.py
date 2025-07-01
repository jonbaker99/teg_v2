import os

def list_py_files(root="streamlit"):
    """
    Walk only the `streamlit/` app folder, skipping caches, venvs, editor dirs, data.
    """
    streamlit_root = os.path.join(os.getcwd(), root)
    for dirpath, dirnames, filenames in os.walk(streamlit_root):
        dirnames[:] = [
            d for d in dirnames
            if d not in {".venv", ".streamlit", ".vscode", "data", "__pycache__"}
        ]
        for fn in filenames:
            if fn.endswith(".py"):
                yield os.path.join(dirpath, fn)
