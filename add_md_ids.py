import re
import os
import glob
import sys
from collections import OrderedDict

# --- 1. Define Class Mappings and Headings ---

CLASS_MAPPING = OrderedDict([
    # Headings to handle specific text variations/capitalization
    ("## At-a-Glance", "at-a-glance"),
    ("## AT-A-GLANCE", "at-a-glance"),

    # Headings to group under one class for consistency
    ("## Tournament Summary", "recap"),
    ("## Tournament Verdict", "recap"),
    ("## Tournament Recap", "recap"),
    ("## Intro", "recap"),  # Found in one file, group here

    # Universal, single-variant headings
    ("## Player-by-Player Summary", "player-summary"),
    ("## RECORDS AND PERSONAL BESTS", "records-pbs"),
    ("## TOURNAMENT STATISTICS", "stats")
])

# Define the file pattern to search for
FILE_PATTERN = '*_main_report.md'

# --- 2. Core Logic Function ---

def add_classes_to_markdown(filepath, class_map):
    """
    Reads a markdown file, adds stable classes to headings based on class_map,
    and saves the modifications.
    """
    
    print(f"Processing: {filepath}")
    
    # Read the entire file content
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return

    new_content = []
    title_found = False  # Track if we've seen the title
    dateline_added = False  # Track if we've already added dateline class

    # Split content into lines for processing
    for line in content.splitlines():
        modified_line = line

        # 0. Check if this is a title (with or without class tag)
        if line.startswith('# ') and not line.startswith('## '):
            if '{.report-title}' in line:
                title_found = True
                new_content.append(line)
                continue

        # Skip if class is already present (for other headings)
        if re.search(r'(#+)\s+.*\{\..*?\}$', line):
            new_content.append(line)
            continue
        
        # 1. Check for standard, exact/grouped matches
        # Sort by length DESC to match longer, more specific headings first
        for heading_text, class_name in sorted(class_map.items(), key=lambda item: len(item[0]), reverse=True):
            if line.startswith(heading_text):
                # Using line.strip() helps isolate the text for a cleaner match
                if line.strip().startswith(heading_text.strip()):
                    modified_line = f"{heading_text} {{.{class_name}}}"
                    break
        
        # 2. Check for Round Headings (using regex for flexibility)
        # We only check this if no match was found in step 1 AND it looks like a heading
        if modified_line == line and line.startswith('## Round'):
            # Regex captures: (##\s) (Round [1-4]:.*) (and the digit for the class)
            match = re.search(r'^(##\s)(Round\s(\d):.*)$', line.strip())

            if match:
                round_num = match.group(3)
                heading_text = match.group(2)
                class_name = f"round-{round_num}" # e.g., 'round-1'

                # Reconstruct the line: ## + Heading Text + {.class}
                modified_line = f"## {heading_text} {{.{class_name}}}"
        
        # 3. Check for the Primary Title (if no match was found in step 1 or 2)
        if modified_line == line and line.startswith('# '):
            # Ensure it's not another # heading by checking for ##
            if not line.startswith('## '):
                match = re.search(r'^(#\s)(.*)$', line.strip())
                if match:
                    heading_text = match.group(2)
                    class_name = "report-title"  # Fixed class for main title
                    modified_line = f"# {heading_text} {{.{class_name}}}"
                    title_found = True

        # 4. Check for dateline (bold text after title, ignoring blank lines)
        if title_found and not dateline_added:
            # Match **text** pattern (with or without class tag) and convert to HTML
            dateline_match = re.search(r'^\*\*(.*?)\*\*(?:\s*\{\.dateline\})?$', line.strip())
            if dateline_match:
                # Extract just the text content
                dateline_text = dateline_match.group(1)
                modified_line = f'<p class="dateline">{dateline_text}</p>'
                dateline_added = True

        new_content.append(modified_line)

    # Overwrite the original file with the new content
    try:
        # Join with newline, ensuring a clean final line
        final_content = '\n'.join(new_content).strip() + '\n'
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(final_content)

        print(f"-> Successfully added classes to {os.path.basename(filepath)}")
    except Exception as e:
        print(f"Error writing to {filepath}: {e}")

# --- 3. Main Execution Block ---

if __name__ == "__main__":
    
    # Check for command-line argument for folder path
    if len(sys.argv) < 2:
        print("Error: Missing folder path argument.")
        print(f"Usage: python {sys.argv[0]} <folder_path>")
        print(f"Example: python {sys.argv[0]} /streamlit/commentary")
        sys.exit(1)

    folder_path = sys.argv[1]
    
    if not os.path.isdir(folder_path):
        print(f"Error: Directory not found at '{folder_path}'")
        sys.exit(1)

    # Construct the full pattern for glob
    search_pattern = os.path.join(folder_path, FILE_PATTERN)
    md_files = glob.glob(search_pattern) 

    if not md_files:
        print(f"⚠️ No files found matching pattern '{FILE_PATTERN}' in '{folder_path}'.")
    else:
        print(f"Found {len(md_files)} files to process in '{folder_path}'.")
        print("-" * 50)
        
        for filename in md_files:
            add_classes_to_markdown(filename, CLASS_MAPPING)

        print("-" * 50)
        print("✅ All processing complete.")