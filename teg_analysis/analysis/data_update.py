"""Headless data-update pipeline.

UI-agnostic port of the Streamlit data-update flow (previously split across
``streamlit/utils.py`` and ``streamlit/helpers/data_update_processing.py``).
Nothing here touches Streamlit, FastAPI, or any session state — every function
takes and returns plain DataFrames / dicts, so the same pipeline can be driven
from a script, a CLI, or a webapp route.

The end-to-end "add a round" flow:

    raw wide-format scores (Google Sheet / CSV)
        -> process_google_sheets_data()        reshape + validate
        -> find_duplicate_keys()               compare vs existing all-scores
        -> (caller decides: overwrite / new-only / abort)
        -> execute_data_update()               process, write, regenerate caches, commit

``execute_data_update`` reuses the existing building blocks in
``teg_analysis.analysis.pipeline`` (``update_all_data``, ``update_streaks_cache``,
``update_commentary_caches``, ``update_bestball_cache``,
``load_and_prepare_handicap_data``) and ``teg_analysis.io`` (``read_file``,
``write_file``, ``batch_commit_to_github``).
"""

import logging

import numpy as np
import pandas as pd

from teg_analysis.constants import (
    PLAYER_DICT,
    ALL_SCORES_PARQUET,
    ALL_DATA_PARQUET,
    ALL_DATA_CSV_MIRROR,
    HANDICAPS_CSV,
    ROUND_INFO_CSV,
)

logger = logging.getLogger(__name__)

# Hole-level identity keys used throughout to compare existing vs new data.
_HOLE_KEYS = ['TEGNum', 'Round', 'Hole', 'Pl']


# ---------------------------------------------------------------------------
# Pure processing functions (no I/O)
# ---------------------------------------------------------------------------

