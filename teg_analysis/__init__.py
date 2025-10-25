"""TEG Analysis Package - Modular refactoring of TEG tournament analysis system.

This package contains the core analysis and utilities for the TEG (annual golf
tournament) data system, organized into logical subsystems:

Packages:
- io: File operations and GitHub integration (Railway-aware) ✅ COMPLETE
- core: Data loading and transformation ✅ COMPLETE
- analysis: Scoring, rankings, and analysis functions ✅ COMPLETE
- display: Formatting and display utilities ✅ COMPLETE
- api: REST API endpoints (reserved for future use)
"""

# Import all layers to make them available at package level
from . import io
from . import core
from . import analysis
from . import display
from . import api

# Define public API
__all__ = [
    'io',
    'core',
    'analysis',
    'display',
    'api',
]
