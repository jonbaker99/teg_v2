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
PLAYERS_CSV = "data/players.csv"
ROUND_INFO_CSV = "data/round_info.csv"
COURSE_PARS_CSV = "data/course_pars.csv"
ROUND_PARS_CSV = "data/round_pars.csv"
LIVE_ROUNDS_REGISTRY_CSV = "data/live_rounds.csv"
LIVE_ROUND_STAGING_DIR = "data/live_rounds"

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
# LEGACY SEED -- data/players.csv is the source of truth for player identity
# (it's writable from the deployed webapp; this dict isn't). Use
# teg_analysis.core.players.get_player_dict() for lookups, never this dict
# directly. Kept as the fallback seed for environments without the file, and
# for any player here that the file doesn't list.
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

# Verified player relationships. Used by the reporting layer to prevent the
# writer from inventing ties between players (observed: TEG 11 report
# described the Baker brothers as cousins). Only relationships listed here
# are facts; everything else is unknown and must NOT be inferred from
# shared surnames or any other signal.
#
# Format: list of {"players": [name, name], "relationship": str} entries.
# Names are in proper case to match the bundle.
PLAYER_RELATIONSHIPS = [
    {"players": ["Alex Baker", "Jon Baker"], "relationship": "brothers"},
    {"players": ["John Patterson", "Graham Patterson"], "relationship": "brothers"},
]

# ---------------------------------------------------------------------------
# Course data
# ---------------------------------------------------------------------------
# Courses confirmed (not guessed) to sometimes be played with the front/back 9
# swapped, so a per-hole-number Par/SI "conflict" there is real variation, not
# an error -- course_pars.csv still has a default (the most recently played
# round), but pre-round setup should flag these for a human double-check
# rather than trust the default blindly. Confirmed by Jon, 2026-07-07, re:
# Praia D'El Rey specifically (see DATA_STORAGE_INGESTION_PLAN.md).
KNOWN_VARIABLE_ROUTING = {
    "Praia D'El Rey": (
        "Sometimes played back-9-first. The course_pars.csv default is just the "
        "usual routing -- confirm/edit before trusting it for a new round."
    ),
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
