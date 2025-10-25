"""I/O Layer - File operations and GitHub integration.

This package provides environment-aware file operations that work seamlessly
across Railway production and local development environments.

Public API exports for I/O operations:
"""

# Import all public functions from submodules
from .volume_operations import (
    _is_railway,
    _get_volume_path,
    _get_local_path,
    _ensure_volume_dir,
    clear_volume_cache,
)

from .file_operations import (
    read_file,
    write_file,
    read_text_file,
    write_text_file,
    backup_file,
    check_for_complete_and_duplicate_data,
)

from .github_operations import (
    read_from_github,
    read_text_from_github,
    write_text_to_github,
    write_to_github,
    batch_commit_to_github,
)

# Define public API
__all__ = [
    # Volume operations
    '_is_railway',
    '_get_volume_path',
    '_get_local_path',
    '_ensure_volume_dir',
    'clear_volume_cache',
    # File operations
    'read_file',
    'write_file',
    'read_text_file',
    'write_text_file',
    'backup_file',
    'check_for_complete_and_duplicate_data',
    # GitHub operations
    'read_from_github',
    'read_text_from_github',
    'write_text_to_github',
    'write_to_github',
    'batch_commit_to_github',
]
