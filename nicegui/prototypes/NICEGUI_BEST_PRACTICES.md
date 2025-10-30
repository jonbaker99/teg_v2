# NiceGUI Best Practices for TEG Analysis Prototypes

This document captures common patterns, issues, and solutions discovered during NiceGUI prototype development.

---

## 1. HTML Content Rendering - `ui.html()` Sanitization

### Issue
When using `ui.html()` to display HTML content (from DataFrames, markdown, etc.), you may encounter:

```
Error: Html.__init__() missing 1 required keyword-only argument: 'sanitize'
```

### Cause
NiceGUI's `ui.html()` function requires an explicit `sanitize` keyword argument. The function signature changed between versions to force developers to explicitly choose whether to sanitize HTML content.

### Solution
Always include the `sanitize` parameter when calling `ui.html()`:

```python
# WRONG - Will cause error
ui.html(df.to_html())

# CORRECT - Explicitly specify sanitize parameter
ui.html(df.to_html(), sanitize=False)
```

### When to Use `sanitize=False` vs `sanitize=True`

| Scenario | Value | Reason |
|----------|-------|--------|
| Display DataFrame as HTML table | `sanitize=False` | We generated the HTML from trusted pandas data |
| Display markdown-converted HTML | `sanitize=False` | We control the markdown source |
| Display external/user-provided HTML | `sanitize=True` | Prevents XSS and injection attacks |

### Examples in TEG Prototypes

**Displaying DataFrame tables:**
```python
html_output = history_table.to_html(index=False, escape=False)
ui.html(html_output, sanitize=False)  # Trusted source - our dataframe
```

**Displaying markdown reports:**
```python
html_content = markdown.markdown(report_text)
ui.html(html_content, sanitize=False)  # Trusted source - our markdown conversion
```

---

## 2. Navigation Pattern

### Page Routes
All prototype pages use the `@ui.page()` decorator with a specific route:

```python
@ui.page('/history/teg-history')
def teg_history_page():
    # Page content here
    pass
```

### Navigation Between Pages
Use `ui.navigate.to()` for client-side navigation:

```python
ui.button('Go to TEG History').on_click(
    lambda: ui.navigate.to('/history/teg-history')
)
```

### Root Page Required
NiceGUI requires at least one page at the root path `/`. The prototype application uses `prototype_index.py` for this purpose.

---

## 3. Data Loading Pattern

### Caching Strategy
Data is cached at module level in `shared_setup_prototypes.py`:

```python
# Cached once when module is imported
all_data_history = load_all_data()
all_data_records = load_all_data(exclude_teg_50=True)
```

**Advantage:** Fast subsequent loads
**Disadvantage:** Data doesn't refresh without restarting the app

### Loading Data in Pages
Pages import cached data:

```python
from prototypes.shared_setup_prototypes import all_data_history
```

Or load dynamically if fresher data is needed:

```python
from utils import load_all_data
teg_data = load_all_data()  # Fresh load each time
```

---

## 4. Error Handling Pattern

### Standard Try-Catch Pattern
All data loading should be wrapped in try-except:

```python
def display_data():
    try:
        # Load and process data
        data = load_data()
        if data.empty:
            ui.label('No data available').classes('text-gray-600')
            return

        # Display data
        html = data.to_html()
        ui.html(html, sanitize=False)

    except Exception as e:
        ui.label(f'Error: {str(e)}').classes('text-red-600')
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
```

### User-Friendly Error Messages
Always show helpful messages:

```python
# BAD - Not helpful
ui.label(f'Error: {str(e)}')

# GOOD - Contextual
ui.label(f'Error loading TEG Trophy rankings: {str(e)}').classes('text-red-600')
```

---

## 5. Page Structure Template

### Standard Layout
All prototype pages follow this structure:

