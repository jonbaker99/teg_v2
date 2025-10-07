import os
import json
import re

def insert_title_into_report(teg_number, title):
    """
    Inserts the generated title into the main_report.md file for a given TEG.
    Replaces the existing title (line 1) with the new title.
    """
    report_path = f"streamlit/commentary/outputs/teg_{teg_number}_main_report.md"

    # Check if file exists
    if not os.path.exists(report_path):
        print(f"⚠️  Report file not found for TEG {teg_number}")
        return False

    # Read the file
    with open(report_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if not lines:
        print(f"⚠️  Report file is empty for TEG {teg_number}")
        return False

    # Replace the first line (title line) with the new title
    # Keep the ID tag if it exists
    if '{#report-title}' in lines[0]:
        lines[0] = f"# {title} {{#report-title}}\n"
    else:
        lines[0] = f"# {title}\n"

    # Write back to file
    with open(report_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f"Updated TEG {teg_number}")
    return True

def main():
    """
    Read the generated titles and insert them into each main_report.md file.
    """
    titles_file = "streamlit/commentary/outputs/generated_titles.json"

    # Check if titles file exists
    if not os.path.exists(titles_file):
        print(f"❌ Titles file not found at {titles_file}")
        print("Please run generate_titles.py first to generate the titles.")
        return

    # Load titles
    with open(titles_file, 'r', encoding='utf-8') as f:
        titles = json.load(f)

    print("Inserting titles into main_report files...")
    print("-" * 60)

    success_count = 0
    for teg_key, title in titles.items():
        # Extract TEG number from key (e.g., "teg_3" -> 3)
        teg_number = int(teg_key.split('_')[1])
        if insert_title_into_report(teg_number, title):
            success_count += 1

    print("-" * 60)
    print(f"Successfully updated {success_count}/{len(titles)} files")

if __name__ == "__main__":
    main()
