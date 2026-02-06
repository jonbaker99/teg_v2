"""Mock utilities for testing - handles Streamlit compatibility

This module provides mocking utilities to allow tests to import from utils.py
even when using an older Streamlit version that doesn't have cache_data.
"""

import sys
import unittest.mock as mock


def setup_streamlit_mocks():
    """Setup mock Streamlit decorators for older versions

    Streamlit 1.50.0 doesn't have cache_data decorator.
    This function adds mocks so tests can import modules using it.
    """
    # Create a mock streamlit module if needed
    import streamlit

    # If cache_data doesn't exist, add a no-op decorator
    if not hasattr(streamlit, 'cache_data'):
        streamlit.cache_data = lambda *args, **kwargs: lambda f: f

    if not hasattr(streamlit, 'cache'):
        streamlit.cache = lambda *args, **kwargs: lambda f: f

    return streamlit


# Setup mocks when module loads
setup_streamlit_mocks()
