# TEG Golf Data Application Codebase Context

## 1. High-Level Architecture

### Data Flow
1. **Ingestion**: 
   - Google Sheets integration via `1000Data update.py`
   - Streamlit interface for data validation and entry

2. **Processing**:
   - Raw data validation and transformation pipelines
   - Metadata enrichment (handicaps, cumulative scores)
   - DataFrame restructuring for analysis

3. **Storage**:
   - Primary dataset: `data/all-scores.parquet` (optimized for performance)
   - Human-readable mirror: `data/all-scores.csv`
   - Automated backups in `data/backups/` directory

4. **Analysis**:
   - 20+ Streamlit pages for different analytical perspectives
   - Cached data access for responsive UI

## 2. Key Directories

### `data/`
- **Core Datasets**:
  - `all-scores.parquet` - Primary analysis dataset (Parquet format)
  - `handicaps.csv` - Current player handicap calculations
  - `players.csv` - Player metadata and identifiers
  - `round_info.csv` - Contextual data for TEG rounds

- **Supporting Data**:
  - `sc-data-by-r.csv` - Stableford scoring metrics
  - `teg-all-data-long.csv` - Historical data in long format

### `streamlit/`
- **Data Management**:
  - `1000Data update.py` - Main data ingestion and processing pipeline
  - `delete_data.py` - Data version control and rollback

- **Core Analysis Modules**:
  - `101TEG History.py` - Longitudinal performance analysis
  - `102TEG Results.py` - Individual event outcomes
  - `500Handicaps.py` - Handicap tracking and calculations

- **Specialized Views**:
  - `leaderboard.py` - Competitive standings
  - `streaks.py` - Performance trend analysis
  - `birdies_etc.py` - Scoring pattern analysis

## 3. Deployment Architecture

- **GitHub Integration**:
  - Source of truth for code and data files
  - Main branch synchronization between environments

- **Railway Deployment**:
  - Environment variable configuration
  - Automated deployments from GitHub
  - RAILWAY_GIT_BRANCH environment variable for branch awareness

## 4. Key Modules

### `utils.py`
- Centralized constants for file paths and URLs
- Data I/O functions (`read_file`, `write_file`) with automatic format detection
- GitHub API helpers for data synchronization
- Data processing utilities (cumulative scores, metadata merging)

### `1000Data update.py`
- State machine pattern for multi-step data ingestion
- Google Sheets API integration
- Data validation and type enforcement
- Cache invalidation triggers for updated data

## 5. Cross-Cutting Concerns

- **Error Handling**:
  - Robust session state management
  - Type checking before DataFrame operations

- **Performance**:
  - Parquet format for fast I/O operations
  - Streamlit caching decorators (@st.cache_data)
  - Vectorized Pandas operations

- **Data Integrity**:
  - Automated backup system pre-changes
  - Data type consistency checks
  - Diagnostic utilities (`data_diagnostic_newteg.py`)
