import os
import anthropic
import json

# Get API key with fallback to streamlit secrets
try:
    import streamlit as st
    def get_api_key():
        if hasattr(st, 'secrets') and 'ANTHROPIC_API_KEY' in st.secrets:
            return st.secrets['ANTHROPIC_API_KEY']
        return os.getenv('ANTHROPIC_API_KEY')
except ImportError:
    def get_api_key():
        return os.getenv('ANTHROPIC_API_KEY')

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=get_api_key())

def generate_title_for_teg(teg_number):
    """
    Reads the story_notes file for a given TEG and generates a title using Claude.
    Returns the generated title.
    """
    story_notes_path = f"streamlit/commentary/outputs/teg_{teg_number}_story_notes.md"

    # Check if file exists
    if not os.path.exists(story_notes_path):
        print(f"⚠️  Story notes file not found for TEG {teg_number}")
        return None

    # Read the story notes
    with open(story_notes_path, 'r', encoding='utf-8') as f:
        story_notes = f.read()

    # Create prompt for Claude
    prompt = f"""Based on these tournament story notes, generate a compelling title for this golf tournament report.

The title should:
- Start with "TEG {teg_number}: " followed by the subtitle
- Capture the essence of the tournament's main narrative or most significant event
- The subtitle should be concise and engaging (aim for 5-10 words)
- Follow a journalistic style appropriate for a tournament report
- Focus on the human story, drama, or key achievement

Story notes:
{story_notes}

Please respond with ONLY the title text in the format "TEG {teg_number}: [subtitle]", nothing else."""

    print(f"Generating title for TEG {teg_number}...", end=" ")

    # Call Claude API
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=100,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    title = message.content[0].text.strip()
    print(f"✓")
    return title

def main():
    """
    Generate titles for TEGs 3-17 and save to a JSON file.
    """
    print("Starting title generation for TEGs 3-17...")
    print("-" * 60)

    titles = {}

    for teg_num in range(3, 18):  # 3 to 17 inclusive
        title = generate_title_for_teg(teg_num)
        if title:
            titles[f"teg_{teg_num}"] = title

    # Save titles to JSON file
    output_file = "streamlit/commentary/outputs/generated_titles.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(titles, f, indent=2, ensure_ascii=False)

    print("-" * 60)
    print(f"✅ Titles saved to {output_file}")
    print("\nGenerated titles:")
    for teg_key, title in titles.items():
        print(f"  {teg_key}: {title}")

if __name__ == "__main__":
    main()
