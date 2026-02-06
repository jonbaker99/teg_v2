"""pytest configuration and shared fixtures for TEG Analysis tests

This module provides shared fixtures and configuration for the test suite.
All test files can import and use these fixtures.
"""

import pytest
import pandas as pd
import sys
from pathlib import Path
import os

# Setup Streamlit mocks BEFORE importing any modules that use streamlit
# This allows tests to work with older Streamlit versions
import streamlit

def _no_op_decorator(*args, **kwargs):
    """Decorator that does nothing - used for cache_data/cache mocks"""
    # If called with a function directly, return it unchanged
    if len(args) == 1 and callable(args[0]) and not kwargs:
        return args[0]
    # Otherwise, return a decorator function
    return lambda f: f

if not hasattr(streamlit, 'cache_data'):
    streamlit.cache_data = _no_op_decorator
if not hasattr(streamlit, 'cache'):
    streamlit.cache = _no_op_decorator

# Add streamlit directory to path so we can import modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "streamlit"))

# Set environment variable to use local files (not GitHub)
os.environ['RAILWAY_ENVIRONMENT'] = ''


@pytest.fixture
def sample_all_data():
    """Sample all-data dataframe for testing core functionality

    Returns a minimal but valid dataframe matching the structure
    of all-scores.parquet with key columns for testing.
    """
    return pd.DataFrame({
        'TEG': [1, 1, 1, 1, 2, 2, 2, 2],
        'Player': ['AB', 'CD', 'EF', 'GH', 'AB', 'CD', 'EF', 'GH'],
        'Round': [1, 1, 1, 1, 1, 1, 1, 1],
        'Hole': [1, 2, 3, 4, 1, 2, 3, 4],
        'Score': [4, 5, 3, 4, 4, 4, 4, 5],
        'Par': [4, 4, 4, 4, 4, 4, 4, 4],
        'HCP': [10, 12, 8, 15, 10, 12, 8, 15],
        'Gross': [4, 5, 3, 4, 4, 4, 4, 5],
        'Net': [2, 3, 1, 2, 2, 2, 2, 3],
        'Stableford': [2, 1, 3, 2, 2, 2, 2, 1],
    })


@pytest.fixture
def sample_round_info():
    """Sample round info dataframe for testing course information

    Returns a dataframe with course and round metadata.
    """
    return pd.DataFrame({
        'TEG': [1, 1, 1, 1, 2, 2, 2, 2],
        'Round': [1, 2, 3, 4, 1, 2, 3, 4],
        'Course': ['Course A', 'Course B', 'Course C', 'Course A', 'Course D', 'Course E', 'Course F', 'Course G'],
        'Par': [72, 71, 72, 72, 70, 72, 71, 72],
        'HCP': [19, 18, 20, 19, 17, 19, 18, 20],
    })


@pytest.fixture
def sample_handicaps():
    """Sample handicaps dataframe for testing player reference data

    Returns a dataframe with player codes and handicaps.
    """
    return pd.DataFrame({
        'Code': ['AB', 'CD', 'EF', 'GH', 'IJ'],
        'Player': ['Alice Brown', 'Charlie Davis', 'Eve Foster', 'George Henry', 'Iris Johnson'],
        'Handicap': [10, 12, 8, 15, 9],
    })


@pytest.fixture
def sample_player_names():
    """Sample player name mapping for testing

    Returns a dictionary mapping player codes to names.
    """
    return {
        'AB': 'Alice Brown',
        'CD': 'Charlie Davis',
        'EF': 'Eve Foster',
        'GH': 'George Henry',
        'IJ': 'Iris Johnson',
    }


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create a temporary data directory for file tests

    Returns path to temporary directory for test files.
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def temp_csv_file(temp_data_dir, sample_handicaps):
    """Create a temporary CSV file for testing file operations

    Returns path to temporary CSV file with sample data.
    """
    csv_path = temp_data_dir / "test_handicaps.csv"
    sample_handicaps.to_csv(csv_path, index=False)
    return csv_path


@pytest.fixture
def temp_parquet_file(temp_data_dir, sample_all_data):
    """Create a temporary Parquet file for testing file operations

    Returns path to temporary Parquet file with sample data.
    """
    parquet_path = temp_data_dir / "test_scores.parquet"
    sample_all_data.to_parquet(parquet_path)
    return parquet_path
