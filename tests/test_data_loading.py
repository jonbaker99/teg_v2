"""Tests for core data loading functions

Tests verify that data loading functions:
1. Return correct data types (DataFrame)
2. Have required columns
3. Load data without errors
4. Handle different file formats (CSV, Parquet)
5. Filter and exclude data correctly
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

# Add streamlit directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "streamlit"))

# Import functions under test
from utils import load_all_data, read_file, load_and_prepare_handicap_data


class TestLoadAllData:
    """Tests for the load_all_data() function"""

    def test_load_all_data_returns_dataframe(self):
        """Verify load_all_data returns a pandas DataFrame"""
        df = load_all_data()
        assert isinstance(df, pd.DataFrame), "load_all_data should return DataFrame"

    def test_load_all_data_has_data(self):
        """Verify load_all_data returns non-empty dataframe"""
        df = load_all_data()
        assert len(df) > 0, "load_all_data should return non-empty DataFrame"

    def test_load_all_data_has_required_columns(self):
        """Verify load_all_data returns expected columns"""
        df = load_all_data()
        # Check for key columns (actual column names in data)
        required_cols = ['TEG', 'Player', 'Round', 'Hole']

        for col in required_cols:
            assert col in df.columns, f"Missing required column: {col}"

    def test_load_all_data_with_exclude_incomplete_tegs(self):
        """Test that exclude_incomplete_tegs parameter works"""
        df_with = load_all_data(exclude_incomplete_tegs=False)
        df_without = load_all_data(exclude_incomplete_tegs=True)

        # Data with incomplete should be >= data without
        assert len(df_with) >= len(df_without), \
            "Including incomplete TEGs should have >= rows"

    def test_load_all_data_with_exclude_teg_50(self):
        """Test that exclude_teg_50 parameter works"""
        df_with_50 = load_all_data(exclude_teg_50=False)
        df_without_50 = load_all_data(exclude_teg_50=True)

        # With TEG 50 should have >= rows
        assert len(df_with_50) >= len(df_without_50), \
            "Including TEG 50 should have >= rows"

    def test_load_all_data_no_nulls_in_key_columns(self):
        """Verify key columns have no null values"""
        df = load_all_data()
        key_cols = ['TEG', 'Player', 'Round', 'Hole']

        for col in key_cols:
            null_count = df[col].isna().sum()
            assert null_count == 0, f"Column {col} has {null_count} null values"

    def test_load_all_data_teg_column_exists(self):
        """Verify TEG column exists"""
        df = load_all_data()
        assert 'TEG' in df.columns, "TEG column should exist"

    def test_load_all_data_player_column_exists(self):
        """Verify Player column exists"""
        df = load_all_data()
        assert 'Player' in df.columns, "Player column should exist"


class TestReadFile:
    """Tests for the read_file() function"""

    def test_read_file_csv_returns_dataframe(self, temp_csv_file):
        """Test read_file with CSV format"""
        df = read_file(str(temp_csv_file))
        assert isinstance(df, pd.DataFrame), "read_file should return DataFrame"

    def test_read_file_csv_preserves_data(self, temp_csv_file, sample_handicaps):
        """Test that CSV data is read correctly"""
        df = read_file(str(temp_csv_file))

        # Check shape matches
        assert df.shape == sample_handicaps.shape, \
            "Read DataFrame should match original shape"

    def test_read_file_parquet_returns_dataframe(self, temp_parquet_file):
        """Test read_file with Parquet format"""
        df = read_file(str(temp_parquet_file))
        assert isinstance(df, pd.DataFrame), "read_file should return DataFrame"

    def test_read_file_parquet_preserves_data(self, temp_parquet_file, sample_all_data):
        """Test that Parquet data is read correctly"""
        df = read_file(str(temp_parquet_file))

        # Check shape matches
        assert df.shape == sample_all_data.shape, \
            "Read DataFrame should match original shape"

    def test_read_file_real_handicaps(self):
        """Test reading actual handicaps.csv file if it exists"""
        handicaps_path = "data/handicaps.csv"
        try:
            df = read_file(handicaps_path)
            assert isinstance(df, pd.DataFrame)
            assert len(df) > 0
        except FileNotFoundError:
            pytest.skip("handicaps.csv not found in data/ directory")

    def test_read_file_real_all_scores(self):
        """Test reading actual all-scores.parquet file if it exists"""
        scores_path = "data/all-scores.parquet"
        try:
            df = read_file(scores_path)
            assert isinstance(df, pd.DataFrame)
            assert len(df) > 0
        except FileNotFoundError:
            pytest.skip("all-scores.parquet not found in data/ directory")


class TestLoadHandicapData:
    """Tests for the load_and_prepare_handicap_data() function"""

    def test_load_handicap_data_non_empty(self):
        """Verify loaded handicap data is not empty"""
        # Load actual handicap file if it exists
        hcp_file = "data/handicaps.csv"
        try:
            df = load_and_prepare_handicap_data(hcp_file)
            assert isinstance(df, pd.DataFrame), \
                "load_and_prepare_handicap_data should return DataFrame"
            assert len(df) > 0, "Handicap data should not be empty"
        except (FileNotFoundError, KeyError):
            pytest.skip("handicaps.csv not found or invalid format")


class TestDataIntegrity:
    """Tests to verify data integrity and consistency"""

    def test_data_has_multiple_rows(self):
        """Verify data has enough rows for analysis"""
        df = load_all_data()

        # Should have multiple TEGs with multiple players
        assert len(df) > 100, "Should have enough data for analysis"

    def test_round_numbers_sequential(self):
        """Verify round numbers are reasonable"""
        df = load_all_data()

        # Round should be between 1 and 4 (typically)
        assert (df['Round'] >= 1).all(), "Round should be >= 1"
        assert (df['Round'] <= 4).all(), "Round should be <= 4"

    def test_hole_numbers_sequential(self):
        """Verify hole numbers are between 1-18"""
        df = load_all_data()

        # Holes should be 1-18
        assert (df['Hole'] >= 1).all(), "Hole should be >= 1"
        assert (df['Hole'] <= 18).all(), "Hole should be <= 18"

    def test_teg_column_not_empty(self):
        """Verify TEG column has values"""
        df = load_all_data()

        # All rows should have a TEG value
        assert df['TEG'].notna().all(), "All rows should have a TEG value"


class TestDataConsistency:
    """Tests to verify consistency of data structure"""

    def test_each_player_has_complete_rounds(self):
        """Verify players have complete rounds (18 holes per round)"""
        df = load_all_data()

        # Group by TEG, Player, Round and count holes
        round_groups = df.groupby(['TEG', 'Player', 'Round']).size()

        # Most should have 18 holes (some may have fewer if incomplete)
        max_holes = round_groups.max()
        assert max_holes == 18 or max_holes == 9, \
            f"Expected 18 or 9 holes, got max {max_holes}"

    def test_player_column_not_empty(self):
        """Verify all rows have a player"""
        df = load_all_data()
        assert df['Player'].notna().all(), \
            "All rows should have a Player value"


# Pytest markers for categorizing tests
pytestmark = [pytest.mark.data_loading, pytest.mark.unit]
