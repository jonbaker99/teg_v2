import sys, site
print("EXE:", sys.executable)
print("PATHS:", site.getsitepackages())


from multiagent.agents.code_analyst import CodeAnalyst
from multiagent.utils.file_reader import list_py_files

print("Found files:", list(list_py_files()))

if __name__ == "__main__":
    # Ensure your LLM key is in env, e.g. export OPENAI_API_KEY=…
    CodeAnalyst().run()
