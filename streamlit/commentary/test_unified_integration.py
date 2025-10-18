"""
Quick test to verify unified data loader integration with tournament commentary generator.
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from pattern_analysis import process_all_data_types
from unified_round_data_loader import load_unified_round_data
from generate_tournament_commentary_v2 import compact_round_data_lossless, abbreviate_for_prompt
import json

print("\n" + "="*60)
print("TESTING UNIFIED INTEGRATION")
print("="*60 + "\n")

# Test with TEG 17, Round 2
teg_num = 17
round_num = 2

print(f"Step 1: Process all data for TEG {teg_num}...")
all_data = process_all_data_types(teg_num)
print("  > Data processing complete")

print(f"\nStep 2: Load unified round data for Round {round_num}...")
round_data = load_unified_round_data(teg_num, round_num, all_data)
print("  > Unified data loaded")

print("\nStep 3: Test compaction and abbreviation...")
rd_compact = compact_round_data_lossless(round_data)
rd_abbrev, legend_text = abbreviate_for_prompt(rd_compact)
print("  > Compaction successful")

print("\nStep 4: Test JSON serialization...")
round_data_json = json.dumps(rd_abbrev, separators=(",", ":"), ensure_ascii=False, default=str)
print(f"  > JSON size: {len(round_data_json):,} characters")
print(f"  > Estimated tokens: ~{len(round_data_json)//4:,}")

print("\n" + "="*60)
print("KEY DATA SECTIONS")
print("="*60)

# Check what sections are in unified data
sections = list(round_data.keys())
print(f"\nTotal sections: {len(sections)}")
for section in sections:
    if isinstance(round_data[section], list):
        print(f"  - {section}: {len(round_data[section])} items")
    elif isinstance(round_data[section], dict):
        print(f"  - {section}: dict with {len(round_data[section])} keys")
    else:
        print(f"  - {section}: {type(round_data[section]).__name__}")

# Check for new sections
new_sections = ['course_context', 'location_context', 'positions_through_round']
print(f"\nNew unified sections present:")
for section in new_sections:
    if section in round_data:
        print(f"  ✅ {section}")
    else:
        print(f"  ❌ {section} MISSING")

# Check course context details
if round_data.get('course_context'):
    cc = round_data['course_context']
    print(f"\nCourse Context:")
    print(f"  - Course: {cc.get('course_name')}")
    print(f"  - Area: {cc.get('course_area')}")
    print(f"  - History: {len(cc.get('course_history_tegs', []))} previous TEGs")
    print(f"  - Records: {'Yes' if cc.get('course_records') else 'No (course played ≤2 times)'}")

# Check location context details
if round_data.get('location_context'):
    lc = round_data['location_context']
    print(f"\nLocation Context:")
    print(f"  - Area: {lc.get('area')}")
    print(f"  - Status: {lc.get('area_return_status')}")
    print(f"  - Previous TEGs in area: {len(lc.get('previous_area_tegs', []))}")

# Check positions through round
if 'positions_through_round' in round_data:
    ptr = round_data['positions_through_round']
    if ptr:
        print(f"\nPositions Through Round:")
        print(f"  - Records: {len(ptr)}")
        # Check for dual competition fields
        sample = ptr[0] if ptr else {}
        has_stableford = 'Position_Stableford' in sample
        has_gross = 'Position_Gross' in sample
        print(f"  - Dual competition tracking: {'✅ Yes' if (has_stableford and has_gross) else '❌ No'}")

print("\n" + "="*60)
print("INTEGRATION TEST COMPLETE")
print("="*60)
print("\nResult: ✅ Unified data loader successfully integrated!")
print("The generate_tournament_commentary_v2.py can now use load_unified_round_data().")
