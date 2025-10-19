"""
Analyze dependencies across all active pages in the TEG Streamlit application.
"""

import re
import os
from collections import defaultdict

ACTIVE_PAGES = [
    "contents.py", "101TEG History.py", "101TEG Honours Board.py", "102TEG Results.py",
    "player_history.py", "teg_reports.py", "300TEG Records.py", "301Best_TEGs_and_Rounds.py",
    "302Personal Best Rounds & TEGs.py", "birdies_etc.py", "streaks.py", "ave_by_par.py",
    "ave_by_teg.py", "ave_by_course.py", "score_by_course.py", "score_matrix.py",
    "sc_count.py", "biggest_changes.py", "score_heatmaps.py", "303Final Round Comebacks.py",
    "leaderboard.py", "latest_round.py", "latest_teg_context.py", "500Handicaps.py",
    "scorecard_v2.py", "bestball.py", "eclectic.py", "best_eclectics.py",
    "1000Data update.py", "1001Report Generation.py", "data_edit.py", "delete_data.py",
    "admin_volume_management.py"
]

def extract_imports(file_path):
    utils_imports = []
    helper_imports = defaultdict(list)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract from utils import
        utils_pattern = r'from utils import\s*\(?([^)]+)\)?'
        for match in re.finditer(utils_pattern, content, re.MULTILINE | re.DOTALL):
            imports_str = match.group(1)
            imports = [imp.strip() for imp in imports_str.split(',')]
            utils_imports.extend([imp for imp in imports if imp and not imp.startswith('#')])
        
        # Extract from helpers.X import
        helper_pattern = r'from helpers\.(\w+) import\s*\(?([^)]+)\)?'
        for match in re.finditer(helper_pattern, content, re.MULTILINE | re.DOTALL):
            module_name = match.group(1)
            imports_str = match.group(2)
            imports = [imp.strip() for imp in imports_str.split(',')]
            helper_imports[module_name].extend([imp for imp in imports if imp and not imp.startswith('#')])
    
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return {'utils': utils_imports, 'helpers': dict(helper_imports)}

streamlit_dir = "streamlit"
results = {}

for page in ACTIVE_PAGES:
    page_path = os.path.join(streamlit_dir, page)
    if os.path.exists(page_path):
        results[page] = extract_imports(page_path)

# Count usage
utils_usage = defaultdict(int)
helper_module_usage = defaultdict(int)

for page, imports in results.items():
    for func in imports['utils']:
        utils_usage[func] += 1
    for module in imports['helpers'].keys():
        helper_module_usage[module] += 1

print("=" * 80)
print("UTILS.PY FUNCTIONS USED BY ACTIVE PAGES")
print("=" * 80)
print(f"Total unique utils functions: {len(utils_usage)}\n")

sorted_utils = sorted(utils_usage.items(), key=lambda x: x[1], reverse=True)
for func, count in sorted_utils:
    print(f"{func:50s} : {count:2d} pages")

print("\n" + "=" * 80)
print("HELPER MODULES USED BY ACTIVE PAGES")
print("=" * 80)
print(f"Total helper modules: {len(helper_module_usage)}\n")

sorted_helpers = sorted(helper_module_usage.items(), key=lambda x: x[1], reverse=True)
for module, count in sorted_helpers:
    print(f"helpers.{module:40s} : {count:2d} pages")

print(f"\n\nTotal active pages analyzed: {len(results)}")
print(f"Unique utils functions used: {len(utils_usage)}")
print(f"Helper modules used: {len(helper_module_usage)}")
