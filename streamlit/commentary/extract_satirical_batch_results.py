"""
Extract satirical reports from batch results JSONL file and save to markdown files.

This is a one-time script to extract the satirical reports from a batch results file
and save them to the appropriate commentary draft files.
"""

import json
import os
import sys

def extract_satirical_reports(jsonl_path: str, output_base_dir: str = "data/commentary/drafts"):
    """
    Extract satirical reports from JSONL batch results and save to files.

    Args:
        jsonl_path: Path to the JSONL results file
        output_base_dir: Base directory for output files
    """
    print("\n" + "="*60)
    print("EXTRACTING SATIRICAL REPORTS FROM BATCH RESULTS")
    print("="*60)
    print(f"Input file: {jsonl_path}")
    print(f"Output directory: {output_base_dir}")
    print()

    # Ensure output directory exists
    os.makedirs(output_base_dir, exist_ok=True)

    # Track results
    successful = 0
    failed = 0

    # Process each line in JSONL file
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                # Parse JSON
                result = json.loads(line)
                custom_id = result['custom_id']

                # Check if result succeeded
                if result['result']['type'] == 'error':
                    error_info = result['result']['error']
                    print(f"  [ERROR] {custom_id}: ERROR - {error_info['type']}: {error_info.get('message', 'Unknown error')}")
                    failed += 1
                    continue

                # Extract TEG number from custom_id (format: "TEG10_satire")
                if not custom_id.startswith('TEG') or not custom_id.endswith('_satire'):
                    print(f"  [WARNING] {custom_id}: Unexpected format, skipping")
                    failed += 1
                    continue

                teg_num = custom_id.replace('TEG', '').replace('_satire', '')

                # Extract generated text
                generated_text = result['result']['message']['content'][0]['text']

                # Save to file
                output_path = os.path.join(output_base_dir, f"teg_{teg_num}_satire.md")
                with open(output_path, 'w', encoding='utf-8') as out_f:
                    out_f.write(generated_text)

                print(f"  [OK] TEG {teg_num}: Saved to {output_path} ({len(generated_text):,} chars)")
                successful += 1

            except Exception as e:
                print(f"  [ERROR] Line {line_num}: Error processing - {e}")
                failed += 1
                continue

    # Summary
    print()
    print("="*60)
    print("EXTRACTION COMPLETE")
    print("="*60)
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total: {successful + failed}")
    print("="*60)
    print()


if __name__ == "__main__":
    # Default path to the JSONL file
    default_jsonl = "streamlit/commentary/batch_results/msgbatch_01ReiR66TxvnvJFBiasZWKDE_results.jsonl"

    # Allow command-line override
    jsonl_path = sys.argv[1] if len(sys.argv) > 1 else default_jsonl

    if not os.path.exists(jsonl_path):
        print(f"Error: File not found: {jsonl_path}")
        sys.exit(1)

    extract_satirical_reports(jsonl_path)
