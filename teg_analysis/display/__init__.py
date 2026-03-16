"""Display Layer - Formatting and display utilities.

This package contains display and formatting functions for the TEG analysis system:
- formatters: Value formatting and display utilities
- tables: Table generation functions
- navigation: Trophy name and URL utilities
"""

from . import formatters
from . import tables
from . import navigation

# Export commonly used functions for convenience
from .formatters import format_vs_par, prepare_records_table
from .tables import create_stat_section, datawrapper_table
from .navigation import (
    convert_trophy_name,
    get_trophy_full_name,
    convert_filename_to_streamlit_url,
    get_app_base_url,
)

__all__ = [
    'formatters',
    'tables',
    'navigation',
    # Common exports
    'format_vs_par',
    'prepare_records_table',
    'create_stat_section',
    'datawrapper_table',
    # Navigation utilities
    'convert_trophy_name',
    'get_trophy_full_name',
    'convert_filename_to_streamlit_url',
    'get_app_base_url',
]
