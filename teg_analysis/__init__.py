"""TEG Analysis Package - Modular refactoring of TEG tournament analysis system.

This package contains the core analysis and utilities for the TEG (annual golf
tournament) data system, organized into logical subsystems:

Packages:
- io: File operations and GitHub integration (Railway-aware)
- core: Data loading and transformation (to be implemented in Phase II)
- analysis: Scoring, rankings, and analysis functions (to be implemented in Phase III)
- display: Formatting and display utilities (to be implemented in Phase IV)
- api: REST API endpoints (reserved for future use)
"""

# Import I/O layer to make it available at package level
from . import io

# Define public API
__all__ = [
    'io',
]
