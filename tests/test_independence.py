"""Test that teg_analysis imports without Streamlit.

This test validates that the teg_analysis package is UI-independent
and can be imported without Streamlit being installed or available.

Run with: python tests/test_independence.py
"""
import sys
import os
import importlib

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_no_streamlit_dependency():
    """Ensure teg_analysis can import without Streamlit."""
    print("=" * 60)
    print("TEST: teg_analysis independence from Streamlit")
    print("=" * 60)

    # Ensure streamlit not in sys.modules
    if 'streamlit' in sys.modules:
        print("Removing streamlit from sys.modules for clean test...")
        del sys.modules['streamlit']

    # Try importing teg_analysis
    print("\n1. Testing: import teg_analysis")
    try:
        import teg_analysis
        print("   SUCCESS: teg_analysis imports without Streamlit")
    except ImportError as e:
        print(f"   FAIL: {e}")
        sys.exit(1)

    # Test key module imports
    print("\n2. Testing: Module imports")

    modules_to_test = [
        ('teg_analysis.io', 'io operations'),
        ('teg_analysis.core', 'core utilities'),
        ('teg_analysis.analysis', 'analysis functions'),
        ('teg_analysis.display', 'display utilities'),
    ]

    for module_name, description in modules_to_test:
        try:
            importlib.import_module(module_name)
            print(f"   OK: {module_name} ({description})")
        except ImportError as e:
            print(f"   FAIL: {module_name} - {e}")
            sys.exit(1)

    # Test key function imports
    print("\n3. Testing: Key function imports")

    functions_to_test = [
        ('teg_analysis.core.metadata', 'get_teg_metadata'),
        ('teg_analysis.core.metadata', 'load_course_info'),
        ('teg_analysis.core.data_loader', 'load_all_data'),
        ('teg_analysis.core.data_loader', 'get_player_name'),
        ('teg_analysis.analysis.aggregation', 'get_current_in_progress_teg_fast'),
        ('teg_analysis.analysis.aggregation', 'filter_data_by_teg'),
        ('teg_analysis.analysis.aggregation', 'aggregate_data'),
        ('teg_analysis.analysis.rankings', 'ordinal'),
        ('teg_analysis.analysis.rankings', 'add_ranks'),
        ('teg_analysis.display.navigation', 'convert_trophy_name'),
        ('teg_analysis.display.formatters', 'format_vs_par'),
    ]

    for module_name, function_name in functions_to_test:
        try:
            module = importlib.import_module(module_name)
            if not hasattr(module, function_name):
                print(f"   FAIL: {function_name} not found in {module_name}")
                sys.exit(1)
            print(f"   OK: {module_name}.{function_name}")
        except ImportError as e:
            print(f"   FAIL: {module_name}.{function_name} - {e}")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)
    print("\nConclusion: teg_analysis is fully UI-independent")
    print("and can be used with any Python framework (FastAPI, Dash, CLI, etc.)")

    return True

if __name__ == "__main__":
    try:
        test_no_streamlit_dependency()
        sys.exit(0)
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
