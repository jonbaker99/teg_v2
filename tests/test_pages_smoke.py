"""Smoke tests for page imports and basic functionality

These are quick tests to verify that major page files can be imported
and basic functionality is available. Full integration testing would
require a Streamlit test environment.
"""

import pytest
import sys
from pathlib import Path

# Setup Streamlit mocks
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


class TestUtilsImport:
    """Test that core utils module imports successfully"""

    def test_utils_imports(self):
        """Test utils module can be imported"""
        try:
            import utils
            assert utils is not None
        except ImportError as e:
            pytest.fail(f"Failed to import utils: {e}")

    def test_utils_has_core_functions(self):
        """Test that utils has key functions"""
        from utils import load_all_data, read_file
        assert callable(load_all_data)
        assert callable(read_file)


class TestHelpersImport:
    """Test that helper modules can be imported"""

    def test_helpers_init_imports(self):
        """Test helpers/__init__.py imports"""
        try:
            import helpers
            assert helpers is not None
        except ImportError as e:
            pytest.fail(f"Failed to import helpers: {e}")

    def test_helpers_submodules_import(self):
        """Test individual helper submodules"""
        try:
            from helpers import scoring_data_processing
            from helpers import streak_analysis_processing
            from helpers import records_identification
            assert scoring_data_processing is not None
            assert streak_analysis_processing is not None
            assert records_identification is not None
        except ImportError as e:
            pytest.fail(f"Failed to import helper submodules: {e}")


class TestMajorPageStructure:
    """Test that major page categories have necessary structure"""

    def test_navigation_file_exists(self):
        """Test that nav.py exists"""
        nav_path = project_root / "streamlit" / "nav.py"
        assert nav_path.exists(), "nav.py should exist"

    def test_data_directory_exists(self):
        """Test that data directory exists"""
        data_path = project_root / "data"
        assert data_path.exists(), "data/ directory should exist"

    def test_required_data_files_exist(self):
        """Test that required data files exist"""
        all_scores = project_root / "data" / "all-scores.parquet"
        handicaps = project_root / "data" / "handicaps.csv"
        # At least one should exist for tests to make sense
        assert all_scores.exists() or handicaps.exists(), \
            "Should have at least one data file"


class TestCommentaryModules:
    """Test that commentary generation modules exist"""

    def test_commentary_directory_exists(self):
        """Test that commentary directory exists"""
        commentary_path = project_root / "streamlit" / "commentary"
        assert commentary_path.exists(), "commentary/ directory should exist"

    def test_commentary_modules_import(self):
        """Test that commentary modules can be imported"""
        try:
            from commentary import generate_tournament_commentary_v2
            assert generate_tournament_commentary_v2 is not None
        except ImportError:
            pytest.skip("Commentary modules not available")


class TestStylesModules:
    """Test that styling modules exist"""

    def test_styles_directory_exists(self):
        """Test that styles directory exists"""
        styles_path = project_root / "streamlit" / "styles"
        assert styles_path.exists(), "styles/ directory should exist"

    def test_styles_modules_import(self):
        """Test that style modules can be imported"""
        try:
            from styles import altair_theme
            assert altair_theme is not None
        except ImportError:
            pytest.skip("Styles modules not available")


class TestRequiredImports:
    """Test that major dependencies are available"""

    def test_pandas_available(self):
        """Test that pandas is available"""
        try:
            import pandas as pd
            assert pd is not None
        except ImportError:
            pytest.fail("pandas should be installed")

    def test_streamlit_available(self):
        """Test that streamlit is available"""
        try:
            import streamlit as st
            assert st is not None
        except ImportError:
            pytest.fail("streamlit should be installed")

    def test_numpy_available(self):
        """Test that numpy is available"""
        try:
            import numpy as np
            assert np is not None
        except ImportError:
            pytest.fail("numpy should be installed")

    def test_plotly_available(self):
        """Test that plotly is available"""
        try:
            import plotly.graph_objects as go
            assert go is not None
        except ImportError:
            pytest.fail("plotly should be installed")


# Pytest markers
pytestmark = [pytest.mark.pages, pytest.mark.smoke]
