#!/usr/bin/env python3
"""
Smoke Test for TEG Function Reorganization

Tests 5 representative pages to ensure core functionality works.
Run this before and after each batch of function moves.

Usage: python smoke_test.py
"""

import sys
import importlib
import traceback
from pathlib import Path

# Add streamlit directory to path
streamlit_dir = Path(__file__).parent / "streamlit"
sys.path.insert(0, str(streamlit_dir))

def test_import(module_name, description):
    """Test if a module can be imported without errors."""
    print(f"Testing {module_name} ({description})...")
    try:
        # Import the module
        module = importlib.import_module(module_name)
        print(f"  [SUCCESS] {module_name} imported successfully")
        return True
    except Exception as e:
        print(f"  [ERROR] {module_name} FAILED: {str(e)}")
        print(f"     Traceback: {traceback.format_exc()}")
        return False

def test_utils_functions():
    """Test critical utils functions can be imported."""
    print("\n=== Testing Core Utils Functions ===")
    try:
        from utils import (
            load_all_data, get_round_data, load_datawrapper_css,
            get_ranked_teg_data, get_best, get_worst,
            format_vs_par, create_stat_section
        )
        print("  [SUCCESS] Core utils functions imported successfully")
        
        # Test a simple function call
        formatted = format_vs_par(2.0)
        assert formatted == "+2", f"format_vs_par failed: expected '+2', got '{formatted}'"
        print("  [SUCCESS] format_vs_par() function call works")
        
        return True
    except Exception as e:
        print(f"  [ERROR] Utils functions FAILED: {str(e)}")
        print(f"     Traceback: {traceback.format_exc()}")
        return False

def run_smoke_tests():
    """Run all smoke tests."""
    print("=" * 60)
    print("TEG FUNCTION REORGANIZATION - SMOKE TEST")
    print("=" * 60)
    
    # Test representative pages covering different function groups
    tests = [
        ("101TEG History", "Trophy functions, win tables"),
        ("102TEG Results", "Data retrieval, charts"), 
        ("300TEG Records", "Statistical analysis, display formatting"),
        ("301Best_TEGs_and_Rounds", "Ranking functions"),
        ("teg_worsts", "Worst performance analysis")
    ]
    
    results = []
    
    # Test utils functions first
    utils_ok = test_utils_functions()
    results.append(("utils functions", utils_ok))
    
    # Test page imports
    print(f"\n=== Testing Representative Pages ===")
    for module_name, description in tests:
        # Replace spaces with underscores and remove special characters for import
        clean_name = module_name.replace(" ", "_").replace("&", "and")
        success = test_import(clean_name, description)
        results.append((module_name, success))
    
    # Summary
    print("\n" + "=" * 60)
    print("SMOKE TEST RESULTS")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\nSUMMARY: {passed}/{total} tests passed")
    
    if passed == total:
        print("[SUCCESS] ALL TESTS PASSED - System is stable")
        return True
    else:
        print("[WARNING] SOME TESTS FAILED - Do not proceed with function moves")
        return False

if __name__ == "__main__":
    success = run_smoke_tests()
    sys.exit(0 if success else 1)