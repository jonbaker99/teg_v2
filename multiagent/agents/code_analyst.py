# multiagent/agents/code_analyst.py

import os
from crewai import Agent
from openrouter import OpenRouter
from multiagent.utils.file_reader import list_py_files
from multiagent.utils.chunker import chunk_text
from multiagent.memory.store import load_memory, save_memory

class CodeAnalyst(Agent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize OpenRouter client for Claude
        self.client = OpenRouter(api_key=os.getenv("OPENROUTER_API_KEY"))
        # Choose your Claude model here
        self.model = "google/gemini-2.5-flash"

    def run(self):
        mem = load_memory()

        for path in list_py_files():
            text = open(path, encoding="utf-8").read()

            # Break each file into manageable chunks
            for idx, chunk in enumerate(chunk_text(text)):
                key = f"{path}:{idx}"
                if key in mem:
                    continue  # skip already-summarized chunks

                # Ask Claude to summarize
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{
                        "role": "user",
                        "content": (
                            "Summarize this code chunk—its purpose, inputs/outputs, "
                            f"and key functions:\n\n{chunk}"
                        )
                    }],
                )
                summary = response["choices"][0]["message"]["content"]
                mem[key] = summary

            # Persist summaries after each file
            save_memory(mem)

            # Collate and confirm the summary with the user
            file_summaries = [
                s for k, s in mem.items() if k.startswith(path)
            ]
            prompt = (
                f"Summary for `{os.path.basename(path)}`:\n"
                + "\n".join(f"- {s}" for s in file_summaries)
                + "\n\nDoes this capture the file correctly?"
            )
            self.ask_user(prompt)
