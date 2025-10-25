"""Display Layer - Formatting and display utilities.

This package contains display and formatting functions for the TEG analysis system:
- formatters: Value formatting and display utilities (9 functions)
- tables: Table generation functions (7 functions)
- charts: Chart generation helpers (0 functions)

Phase IV - COMPLETE ✅
"""

from . import formatters
from . import tables
from . import charts

# Export commonly used functions for convenience
from .formatters import format_vs_par, prepare_records_table
from .tables import create_stat_section, datawrapper_table

__all__ = [
    'formatters',
    'tables',
    'charts',
    # Common exports
    'format_vs_par',
    'prepare_records_table',
    'create_stat_section',
    'datawrapper_table',
]
