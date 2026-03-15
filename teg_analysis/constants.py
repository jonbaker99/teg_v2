"""Constants and configuration for the TEG Analysis package.

This module centralises all constants (file paths, player data, tournament
metadata) so that teg_analysis is fully standalone — no imports from
streamlit/utils.py are needed at runtime.

If you add a new data file or player, update this module.
"""

# ---------------------------------------------------------------------------
# Data file paths (relative to repo root)
# ---------------------------------------------------------------------------
ALL_DATA_PARQUET = "data/all-data.parquet"
ALL_SCORES_PARQUET = "data/all-scores.parquet"
STREAKS_PARQUET = "data/streaks.parquet"
BESTBALL_PARQUET = "data/bestball.parquet"
HANDICAPS_CSV = "data/handicaps.csv"
ROUND_INFO_CSV = "data/round_info.csv"
ALL_DATA_CSV_MIRROR = "data/all-data.csv"

# Commentary data files
COMMENTARY_ROUND_EVENTS_PARQUET = "data/commentary_round_events.parquet"
COMMENTARY_ROUND_SUMMARY_PARQUET = "data/commentary_round_summary.parquet"
COMMENTARY_TOURNAMENT_SUMMARY_PARQUET = "data/commentary_tournament_summary.parquet"
COMMENTARY_ROUND_STREAKS_PARQUET = "data/commentary_round_streaks.parquet"
COMMENTARY_TOURNAMENT_STREAKS_PARQUET = "data/commentary_tournament_streaks.parquet"

# ---------------------------------------------------------------------------
# Scoring / hole constants
# ---------------------------------------------------------------------------
TOTAL_HOLES = 18

# ---------------------------------------------------------------------------
# Player lookup
# ---------------------------------------------------------------------------
PLAYER_DICT = {
    'AB': 'Alex BAKER',
    'JB': 'Jon BAKER',
    'DM': 'David MULLIN',
    'GW': 'Gregg WILLIAMS',
    'HM': 'Henry MELLER',
    'SN': 'Stuart NEUMANN',
    'JP': 'John PATTERSON',
    'GP': 'Graham PATTERSON',
}

# ---------------------------------------------------------------------------
# Tournament structure
# ---------------------------------------------------------------------------
# TEGs where the number of rounds differs from the default (4).
TEG_ROUNDS = {
    'TEG 1': 1,
    'TEG 2': 3,
}

# Same data keyed by integer TEG number (derived automatically).
TEGNUM_ROUNDS = {
    int(teg.split()[1]): rounds
    for teg, rounds in TEG_ROUNDS.items()
}

# Manual overrides for winner records where the data doesn't tell the
# whole story (e.g. tiebreakers decided off-course).
TEG_OVERRIDES = {
    'TEG 5': {
        'Best Net': 'Gregg WILLIAMS',
        'Best Gross': 'Stuart NEUMANN*',
    },
}
