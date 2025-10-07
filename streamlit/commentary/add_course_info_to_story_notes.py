"""
One-off script to add course information to all existing story_notes.md files
"""

import os
import sys
import pandas as pd
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from course_info import COURSE_INFO


def format_course_info_section(teg_num):
    """
    Format course information section from course_info.py.
    Returns formatted Course Information section with details about each course played.
    """
    # Load course data for this TEG
    rounds_df = pd.read_csv('data/round_info.csv')
    current_teg = rounds_df[rounds_df['TEGNum'] == teg_num]

    if len(current_teg) == 0:
        return ""

    # Get unique courses played in this TEG (maintaining order)
    courses_played = current_teg[['Round', 'Course']].values.tolist()
    unique_courses = []
    seen = set()
    for _, course in courses_played:
        if course not in seen:
            unique_courses.append(course)
            seen.add(course)

    # Build course information section
    section = "\n## Course Information\n\n"

    for course in unique_courses:
        if course in COURSE_INFO:
            info = COURSE_INFO[course]
            section += f"**{course}**\n"
            section += f"- {info['full_name']}\n"
            section += f"- {info['location']}\n"
            section += f"- Type: {info['type']}"
            if info['par']:
                section += f" | Par: {info['par']}"
            section += "\n"
            if info['designer']:
                section += f"- Designer: {info['designer']}\n"
            if info['rankings']:
                section += f"- Rankings: {info['rankings']}\n"
            section += f"- {info['description']}\n"
            section += "\n"
        else:
            # Course not in dictionary - add placeholder
            section += f"**{course}**\n"
            section += f"- Course information not available\n\n"

    return section


def add_course_info_to_file(filepath, teg_num):
    """
    Add course information section to a story_notes file if not already present.
    """
    # Read existing file
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if course information already exists
    if "## Course Information" in content:
        print(f"  [SKIP] TEG {teg_num}: Course Information already exists")
        return False

    # Generate course info section
    course_info = format_course_info_section(teg_num)

    if not course_info:
        print(f"  [SKIP] TEG {teg_num}: No course information available")
        return False

    # Append to file
    updated_content = content + "\n" + course_info

    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(updated_content)

    print(f"  [OK] TEG {teg_num}: Added course information")
    return True


def main():
    """
    Find all story_notes files and add course information to them.
    """
    outputs_dir = Path("streamlit/commentary/outputs")

    if not outputs_dir.exists():
        print(f"Error: Directory not found: {outputs_dir}")
        return

    # Find all story_notes files
    story_notes_files = list(outputs_dir.glob("teg_*_story_notes.md"))

    if not story_notes_files:
        print("No story_notes files found")
        return

    print(f"\nFound {len(story_notes_files)} story_notes files\n")
    print("=" * 60)

    updated_count = 0
    skipped_count = 0

    for filepath in sorted(story_notes_files):
        # Extract TEG number from filename
        filename = filepath.name
        try:
            # Format: teg_17_story_notes.md
            teg_num = int(filename.split('_')[1])
        except (IndexError, ValueError):
            print(f"  [SKIP] {filename} - could not parse TEG number")
            continue

        if add_course_info_to_file(filepath, teg_num):
            updated_count += 1
        else:
            skipped_count += 1

    print("=" * 60)
    print(f"\nSummary:")
    print(f"  Updated: {updated_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Total:   {len(story_notes_files)}\n")


if __name__ == "__main__":
    main()
