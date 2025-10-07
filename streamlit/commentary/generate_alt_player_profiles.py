"""
Generate alternate (simplified) player profile versions for all TEGs.
Removes jokey rankings, simplifies eagle mentions, creates 2-3 paragraph profiles.
"""

import anthropic
import os
from pathlib import Path

# Initialize Claude client
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def generate_alt_profile(teg_num: int, original_content: str) -> str:
    """Generate alternate simplified player profile for a TEG"""

    prompt = f"""You are creating a simplified alternate version of player profiles for TEG {teg_num}.

ORIGINAL PLAYER PROFILES:
{original_content}

REQUIREMENTS FOR ALTERNATE VERSION:
1. Create 2-3 paragraphs per player covering the same performance categories
2. Remove all jokey "rankings" and satirical award sections
3. Keep factual performance data (scores, positions, key moments, streaks, etc.)
4. Player title format: "PLAYER NAME - Position Stableford (points) | Position Gross (strokes)"
5. For eagles: Simply mention them factually without excessive fanfare (e.g., "Patterson holed his second shot on Hole 2 for eagle")
6. Maintain professional but engaging tone
7. Include all players from the original
8. End with standard attribution footer

OUTPUT FORMAT:
# TEG {teg_num} - Player Profiles

---

## PLAYER NAME - Position details

[2-3 paragraphs about player]

---

[Repeat for all players]

*🤖 Generated with [Claude Code](https://claude.com/claude-code)*

*Co-Authored-By: Claude <noreply@anthropic.com>*

Generate the alternate simplified player profiles now."""

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4000,
        messages=[{
            "role": "user",
            "content": prompt
        }]
    )

    return message.content[0].text

def main():
    profiles_dir = Path('data/commentary/drafts')

    # Get all player profile files
    profile_files = sorted([f for f in profiles_dir.glob('teg_*_player_profiles.md')])

    print(f"Found {len(profile_files)} player profile files to convert\n")

    for profile_file in profile_files:
        # Extract TEG number from filename
        teg_num = profile_file.stem.split('_')[1]

        # Skip if alternate already exists
        alt_file = profiles_dir / f"teg_{teg_num}_player_profiles_alt.md"
        if alt_file.exists():
            print(f"TEG {teg_num}: Alternate already exists, skipping")
            continue

        print(f"TEG {teg_num}: Generating alternate player profiles...")

        # Read original
        original_content = profile_file.read_text(encoding='utf-8')

        # Generate alternate
        alt_content = generate_alt_profile(int(teg_num), original_content)

        # Write alternate
        alt_file.write_text(alt_content, encoding='utf-8')

        print(f"TEG {teg_num}: ✓ Created {alt_file.name}\n")

    print("All alternate player profiles generated!")

if __name__ == "__main__":
    main()
