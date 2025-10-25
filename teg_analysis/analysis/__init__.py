"""Analysis Layer - Scoring, rankings, and analysis.

This package contains analysis functions for the TEG analysis system including:
- scoring: Scoring calculations and utilities
- rankings: Ranking functions
- aggregation: Data aggregation
- streaks: Streak analysis
- records: Record identification
- commentary: Commentary generation
- pipeline: Data processing pipeline

Phase III - Modules created, to be fully populated with functions.
"""

from . import scoring
from . import rankings
from . import aggregation
from . import streaks
from . import records
from . import commentary
from . import pipeline

__all__ = [
    'scoring',
    'rankings',
    'aggregation',
    'streaks',
    'records',
    'commentary',
    'pipeline',
]
