# Function Dependency Analysis

## Import Analysis - Files and Functions

### Main Page Files (Non-Archive)

#### 1000Data update.py
```python
from utils import (
    # Multi-line import - need to check full import
```

#### 101TEG History.py
```python
from utils import load_all_data, get_teg_winners, get_trophy_full_name, load_datawrapper_css
```
**Functions Used**: 4
- load_all_data (data_retrieval)
- get_teg_winners (statistical_analysis)  
- get_trophy_full_name (helper_utilities)
- load_datawrapper_css (display_formatting)

#### 102TEG Results.py
```python
from utils import get_teg_rounds, get_round_data, load_all_data, load_datawrapper_css
```
**Functions Used**: 4
- get_teg_rounds (helper_utilities)
- get_round_data (data_retrieval)
- load_all_data (data_retrieval)
- load_datawrapper_css (display_formatting)

#### 300TEG Records.py
```python
from utils import get_ranked_teg_data, get_best, get_ranked_round_data, get_ranked_frontback_data, create_stat_section
```
**Functions Used**: 5
- get_ranked_teg_data (data_retrieval)
- get_best (statistical_analysis)
- get_ranked_round_data (data_retrieval)
- get_ranked_frontback_data (data_retrieval)
- create_stat_section (display_formatting)

#### 301Best_TEGs_and_Rounds.py
```python
from utils import get_ranked_teg_data, get_ranked_round_data, load_datawrapper_css
```
**Functions Used**: 3
- get_ranked_teg_data (data_retrieval)
- get_ranked_round_data (data_retrieval)
- load_datawrapper_css (display_formatting)

#### 302Personal Best Rounds & TEGs.py
```python
from utils import get_ranked_teg_data, get_ranked_round_data, load_datawrapper_css
```
**Functions Used**: 3 (identical to 301)
- get_ranked_teg_data (data_retrieval)
- get_ranked_round_data (data_retrieval)
- load_datawrapper_css (display_formatting)

#### 400scoring.py
```python
from utils import score_type_stats, load_all_data, max_scoretype_per_round, load_datawrapper_css
```
**Functions Used**: 4
- score_type_stats (statistical_analysis)
- load_all_data (data_retrieval)
- max_scoretype_per_round (statistical_analysis)
- load_datawrapper_css (display_formatting)

#### 500Handicaps.py
```python
from utils import get_base_directory, load_datawrapper_css, HANDICAPS_CSV
from utils import read_file
```
**Functions Used**: 2 + 1 constant
- get_base_directory (helper_utilities)
- load_datawrapper_css (display_formatting)
- read_file (core_io)
- HANDICAPS_CSV (constant)

#### ave_by_course.py
```python
from utils import get_round_data, load_course_info, load_datawrapper_css, datawrapper_table
```
**Functions Used**: 4
- get_round_data (data_retrieval)
- load_course_info (data_retrieval)
- load_datawrapper_css (display_formatting)
- datawrapper_table (display_formatting)

#### ave_by_par.py
```python
from utils import load_all_data, load_datawrapper_css
```
**Functions Used**: 2
- load_all_data (data_retrieval)
- load_datawrapper_css (display_formatting)

#### ave_by_teg.py
```python
from utils import load_all_data, load_datawrapper_css
```
**Functions Used**: 2 (identical to ave_by_par)
- load_all_data (data_retrieval)
- load_datawrapper_css (display_formatting)

#### bestball.py
```python
from utils import load_all_data, load_datawrapper_css
```
**Functions Used**: 2 (identical to ave_by_par)
- load_all_data (data_retrieval)
- load_datawrapper_css (display_formatting)

#### biggest_changes.py
```python
from utils import get_round_data, load_datawrapper_css, datawrapper_table
```
**Functions Used**: 3
- get_round_data (data_retrieval)
- load_datawrapper_css (display_formatting)
- datawrapper_table (display_formatting)

#### birdies_etc.py
```python
from utils import score_type_stats, max_scoretype_per_round, load_datawrapper_css
```
**Functions Used**: 3
- score_type_stats (statistical_analysis)
- max_scoretype_per_round (statistical_analysis)
- load_datawrapper_css (display_formatting)

#### latest_round.py
```python
from utils import get_ranked_round_data, load_all_data, load_datawrapper_css
```
**Functions Used**: 3
- get_ranked_round_data (data_retrieval)
- load_all_data (data_retrieval)
- load_datawrapper_css (display_formatting)

#### latest_teg_context.py
```python
from utils import get_ranked_teg_data, load_datawrapper_css
```
**Functions Used**: 2
- get_ranked_teg_data (data_retrieval)
- load_datawrapper_css (display_formatting)

