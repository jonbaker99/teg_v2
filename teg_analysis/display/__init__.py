"""Display Layer - Formatting and display utilities.

This package contains display and formatting functions for the TEG analysis system:
- formatters: Value formatting and display utilities
- tables: Table generation functions
- charts: Chart generation helpers

Phase IV - Modules created, to be fully populated with functions.
"""

from . import formatters
from . import tables
from . import charts

__all__ = [
    'formatters',
    'tables',
    'charts',
]
