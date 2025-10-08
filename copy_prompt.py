import importlib.util
import pyperclip
import sys

prompt_name = sys.argv[1] if len(sys.argv) > 1 else "MAIN_REPORT_PROMPT"

spec = importlib.util.spec_from_file_location("prompts", "streamlit/commentary/prompts.py")
prompts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prompts)

if hasattr(prompts, prompt_name):
    pyperclip.copy(getattr(prompts, prompt_name))
    print(f"✅ Copied {prompt_name} to clipboard.")
else:
    print(f"❌ Prompt '{prompt_name}' not found.")
