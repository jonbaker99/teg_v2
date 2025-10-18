# Utils.py Inventory - Section 9B: Navigation & Custom UI Functions

**Section:** Navigation System & Custom UI Components
**Function Count:** 5 functions
**Lines in utils.py:** 4047-4405
**Estimated Complexity:** Medium to Complex

---

## Functions

### 1. `convert_filename_to_streamlit_url(page_file: str) -> str` (Lines 4047-4071)
**Converts page filenames to Streamlit URL format.**
- **Features:**
  - Strips leading numbers (Streamlit does this automatically)
  - Replaces spaces with underscores
  - Returns empty string for main page
- **Examples:**
  - "101TEG History.py" → ""
  - "300TEG Records.py" → "TEG_Records"
  - "500Handicaps.py" → "Handicaps"
- **Type:** PURE | **Complexity:** Simple
- **Used By:** Navigation link generation

### 2. `add_custom_navigation_links(input_value, css_class="custom-nav-link", layout="columns", separator=" | ", exclude_current=True, render=True)` (Lines 4085-4190)
**Generates custom navigation links** for pages in a section.
- **Parameters:**
  - input_value: Page filename or section name
  - css_class: CSS styling class
  - layout: "columns"|"horizontal"|"vertical"
  - separator: Used for horizontal layout
  - exclude_current: Skip current page from links
  - render: True=write to Streamlit, False=return HTML
- **Returns:**
  - None if render=True
  - HTML string or List[List[str]] if render=False
- **Features:**
  - Flexible layout options
  - Excludes current page by default
  - Configurable styling
- **Type:** MIXED | **Complexity:** Complex
- **Used By:** Section navigation displays

### 3. `add_section_navigation_links(input_value=None, css_class="custom-nav-link", layout="columns", separator=" | ", exclude_current=True, exclude_data=True, render=True)` (Lines 4193-4327)
**Generates navigation links** between sections (not pages within section).
- **Parameters:** Similar to add_custom_navigation_links
- **Features:**
  - Links to first page in each section
  - Can exclude "Data" section
  - Can exclude current section
  - Respects SECTION_CONFIG for ordering
- **Type:** MIXED | **Complexity:** Complex
- **Used By:** Main navigation menus

### 4. `create_custom_navigation_section(section_name, pages, current_page, container_class="nav-section")` (Lines 4330-4365)
**Creates fully custom navigation section** with advanced HTML structure.
- **Parameters:**
  - section_name: Display name
  - pages: List of page files in section
  - current_page: Current page (for exclusion)
  - container_class: CSS container class
- **Returns:** HTML string with nav structure
- **Features:**
  - Includes icons from PAGE_DEFINITIONS
  - Custom HTML structure
  - Data attributes for targeting
- **Type:** MIXED | **Complexity:** Complex
- **Used By:** Advanced navigation layouts

### 5. `apply_custom_navigation_css()` (Lines 4368-4405)
**Loads and applies navigation CSS** from external file with fallback.
- **Features:**
  - Loads styles/navigation.css
  - Fallback inline CSS if file missing
  - Safe encoding handling
- **Type:** IO | **Complexity:** Simple
- **Used By:** All navigation functions

---

## Dependencies & Configuration

**Imports:**
- `page_config.py`: PAGE_DEFINITIONS, SECTION_LAYOUTS, SECTION_CONFIG

**Data Structures:**
- PAGE_DEFINITIONS: Dict mapping filenames to config (title, section, icon)
- SECTION_LAYOUTS: Dict mapping sections to column counts
- SECTION_CONFIG: Dict with section metadata (order, display_name)

---

## Section Summary

**Statistics:**
- Total Functions: 5
- Total Lines: ~360 lines
- Type Breakdown: 1 PURE + 4 MIXED/IO
- Complexity: 1 Simple, 3 Complex

**Key Functions:**
- `convert_filename_to_streamlit_url()`: Utility for URL generation
- `add_custom_navigation_links()`: Flexible navigation within section
- `add_section_navigation_links()`: Cross-section navigation
- `create_custom_navigation_section()`: Advanced custom layouts
- `apply_custom_navigation_css()`: CSS styling application

**Architecture:**
- Centralized configuration (page_config.py)
- Multiple layout options (columns, horizontal, vertical)
- Flexible rendering (inline or deferred)
- Graceful fallbacks (CSS missing, custom HTML)

**Used By Extent:**
- All pages use some form of navigation
- Key for multi-page Streamlit apps
- Supports complex navigation hierarchies

---