```python
@ui.page('/history/example-page')
def example_page():
    # ===== PAGE TITLE & DESCRIPTION =====
    ui.label('Page Title').classes('text-h5 font-bold mt-6')
    ui.label('Brief description').classes('text-sm text-gray-600')
    ui.separator()

    # ===== CONTROLS (optional) =====
    selector = ui.select(options, label='Choose:', value=default)

    # ===== DATA DISPLAY AREA =====
    content_card = ui.card().classes('w-full')

    # ===== LOAD FUNCTION =====
    def load_and_display():
        try:
            content_card.clear()
            with content_card:
                # Load data
                # Process data
                # Display data
        except Exception as e:
            content_card.clear()
            with content_card:
                ui.label(f'Error: {str(e)}').classes('text-red-600')

    # ===== EVENT HANDLERS =====
    selector.on_change(lambda: load_and_display())

    # ===== INITIAL LOAD =====
    load_and_display()
```

---

## 6. Common Pitfalls & Solutions

### Pitfall 1: Data Not Updating
**Problem:** Users change a selector, but data doesn't update.

**Solution:** Attach `.on_change()` handler to trigger refresh:
```python
selector.on_change(lambda: load_and_display())
```

### Pitfall 2: Empty or None DataFrames
**Problem:** Code crashes when DataFrame is empty.

**Solution:** Always check:
```python
if data.empty or data is None:
    ui.label('No data available')
    return
```

### Pitfall 3: Missing Column Names
**Problem:** Accessing non-existent columns.

**Solution:** Check columns exist:
```python
if 'GrossVP' in df.columns:
    # Safe to use df['GrossVP']
```

### Pitfall 4: Circular Imports
**Problem:** Module A imports Module B, which imports Module A.

**Solution:** Import inside functions when needed:
```python
def load_data():
    from utils import load_all_data  # Import here, not at top
    return load_all_data()
```

---

## 7. CSS Classes Used

### Common Classes
```python
ui.label('Title').classes('text-h5 font-bold mt-6')        # Large title
ui.label('Description').classes('text-sm text-gray-600')   # Gray subtitle
ui.label('Error').classes('text-red-600')                   # Red error text
ui.label('Success').classes('text-green-600')               # Green success text
ui.label('Warning').classes('text-orange-600')              # Orange warning

ui.card().classes('w-full')                                 # Full width card
ui.row().classes('gap-4 items-center w-full')              # Horizontal layout
ui.column().classes('gap-2 w-full')                        # Vertical layout
```

### Spacing
```python
'mt-4'   # margin-top
'mb-2'   # margin-bottom
'ml-4'   # margin-left
'mr-2'   # margin-right
'p-6'    # padding
'gap-4'  # gap between flex items
```

---

## 8. Testing Checklist for New Pages

Before marking a prototype page as complete:

- [ ] Page loads without 404 error
- [ ] Page handles missing/empty data gracefully
- [ ] All controls (dropdowns, buttons) work without errors
- [ ] Data displays in HTML tables correctly
- [ ] Error messages are user-friendly
- [ ] No missing `sanitize=False` parameters on `ui.html()` calls
- [ ] Page navigation works (to/from index page)
- [ ] Page structure matches standard template

---

## 9. Performance Considerations

### Data Loading
- Use cached data from `shared_setup_prototypes.py` for quick loads
- Load fresh data only when necessary
- Avoid loading data in loops

### UI Updates
- Clear cards before updating: `card.clear()`
- Use `with card:` context for adding content
- Avoid re-creating entire UI on every change

### Large Tables
- Consider pagination for tables with >100 rows
- Use CSS `overflow: auto` for horizontal scrolling

---

## 10. Future Improvements

Potential enhancements for later phases:

1. **Markdown Rendering Enhancement**
   - Add CSS styling for markdown (headers, lists, blockquotes)
   - Consider using `python-markdown-extensions` for tables/code

2. **Table Enhancement**
   - Add sorting/filtering to tables
   - Highlight first place (green) and last place (pink)
   - Add row striping for readability

3. **Performance**
   - Implement lazy loading for large datasets
   - Add progress indicators for long operations

4. **Accessibility**
   - Add ARIA labels to all interactive elements
   - Ensure color contrast meets WCAG standards
   - Add keyboard navigation

---

## References

- NiceGUI Documentation: https://nicegui.io/
- NiceGUI HTML Widget: https://nicegui.io/documentation/html
- Tailwind CSS Classes: https://tailwindcss.com/docs

---

**Last Updated:** 2025-10-29
**Version:** 1.0
