"""Performance benchmarks for critical functions"""
import pytest
import time
import pandas as pd
import sys
import os

# Add streamlit directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'streamlit'))

from utils import create_round_summary, load_all_data


def test_create_round_summary_performance():
    """Benchmark create_round_summary to establish baseline performance"""

    print("\n" + "="*60)
    print("PERFORMANCE BENCHMARK: create_round_summary()")
    print("="*60)

    # Load data
    print("\nLoading data...")
    df = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
    print(f"Loaded {len(df)} rows of golf data")

    # Run benchmark
    print("\nRunning create_round_summary()...")
    start = time.time()
    result = create_round_summary(df)
    elapsed = time.time() - start

    print(f"\nBASELINE PERFORMANCE:")
    print(f"  Time taken: {elapsed:.2f} seconds")
    print(f"  Result rows: {len(result)}")
    print(f"  Result columns: {len(result.columns)}")
    print(f"\nTARGET PERFORMANCE:")
    print(f"  Optimized goal: <3.0 seconds (10x speedup)")
    status = "OPTIMIZED" if elapsed < 3 else "NEEDS OPTIMIZATION"
    print(f"  Current status: {status}")
    print("="*60 + "\n")

    # Current baseline should be around 10-30 seconds per docs
    # After optimization, target is <3 seconds
    assert elapsed < 30, f"Function took {elapsed:.2f}s, which exceeds tolerance of 30s"
    assert len(result) > 0, "Result should have rows"


if __name__ == "__main__":
    test_create_round_summary_performance()
