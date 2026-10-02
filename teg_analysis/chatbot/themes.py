"""Sort the whole Q&A log into themes with one model call (admin "Organise").

The bot already tags each new question with a theme as it answers. Over time
those drift (near-duplicates, one-offs), so this re-reads every question and
assigns each to one of a small, tidy set of themes.
"""

from __future__ import annotations

from pydantic import BaseModel

from teg_analysis.chatbot import qa_log

MAX_THEMES = 10

SYSTEM = f"""You organise questions people asked a golf-stats bot about the TEG, an annual golf
trip between friends. Group them into at most {MAX_THEMES} themes. Theme names are 1-3 words,
Title Case, plain and specific to golf stats (e.g. "Honours", "Records", "Course Stats",
"Player Form", "Streaks", "Round By Round"). Put anything not about the TEG in "Off-topic".
Follow-ups that only make sense in their chat (e.g. "and who's second?") go in the theme of
the question they follow. Every id must appear exactly once."""


class _Assignment(BaseModel):
    id: str
    theme: str


class _Themes(BaseModel):
    assignments: list[_Assignment]


def regroup_themes(model: str | None = None) -> dict:
    """Re-theme every logged question. Returns {"updated": n, "themes": [...]}."""
    from teg_analysis.chatbot.bot import get_model
    from teg_analysis.reporting.llm import generate_structured

    entries = qa_log.read_entries()
    if not entries:
        return {"updated": 0, "themes": []}
    lines = []
    for e in entries:
        short = e["id"][:8]
        lines.append(f"{short} [chat {e.get('conv', '')[:6]}]: {e['question'][:300]}")
    result, _usage = generate_structured(
        SYSTEM, "Questions (id [chat]: question):\n" + "\n".join(lines), _Themes,
        model=model or get_model(), stage="tegbot_themes",
    )
    by_short = {e["id"][:8]: e["id"] for e in entries}
    mapping = {by_short[a.id[:8]]: a.theme for a in result.assignments if a.id[:8] in by_short}
    updated = qa_log.set_themes(mapping)
    return {"updated": updated, "themes": qa_log.themes()}
