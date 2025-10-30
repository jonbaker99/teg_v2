"""Global stylesheet management for TEG Analysis NiceGUI application.

Provides functions to load and apply custom fonts and styles globally across
all pages in the single-page application.

Font Configuration:
- General text: Lora (serif font for excellent readability)
- Table text: Roboto Mono (monospace font for proper number alignment)
"""

from pathlib import Path
from nicegui import ui


def apply_global_styles():
    """Apply global stylesheet with custom fonts to the NiceGUI application.

    This function reads the global.css stylesheet and injects it into the page
    head using `ui.add_head_html()` with `shared=True`, making it available
    across all sub-pages in the SPA.

    Font Configuration:
    - General text (body, labels, buttons, inputs): Lora
    - Table text (tables, code, monospace): Roboto Mono

    Should be called once in the root function BEFORE ui.sub_pages() is defined.

    Example:
        def root():
            apply_global_styles()

            with ui.header():
                # Navigation...

            ui.sub_pages({...})
    """
    css_file = Path(__file__).parent / 'global.css'

    if css_file.exists():
        css_content = css_file.read_text(encoding='utf-8')
        ui.add_head_html(f'<style>{css_content}</style>', shared=True)
    else:
        print(f"Warning: Global stylesheet not found at {css_file}")
        print("Continuing without custom fonts...")


__all__ = ['apply_global_styles']
