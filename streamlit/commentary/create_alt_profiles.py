"""
Simple script to create alternate player profiles from existing ones.
Extracts key information and formats into 2-3 paragraph profiles.
"""

import re
from pathlib import Path

def extract_player_info(profile_text):
    """Extract player sections from profile"""
    # Split by ## headers (player sections)
    sections = re.split(r'\n## ', profile_text)
    players = []

    for section in sections[1:]:  # Skip first split (header)
        # Extract player name and position
        lines = section.split('\n')
        header = lines[0]

        # Find **Final Position:** line
        pos_line = None
        for line in lines:
            if line.startswith('**Final Position:**'):
                pos_line = line
                break

        if pos_line:
            # Extract name from header (format: "FirstName LASTNAME - 'Nickname'")
            name_match = re.search(r'^([^-]+)', header)
            name = name_match.group(1).strip() if name_match else ""

            # Clean position line
            position = pos_line.replace('**Final Position:**', '').strip()

            # Get the content (skip satirical title and rating lines)
            content_lines = []
            in_review = False
            for line in lines:
                if line.startswith('### The Review'):
                    in_review = True
                    continue
                if in_review and not line.startswith('**Rating:'):
                    content_lines.append(line)

            content = '\n'.join(content_lines).strip()

            players.append({
                'name': name,
                'position': position,
                'content': content
            })

    return players

def simplify_content(content):
    """Simplify content to 2-3 paragraphs, removing excessive commentary"""
    # Remove most satirical elements but keep facts
    # This is a basic version - real version would need LLM

    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

    # Take first 2-3 substantive paragraphs
    keep_paragraphs = []
    for p in paragraphs[:4]:
        # Skip if it's just a rating or award
        if p.startswith('**Rating:') or p.startswith('**Overall Assessment:'):
            continue
        keep_paragraphs.append(p)
        if len(keep_paragraphs) >= 3:
            break

    return '\n\n'.join(keep_paragraphs[:3])

def create_alt_profile(teg_num, original_path):
    """Create alternate profile from original"""

    content = original_path.read_text(encoding='utf-8')

    # Extract TEG number from content if not provided
    if not teg_num:
        match = re.search(r'TEG (\d+)', content)
        teg_num = match.group(1) if match else "?"

    players = extract_player_info(content)

    # Build new file
    output = f"# TEG {teg_num} - Player Profiles\n\n---\n\n"

    for player in players:
        output += f"## {player['name']} - {player['position']}\n\n"
        simplified = simplify_content(player['content'])
        output += f"{simplified}\n\n---\n\n"

    # Add footer
    output += "*🤖 Generated with [Claude Code](https://claude.com/claude-code)*\n\n"
    output += "*Co-Authored-By: Claude <noreply@anthropic.com>*\n"

    return output

def main():
    profiles_dir = Path('data/commentary/drafts')

    # Get all player profile files (excluding already created alts)
    profile_files = sorted([f for f in profiles_dir.glob('teg_*_player_profiles.md')
                           if not f.stem.endswith('_alt')])

    print(f"Found {len(profile_files)} player profile files\n")

    for profile_file in profile_files:
        # Extract TEG number
        teg_num = profile_file.stem.split('_')[1]

        # Check if alt already exists
        alt_file = profiles_dir / f"teg_{teg_num}_player_profiles_alt.md"
        if alt_file.exists():
            print(f"TEG {teg_num}: Alt exists, skipping")
            continue

        print(f"TEG {teg_num}: Creating alt profile...")

        try:
            alt_content = create_alt_profile(teg_num, profile_file)
            alt_file.write_text(alt_content, encoding='utf-8')
            print(f"TEG {teg_num}: OK Created\n")
        except Exception as e:
            print(f"TEG {teg_num}: ERROR - {e}\n")

    print("Done!")

if __name__ == "__main__":
    main()
