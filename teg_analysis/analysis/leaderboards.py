"""Leaderboard generation for TEG tournaments and individual rounds."""

import pandas as pd


def filter_data_by_teg(all_data: pd.DataFrame, selected_tegnum) -> pd.DataFrame:
    """Filter data by TEG number, or return all if 'All TEGs'."""
    if selected_tegnum != 'All TEGs':
        return all_data[all_data['TEGNum'] == int(selected_tegnum)]
    return all_data
