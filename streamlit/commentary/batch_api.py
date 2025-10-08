"""
Anthropic Batch API Wrapper for Bulk Report Generation

This module provides utilities for using the Anthropic Batch API to process
large volumes of report generation requests at 50% cost reduction.

Usage:
    1. Build batch requests using create_batch_request()
    2. Submit batch using submit_batch()
    3. Poll status using check_batch_status()
    4. Retrieve results using get_batch_results()

Note: Batch API is 50% cheaper but takes up to 24 hours. Only use for bulk
regeneration tasks, not for live/real-time report generation.
"""

import json
import time
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("Warning: anthropic package not available.")

# ========================
# Batch Request Building
# ========================

def create_batch_request(
    custom_id: str,
    model: str,
    max_tokens: int,
    system_prompt: str,
    user_message: str,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Create a single batch request in the format required by Anthropic Batch API.

    Args:
        custom_id: Unique identifier for this request (e.g., "TEG17_R1_story_notes")
        model: Model name (e.g., "claude-sonnet-4-5")
        max_tokens: Maximum tokens for response
        system_prompt: System prompt text
        user_message: User message text
        use_cache: Whether to use prompt caching (default True)

    Returns:
        Dict in format required by Batch API
    """
    system_block = {
        "type": "text",
        "text": system_prompt
    }

    if use_cache:
        system_block["cache_control"] = {"type": "ephemeral"}

    return {
        "custom_id": custom_id,
        "params": {
            "model": model,
            "max_tokens": max_tokens,
            "system": [system_block],
            "messages": [{
                "role": "user",
                "content": user_message
            }]
        }
    }


def save_batch_requests(requests: List[Dict[str, Any]], output_path: str) -> None:
    """
    Save batch requests to JSONL file (one JSON object per line).

    Args:
        requests: List of batch request dicts
        output_path: Path to save JSONL file
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        for request in requests:
            f.write(json.dumps(request) + '\n')

    print(f"Saved {len(requests)} batch requests to: {output_path}")


# ========================
# Batch Submission
# ========================

def submit_batch(batch_file_path: str, api_key: str) -> Dict[str, Any]:
    """
    Submit a batch of requests to Anthropic Batch API.

    Args:
        batch_file_path: Path to JSONL file with batch requests
        api_key: Anthropic API key

    Returns:
        Dict with batch information including batch_id
    """
    if not ANTHROPIC_AVAILABLE:
        raise ImportError("anthropic package not available. Install with: pip install anthropic")

    client = anthropic.Anthropic(api_key=api_key)

    # Read batch file content
    with open(batch_file_path, 'r', encoding='utf-8') as f:
        requests_content = f.read()

    print(f"Submitting batch from: {batch_file_path}")

    # Create message batch
    batch = client.messages.batches.create(
        requests=requests_content
    )

    print(f"Batch submitted successfully!")
    print(f"  Batch ID: {batch.id}")
    print(f"  Status: {batch.processing_status}")
    print(f"  Request counts: {batch.request_counts}")

    return {
        "batch_id": batch.id,
        "status": batch.processing_status,
        "request_counts": batch.request_counts,
        "created_at": datetime.now().isoformat()
    }


# ========================
# Batch Status Checking
# ========================

def check_batch_status(batch_id: str, api_key: str) -> Dict[str, Any]:
    """
    Check the status of a batch.

    Args:
        batch_id: Batch ID returned from submit_batch()
        api_key: Anthropic API key

    Returns:
        Dict with batch status information
    """
    if not ANTHROPIC_AVAILABLE:
        raise ImportError("anthropic package not available.")

    client = anthropic.Anthropic(api_key=api_key)
    batch = client.messages.batches.retrieve(batch_id)

    return {
        "batch_id": batch.id,
        "status": batch.processing_status,
        "request_counts": batch.request_counts,
        "ended_at": getattr(batch, 'ended_at', None),
        "expires_at": getattr(batch, 'expires_at', None)
    }


def poll_until_complete(
    batch_id: str,
    api_key: str,
    check_interval: int = 60,
    max_wait: int = 86400
) -> Dict[str, Any]:
    """
    Poll batch status until complete or timeout.

    Args:
        batch_id: Batch ID to monitor
        api_key: Anthropic API key
        check_interval: Seconds between status checks (default 60)
        max_wait: Maximum seconds to wait (default 86400 = 24 hours)

    Returns:
        Final batch status dict
    """
    print(f"Polling batch {batch_id} (checking every {check_interval}s, max {max_wait}s)...")

    start_time = time.time()

    while True:
        status = check_batch_status(batch_id, api_key)
        elapsed = int(time.time() - start_time)

        print(f"  [{elapsed}s] Status: {status['status']} | {status['request_counts']}")

        if status['status'] == 'ended':
            print(f"Batch complete after {elapsed}s!")
            return status

        if elapsed >= max_wait:
            print(f"Timeout after {max_wait}s")
            return status

        time.sleep(check_interval)


# ========================
# Results Retrieval
# ========================

def get_batch_results(batch_id: str, api_key: str, output_dir: str) -> Dict[str, str]:
    """
    Retrieve results from a completed batch and save to files.

    Args:
        batch_id: Batch ID of completed batch
        api_key: Anthropic API key
        output_dir: Directory to save result files

    Returns:
        Dict mapping custom_id to generated text
    """
    if not ANTHROPIC_AVAILABLE:
        raise ImportError("anthropic package not available.")

    client = anthropic.Anthropic(api_key=api_key)

    # Get batch info to access results_url
    batch = client.messages.batches.retrieve(batch_id)

    if batch.processing_status != 'ended':
        raise ValueError(f"Batch not complete yet. Status: {batch.processing_status}")

    print(f"Retrieving results for batch {batch_id}...")

    # Retrieve results
    results_response = client.messages.batches.results(batch_id)

    # Parse results (JSONL format)
    results = {}
    os.makedirs(output_dir, exist_ok=True)

    for line in results_response.text.strip().split('\n'):
        if not line.strip():
            continue

        result = json.loads(line)
        custom_id = result['custom_id']

        # Check for errors
        if result['result']['type'] == 'error':
            error_info = result['result']['error']
            print(f"  ✗ {custom_id}: ERROR - {error_info['type']}: {error_info['message']}")
            results[custom_id] = None
            continue

        # Extract generated text
        message = result['result']['message']
        generated_text = message['content'][0]['text']

        results[custom_id] = generated_text
        print(f"  ✓ {custom_id}: {len(generated_text)} chars")

    # Save results summary
    summary_path = os.path.join(output_dir, f"batch_{batch_id}_summary.json")
    with open(summary_path, 'w', encoding='utf-8') as f:
        summary = {
            "batch_id": batch_id,
            "total_requests": len(results),
            "successful": sum(1 for v in results.values() if v is not None),
            "failed": sum(1 for v in results.values() if v is None),
            "custom_ids": list(results.keys())
        }
        json.dump(summary, f, indent=2)

    print(f"\nResults summary saved to: {summary_path}")
    print(f"  Successful: {summary['successful']}/{len(results)}")
    print(f"  Failed: {summary['failed']}/{len(results)}")

    return results


# ========================
# Convenience Functions
# ========================

def save_batch_info(batch_info: Dict[str, Any], output_dir: str, batch_type: str = "unknown") -> str:
    """
    Save batch information to JSON file for later retrieval.

    Args:
        batch_info: Dict with batch_id and other info
        output_dir: Directory to save info file
        batch_type: Type of batch (e.g., "round_story_notes", "tournament_main_reports")

    Returns:
        Path to saved file
    """
    os.makedirs(output_dir, exist_ok=True)

    batch_id = batch_info['batch_id']
    batch_info['batch_type'] = batch_type  # Add type for easier identification
    output_path = os.path.join(output_dir, f"batch_{batch_id}_info.json")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(batch_info, f, indent=2)

    print(f"Batch info saved to: {output_path}")
    return output_path


def load_batch_info(batch_info_path: str) -> Dict[str, Any]:
    """
    Load batch information from JSON file.

    Args:
        batch_info_path: Path to batch info JSON file

    Returns:
        Dict with batch information
    """
    with open(batch_info_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def find_batch_info_file(batch_id: str, search_dir: str = "streamlit/commentary/batch_results") -> Optional[str]:
    """
    Find batch info file by batch_id.

    Args:
        batch_id: Batch ID to search for
        search_dir: Directory to search in

    Returns:
        Path to batch info file, or None if not found
    """
    expected_path = os.path.join(search_dir, f"batch_{batch_id}_info.json")
    if os.path.exists(expected_path):
        return expected_path
    return None


def list_recent_batches(results_dir: str = "streamlit/commentary/batch_results", limit: int = 10) -> List[Dict[str, Any]]:
    """
    List recent batch submissions.

    Args:
        results_dir: Directory containing batch info files
        limit: Maximum number of batches to return

    Returns:
        List of batch info dicts, sorted by creation time (newest first)
    """
    if not os.path.exists(results_dir):
        return []

    batch_files = []
    for filename in os.listdir(results_dir):
        if filename.startswith("batch_") and filename.endswith("_info.json"):
            filepath = os.path.join(results_dir, filename)
            try:
                info = load_batch_info(filepath)
                info['_filepath'] = filepath
                batch_files.append(info)
            except Exception:
                continue

    # Sort by created_at (newest first)
    batch_files.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    return batch_files[:limit]


# ========================
# Example Usage
# ========================

def example_workflow():
    """
    Example workflow showing how to use batch API.
    """
    print("EXAMPLE: Batch API Workflow")
    print("=" * 60)

    # 1. Build batch requests
    requests = []
    for i in range(1, 5):
        request = create_batch_request(
            custom_id=f"TEG17_R{i}_example",
            model="claude-sonnet-4-5",
            max_tokens=3000,
            system_prompt="You are a golf tournament reporter.",
            user_message=f"Write a summary for Round {i}.",
            use_cache=True
        )
        requests.append(request)

    # 2. Save to JSONL file
    batch_file = "streamlit/commentary/batch_requests/example_batch.jsonl"
    save_batch_requests(requests, batch_file)

    # 3. Submit batch (requires API key)
    # api_key = os.getenv('ANTHROPIC_API_KEY')
    # batch_info = submit_batch(batch_file, api_key)
    # save_batch_info(batch_info, "streamlit/commentary/batch_results")

    # 4. Poll until complete (or check manually later)
    # status = poll_until_complete(batch_info['batch_id'], api_key)

    # 5. Retrieve results
    # results = get_batch_results(batch_info['batch_id'], api_key, "streamlit/commentary/batch_results")

    print("\nExample complete. See comments for actual usage.")


if __name__ == "__main__":
    example_workflow()
