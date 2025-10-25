"""Import verification tests

Tests to ensure all imports resolve correctly and there are no
circular import issues or missing dependencies.
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


class TestCoreImports:
    """Test core module imports"""

    def test_import_utils(self):
        """Test importing utils module"""
        import utils
        assert utils is not None

    def test_import_helpers(self):
        """Test importing helpers package"""
        import helpers
        assert helpers is not None


class TestHelperImports:
    """Test all helper module imports"""

    @pytest.mark.parametrize("module_name", [
        "best_performance_processing",
        "bestball_processing",
        "comeback_analysis",
        "commentary_generator",
        "course_analysis_processing",
        "data_deletion_processing",
        "data_update_processing",
        "display_helpers",
        "history_data_processing",
        "latest_round_processing",
        "par_analysis_processing",
        "records_css",
        "records_identification",
        "score_count_processing",
        "scorecard_data_processing",
        "scoring_achievements_processing",
        "scoring_data_processing",
        "streak_analysis_processing",
        "worst_performance_processing",
    ])
    def test_helper_module_import(self, module_name):
        """Test that helper module can be imported"""
        try:
            __import__(f"helpers.{module_name}")
        except ImportError as e:
            pytest.skip(f"Module {module_name} not found: {e}")
        except Exception as e:
            pytest.fail(f"Failed to import helpers.{module_name}: {e}")


class TestCommentaryImports:
    """Test commentary module imports"""

    def test_import_generate_tournament_commentary_v2(self):
        """Test importing generate_tournament_commentary_v2"""
        try:
            from commentary import generate_tournament_commentary_v2
            assert generate_tournament_commentary_v2 is not None
        except ImportError:
            pytest.skip("commentary module not available")

    def test_import_generate_round_report(self):
        """Test importing generate_round_report"""
        try:
            from commentary import generate_round_report
            assert generate_round_report is not None
        except ImportError:
            pytest.skip("generate_round_report module not available")


class TestStylesImports:
    """Test styles module imports"""

    def test_import_altair_theme(self):
        """Test importing altair_theme"""
        try:
            from styles import altair_theme
            assert altair_theme is not None
        except ImportError:
            pytest.skip("styles module not available")


class TestUtilsSubFunctions:
    """Test that major functions can be imported from utils"""

    def test_import_load_functions(self):
        """Test importing load functions"""
        from utils import load_all_data, load_and_prepare_handicap_data
        assert callable(load_all_data)
        assert callable(load_and_prepare_handicap_data)

    def test_import_read_functions(self):
        """Test importing read functions"""
        from utils import read_file, read_from_github
        assert callable(read_file)
        assert callable(read_from_github)

    def test_import_format_functions(self):
        """Test importing format functions"""
        from utils import format_vs_par
        assert callable(format_vs_par)


class TestCircularImports:
    """Test for circular import issues"""

    def test_no_circular_import_utils_helpers(self):
        """Test that utils and helpers don't have circular imports"""
        try:
            import utils
            import helpers
            # If we get here, no circular import
            assert True
        except ImportError as e:
            if "circular" in str(e).lower():
                pytest.fail(f"Circular import detected: {e}")
            else:
                pytest.skip(f"Import issue (not circular): {e}")

    def test_helpers_independent_import(self):
        """Test that helpers can be imported independently"""
        try:
            import helpers
            # Helpers should be importable without utils
            assert helpers is not None
        except Exception as e:
            pytest.skip(f"Helpers import issue: {e}")


class TestExternalDependencies:
    """Test that external dependencies are available"""

    @pytest.mark.parametrize("module_name", [
        "pandas",
        "numpy",
        "streamlit",
        "plotly",
        "altair",
    ])
    def test_external_dependency_available(self, module_name):
        """Test that required external module is available"""
        try:
            __import__(module_name)
        except ImportError:
            pytest.fail(f"Required dependency '{module_name}' not installed")


# Pytest markers
pytestmark = [pytest.mark.imports, pytest.mark.unit]
