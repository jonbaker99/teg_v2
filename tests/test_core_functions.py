"""Test core teg_analysis functions work correctly.

This test validates that key functions in teg_analysis return expected
data types and structures without requiring Streamlit UI.

Run with: python tests/test_core_functions.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_metadata_functions():
    """Test metadata functions return expected types."""
    print("\n" + "=" * 60)
    print("TEST: Metadata Functions")
    print("=" * 60)

    from teg_analysis.core.metadata import get_teg_metadata, load_course_info

    # Test get_teg_metadata
    print("\n1. Testing get_teg_metadata(18)")
    try:
        metadata = get_teg_metadata(18)
        assert isinstance(metadata, dict), "Should return dict"
        print(f"   ✓ Returns dict with {len(metadata)} keys")
        if metadata:
            print(f"   ✓ Sample keys: {list(metadata.keys())[:5]}")
    except Exception as e:
        print(f"   ✗ FAIL: {e}")
        return False

    # Test load_course_info
    print("\n2. Testing load_course_info()")
    try:
        course_info = load_course_info()
        assert hasattr(course_info, 'shape'), "Should return DataFrame"
        print(f"   ✓ Returns DataFrame with shape {course_info.shape}")
    except Exception as e:
        print(f"   ✗ FAIL: {e}")
        return False

    return True

def test_data_loader_functions():
    """Test data loader functions return expected types."""
    print("\n" + "=" * 60)
    print("TEST: Data Loader Functions")
    print("=" * 60)

    from teg_analysis.core.data_loader import get_player_name

    # Test get_player_name
    print("\n1. Testing get_player_name('JB')")
    try:
        name = get_player_name('JB')
        assert isinstance(name, str), "Should return string"
        print(f"   ✓ Returns: '{name}'")
    except Exception as e:
        print(f"   ✗ FAIL: {e}")
        return False

    # Test unknown player
    print("\n2. Testing get_player_name('UNKNOWN')")
    try:
        name = get_player_name('UNKNOWN')
        assert 'Unknown' in name or name == 'UNKNOWN', "Should handle unknown players"
        print(f"   ✓ Returns: '{name}'")
    except Exception as e:
        print(f"   ✗ FAIL: {e}")
        return False

    return True

def test_aggregation_functions():
    """Test aggregation functions return expected types."""
    print("\n" + "=" * 60)
    print("TEST: Aggregation Functions")
    print("=" * 60)

    from teg_analysis.analysis.aggregation import (
        get_current_in_progress_teg_fast,
        get_last_completed_teg_fast,
        has_incomplete_teg_fast
    )

    # Test get_current_in_progress_teg_fast
    print("\n1. Testing get_current_in_progress_teg_fast()")
    try:
        result = get_current_in_progress_teg_fast()
        assert isinstance(result, tuple), "Should return tuple"
        assert len(result) == 2, "Should return (teg_num, rounds)"
        print(f"   ✓ Returns: {result}")
    except Exception as e:
        print(f"   ✗ FAIL: {e}")
        return False

    # Test get_last_completed_teg_fast
    print("\n2. Testing get_last_completed_teg_fast()")
    try:
        result = get_last_completed_teg_fast()
        assert isinstance(result, tuple), "Should return tuple"
        assert len(result) == 2, "Should return (teg_num, rounds)"
        print(f"   ✓ Returns: {result}")
    except Exception as e:
        print(f"   ✗ FAIL: {e}")
        return False

    # Test has_incomplete_teg_fast
    print("\n3. Testing has_incomplete_teg_fast()")
    try:
        result = has_incomplete_teg_fast()
        assert isinstance(result, bool), "Should return bool"
        print(f"   ✓ Returns: {result}")
    except Exception as e:
        print(f"   ✗ FAIL: {e}")
        return False

    return True

def test_ranking_functions():
    """Test ranking functions return expected types."""
    print("\n" + "=" * 60)
    print("TEST: Ranking Functions")
    print("=" * 60)

    from teg_analysis.analysis.rankings import ordinal

    # Test ordinal
    test_cases = [
        (1, "1st"),
        (2, "2nd"),
        (3, "3rd"),
        (4, "4th"),
        (11, "11th"),
        (21, "21st"),
        (22, "22nd"),
        (23, "23rd"),
    ]

    print("\n1. Testing ordinal() function")
    for num, expected in test_cases:
        try:
            result = ordinal(num)
            assert result == expected, f"Expected {expected}, got {result}"
            print(f"   ✓ ordinal({num}) = '{result}'")
        except Exception as e:
            print(f"   ✗ FAIL: ordinal({num}) - {e}")
            return False

    return True

def test_display_functions():
    """Test display functions return expected types."""
    print("\n" + "=" * 60)
    print("TEST: Display Functions")
    print("=" * 60)

    from teg_analysis.display.formatters import format_vs_par
    from teg_analysis.display.navigation import convert_trophy_name

    # Test format_vs_par
    print("\n1. Testing format_vs_par()")
    test_cases = [
        (0, "="),
        (3, "+3"),
        (-2, "-2"),
    ]

    for value, expected in test_cases:
        try:
            result = format_vs_par(value)
            assert result == expected, f"Expected {expected}, got {result}"
            print(f"   ✓ format_vs_par({value}) = '{result}'")
        except Exception as e:
            print(f"   ✗ FAIL: format_vs_par({value}) - {e}")
            return False

    # Test convert_trophy_name
    print("\n2. Testing convert_trophy_name()")
    test_cases = [
        ("trophy", "TEG Trophy"),
        ("TEG Trophy", "trophy"),
        ("jacket", "Green Jacket"),
    ]

    for input_name, expected in test_cases:
        try:
            result = convert_trophy_name(input_name)
            assert result == expected, f"Expected {expected}, got {result}"
            print(f"   ✓ convert_trophy_name('{input_name}') = '{result}'")
        except Exception as e:
            print(f"   ✗ FAIL: convert_trophy_name('{input_name}') - {e}")
            return False

    return True

def run_all_tests():
    """Run all core function tests."""
    print("=" * 60)
    print("CORE FUNCTIONS TEST SUITE")
    print("=" * 60)

    tests = [
        ("Metadata Functions", test_metadata_functions),
        ("Data Loader Functions", test_data_loader_functions),
        ("Aggregation Functions", test_aggregation_functions),
        ("Ranking Functions", test_ranking_functions),
        ("Display Functions", test_display_functions),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"\n✓ {test_name} PASSED")
            else:
                failed += 1
                print(f"\n✗ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"\n✗ {test_name} FAILED: {e}")

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{len(tests)} tests passed")
    print("=" * 60)

    if failed > 0:
        print(f"\n✗ {failed} test(s) failed")
        return False
    else:
        print("\n✓ ALL TESTS PASSED")
        print("\nConclusion: All core functions work correctly without UI")
        return True

if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ TEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