def process_google_sheets_data(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Reshape and validate wide-format round data.

    Converts the wide Google-Sheet layout (one column per player) into long
    format, drops invalid scores (NaN / 0), and keeps only complete 18-hole
    rounds so partial scorecards can never enter the dataset.

    Args:
        raw_df: Raw wide-format data (columns: TEGNum, Round, Hole, Par, SI,
            then one column per player code).

    Returns:
        Long-format DataFrame with columns [TEGNum, Round, Hole, Par, SI, Pl,
        Score], containing only complete 18-hole player-rounds.
    """
    # Deferred import: reshape_round_data lives in the sibling pipeline module.
    from teg_analysis.analysis.pipeline import reshape_round_data

    long_df = reshape_round_data(raw_df, ['TEGNum', 'Round', 'Hole', 'Par', 'SI'])

    # Remove invalid scores (NaN or 0).
    long_df = long_df[long_df['Score'].notna() & (long_df['Score'] != 0)]

    # Keep only complete 18-hole rounds (per TEG/Round/Player).
    rounds_with_18_holes = long_df.groupby(['TEGNum', 'Round', 'Pl']).filter(
        lambda x: len(x) == 18
    )

    return rounds_with_18_holes


def process_round_for_all_scores(long_df: pd.DataFrame, hc_long: pd.DataFrame) -> pd.DataFrame:
    """Calculate scoring metrics for long-format round data.

    Merges handicap data and computes the per-hole metrics that make up the
    ``all-scores`` dataset: HoleID, FrontBack, Player, HCStrokes, GrossVP, Net,
    NetVP and Stableford.

    Args:
        long_df: Long-format round data (columns TEGNum, Round, Hole, Par/PAR,
            SI, Pl, Score/Sc).
        hc_long: Handicap lookup (columns TEG, Pl, HC) — e.g. from
            ``load_and_prepare_handicap_data``.

    Returns:
        Processed DataFrame with the computed scoring columns added.
    """
    logger.info("Processing rounds for all scores.")

    # Work on a copy so callers' frames are never mutated in place.
    long_df = long_df.copy()

    # Normalise column names.
    long_df.rename(columns={'Score': 'Sc', 'Par': 'PAR'}, inplace=True)
    for col in ['Sc', 'PAR']:
        if col not in long_df.columns:
            logger.warning(f"Column '{col}' not found.")

    # Build the TEG label used to join handicaps.
    long_df['TEG'] = 'TEG ' + long_df['TEGNum'].astype(str)

    long_df = long_df.merge(hc_long, on=['TEG', 'Pl'], how='left')
    long_df['HC'] = long_df['HC'].fillna(0)
    logger.debug("Handicap data merged.")

    long_df['HoleID'] = (
        "T" + long_df['TEGNum'].astype(int).astype(str).str.zfill(2) +
        "|R" + long_df['Round'].astype(int).astype(str).str.zfill(2) +
        "|H" + long_df['Hole'].astype(int).astype(str).str.zfill(2)
    )

    long_df['FrontBack'] = np.where(long_df['Hole'] < 10, 'Front', 'Back')

    long_df['Player'] = long_df['Pl'].map(PLAYER_DICT).fillna('Unknown Player')

    # Strokes received per hole = full rounds of handicap + an extra on holes
    # whose stroke index is within the remainder.
    long_df['HCStrokes'] = (long_df['HC'] // 18) + ((long_df['HC'] % 18 >= long_df['SI']).astype(int))

    long_df['GrossVP'] = long_df['Sc'] - long_df['PAR']
    long_df['Net'] = long_df['Sc'] - long_df['HCStrokes']
    long_df['NetVP'] = long_df['Net'] - long_df['PAR']
    long_df['Stableford'] = (2 - long_df['NetVP']).clip(lower=0)

    logger.info("Round processing completed.")
    return long_df


def find_duplicate_keys(existing_df: pd.DataFrame, new_long_df: pd.DataFrame) -> pd.DataFrame:
    """Identify hole-level records present in both existing and new data.

    Args:
        existing_df: The current ``all-scores`` data (may be empty).
        new_long_df: Incoming long-format data (columns include the hole keys).

    Returns:
        DataFrame of duplicate keys (columns [TEGNum, Round, Hole, Pl]); empty
        if there are no overlaps.
    """
    empty_keys = pd.DataFrame(columns=_HOLE_KEYS)

    if existing_df is None or existing_df.empty:
        return empty_keys

    existing = existing_df.copy()
    new_keys = new_long_df[_HOLE_KEYS].drop_duplicates().copy()

    # Coerce the numeric keys on both sides so the merge matches reliably.
    for col in ['TEGNum', 'Round', 'Hole']:
        existing[col] = pd.to_numeric(existing[col])
        new_keys[col] = pd.to_numeric(new_keys[col])

    duplicates = existing.merge(new_keys, on=_HOLE_KEYS, how='inner')
    return duplicates[_HOLE_KEYS].drop_duplicates().reset_index(drop=True)


def analyze_hole_level_differences(
    existing_df: pd.DataFrame,
    new_long_df: pd.DataFrame,
    duplicate_keys: pd.DataFrame,
) -> tuple[pd.DataFrame, bool]:
    """Compare scores for overlapping hole records.

    Args:
        existing_df: Current ``all-scores`` data.
        new_long_df: Incoming long-format data (with a 'Score' column).
        duplicate_keys: Output of :func:`find_duplicate_keys`.

    Returns:
        ``(differences_df, has_differences)``. ``differences_df`` has columns
        [Pl, TEG, Round, Hole, Score (existing), Score (google sheets)] and is
        empty when the overlapping scores all match.
    """
    if duplicate_keys is None or duplicate_keys.empty:
        return pd.DataFrame(), False

    existing_dupes = existing_df.merge(
        duplicate_keys, on=_HOLE_KEYS, how='inner'
    )[_HOLE_KEYS + ['Sc']].rename(columns={'Sc': 'Score_existing'})

    new_dupes = new_long_df.merge(
        duplicate_keys, on=_HOLE_KEYS, how='inner'
    )[_HOLE_KEYS + ['Score']].rename(columns={'Score': 'Score_new'})

    comparison = existing_dupes.merge(new_dupes, on=_HOLE_KEYS, how='inner')
    differences = comparison[comparison['Score_existing'] != comparison['Score_new']].copy()

    if differences.empty:
        return pd.DataFrame(), False

    differences_display = differences[
        ['Pl', 'TEGNum', 'Round', 'Hole', 'Score_existing', 'Score_new']
    ].copy()
    differences_display.columns = [
        'Pl', 'TEG', 'Round', 'Hole', 'Score (existing)', 'Score (google sheets)'
    ]
    differences_display = differences_display.sort_values(['TEG', 'Round', 'Pl', 'Hole'])
    return differences_display, True


def summarise_round_scores(new_long_df: pd.DataFrame) -> pd.DataFrame:
    """Pivot incoming scores to total-per-player-per-round for confirmation.

    Args:
        new_long_df: Long-format data with a 'Score' column.

    Returns:
        Pivot table (index Pl, columns Round/TEGNum) of round totals.
    """
    summary = new_long_df.groupby(['TEGNum', 'Round', 'Pl'])['Score'].sum().reset_index()
    return summary.pivot(index='Pl', columns=['Round', 'TEGNum'], values='Score').fillna('-')


# ---------------------------------------------------------------------------
# TEG status files (completed / in-progress)
# ---------------------------------------------------------------------------

def analyze_teg_completion(all_data: pd.DataFrame) -> pd.DataFrame:
    """Determine completion status and round count per TEG.

    Args:
        all_data: Hole-level data (columns TEGNum, Round, ...).

    Returns:
        DataFrame with columns [TEGNum, TEG, Year, Status, Rounds] where Status
        is 'complete' or 'in_progress'.
    """
    from teg_analysis.core.data_loader import get_incomplete_tegs
    from teg_analysis.io import read_file

    round_info = read_file(ROUND_INFO_CSV)
    incomplete_teg_nums = set(get_incomplete_tegs(all_data))

    rows = []
    for teg_num in all_data['TEGNum'].unique():
        teg_data = all_data[all_data['TEGNum'] == teg_num]
        status = "in_progress" if teg_num in incomplete_teg_nums else "complete"
        teg_info = round_info[round_info['TEGNum'] == teg_num].iloc[0]
        rows.append({
            'TEGNum': teg_num,
            'TEG': teg_info['TEG'],
            'Year': teg_info['Year'],
            'Status': status,
            'Rounds': teg_data['Round'].max(),
        })

    return pd.DataFrame(rows)


def save_teg_status_file(status_data: pd.DataFrame, filename: str, defer_github: bool = False):
    """Write a TEG status CSV (sorted by TEGNum).

    Args:
        status_data: Status rows to write.
        filename: Bare filename, e.g. 'completed_tegs.csv'.
        defer_github: If True, defer the GitHub push for a batch commit.

    Returns:
        File info dict if ``defer_github`` else None.
    """
    from teg_analysis.io import write_file

    sorted_data = status_data.sort_values('TEGNum') if not status_data.empty else status_data
    return write_file(f'data/{filename}', sorted_data, defer_github=defer_github)


def update_teg_status_files(defer_github: bool = False):
    """Regenerate completed_tegs.csv and in_progress_tegs.csv from current data.

    Args:
        defer_github: If True, defer GitHub pushes for a batch commit.

    Returns:
        List of file infos if ``defer_github`` else None.
    """
    from teg_analysis.core.data_loader import load_all_data

    all_data = load_all_data(exclude_incomplete_tegs=False)
    if all_data.empty:
        logger.warning("No data available for TEG status analysis")
        return None

    teg_completion = analyze_teg_completion(all_data)
    completed = teg_completion[teg_completion['Status'] == 'complete']
    in_progress = teg_completion[teg_completion['Status'] == 'in_progress']

    file_infos = []
    for status_df, filename in (
        (completed, 'completed_tegs.csv'),
        (in_progress, 'in_progress_tegs.csv'),
    ):
        file_info = save_teg_status_file(status_df, filename, defer_github=defer_github)
        if file_info:
            file_infos.append(file_info)

    logger.info(
        f"Updated TEG status files: {len(completed)} completed, {len(in_progress)} in progress"
    )
    return file_infos if defer_github else None


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def execute_data_update(
    new_long_df: pd.DataFrame,
    *,
    overwrite: bool = False,
    new_data_only: bool = False,
    defer_github: bool = None,
) -> dict:
    """Apply a processed round update end-to-end.

    Merges ``new_long_df`` into the existing ``all-scores`` data, recomputes the
    derived datasets (all-data, TEG status, streaks, commentary, bestball) and,
    on Railway, commits everything to GitHub in a single batch.

    Duplicate handling (records that already exist at hole level):
      * ``overwrite=True``   — drop the existing matching records, keep the new.
      * ``new_data_only=True`` — drop the matching records from the new data.
      * neither               — append everything (duplicates will co-exist;
        callers should resolve duplicates before calling).

    Args:
        new_long_df: Validated long-format scores (e.g. from
            :func:`process_google_sheets_data`).
        overwrite: Replace existing duplicate records with the new ones.
        new_data_only: Append only records that are not already present.
        defer_github: Override the commit strategy. Defaults to ``True`` on
            Railway (volume write now, single GitHub batch commit at the end)
            and ``False`` locally (direct filesystem writes).

    Returns:
        Summary dict: ``records_added``, ``changed_rounds`` ({teg: [rounds]}),
        ``committed`` (bool), ``files_committed`` (int).
    """
    from teg_analysis.io import read_file, write_file, batch_commit_to_github, _is_railway
    from teg_analysis.analysis.pipeline import (
        load_and_prepare_handicap_data,
        update_all_data,
        update_streaks_cache,
        update_commentary_caches,
        update_bestball_cache,
    )

    if defer_github is None:
        defer_github = bool(_is_railway())

    # Load existing all-scores (treat a missing file as an empty dataset).
    try:
        existing_df = read_file(ALL_SCORES_PARQUET)
    except FileNotFoundError:
        existing_df = pd.DataFrame(columns=_HOLE_KEYS)

    duplicate_keys = find_duplicate_keys(existing_df, new_long_df)

    # Record which rounds changed (useful for downstream commentary regen).
    changed = new_long_df[['TEGNum', 'Round']].drop_duplicates()
    changed_rounds: dict[int, list[int]] = {}
    for _, row in changed.iterrows():
        changed_rounds.setdefault(int(row['TEGNum']), []).append(int(row['Round']))

    if overwrite and not duplicate_keys.empty:
        existing_df = existing_df.merge(
            duplicate_keys, on=_HOLE_KEYS, how='left', indicator=True
        )
        existing_df = existing_df[existing_df['_merge'] == 'left_only'].drop(columns=['_merge'])
    elif new_data_only and not duplicate_keys.empty:
        new_long_df = new_long_df.merge(
            duplicate_keys, on=_HOLE_KEYS, how='left', indicator=True
        )
        new_long_df = new_long_df[new_long_df['_merge'] == 'left_only'].drop(columns=['_merge'])

    hc_long = load_and_prepare_handicap_data(HANDICAPS_CSV)
    processed_rounds = process_round_for_all_scores(new_long_df, hc_long)

    if processed_rounds.empty:
        logger.warning("No new records to append.")
        return {
            'records_added': 0,
            'changed_rounds': changed_rounds,
            'committed': False,
            'files_committed': 0,
        }

    # Align dtypes before concatenating.
    for col in ['TEGNum', 'Round']:
        if not existing_df.empty:
            existing_df[col] = pd.to_numeric(existing_df[col])
        processed_rounds[col] = pd.to_numeric(processed_rounds[col])

    final_df = pd.concat([existing_df, processed_rounds], ignore_index=True)

    batch_files = []

    file_info = write_file(
        ALL_SCORES_PARQUET, final_df,
        f"Updated data with {len(processed_rounds)} new records",
        defer_github=defer_github,
    )
    if file_info:
        batch_files.append(file_info)

    # all-data parquet + CSV mirror.
    update_files = update_all_data(
        ALL_SCORES_PARQUET, ALL_DATA_PARQUET, ALL_DATA_CSV_MIRROR, defer_github=defer_github
    )
    if update_files:
        batch_files.extend(update_files)

    # TEG status, then the derived caches. On Railway each write lands on the
    # volume immediately (GitHub deferred), so these regen steps read the fresh
    # data even before the batch commit.
    status_files = update_teg_status_files(defer_github=defer_github)
    if status_files:
        batch_files.extend(status_files)

    streaks_file = update_streaks_cache(defer_github=defer_github)
    if streaks_file:
        batch_files.append(streaks_file)

    commentary_files = update_commentary_caches(defer_github=defer_github)
    if commentary_files:
        batch_files.extend(commentary_files)

    bestball_file = update_bestball_cache(defer_github=defer_github)
    if bestball_file:
        batch_files.append(bestball_file)

    committed = False
    if defer_github and batch_files:
        batch_commit_to_github(
            batch_files,
            f"Data update: {len(processed_rounds)} new records + cache updates",
        )
        committed = True

    logger.info(
        f"Data update complete: {len(processed_rounds)} records, "
        f"{len(batch_files)} files, committed={committed}"
    )
    return {
        'records_added': len(processed_rounds),
        'changed_rounds': changed_rounds,
        'committed': committed,
        'files_committed': len(batch_files),
    }
