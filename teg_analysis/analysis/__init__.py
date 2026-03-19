"""Analysis Layer - Scoring, rankings, and analysis.

This package contains analysis functions for the TEG analysis system including:
- scoring: Scoring calculations and utilities
- rankings: Ranking functions
- aggregation: Core aggregation engine and data accessors
- history: TEG winners, history tables, eagles, completeness checking
- performance: Best/worst performance tables (parameterised)
- leaderboards: TEG and round leaderboard generation
- bestball: Bestball/worstball team format analysis
- streaks: Streak analysis
- records: Record identification
- commentary: Commentary generation
- pipeline: Data processing pipeline
"""

from . import scoring
from . import rankings
from . import aggregation
from . import history
from . import performance
from . import leaderboards
from . import bestball
from . import streaks
from . import records
from . import commentary
from . import pipeline
from . import eclectic

# Export commonly used functions for convenience
from .scoring import format_vs_par, get_net_competition_measure
from .aggregation import (
    aggregate_data,
    get_complete_teg_data,
    get_current_in_progress_teg_fast,
    get_last_completed_teg_fast,
    has_incomplete_teg_fast,
)
from .history import get_teg_winners
from .leaderboards import filter_data_by_teg
from .rankings import add_ranks, get_best, get_worst

__all__ = [
    'scoring',
    'rankings',
    'aggregation',
    'history',
    'performance',
    'leaderboards',
    'bestball',
    'streaks',
    'records',
    'commentary',
    'pipeline',
    'eclectic',
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
