"""Core Layer - Data loading and transformation.

This package contains data loading and transformation functions for the TEG analysis system.

Modules:
- data_loader: Primary data loading functions (load_all_data, process_round_for_all_scores)
- data_transforms: Data transformation and enrichment functions

Phase II implementation - migrated from streamlit/utils.py
"""

from .data_loader import (
    load_all_data,
    get_number_of_completed_rounds_by_teg,
    get_incomplete_tegs,
    exclude_incomplete_tegs_function,
    get_player_name,
    process_round_for_all_scores,
    add_round_info,
)

from .data_transforms import (
    check_hc_strokes_combinations,
    add_cumulative_scores,
    add_rankings_and_gaps,
    save_to_parquet,
    reshape_round_data,
    load_and_prepare_handicap_data,
)

__all__ = [
    # data_loader
    'load_all_data',
    'get_number_of_completed_rounds_by_teg',
    'get_incomplete_tegs',
    'exclude_incomplete_tegs_function',
    'get_player_name',
    'process_round_for_all_scores',
    'add_round_info',
    # data_transforms
    'check_hc_strokes_combinations',
    'add_cumulative_scores',
    'add_rankings_and_gaps',
    'save_to_parquet',
    'reshape_round_data',
    'load_and_prepare_handicap_data',
]
