"""FastAPI Example - Using teg_analysis with FastAPI REST API.

This example demonstrates how to use the teg_analysis package
to create a REST API for TEG tournament data using FastAPI.

Installation:
    pip install fastapi uvicorn

Run the server:
    uvicorn examples.example_fastapi:app --reload

Then visit:
    http://localhost:8000/docs - Interactive API documentation
    http://localhost:8000/teg/18 - Get TEG 18 metadata
    http://localhost:8000/current - Get current in-progress TEG
"""

from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

# Import teg_analysis (no Streamlit required!)
from teg_analysis.core.metadata import get_teg_metadata, load_course_info
from teg_analysis.core.data_loader import load_all_data, get_player_name
from teg_analysis.analysis.aggregation import (
    get_current_in_progress_teg_fast,
    get_last_completed_teg_fast,
    aggregate_data,
)
from teg_analysis.analysis.leaderboards import filter_data_by_teg
from teg_analysis.analysis.rankings import ordinal
from teg_analysis.display.formatters import format_vs_par

# Create FastAPI app
app = FastAPI(
    title="TEG Analysis API",
    description="REST API for TEG golf tournament analysis",
    version="1.0.0",
)

# ============================================================================
# Endpoints
# ============================================================================

@app.get("/")
def root():
    """API root - welcome message."""
    return {
        "message": "Welcome to TEG Analysis API",
        "docs": "/docs",
        "endpoints": {
            "metadata": "/teg/{teg_num}",
            "current": "/current",
            "last_completed": "/last-completed",
            "courses": "/courses",
            "player": "/player/{initials}",
            "data": "/data?teg={num}",
        }
    }

@app.get("/teg/{teg_num}")
def get_teg(teg_num: int, round_num: Optional[int] = None):
    """Get TEG metadata.

    Args:
        teg_num: TEG number (e.g., 18)
        round_num: Optional round number for round-specific data

    Returns:
        TEG metadata including course, area, date, etc.
    """
    try:
        metadata = get_teg_metadata(teg_num, round_num)
        if not metadata:
            raise HTTPException(status_code=404, detail=f"TEG {teg_num} not found")
        return metadata
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/current")
def get_current():
    """Get current in-progress TEG.

    Returns:
        Current TEG number and rounds played
    """
    try:
        teg_num, rounds = get_current_in_progress_teg_fast()
        return {
            "current_teg": teg_num,
            "rounds_played": rounds,
            "status": "in_progress" if teg_num else "no_active_teg"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/last-completed")
def get_last_completed():
    """Get last completed TEG.

    Returns:
        Last completed TEG number and rounds
    """
    try:
        teg_num, rounds = get_last_completed_teg_fast()
        return {
            "last_completed_teg": teg_num,
            "rounds": rounds,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/courses")
def get_courses():
    """Get list of all courses.

    Returns:
        List of unique course/area combinations
    """
    try:
        courses = load_course_info()
        return courses.to_dict(orient='records')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/player/{initials}")
def get_player(initials: str):
    """Get player name from initials.

    Args:
        initials: Player initials (e.g., 'JB')

    Returns:
        Player full name
    """
    try:
        name = get_player_name(initials.upper())
        return {
            "initials": initials.upper(),
            "name": name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/data")
def get_data(
    teg: Optional[int] = Query(None, description="Filter by TEG number"),
    limit: int = Query(100, description="Limit number of results"),
):
    """Get tournament data.

    Args:
        teg: Optional TEG number to filter by
        limit: Maximum number of records to return

    Returns:
        Tournament data (limited to first N rows)
    """
    try:
        # Load data
        data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)

        # Filter by TEG if specified
        if teg is not None:
            data = filter_data_by_teg(data, teg)

        # Limit results
        data_limited = data.head(limit)

        return {
            "total_rows": len(data),
            "returned_rows": len(data_limited),
            "data": data_limited.to_dict(orient='records')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats/player")
def get_player_stats(
    teg: Optional[int] = Query(None, description="Filter by TEG number"),
):
    """Get player statistics.

    Args:
        teg: Optional TEG number to filter by

    Returns:
        Player-level aggregated statistics
    """
    try:
        # Load data
        data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)

        # Filter by TEG if specified
        if teg is not None:
            data = filter_data_by_teg(data, teg)

        # Aggregate to player level
        player_stats = aggregate_data(
            data,
            aggregation_level='Player',
            measures=['Sc', 'GrossVP', 'NetVP', 'Stableford']
        )

        return {
            "filters": {"teg": teg} if teg else {},
            "stats": player_stats.to_dict(orient='records')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/utils/ordinal/{number}")
def get_ordinal(number: int):
    """Convert number to ordinal (1st, 2nd, 3rd, etc.).

    Args:
        number: Number to convert

    Returns:
        Ordinal representation
    """
    try:
        return {
            "number": number,
            "ordinal": ordinal(number)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/utils/format-vs-par/{value}")
def format_vs_par_endpoint(value: float):
    """Format value vs par.

    Args:
        value: Score vs par (e.g., 3 for +3, -2 for -2, 0 for =)

    Returns:
        Formatted string
    """
    try:
        return {
            "value": value,
            "formatted": format_vs_par(value)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Run Instructions
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("TEG Analysis API - FastAPI Example")
    print("=" * 60)
    print("\nStarting server on http://localhost:8000")
    print("\nEndpoints:")
    print("  http://localhost:8000/docs - Interactive API docs")
    print("  http://localhost:8000/teg/18 - Get TEG 18 metadata")
    print("  http://localhost:8000/current - Current in-progress TEG")
    print("  http://localhost:8000/data?teg=18 - Get TEG 18 data")
    print("\nPress CTRL+C to stop the server")
    print("=" * 60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
