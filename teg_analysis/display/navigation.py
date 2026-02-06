"""Navigation and trophy name utilities.

This module provides utility functions for trophy name conversions and
basic URL formatting. Note that full Streamlit navigation functions remain
in streamlit/utils.py as they are UI-specific.
"""

from typing import Dict

# Trophy name lookups
TROPHY_NAME_LOOKUPS_SHORTLONG: Dict[str, str] = {
    "trophy": "TEG Trophy",
    "jacket": "Green Jacket",
    "spoon": "HMM Wooden Spoon",
}

# Reverse lookup (keys normalized to lowercase)
TROPHY_NAME_LOOKUPS_LONGSHORT: Dict[str, str] = {
    v.lower(): k for k, v in TROPHY_NAME_LOOKUPS_SHORTLONG.items()
}


def convert_trophy_name(name: str) -> str:
    """Convert between short and long trophy names.

    Input is case-insensitive.
    Output always uses the canonical form from TROPHY_NAME_LOOKUPS.

    Args:
        name: Trophy name (short or long form)

    Returns:
        str: Converted trophy name

    Raises:
        ValueError: If trophy name is unknown

    Examples:
        >>> convert_trophy_name("trophy")
        'TEG Trophy'
        >>> convert_trophy_name("TEG Trophy")
        'trophy'
        >>> convert_trophy_name("jacket")
        'Green Jacket'
        >>> convert_trophy_name("green jacket")
        'jacket'
    """
    key = name.strip().lower()

    # short -> long
    if key in TROPHY_NAME_LOOKUPS_SHORTLONG:
        return TROPHY_NAME_LOOKUPS_SHORTLONG[key]

    # long -> short
    if key in TROPHY_NAME_LOOKUPS_LONGSHORT:
        return TROPHY_NAME_LOOKUPS_LONGSHORT[key]

    raise ValueError(f"Unknown trophy name: {name!r}")


def get_trophy_full_name(trophy: str) -> str:
    """Get the full name of a trophy given its short name.

    This function is more lenient than convert_trophy_name() - it accepts
    either short or long names and always returns the long name.

    Args:
        trophy: The trophy name (short or long)

    Returns:
        str: The full name of the trophy

    Examples:
        >>> get_trophy_full_name("trophy")
        'TEG Trophy'
        >>> get_trophy_full_name("TEG Trophy")
        'TEG Trophy'
        >>> get_trophy_full_name("jacket")
        'Green Jacket'
    """
    key = trophy.strip()

    if key.lower() in TROPHY_NAME_LOOKUPS_LONGSHORT:
        # It's already a long name → use as-is
        trophy_name = key
    else:
        # Otherwise assume it's a short name → convert
        trophy_name = convert_trophy_name(key)

    return trophy_name


def convert_filename_to_streamlit_url(page_file: str) -> str:
    """Convert a page filename to Streamlit's URL format.

    Streamlit strips leading numbers from filenames when creating URLs.

    Args:
        page_file: Page filename (e.g., "101TEG History.py")

    Returns:
        str: URL-formatted page name (e.g., "TEG_History")

    Examples:
        >>> convert_filename_to_streamlit_url("300TEG Records.py")
        'TEG_Records'
        >>> convert_filename_to_streamlit_url("500Handicaps.py")
        'Handicaps'
        >>> convert_filename_to_streamlit_url("leaderboard.py")
        'leaderboard'
    """
    import re

    # Remove .py extension
    page_name = page_file.replace('.py', '')
    # Replace spaces with underscores
    page_name = page_name.replace(' ', '_')
    # Remove leading digits (Streamlit does this automatically)
    page_name = re.sub(r'^\d+', '', page_name)
    return page_name


def get_app_base_url() -> str:
    """Dynamically get the base URL for the current Streamlit app.

    Returns:
        str: Base URL for the app (e.g., 'http://localhost:8501' or production URL)

    Examples:
        >>> url = get_app_base_url()
        >>> print(url)  # 'http://localhost:8501' or production URL
    """
    import os

    if os.getenv('RAILWAY_ENVIRONMENT'):
        # Railway deployment - check for public domain
        railway_domain = os.getenv('RAILWAY_PUBLIC_DOMAIN')
        if railway_domain:
            return f"https://{railway_domain}"
        else:
            # Fallback - should be updated with actual Railway URL
            return "https://your-railway-app.railway.app"
    else:
        # Local development - use default Streamlit port
        return "http://localhost:8501"
