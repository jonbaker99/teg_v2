# Utils.py Inventory - Section 9A: TEG Status & URL Functions

**Section:** Application Status & URL Management
**Function Count:** 6 functions
**Lines in utils.py:** 4027-4044
**Estimated Complexity:** Simple

---

## Functions

### 1. `get_app_base_url() -> str` (Lines 4027-4044)
**Determines application base URL** for current environment.
- **Railway:** https://{RAILWAY_PUBLIC_DOMAIN}
- **Local:** http://localhost:8501
- **Returns:** Full base URL
- **Used By:** Navigation link generation

### 2-6. Fast TEG Status Functions (from Section 8C)
See UTILS_INVENTORY_08C for detailed documentation of:
- `update_teg_status_files()`
- `get_next_teg_and_check_if_in_progress_fast()`
- `get_last_completed_teg_fast()`
- `get_current_in_progress_teg_fast()`
- `has_incomplete_teg_fast()`

---

