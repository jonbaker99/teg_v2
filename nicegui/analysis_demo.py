#!/usr/bin/env python3
import pandas as pd
from nicegui import ui
import sys
import os
import logging # Added logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Add project root to sys.path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    logger.info(f"Adding project root to sys.path: {project_root}")
    sys.path.insert(0, project_root)

# --- Data Loading ---
all_data_df = None # Initialize df variable
DATA_LOADED = False
try:
    logger.info("Attempting to import teg_analysis modules...")
    # Simplified import: Only use load_all_data from core.data_loader
    from teg_analysis.core.data_loader import load_all_data
    from teg_analysis.analysis import (
        aggregation,
        rankings,
        records,
        streaks,
    )
    logger.info("Modules imported successfully.")

    # Load data once using the confirmed function
    logger.info("Attempting to load data using load_all_data()...")
    # load_all_data seems to use constants defined within streamlit.utils to find the path
    # Ensure those constants point correctly or that load_all_data can find the file
    all_data_df = load_all_data() # Assuming it finds data path internally

    if all_data_df is None or all_data_df.empty:
         raise ValueError("load_all_data() returned an empty or None DataFrame.")

    logger.info(f"Data loaded successfully. Shape: {all_data_df.shape}")

    # For functions that might need aggregated scores (like rankings, records):
    # Perform a basic aggregation here if needed.
    # This assumes 'Sc', 'Player', 'TEGNum', 'Round' columns exist after load_all_data()
    # Adjust aggregation keys as necessary based on all_data_df columns
    logger.info("Aggregating scores per round for analysis functions...")
    required_cols = ['Player', 'TEGNum', 'Round', 'Sc', 'PAR', 'HC', 'Net', 'Stableford', 'GrossVP']
    if not all(col in all_data_df.columns for col in required_cols):
        logger.warning(f"One or more required columns missing for aggregation: {required_cols}. Attempting aggregation anyway.")
        # Attempt basic aggregation even if some columns are missing, functions might handle it
        agg_cols_present = [col for col in ['Sc', 'Net', 'Stableford', 'GrossVP'] if col in all_data_df.columns]
        if not agg_cols_present:
             raise ValueError("No score columns (Sc, Net, Stableford, GrossVP) found in all_data_df for aggregation.")
        all_scores_agg_df = all_data_df.groupby(['Player', 'TEGNum', 'TEG', 'Round'])[agg_cols_present].sum().reset_index()
    else:
        all_scores_agg_df = all_data_df.groupby(['Player', 'TEGNum', 'TEG', 'Round'])[required_cols].sum().reset_index() # Summing HC might not be right, adjust if needed
        # Recalculate 'GrossVP' if PAR was summed incorrectly, or use first() for PAR/HC if appropriate
        par_per_round = all_data_df.groupby(['Player', 'TEGNum', 'TEG', 'Round'])['PAR'].sum().reset_index()
        all_scores_agg_df = pd.merge(all_scores_agg_df.drop(columns=['PAR', 'GrossVP'], errors='ignore'), par_per_round, on=['Player', 'TEGNum', 'TEG', 'Round'])
        all_scores_agg_df['GrossVP'] = all_scores_agg_df['Sc'] - all_scores_agg_df['PAR']

    logger.info(f"Aggregated scores DataFrame created. Shape: {all_scores_agg_df.shape}")

    # Use all_data_df directly for streaks and the aggregated df for others
    processed_scores_df = all_scores_agg_df # Use aggregated for functions needing round scores
    hole_data_df = all_data_df # Use original hole data for functions like streaks

    DATA_LOADED = True

except ImportError as e:
    logger.error(f"Error importing teg_analysis modules: {e}", exc_info=True)
    logger.error(f"Project root added to path: {project_root}")
    logger.error("Please ensure the teg_analysis package exists in the project root "
          "and required dependencies are installed.")
    DATA_LOADED = False
except FileNotFoundError as e:
    logger.error(f"Error loading data files: {e}", exc_info=True)
    # Cannot reliably determine DATA_PATH here as load_all_data uses internal constants
    logger.error("Check that the data files (e.g., all-data.parquet) exist in the expected location.")
    DATA_LOADED = False