#### leaderboard.py
```python
from utils import get_teg_rounds, get_round_data, load_all_data, load_datawrapper_css
```
**Functions Used**: 4 (identical to 102TEG Results)
- get_teg_rounds (helper_utilities)
- get_round_data (data_retrieval)
- load_all_data (data_retrieval)
- load_datawrapper_css (display_formatting)

#### sc_count.py
```python
from utils import load_all_data, load_datawrapper_css, datawrapper_table
```
**Functions Used**: 3
- load_all_data (data_retrieval)
- load_datawrapper_css (display_formatting)
- datawrapper_table (display_formatting)

#### score_by_course.py
```python
from utils import load_all_data, get_best, get_ranked_teg_data, get_ranked_round_data, load_datawrapper_css, get_round_data
```
**Functions Used**: 6
- load_all_data (data_retrieval)
- get_best (statistical_analysis)
- get_ranked_teg_data (data_retrieval)
- get_ranked_round_data (data_retrieval)
- load_datawrapper_css (display_formatting)
- get_round_data (data_retrieval)

#### scorecard_v2.py
```python
from utils import load_all_data, get_scorecard_data, get_teg_metadata, format_date_for_scorecard
```
**Functions Used**: 4
- load_all_data (data_retrieval)
- get_scorecard_data (data_retrieval)
- get_teg_metadata (data_retrieval)
- format_date_for_scorecard (display_formatting)

#### scorecard_v2_mobile.py
```python
from utils import load_all_data, get_scorecard_data, get_teg_metadata, format_date_for_scorecard
```
**Functions Used**: 4 (identical to scorecard_v2)
- load_all_data (data_retrieval)
- get_scorecard_data (data_retrieval)
- get_teg_metadata (data_retrieval)
- format_date_for_scorecard (display_formatting)

#### scorecard_utils.py
```python
from utils import get_scorecard_data, get_teg_metadata, format_date_for_scorecard
```
**Functions Used**: 3
- get_scorecard_data (data_retrieval)
- get_teg_metadata (data_retrieval)
- format_date_for_scorecard (display_formatting)

#### streaks.py
```python
from utils import load_all_data, load_datawrapper_css
```
**Functions Used**: 2 (identical to ave_by_par)
- load_all_data (data_retrieval)
- load_datawrapper_css (display_formatting)

#### teg_worsts.py
```python
from utils import get_round_data, get_9_data, get_worst
```
**Functions Used**: 3
- get_round_data (data_retrieval)
- get_9_data (data_retrieval)
- get_worst (statistical_analysis)

#### utils_win_tables.py
```python
from utils import convert_trophy_name, TROPHY_NAME_LOOKUPS_LONGSHORT, TROPHY_NAME_LOOKUPS_SHORTLONG
```
**Functions Used**: 1 + 2 constants
- convert_trophy_name (helper_utilities)
- TROPHY_NAME_LOOKUPS_LONGSHORT (constant)
- TROPHY_NAME_LOOKUPS_SHORTLONG (constant)

### Helper Files

#### helpers/data_deletion_processing.py
```python
from utils import read_file, write_file, backup_file, clear_all_caches
# Plus constants: ALL_SCORES_PARQUET, ALL_DATA_PARQUET, ALL_DATA_CSV_MIRROR
```
**Functions Used**: 4 + 3 constants
- read_file (core_io)
- write_file (core_io)
- backup_file (core_io)
- clear_all_caches (streamlit_functionality)

#### helpers/data_update_processing.py
```python
from utils import (
    # Multi-line import - need to check full content
```

### Most Frequently Used Functions

1. **load_datawrapper_css** (display_formatting) - Used in 20+ files
2. **load_all_data** (data_retrieval) - Used in 15+ files  
3. **get_round_data** (data_retrieval) - Used in 8+ files
4. **get_ranked_teg_data** (data_retrieval) - Used in 6+ files
5. **get_ranked_round_data** (data_retrieval) - Used in 6+ files

### Common Function Groupings

**Pattern 1: Basic Analysis Display**
- load_all_data + load_datawrapper_css (8 files)

**Pattern 2: TEG/Round Rankings**  
- get_ranked_teg_data + get_ranked_round_data + load_datawrapper_css (3 files)

**Pattern 3: Scorecard Generation**
- load_all_data + get_scorecard_data + get_teg_metadata + format_date_for_scorecard (3 files)

**Pattern 4: Data Table Display**
- get_round_data + load_datawrapper_css + datawrapper_table (2 files)

### Functions Never Imported Individually (Only Used Internally)
- TBD - need to compare with full function list