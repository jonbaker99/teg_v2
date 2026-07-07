"""Catalog of the project's data files — what each is, how it's updated.

A single, UI-agnostic reference describing the files in ``data/`` (and the
commentary subfolders): their role, format, how they're maintained, and whether
they're editable from the admin pages. Drives the admin **File guide** page and
the info icons on the **GitHub sync** page, and doubles as living documentation.

Ranked by ``importance`` (1 = most critical to the site working). Keep this in
sync with ``teg_analysis/constants.py`` and ``DATA_FLOW.md`` when files change.
"""

# Categories, roughly source -> derived. Used to group the File guide table.
CATEGORY_SOURCE = "Source data"
CATEGORY_PROCESSED = "Processed data"
CATEGORY_METADATA = "Metadata (editable)"
CATEGORY_STATUS = "Status (auto-generated)"
CATEGORY_DERIVED = "Derived cache"
CATEGORY_COMMENTARY = "Commentary"

# Each entry: name (basename, used for lookups), path, category, importance,
# format, role (what it's for), updated_by (how it changes), edit_slug (the
# /admin/edit-data slug if editable inline, else None).
DATA_FILE_CATALOG: list[dict] = [
    {
        "name": "all-scores.parquet",
        "path": "data/all-scores.parquet",
        "category": CATEGORY_SOURCE,
        "importance": 1,
        "format": "parquet",
        "role": "Raw hole-level scores (17 cols) — the source of truth for every "
                "score. Everything else is derived from this.",
        "updated_by": "Add a round (from the Google Sheet) and Delete rounds. Not "
                      "hand-edited.",
        "edit_slug": None,
    },
    {
        "name": "all-data.parquet",
        "path": "data/all-data.parquet",
        "category": CATEGORY_PROCESSED,
        "importance": 2,
        "format": "parquet",
        "role": "Processed hole-level data (53 cols) with cumulative stats and "
                "rankings pre-computed. Powers teg_analysis and the webapp.",
        "updated_by": "Regenerated from all-scores by Add a round / Delete rounds. "
                      "View read-only via Edit data → View Processed Data.",
        "edit_slug": "processed",
    },
    {
        "name": "round_info.csv",
        "path": "data/round_info.csv",
        "category": CATEGORY_METADATA,
        "importance": 3,
        "format": "csv",
        "role": "Course, date and area metadata per TEG + Round. A round's TEG must "
                "exist here before it can be added.",
        "updated_by": "Edit inline on the Edit data page.",
        "edit_slug": "round_info",
    },
    {
        "name": "handicaps.csv",
        "path": "data/handicaps.csv",
        "category": CATEGORY_METADATA,
        "importance": 4,
        "format": "csv",
        "role": "Player handicaps per TEG, used for all net-scoring calculations.",
        "updated_by": "Edit inline on the Edit data page.",
        "edit_slug": "handicaps",
    },
    {
        "name": "teg_winners.csv",
        "path": "data/teg_winners.csv",
        "category": CATEGORY_METADATA,
        "importance": 6,
        "format": "csv",
        "role": "Cached TEG winners for fast history-page loading.",
        "updated_by": "Edit inline on the Edit data page.",
        "edit_slug": "teg_winners",
    },
    {
        "name": "future_tegs.csv",
        "path": "data/future_tegs.csv",
        "category": CATEGORY_METADATA,
        "importance": 7,
        "format": "csv",
        "role": "Planned future tournaments, shown on the history pages.",
        "updated_by": "Edit inline on the Edit data page.",
        "edit_slug": "future_tegs",
    },
    {
        "name": "streaks.parquet",
        "path": "data/streaks.parquet",
        "category": CATEGORY_DERIVED,
        "importance": 8,
        "format": "parquet",
        "role": "Pre-computed streak counters per hole per player.",
        "updated_by": "Regenerated automatically by the add/delete flows.",
        "edit_slug": None,
    },
    {
        "name": "bestball.parquet",
        "path": "data/bestball.parquet",
        "category": CATEGORY_DERIVED,
        "importance": 9,
        "format": "parquet",
        "role": "Best-ball / worst-ball competition data.",
        "updated_by": "Regenerated automatically by the add/delete flows.",
        "edit_slug": None,
    },
    {
        "name": "completed_tegs.csv",
        "path": "data/completed_tegs.csv",
        "category": CATEGORY_STATUS,
        "importance": 10,
        "format": "csv",
        "role": "Status tracking: TEGs with all rounds complete.",
        "updated_by": "Auto-generated. Rebuild via Edit data → Regenerate. Manual "
                      "edits are overwritten on the next update.",
        "edit_slug": "completed_tegs",
    },
    {
        "name": "in_progress_tegs.csv",
        "path": "data/in_progress_tegs.csv",
        "category": CATEGORY_STATUS,
        "importance": 11,
        "format": "csv",
        "role": "Status tracking: TEGs with 1–3 rounds complete (in progress).",
        "updated_by": "Auto-generated. Rebuild via Edit data → Regenerate. Manual "
                      "edits are overwritten on the next update.",
        "edit_slug": "in_progress_tegs",
    },
    {
        "name": "commentary_round_events.parquet",
        "path": "data/commentary_round_events.parquet",
        "category": CATEGORY_COMMENTARY,
        "importance": 12,
        "format": "parquet",
        "role": "Evidence beats per round for the LLM report pipeline.",
        "updated_by": "Regenerated automatically by the add/delete flows.",
        "edit_slug": None,
    },
    {
        "name": "commentary_round_summary.parquet",
        "path": "data/commentary_round_summary.parquet",
        "category": CATEGORY_COMMENTARY,
        "importance": 13,
        "format": "parquet",
        "role": "Per-round summary data for the report pipeline.",
        "updated_by": "Regenerated automatically by the add/delete flows.",
        "edit_slug": None,
    },
    {
        "name": "commentary_tournament_summary.parquet",
        "path": "data/commentary_tournament_summary.parquet",
        "category": CATEGORY_COMMENTARY,
        "importance": 14,
        "format": "parquet",
        "role": "Per-tournament summary data for the report pipeline.",
        "updated_by": "Regenerated automatically by the add/delete flows.",
        "edit_slug": None,
    },
    {
        "name": "commentary_round_streaks.parquet",
        "path": "data/commentary_round_streaks.parquet",
        "category": CATEGORY_COMMENTARY,
        "importance": 15,
        "format": "parquet",
        "role": "Round-level streak data for the report pipeline.",
        "updated_by": "Regenerated automatically by the add/delete flows.",
        "edit_slug": None,
    },
    {
        "name": "commentary_tournament_streaks.parquet",
        "path": "data/commentary_tournament_streaks.parquet",
        "category": CATEGORY_COMMENTARY,
        "importance": 16,
        "format": "parquet",
        "role": "Tournament-level streak data for the report pipeline.",
        "updated_by": "Regenerated automatically by the add/delete flows.",
        "edit_slug": None,
    },
]

# Lookup by basename. Built once at import.
_BY_NAME = {entry["name"]: entry for entry in DATA_FILE_CATALOG}


def get_file_definition(name: str) -> dict | None:
    """Return the catalog entry for a file basename, or None if unknown."""
    return _BY_NAME.get(name)


def catalog_by_importance() -> list[dict]:
    """The catalog sorted most-important first (then by name)."""
    return sorted(DATA_FILE_CATALOG, key=lambda e: (e["importance"], e["name"]))


def file_anchor(name: str) -> str:
    """Stable HTML anchor id for a file (used for deep links from the sync page)."""
    return "file-" + name.replace(".", "-")
