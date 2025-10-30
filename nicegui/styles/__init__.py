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
    """Apply all global stylesheets to the NiceGUI application.

    This function reads and injects all CSS stylesheets into the page head
    using `ui.add_head_html()` with `shared=True`, making them available
    across all sub-pages in the SPA.

    Stylesheets loaded (in order):
    1. global.css - Custom fonts (Lora for text, Roboto Mono for tables)
    2. datawrapper.css - Data table styling (13px font, column alignment)
    3. scorecard_styles.css - Golf scorecard styling (color coding, mobile layouts)

    Should be called once in the root function BEFORE ui.sub_pages() is defined.

    Example:
        def root():
            apply_global_styles()

            with ui.header():
                # Navigation...

            ui.sub_pages({...})
    """
    css_files = ['global.css', 'datawrapper.css', 'scorecard_styles.css']
    styles_dir = Path(__file__).parent

    for css_filename in css_files:
        css_file = styles_dir / css_filename

        if css_file.exists():
            try:
                css_content = css_file.read_text(encoding='utf-8')
                ui.add_head_html(f'<style>{css_content}</style>', shared=True)
                print(f"Loaded stylesheet: {css_filename}")
            except Exception as e:
                print(f"Warning: Error reading {css_filename}: {str(e)}")
        else:
            print(f"Warning: Stylesheet not found at {css_file}")


__all__ = ['apply_global_styles']
