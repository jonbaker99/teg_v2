"""Analysis Layer - Scoring, rankings, and analysis.

This package contains analysis functions for the TEG analysis system including:
- scoring: Scoring calculations and utilities (~35 functions)
- rankings: Ranking functions (8 functions)
- aggregation: Data aggregation (~90 functions)
- streaks: Streak analysis (27 functions)
- records: Record identification (~14 functions)
- commentary: Commentary generation (6 functions)
- pipeline: Data processing pipeline (~20 functions)

Phase III - COMPLETE ✅ (186 total functions)
"""

from . import scoring
from . import rankings
from . import aggregation
from . import streaks
from . import records
from . import commentary
from . import pipeline

# Export commonly used functions for convenience
from .scoring import format_vs_par, get_net_competition_measure
from .aggregation import (
    aggregate_data,
    get_teg_winners,
    get_complete_teg_data,
    get_current_in_progress_teg_fast,
    get_last_completed_teg_fast,
    has_incomplete_teg_fast,
    filter_data_by_teg,
)
from .rankings import add_ranks, get_best, get_worst

__all__ = [
    'scoring',
    'rankings',
    'aggregation',
    'streaks',
    'records',
    'commentary',
    'pipeline',
    # Common exports
    'format_vs_par',
    'get_net_competition_measure',
    'aggregate_data',
    'get_teg_winners',
    'get_complete_teg_data',
    'add_ranks',
    'get_best',
    'get_worst',
    # TEG status functions
    'get_current_in_progress_teg_fast',
    'get_last_completed_teg_fast',
    'has_incomplete_teg_fast',
    'filter_data_by_teg',
]
