"""Performance benchmark tests for teg_analysis package.

Tests that core operations complete within acceptable time limits.

Run with: python tests/test_teg_analysis_performance.py
"""
import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def benchmark_load_all_data():
    """Benchmark load_all_data() performance."""
    print("\n" + "=" * 60)
    print("BENCHMARK: load_all_data()")
    print("=" * 60)

    from teg_analysis.core.data_loader import load_all_data

    print("\nLoading all tournament data...")
    start = time.time()

    try:
        data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
        elapsed = time.time() - start

        rows = len(data)
        cols = len(data.columns)

        print(f"\n✓ Data loaded successfully")
        print(f"  Rows: {rows:,}")
        print(f"  Columns: {cols}")
        print(f"  Time: {elapsed:.3f}s")

        # Performance assertions
        max_time = 10.0  # seconds
        if elapsed < max_time:
            print(f"  ✓ Performance: {elapsed:.3f}s < {max_time}s (PASS)")
            return True, elapsed, rows
        else:
            print(f"  ✗ Performance: {elapsed:.3f}s >= {max_time}s (SLOW)")
            return False, elapsed, rows

    except Exception as e:
        print(f"\n✗ FAIL: {e}")
        return False, 0, 0

def benchmark_filter_data():
    """Benchmark filter_data_by_teg() performance."""
    print("\n" + "=" * 60)
    print("BENCHMARK: filter_data_by_teg()")
    print("=" * 60)

    from teg_analysis.core.data_loader import load_all_data
    from teg_analysis.analysis.leaderboards import filter_data_by_teg

    # Load data first
    print("\nLoading data...")
    data = load_all_data()

    print(f"Testing filter for TEG 18...")
    start = time.time()

    try:
        filtered = filter_data_by_teg(data, 18)
        elapsed = time.time() - start

        rows = len(filtered)

        print(f"\n✓ Filter completed")
        print(f"  Filtered rows: {rows:,}")
        print(f"  Time: {elapsed:.3f}s")

        # Performance assertion
        max_time = 1.0  # second
        if elapsed < max_time:
            print(f"  ✓ Performance: {elapsed:.3f}s < {max_time}s (PASS)")
            return True, elapsed
        else:
            print(f"  ✗ Performance: {elapsed:.3f}s >= {max_time}s (SLOW)")
            return False, elapsed

    except Exception as e:
        print(f"\n✗ FAIL: {e}")
        return False, 0

def benchmark_metadata():
    """Benchmark get_teg_metadata() performance."""
    print("\n" + "=" * 60)
    print("BENCHMARK: get_teg_metadata()")
    print("=" * 60)

    from teg_analysis.core.metadata import get_teg_metadata

    print("\nFetching metadata for TEG 18...")
    start = time.time()

    try:
        metadata = get_teg_metadata(18)
        elapsed = time.time() - start

        keys = len(metadata) if metadata else 0

        print(f"\n✓ Metadata retrieved")
        print(f"  Keys: {keys}")
        print(f"  Time: {elapsed:.3f}s")

        # Performance assertion
        max_time = 0.5  # seconds
        if elapsed < max_time:
            print(f"  ✓ Performance: {elapsed:.3f}s < {max_time}s (PASS)")
            return True, elapsed
        else:
            print(f"  ✗ Performance: {elapsed:.3f}s >= {max_time}s (SLOW)")
            return False, elapsed

    except Exception as e:
        print(f"\n✗ FAIL: {e}")
        return False, 0

def benchmark_aggregation():
    """Benchmark aggregate_data() performance."""
    print("\n" + "=" * 60)
    print("BENCHMARK: aggregate_data()")
    print("=" * 60)

    from teg_analysis.core.data_loader import load_all_data
    from teg_analysis.analysis.aggregation import aggregate_data

    # Load data first
    print("\nLoading data...")
    data = load_all_data()

    print(f"Aggregating to Player level...")
    start = time.time()

    try:
        aggregated = aggregate_data(data, 'Player', measures=['Sc', 'GrossVP'])
        elapsed = time.time() - start

        rows = len(aggregated)

        print(f"\n✓ Aggregation completed")
        print(f"  Aggregated rows: {rows:,}")
        print(f"  Time: {elapsed:.3f}s")

        # Performance assertion
        max_time = 2.0  # seconds
        if elapsed < max_time:
            print(f"  ✓ Performance: {elapsed:.3f}s < {max_time}s (PASS)")
            return True, elapsed
        else:
            print(f"  ✗ Performance: {elapsed:.3f}s >= {max_time}s (SLOW)")
            return False, elapsed

    except Exception as e:
        print(f"\n✗ FAIL: {e}")
        return False, 0

def run_all_benchmarks():
    """Run all performance benchmarks."""
    print("=" * 60)
    print("PERFORMANCE BENCHMARK SUITE")
    print("=" * 60)

    benchmarks = [
        ("load_all_data", benchmark_load_all_data),
        ("filter_data_by_teg", benchmark_filter_data),
        ("get_teg_metadata", benchmark_metadata),
        ("aggregate_data", benchmark_aggregation),
    ]

    results = []
    passed = 0
    failed = 0

    for name, benchmark_func in benchmarks:
        try:
            result = benchmark_func()
            if isinstance(result, tuple):
                success = result[0]
                timing = result[1] if len(result) > 1 else 0
            else:
                success = result
                timing = 0

            results.append((name, success, timing))

            if success:
                passed += 1
            else:
                failed += 1

        except Exception as e:
            failed += 1
            results.append((name, False, 0))
            print(f"\n✗ {name} benchmark failed: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)

    for name, success, timing in results:
        status = "✓ PASS" if success else "✗ FAIL"
        if timing > 0:
            print(f"{status} - {name}: {timing:.3f}s")
        else:
            print(f"{status} - {name}")

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{len(benchmarks)} benchmarks passed")
    print("=" * 60)

    if failed > 0:
        print(f"\n✗ {failed} benchmark(s) failed or too slow")
        print("\nNote: Performance issues may be due to:")
        print("  - First-time file I/O (no caching)")
        print("  - Large dataset size")
        print("  - System resources")
        return False
    else:
        print("\n✓ ALL BENCHMARKS PASSED")
        print("\nConclusion: teg_analysis performs within acceptable limits")
        return True

if __name__ == "__main__":
    try:
        success = run_all_benchmarks()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ BENCHMARK SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
