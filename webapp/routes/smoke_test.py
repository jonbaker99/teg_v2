"""Smoke test route — calls all major analysis functions in one pass."""

import time
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from teg_analysis.analysis.aggregation import (
    aggregate_data,
    calculate_final_round_differentials,
    calculate_biggest_comebacks,
)
from teg_analysis.analysis.bestball import (
    prepare_bestball_data,
    calculate_bestball_scores,
    calculate_worstball_scores,
    format_team_scores_for_display,
)
from teg_analysis.analysis.eclectic import calculate_eclectic_by_dimension
from teg_analysis.analysis.history import (
    prepare_complete_history_table_fast,
    get_teg_winners,
    calculate_trophy_jacket_doubles,
    get_eagles_data,
    get_holes_in_one_data,
)
from teg_analysis.analysis.records import identify_aggregate_records_and_pbs
from teg_analysis.analysis.scoring import (
    calculate_par_performance_matrix,
    count_scores_by_player,
)
from teg_analysis.analysis.streaks import (
    build_streaks,
    get_max_streaks,
    get_current_streaks,
    prepare_record_best_streaks_data,
    prepare_record_worst_streaks_data,
    prepare_good_streaks_data,
    prepare_bad_streaks_data,
)
from teg_analysis.constants import ROUND_INFO_CSV, HANDICAPS_CSV
from teg_analysis.core.metadata import get_scorecard_data, get_teg_metadata
from teg_analysis.display.formatters import (
    prepare_records_table,
    prepare_worst_records_table,
    prepare_streak_records_table,
    prepare_score_count_records_table,
)
from teg_analysis.display.tables import score_type_stats, max_scoretype_per_round
from teg_analysis.io.file_operations import read_file
from webapp.deps import (
    cached_load_all_data,
    cached_round_data,
    cached_complete_teg_data,
    cached_9_data,
    cached_ranked_teg_data,
    cached_ranked_round_data,
    cached_ranked_frontback_data,
    create_leaderboard,
    get_filtered_teg_data,
    get_default_teg_num,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _run(label: str, fn: Callable) -> dict:
    start = time.perf_counter()
    try:
        fn()
        return {
            "label": label,
            "status": "pass",
            "time_ms": round((time.perf_counter() - start) * 1000),
            "error": None,
        }
    except Exception as e:
        return {
            "label": label,
            "status": "fail",
            "time_ms": round((time.perf_counter() - start) * 1000),
            "error": str(e),
        }


@router.get("/smoke-test")
async def smoke_test(request: Request):
    teg_num = get_default_teg_num()
    teg_str = f"TEG {teg_num}"

    def _safe(fn):
        try:
            return fn()
        except Exception:
            return None

    # Pre-load shared data so each test lambda gets the real objects
    all_data = _safe(cached_load_all_data)
    round_data = _safe(cached_round_data)
    ranked_teg = _safe(cached_ranked_teg_data)
    ranked_round = _safe(cached_ranked_round_data)
    ranked_fb = _safe(cached_ranked_frontback_data)
    nine_data = _safe(cached_9_data)
    filtered_teg = _safe(get_filtered_teg_data)
    round_info = _safe(lambda: read_file(ROUND_INFO_CSV))

    # Derived inputs reused across multiple tests
    teg_round_data = (
        round_data[round_data["TEGNum"] == teg_num] if round_data is not None else None
    )
    streaks_df = _safe(lambda: build_streaks(all_data)) if all_data is not None else None
    winners_df = _safe(lambda: get_teg_winners(all_data)) if all_data is not None else None
    bb_data = _safe(lambda: prepare_bestball_data(all_data)) if all_data is not None else None
    bestball_scores = (
        _safe(lambda: calculate_bestball_scores(bb_data)) if bb_data is not None else None
    )

    tests: list[tuple[str, str, Callable]] = [
        # Data Loading
        ("Data Loading", "cached_load_all_data()", lambda: cached_load_all_data()),
        ("Data Loading", "cached_round_data()", lambda: cached_round_data()),
        ("Data Loading", "cached_complete_teg_data()", lambda: cached_complete_teg_data()),
        ("Data Loading", "cached_9_data()", lambda: cached_9_data()),
        ("Data Loading", "cached_ranked_teg_data()", lambda: cached_ranked_teg_data()),
        ("Data Loading", "cached_ranked_round_data()", lambda: cached_ranked_round_data()),
        ("Data Loading", "cached_ranked_frontback_data()", lambda: cached_ranked_frontback_data()),
        # Leaderboard
        (
            "Leaderboard",
            f"create_leaderboard(teg_{teg_num}_rounds, 'GrossVP')",
            lambda: create_leaderboard(teg_round_data, "GrossVP", ascending=True),
        ),
        # Records
        ("Records", "prepare_records_table(ranked_teg, 'teg')", lambda: prepare_records_table(ranked_teg, "teg")),
        ("Records", "prepare_worst_records_table(filtered_teg, 'teg')", lambda: prepare_worst_records_table(filtered_teg, "teg")),
        ("Records", "prepare_records_table(ranked_round, 'round')", lambda: prepare_records_table(ranked_round, "round")),
        ("Records", "prepare_worst_records_table(round_data, 'round')", lambda: prepare_worst_records_table(round_data, "round")),
        ("Records", "prepare_records_table(ranked_fb, 'frontback')", lambda: prepare_records_table(ranked_fb, "frontback")),
        ("Records", "prepare_worst_records_table(nine_data, 'frontback')", lambda: prepare_worst_records_table(nine_data, "frontback")),
        ("Records", "prepare_score_count_records_table(all_data)", lambda: prepare_score_count_records_table(all_data)),
        # Streaks
        ("Streaks", "build_streaks(all_data)", lambda: build_streaks(all_data)),
        ("Streaks", "get_max_streaks(streaks_df)", lambda: get_max_streaks(streaks_df)),
        ("Streaks", "get_current_streaks(streaks_df)", lambda: get_current_streaks(streaks_df)),
        ("Streaks", "prepare_record_best_streaks_data(all_data)", lambda: prepare_record_best_streaks_data(all_data)),
        ("Streaks", "prepare_record_worst_streaks_data(all_data)", lambda: prepare_record_worst_streaks_data(all_data)),
        ("Streaks", "prepare_good_streaks_data(all_data)", lambda: prepare_good_streaks_data(all_data)),
        ("Streaks", "prepare_bad_streaks_data(all_data)", lambda: prepare_bad_streaks_data(all_data)),
        # History
        ("History", "get_teg_winners(all_data)", lambda: get_teg_winners(all_data)),
        ("History", "calculate_trophy_jacket_doubles(winners_df)", lambda: calculate_trophy_jacket_doubles(winners_df)),
        ("History", "get_eagles_data(all_data)", lambda: get_eagles_data(all_data)),
        ("History", "get_holes_in_one_data(all_data)", lambda: get_holes_in_one_data(all_data)),
        ("History", "prepare_complete_history_table_fast()", lambda: prepare_complete_history_table_fast()),
        # Scoring
        ("Scoring", "score_type_stats(all_data)", lambda: score_type_stats(all_data)),
        ("Scoring", "calculate_par_performance_matrix(all_data)", lambda: calculate_par_performance_matrix(all_data)),
        ("Scoring", "count_scores_by_player(all_data)", lambda: count_scores_by_player(all_data)),
        ("Scoring", "max_scoretype_per_round(all_data)", lambda: max_scoretype_per_round(all_data)),
        ("Scoring", "aggregate_data(all_data, 'TEG', ['GrossVP'])", lambda: aggregate_data(all_data, "TEG", ["GrossVP"])),
        ("Scoring", "aggregate_data(all_data, 'Round', ['GrossVP'])", lambda: aggregate_data(all_data, "Round", ["GrossVP"])),
        # Eclectic
        ("Eclectic", "calculate_eclectic_by_dimension(all_data, 'Player')", lambda: calculate_eclectic_by_dimension(all_data, "Player")),
        ("Eclectic", "calculate_eclectic_by_dimension(all_data, 'TEGNum')", lambda: calculate_eclectic_by_dimension(all_data, "TEGNum")),
        # Best Ball
        ("Best Ball", "prepare_bestball_data(all_data)", lambda: prepare_bestball_data(all_data)),
        ("Best Ball", "calculate_bestball_scores(bb_data)", lambda: calculate_bestball_scores(bb_data)),
        ("Best Ball", "calculate_worstball_scores(bb_data)", lambda: calculate_worstball_scores(bb_data)),
        ("Best Ball", "format_team_scores_for_display(bestball_scores)", lambda: format_team_scores_for_display(bestball_scores)),
        # Scorecard
        ("Scorecard", f"get_scorecard_data({teg_num}, 1)", lambda: get_scorecard_data(teg_num, 1)),
        ("Scorecard", f"get_teg_metadata({teg_num}, 1)", lambda: get_teg_metadata(teg_num, 1)),
        # Performance
        (
            "Performance",
            f"identify_aggregate_records_and_pbs(ranked_teg, '{teg_str}')",
            lambda: identify_aggregate_records_and_pbs(ranked_teg, teg_str),
        ),
        (
            "Performance",
            f"identify_aggregate_records_and_pbs(ranked_round, '{teg_str}', 1)",
            lambda: identify_aggregate_records_and_pbs(ranked_round, teg_str, 1),
        ),
        # Comebacks
        (
            "Comebacks",
            "calculate_final_round_differentials(..., 'GrossVP')",
            lambda: calculate_final_round_differentials(all_data, round_info, "GrossVP"),
        ),
        (
            "Comebacks",
            "calculate_biggest_comebacks(..., 'GrossVP')",
            lambda: calculate_biggest_comebacks(all_data, round_info, "GrossVP"),
        ),
        # Data files
        ("Data Files", "read_file(HANDICAPS_CSV)", lambda: read_file(HANDICAPS_CSV)),
        ("Data Files", "read_file(ROUND_INFO_CSV)", lambda: read_file(ROUND_INFO_CSV)),
    ]

    results = []
    for category, label, fn in tests:
        r = _run(label, fn)
        r["category"] = category
        results.append(r)

    passed = sum(1 for r in results if r["status"] == "pass")
    failed = len(results) - passed

    return templates.TemplateResponse("smoke_test.html", {
        "request": request,
        "active_page": "smoke_test",
        "results": results,
        "passed": passed,
        "failed": failed,
        "total": len(results),
        "total_ms": sum(r["time_ms"] for r in results),
    })
