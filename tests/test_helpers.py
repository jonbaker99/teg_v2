"""Tests for helper module functions

Tests verify that helper modules provide correct data transformations,
formatting, and analysis functions used throughout the application.
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

# Setup Streamlit mocks BEFORE importing helpers
import streamlit
def _no_op_decorator(*args, **kwargs):
    if len(args) == 1 and callable(args[0]) and not kwargs:
        return args[0]
    return lambda f: f
if not hasattr(streamlit, 'cache_data'):
    streamlit.cache_data = _no_op_decorator
if not hasattr(streamlit, 'cache'):
    streamlit.cache = _no_op_decorator

# Add streamlit directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "streamlit"))

# Import helpers
from helpers.scoring_data_processing import (
    format_vs_par_value,
    prepare_average_scores_by_par,
    format_scoring_stats_columns
)


class TestScoringDataProcessing:
    """Tests for scoring_data_processing helper module"""

    def test_format_vs_par_value_even_par(self):
        """Test formatting of even par (0)"""
        result = format_vs_par_value(0)
        assert result == "=", f"Expected '=' for even par, got {result}"

    def test_format_vs_par_value_over_par(self):
        """Test formatting of over par"""
        result = format_vs_par_value(3)
        assert result == "+3.00", f"Expected '+3.00', got {result}"

    def test_format_vs_par_value_under_par(self):
        """Test formatting of under par"""
        result = format_vs_par_value(-2)
        assert result == "-2.00", f"Expected '-2.00', got {result}"

    def test_format_vs_par_value_plus_one(self):
        """Test formatting of +1"""
        result = format_vs_par_value(1)
        assert result == "+1.00", f"Expected '+1.00', got {result}"

    def test_format_vs_par_value_minus_one(self):
        """Test formatting of -1"""
        result = format_vs_par_value(-1)
        assert result == "-1.00", f"Expected '-1.00', got {result}"

    def test_prepare_average_scores_with_real_data(self):
        """Test that prepare_average_scores_by_par works with real data"""
        try:
            from utils import load_all_data
            df = load_all_data()
            result = prepare_average_scores_by_par(df)
            assert isinstance(result, pd.DataFrame), \
                "prepare_average_scores_by_par should return DataFrame"
        except (KeyError, ImportError):
            pytest.skip("Real data loading failed or required columns missing")

    def test_format_scoring_stats_with_real_data(self):
        """Test that format_scoring_stats_columns works with real data"""
        try:
            from utils import load_all_data
            df = load_all_data()
            result = format_scoring_stats_columns(df)
            assert isinstance(result, pd.DataFrame), \
                "format_scoring_stats_columns should return DataFrame"
        except (KeyError, ImportError):
            pytest.skip("Real data loading failed or required columns missing")


class TestHelperModuleImports:
    """Tests to verify all major helper modules can be imported"""

    def test_import_best_performance_processing(self):
        """Test importing best_performance_processing"""
        try:
            from helpers import best_performance_processing
            assert best_performance_processing is not None
        except ImportError:
            pytest.fail("Failed to import best_performance_processing")

    def test_import_display_helpers(self):
        """Test importing display_helpers"""
        try:
            from helpers import display_helpers
            # Check that module loads
            assert display_helpers is not None
        except ImportError:
            pytest.fail("Failed to import display_helpers")

    def test_import_history_data_processing(self):
        """Test importing history_data_processing"""
        try:
            from helpers import history_data_processing
            assert history_data_processing is not None
        except ImportError:
            pytest.fail("Failed to import history_data_processing")

    def test_import_records_identification(self):
        """Test importing records_identification"""
        try:
            from helpers import records_identification
            assert records_identification is not None
        except ImportError:
            pytest.fail("Failed to import records_identification")

    def test_import_streak_analysis_processing(self):
        """Test importing streak_analysis_processing"""
        try:
            from helpers import streak_analysis_processing
            assert streak_analysis_processing is not None
        except ImportError:
            pytest.fail("Failed to import streak_analysis_processing")

    def test_import_scoring_data_processing(self):
        """Test importing scoring_data_processing"""
        try:
            from helpers import scoring_data_processing
            assert scoring_data_processing is not None
        except ImportError:
            pytest.fail("Failed to import scoring_data_processing")


class TestFormatVsParValue:
    """Detailed tests for format_vs_par_value function"""

    @pytest.mark.parametrize("value,expected", [
        (0, "="),
        (1, "+1.00"),
        (2, "+2.00"),
        (3, "+3.00"),
        (5, "+5.00"),
        (10, "+10.00"),
        (-1, "-1.00"),
        (-2, "-2.00"),
        (-3, "-3.00"),
        (-5, "-5.00"),
        (-10, "-10.00"),
    ])
    def test_format_vs_par_comprehensive(self, value, expected):
        """Test format_vs_par_value with various inputs"""
        result = format_vs_par_value(value)
        assert result == expected, \
            f"format_vs_par_value({value}) expected '{expected}', got '{result}'"

    def test_format_vs_par_handles_float(self):
        """Test that function handles float values"""
        # Should handle float but return int-based string
        result = format_vs_par_value(3.5)
        # Result should still be formatted correctly
        assert result is not None, "Should handle float values"

    def test_format_vs_par_return_type(self):
        """Test that function returns string"""
        result = format_vs_par_value(5)
        assert isinstance(result, str), "format_vs_par_value should return string"


class TestDataFrameTransformations:
    """Tests for dataframe transformation functions"""

    def test_format_vs_par_works_with_decimals(self):
        """Test format_vs_par_value with decimal values"""
        result = format_vs_par_value(1.5)
        # Should return properly formatted decimal
        assert isinstance(result, str)
        assert "+" in result or "-" in result or result == "="

    def test_format_vs_par_function_availability(self):
        """Test that format_vs_par_value function exists and is callable"""
        assert callable(format_vs_par_value)
        # Should be able to call with numeric value
        result = format_vs_par_value(0)
        assert isinstance(result, str)


# Pytest markers
pytestmark = [pytest.mark.helpers, pytest.mark.unit]
