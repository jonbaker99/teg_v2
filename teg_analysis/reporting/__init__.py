"""UI-agnostic report-generation pipeline for TEG tournaments.

Stages (see plan):
1. The Record    - hole-by-hole data (reuses teg_analysis.core.data_loader)
2. Notable events + 3-axis scoring  - events.py / scoring.py
3. Story plan (LLM)                  - story_plan.py        [todo]
4. Authoring (LLM): dry draft + entertaining report  - authoring.py [todo]
5. Rendering (narrative + round-by-round)             - render.py     [todo]

Stage 2 is pure Python and fully inspectable without any LLM/API key.
"""

from . import scoring
from . import events
from . import venue
from . import story_plan
from . import authoring
from . import render
from .events import build_notable_events, render_events_markdown
from .venue import build_venue_context, render_venue_markdown
from .story_plan import build_story_plan, StoryPlan
from .authoring import generate_dry_draft
from .render import apply_styling, style_report

__all__ = [
    "scoring", "events", "venue", "story_plan", "authoring", "render",
    "build_notable_events", "render_events_markdown",
    "build_venue_context", "render_venue_markdown",
    "build_story_plan", "StoryPlan",
    "generate_dry_draft",
    "apply_styling", "style_report",
]