except ValueError as e:
    logger.error(f"Data loading or processing error: {e}", exc_info=True)
    DATA_LOADED = False
except Exception as e:
    logger.error(f"An unexpected error occurred during data loading or import: {e}", exc_info=True)
    DATA_LOADED = False

# --- UI Definition ---

@ui.page('/')
def main_page():
    ui.label('TEG Analysis Module Demonstration').classes('text-h4 q-mb-md')

    if not DATA_LOADED or all_data_df is None:
        ui.label('Failed to load data or analysis modules. Cannot display results. Check console output for details.').classes('text-negative')
        return

    # --- Aggregation Example ---
    with ui.card().tight():
        ui.label('aggregation.aggregate_scores_by_player').classes('text-h6 q-pa-md')
        ui.separator()
        try:
            # Assuming aggregate_scores_by_player works on the *aggregated* round scores
            player_agg_df = aggregation.aggregate_scores_by_player(processed_scores_df)
            ui.table.from_pandas(player_agg_df.head(10)).classes('q-pa-md')
        except Exception as e:
            logger.error(f"Error in aggregation.aggregate_scores_by_player: {e}", exc_info=True)
            ui.label(f"Error running aggregation.aggregate_scores_by_player: {e}").classes('text-negative q-pa-md')

    # --- Rankings Example ---
    with ui.card().tight():
        ui.label('rankings.get_historical_rankings').classes('text-h6 q-pa-md')
        ui.separator()
        try:
            # Assuming get_historical_rankings needs aggregated scores
            rankings_df = rankings.get_historical_rankings(processed_scores_df)
            if not rankings_df.empty and 'TEG' in rankings_df.columns:
                latest_teg = rankings_df['TEG'].max()
                ui.table.from_pandas(rankings_df[rankings_df['TEG'] == latest_teg].head(10)).classes('q-pa-md')
            elif not rankings_df.empty:
                 ui.table.from_pandas(rankings_df.head(10)).classes('q-pa-md') # Fallback if 'TEG' column missing
            else:
                 ui.label("No ranking data returned.").classes('q-pa-md')
        except Exception as e:
             logger.error(f"Error in rankings.get_historical_rankings: {e}", exc_info=True)
             ui.label(f"Error running rankings.get_historical_rankings: {e}").classes('text-negative q-pa-md')

    # --- Records Example ---
    with ui.card().tight():
        ui.label('records.find_best_gross_rounds').classes('text-h6 q-pa-md')
        ui.separator()
        try:
             # Assuming find_best_gross_rounds needs aggregated scores
            best_gross_df = records.find_best_gross_rounds(processed_scores_df, n=10)
            ui.table.from_pandas(best_gross_df).classes('q-pa-md')
        except Exception as e:
             logger.error(f"Error in records.find_best_gross_rounds: {e}", exc_info=True)
             ui.label(f"Error running records.find_best_gross_rounds: {e}").classes('text-negative q-pa-md')

    # --- Streaks Example ---
    with ui.card().tight():
        ui.label('streaks.find_longest_birdie_streak (Overall)').classes('text-h6 q-pa-md')
        ui.separator()
        try:
            # Pass the original hole_data_df here
            longest_streak_df = streaks.find_longest_birdie_streak(hole_data_df, group_by_player=False, n=5)
            ui.table.from_pandas(longest_streak_df).classes('q-pa-md')
        except KeyError as e:
            logger.error(f"KeyError in streaks.find_longest_birdie_streak: {e}", exc_info=True)
            ui.label(f"Error running streaks.find_longest_birdie_streak: Missing expected column - {e}. "
                     "Ensure 'all_data_df' has hole-by-hole score names.").classes('text-negative q-pa-md')
        except Exception as e:
            logger.error(f"Error in streaks.find_longest_birdie_streak: {e}", exc_info=True)
            ui.label(f"Error running streaks.find_longest_birdie_streak: {e}").classes('text-negative q-pa-md')


# --- Run the App ---
if DATA_LOADED:
    logger.info("Starting NiceGUI app...")
    ui.run(reload=False) # Set reload=False for stability
else:
    logger.error("NiceGUI app cannot start due to previous errors during data loading or import.")
    print("\nNiceGUI app cannot start due to previous errors. Check log output above.")

