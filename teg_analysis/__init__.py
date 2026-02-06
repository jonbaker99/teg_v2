"""TEG Analysis Package - Modular refactoring of TEG tournament analysis system.

This package contains the core analysis and utilities for the TEG (annual golf
tournament) data system, organized into logical subsystems:

Modules:
- constants: Centralised constants (file paths, player data, tournament metadata)
- io: File operations and GitHub integration (Railway-aware)
- core: Data loading and transformation
- analysis: Scoring, rankings, and analysis functions
- display: Formatting and display utilities
- api: REST API endpoints (placeholder for future use)
"""

from . import constants
from . import io
from . import core
from . import analysis
from . import display
from . import api

__all__ = [
    'constants',
    'io',
    'core',
    'analysis',
    'display',
    'api',
]
