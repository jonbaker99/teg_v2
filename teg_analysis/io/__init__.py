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

from .sync import (
    SYNC_FOLDERS,
    is_railway,
    store_label,
    build_sync_status,
    build_sync_preview,
    file_diff,
    pull_files,
    push_files,
    sync_report_files,
    detect_pull_conflicts,
    detect_push_conflicts,
    list_sync_backups,
    backups_for,
    restore_backup,
    list_store_dir,
    read_store_file,
    delete_store_file,
)

from .file_catalog import (
    DATA_FILE_CATALOG,
    get_file_definition,
    catalog_by_importance,
    file_anchor,
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
    # GitHub <-> store sync
    'SYNC_FOLDERS',
    'is_railway',
    'store_label',
    'build_sync_status',
    'build_sync_preview',
    'file_diff',
    'pull_files',
    'push_files',
    'sync_report_files',
    'detect_pull_conflicts',
    'detect_push_conflicts',
    'list_sync_backups',
    'backups_for',
    'restore_backup',
    'list_store_dir',
    'read_store_file',
    'delete_store_file',
    # Data file catalog
    'DATA_FILE_CATALOG',
    'get_file_definition',
    'catalog_by_importance',
    'file_anchor',
]
