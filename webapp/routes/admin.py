"""Admin data-update page.

A small, password-gated UI to add a round of scores from the Google Sheet while
out and about (e.g. straight after a round). It drives the headless pipeline in
``teg_analysis.analysis.data_update`` — this route layer only handles auth, the
two-step preview/confirm UX, and clearing the webapp's data caches afterwards.

Flow:
  GET  /admin                      -> login or the update page
  GET  /admin/login  POST          -> set/clear the admin cookie
  GET  /admin/data-update          -> the update page (load button)
  POST /admin/data-update/preview  -> fetch sheet, show totals + duplicate check
  POST /admin/data-update/execute  -> run the update, commit, clear caches
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from webapp.admin_auth import is_authed, check_password, set_auth_cookie, clear_auth_cookie
from webapp import deps

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

# Defaults for the TEG round-input sheet (matches the legacy Streamlit flow).
DEFAULT_SHEET = "TEG Round Input"
DEFAULT_WORKSHEET = "Scores"

_TABLE_CLASSES = "teg-table"


def _redirect(url: str) -> RedirectResponse:
    # 303 so the browser issues a GET after our POST handlers.
    return RedirectResponse(url, status_code=303)


# --- Auth ---------------------------------------------------------------------

@router.get("/admin")
async def admin_home(request: Request):
    if not is_authed(request):
        return _redirect("/admin/login")
    return _redirect("/admin/data-update")


@router.get("/admin/login")
async def admin_login_form(request: Request, error: str = ""):
    return templates.TemplateResponse("admin_login.html", {
        "request": request,
        "active_page": None,
        "error": error,
    })


@router.post("/admin/login")
async def admin_login(request: Request, password: str = Form("")):
    if not check_password(password):
        return templates.TemplateResponse("admin_login.html", {
            "request": request,
            "active_page": None,
            "error": "Incorrect password.",
        })
    response = _redirect("/admin/data-update")
    set_auth_cookie(response)
    return response


@router.get("/admin/logout")
async def admin_logout():
    response = _redirect("/admin/login")
    clear_auth_cookie(response)
    return response


# --- Data update --------------------------------------------------------------

@router.get("/admin/data-update")
async def admin_data_update(request: Request):
    if not is_authed(request):
        return _redirect("/admin/login")
    return templates.TemplateResponse("admin_data_update.html", {
        "request": request,
        "active_page": None,
        "sheet": DEFAULT_SHEET,
        "worksheet": DEFAULT_WORKSHEET,
    })


@router.post("/admin/data-update/preview", response_class=HTMLResponse)
async def admin_data_update_preview(
    request: Request,
    sheet: str = Form(DEFAULT_SHEET),
    worksheet: str = Form(DEFAULT_WORKSHEET),
):
    if not is_authed(request):
        return HTMLResponse('<p class="error">Session expired — please reload and log in.</p>', status_code=401)

    from teg_analysis.analysis.pipeline import get_google_sheet
    from teg_analysis.analysis.data_update import (
        process_google_sheets_data, summarise_round_scores,
        find_duplicate_keys, analyze_hole_level_differences,
    )
    from teg_analysis.io import read_file
    from teg_analysis.constants import ALL_SCORES_PARQUET

    ctx = {"request": request, "sheet": sheet, "worksheet": worksheet}

    try:
        raw = get_google_sheet(sheet, worksheet)
        new_df = process_google_sheets_data(raw)
    except Exception as e:  # noqa: BLE001 - surface any fetch/parse error to the UI
        logger.error(f"Preview load failed: {e}", exc_info=True)
        ctx["error"] = f"Could not load the sheet: {e}"
        return templates.TemplateResponse("partials/admin_update_preview.html", ctx)

    if new_df.empty:
        ctx["error"] = "No complete 18-hole rounds found in the sheet."
        return templates.TemplateResponse("partials/admin_update_preview.html", ctx)

    try:
        existing = read_file(ALL_SCORES_PARQUET)
    except Exception:
        existing = None

    dup_keys = find_duplicate_keys(existing, new_df)  # handles existing=None
    has_duplicates = not dup_keys.empty

    diff_html = ""
    if has_duplicates:
        diffs, has_diff = analyze_hole_level_differences(existing, new_df, dup_keys)
        if has_diff:
            diff_html = diffs.to_html(index=False, classes=_TABLE_CLASSES, border=0)

    summary_html = summarise_round_scores(new_df).to_html(classes=_TABLE_CLASSES, border=0)

    ctx.update({
        "summary_html": summary_html,
        "has_duplicates": has_duplicates,
        "duplicate_count": int(len(dup_keys)),
        "diff_html": diff_html,
        "row_count": int(len(new_df)),
    })
    return templates.TemplateResponse("partials/admin_update_preview.html", ctx)


@router.post("/admin/data-update/execute", response_class=HTMLResponse)
async def admin_data_update_execute(
    request: Request,
    sheet: str = Form(DEFAULT_SHEET),
    worksheet: str = Form(DEFAULT_WORKSHEET),
    mode: str = Form("append"),
):
    if not is_authed(request):
        return HTMLResponse('<p class="error">Session expired — please reload and log in.</p>', status_code=401)

    from teg_analysis.analysis.pipeline import get_google_sheet
    from teg_analysis.analysis.data_update import process_google_sheets_data, execute_data_update

    ctx = {"request": request}

    try:
        raw = get_google_sheet(sheet, worksheet)
        new_df = process_google_sheets_data(raw)
        if new_df.empty:
            ctx["error"] = "No complete 18-hole rounds found in the sheet."
            return templates.TemplateResponse("partials/admin_update_result.html", ctx)

        result = execute_data_update(
            new_df,
            overwrite=(mode == "overwrite"),
            new_data_only=(mode == "new_only"),
        )
        # Site reads are cached in-process; drop them so the update shows immediately.
        deps.clear_all_data_caches()
    except Exception as e:  # noqa: BLE001
        logger.error(f"Data update failed: {e}", exc_info=True)
        ctx["error"] = f"Update failed: {e}"
        return templates.TemplateResponse("partials/admin_update_result.html", ctx)

    ctx["result"] = result
    return templates.TemplateResponse("partials/admin_update_result.html", ctx)


# --- Edit metadata CSVs -------------------------------------------------------

@router.get("/admin/edit-data")
async def admin_edit_data(request: Request, file: str = "round_info"):
    if not is_authed(request):
        return _redirect("/admin/login")

    from teg_analysis.analysis.data_update import EDITABLE_DATA_FILES
    from teg_analysis.io import read_file

    # "processed" is a special read-only view of the fully processed dataset.
    is_processed = file == "processed"
    if not is_processed and file not in EDITABLE_DATA_FILES:
        file = "round_info"

    ctx = {
        "request": request,
        "active_page": None,
        "files": EDITABLE_DATA_FILES,
        "selected": file,
        "is_processed": is_processed,
    }

    if is_processed:
        ctx["meta"] = {
            "label": "Processed Tournament Data",
            "description": "Read-only view of fully processed data (all-data.parquet).",
            "kind": "readonly",
        }
        try:
            from teg_analysis.core.data_loader import load_all_data
            all_data = load_all_data(exclude_teg_50=True, exclude_incomplete_tegs=False)
            ctx["row_count"] = int(len(all_data))
            ctx["table_html"] = all_data.head(500).to_html(
                index=False, classes=_TABLE_CLASSES, border=0
            )
        except Exception as e:  # noqa: BLE001
            logger.error(f"Processed-data view failed: {e}", exc_info=True)
            ctx["error"] = f"Could not load processed data: {e}"
        return templates.TemplateResponse("admin_edit_data.html", ctx)

    meta = EDITABLE_DATA_FILES[file]
    ctx["meta"] = meta
    try:
        df = read_file(meta["path"])
        ctx["columns"] = list(df.columns)
        # Stringify cells for the editable grid (NaN -> empty).
        ctx["rows"] = df.astype(object).where(df.notna(), "").values.tolist()
        ctx["missing"] = False
    except FileNotFoundError:
        ctx["missing"] = True
        ctx["columns"] = []
        ctx["rows"] = []
    except Exception as e:  # noqa: BLE001
        logger.error(f"Edit-data load failed for {meta['path']}: {e}", exc_info=True)
        ctx["error"] = f"Could not load {meta['path']}: {e}"
        ctx["missing"] = False
        ctx["columns"] = []
        ctx["rows"] = []

    return templates.TemplateResponse("admin_edit_data.html", ctx)


@router.post("/admin/edit-data/save", response_class=HTMLResponse)
async def admin_edit_data_save(request: Request):
    if not is_authed(request):
        return HTMLResponse('<p class="error">Session expired — please reload and log in.</p>', status_code=401)

    import json
    import re
    from collections import defaultdict

    import pandas as pd

    from teg_analysis.analysis.data_update import EDITABLE_DATA_FILES, save_data_file

    form = await request.form()
    slug = form.get("file", "")
    ctx = {"request": request, "selected": slug}

    if slug not in EDITABLE_DATA_FILES:
        ctx["error"] = "Unknown file."
        return templates.TemplateResponse("partials/admin_edit_result.html", ctx)

    meta = EDITABLE_DATA_FILES[slug]
    try:
        columns = json.loads(form.get("columns", "[]"))
    except json.JSONDecodeError:
        columns = []

    # Rebuild rows from cell__{rid}__{cidx} fields (robust to added/deleted rows).
    grouped: dict[int, dict[int, str]] = defaultdict(dict)
    for key, val in form.multi_items():
        m = re.match(r"cell__(\d+)__(\d+)$", key)
        if m:
            grouped[int(m.group(1))][int(m.group(2))] = val

    records = []
    for rid in sorted(grouped):
        row = grouped[rid]
        # Skip fully-blank rows so a stray added row doesn't write empties.
        values = [row.get(cidx, "") for cidx in range(len(columns))]
        if any(str(v).strip() for v in values):
            records.append(values)

    try:
        df = pd.DataFrame(records, columns=columns)
        # Light type coercion: numeric columns become numeric in the CSV.
        for col in df.columns:
            coerced = pd.to_numeric(df[col], errors="coerce")
            if coerced.notna().all() and len(df) > 0:
                df[col] = coerced
        save_data_file(meta["path"], df, commit_message=f"Edit {meta['label']} via admin")
        deps.clear_all_data_caches()
    except Exception as e:  # noqa: BLE001
        logger.error(f"Edit-data save failed for {meta['path']}: {e}", exc_info=True)
        ctx["error"] = f"Save failed: {e}"
        return templates.TemplateResponse("partials/admin_edit_result.html", ctx)

    ctx["result"] = {"path": meta["path"], "label": meta["label"], "rows": len(df)}
    return templates.TemplateResponse("partials/admin_edit_result.html", ctx)


@router.post("/admin/edit-data/regenerate-status", response_class=HTMLResponse)
async def admin_edit_regenerate_status(request: Request):
    if not is_authed(request):
        return HTMLResponse('<p class="error">Session expired — please reload and log in.</p>', status_code=401)

    from teg_analysis.analysis.data_update import regenerate_status_files

    ctx = {"request": request, "selected": ""}
    try:
        result = regenerate_status_files()
        deps.clear_all_data_caches()
    except Exception as e:  # noqa: BLE001
        logger.error(f"Status regeneration failed: {e}", exc_info=True)
        ctx["error"] = f"Regeneration failed: {e}"
        return templates.TemplateResponse("partials/admin_edit_result.html", ctx)

    ctx["result"] = {"regenerated": True, **result}
    return templates.TemplateResponse("partials/admin_edit_result.html", ctx)


# --- Delete rounds ------------------------------------------------------------

@router.get("/admin/delete-data")
async def admin_delete_data(request: Request):
    if not is_authed(request):
        return _redirect("/admin/login")

    from teg_analysis.analysis.data_update import get_available_tegs_and_rounds
    from teg_analysis.io import read_file
    from teg_analysis.constants import ALL_SCORES_PARQUET

    ctx = {"request": request, "active_page": None}
    try:
        scores = read_file(ALL_SCORES_PARQUET)
        ctx["tegs"] = get_available_tegs_and_rounds(scores)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Delete-data load failed: {e}", exc_info=True)
        ctx["tegs"] = {}
        ctx["error"] = f"Could not load scores: {e}"
    return templates.TemplateResponse("admin_delete_data.html", ctx)


@router.post("/admin/delete-data/preview", response_class=HTMLResponse)
async def admin_delete_data_preview(request: Request):
    if not is_authed(request):
        return HTMLResponse('<p class="error">Session expired — please reload and log in.</p>', status_code=401)

    from teg_analysis.analysis.data_update import (
        preview_deletion_data, validate_deletion_selection,
    )
    from teg_analysis.io import read_file
    from teg_analysis.constants import ALL_SCORES_PARQUET

    form = await request.form()
    teg = form.get("teg", "")
    rounds = form.getlist("rounds")
    ctx = {"request": request, "teg": teg, "rounds": rounds}

    if not teg or not validate_deletion_selection(rounds):
        ctx["error"] = "Select a TEG and at least one round to delete."
        return templates.TemplateResponse("partials/admin_delete_preview.html", ctx)

    try:
        scores = read_file(ALL_SCORES_PARQUET)
        to_delete = preview_deletion_data(scores, teg, rounds)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Delete preview failed: {e}", exc_info=True)
        ctx["error"] = f"Could not build preview: {e}"
        return templates.TemplateResponse("partials/admin_delete_preview.html", ctx)

    ctx["row_count"] = int(len(to_delete))
    ctx["preview_html"] = to_delete.head(200).to_html(
        index=False, classes=_TABLE_CLASSES, border=0
    )
    return templates.TemplateResponse("partials/admin_delete_preview.html", ctx)


@router.post("/admin/delete-data/execute", response_class=HTMLResponse)
async def admin_delete_data_execute(request: Request):
    if not is_authed(request):
        return HTMLResponse('<p class="error">Session expired — please reload and log in.</p>', status_code=401)

    from teg_analysis.analysis.data_update import (
        execute_data_deletion, validate_deletion_selection,
    )

    form = await request.form()
    teg = form.get("teg", "")
    rounds = form.getlist("rounds")
    ctx = {"request": request}

    if not teg or not validate_deletion_selection(rounds):
        ctx["error"] = "Select a TEG and at least one round to delete."
        return templates.TemplateResponse("partials/admin_delete_result.html", ctx)

    try:
        # Re-fetch happens inside execute_data_deletion (reads the live files).
        result = execute_data_deletion(int(teg), [int(r) for r in rounds])
        deps.clear_all_data_caches()
    except Exception as e:  # noqa: BLE001
        logger.error(f"Deletion failed: {e}", exc_info=True)
        ctx["error"] = f"Deletion failed: {e}"
        return templates.TemplateResponse("partials/admin_delete_result.html", ctx)

    ctx["result"] = result
    return templates.TemplateResponse("partials/admin_delete_result.html", ctx)


# --- GitHub <-> store sync ----------------------------------------------------

def _sync_body_ctx(request: Request, folder: str, result: dict = None) -> dict:
    """Build the context for the sync body partial (status table + forms)."""
    from teg_analysis.io import (
        build_sync_status, store_label, SYNC_FOLDERS, is_railway, list_sync_backups,
    )

    if folder not in SYNC_FOLDERS:
        folder = SYNC_FOLDERS[0]

    ctx = {
        "request": request,
        "folders": SYNC_FOLDERS,
        "folder": folder,
        "store_label": store_label(),
        "is_railway": is_railway(),
        "result": result,
    }
    try:
        ctx["rows"] = build_sync_status(folder)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Sync status failed for {folder}: {e}", exc_info=True)
        ctx["rows"] = []
        ctx["error"] = f"Could not list files: {e}"
    try:
        ctx["backups"] = list_sync_backups()
    except Exception as e:  # noqa: BLE001
        logger.error(f"Listing sync backups failed: {e}", exc_info=True)
        ctx["backups"] = []
    return ctx


@router.get("/admin/volume-sync")
async def admin_volume_sync(request: Request, folder: str = "data"):
    if not is_authed(request):
        return _redirect("/admin/login")
    ctx = _sync_body_ctx(request, folder)
    ctx["active_page"] = None
    return templates.TemplateResponse("admin_volume_sync.html", ctx)


def _sync_conflict_response(request: Request, *, action: str, folder: str,
                            names: list[str], conflicts: list[dict]):
    """Render the overwrite-confirm screen when newer files would be clobbered."""
    ctx = {
        "request": request,
        "action": action,
        "folder": folder,
        "names": names,
        "conflicts": conflicts,
    }
    return templates.TemplateResponse("partials/admin_sync_conflict.html", ctx)


@router.post("/admin/volume-sync/pull", response_class=HTMLResponse)
async def admin_volume_sync_pull(request: Request):
    if not is_authed(request):
        return HTMLResponse('<p class="error">Session expired — please reload and log in.</p>', status_code=401)

    from teg_analysis.io import pull_files, detect_pull_conflicts

    form = await request.form()
    folder = form.get("folder", "data")
    names = form.getlist("files")
    confirmed = form.get("confirm", "") == "1"

    if not names:
        ctx = _sync_body_ctx(request, folder, result={"action": "pull", "empty": True})
        return templates.TemplateResponse("partials/admin_sync_body.html", ctx)

    # Warn before overwriting a store copy that's newer than GitHub's.
    if not confirmed:
        try:
            conflicts = detect_pull_conflicts(folder, names)
        except Exception:  # noqa: BLE001 - never block the action on a check failure
            conflicts = []
        if conflicts:
            return _sync_conflict_response(
                request, action="pull", folder=folder, names=names, conflicts=conflicts)

    try:
        outcome = pull_files(folder, names)
        deps.clear_all_data_caches()  # store changed — drop in-process caches
        result = {"action": "pull", **outcome}
    except Exception as e:  # noqa: BLE001
        logger.error(f"Pull failed: {e}", exc_info=True)
        result = {"action": "pull", "error": str(e)}

    ctx = _sync_body_ctx(request, folder, result=result)
    return templates.TemplateResponse("partials/admin_sync_body.html", ctx)


@router.post("/admin/volume-sync/push", response_class=HTMLResponse)
async def admin_volume_sync_push(request: Request):
    if not is_authed(request):
        return HTMLResponse('<p class="error">Session expired — please reload and log in.</p>', status_code=401)

    from teg_analysis.io import push_files, detect_push_conflicts

    form = await request.form()
    folder = form.get("folder", "data")
    names = form.getlist("files")
    message = form.get("commit_message", "").strip() or None
    confirmed = form.get("confirm", "") == "1"

    if not names:
        ctx = _sync_body_ctx(request, folder, result={"action": "push", "empty": True})
        return templates.TemplateResponse("partials/admin_sync_body.html", ctx)

    # Warn before overwriting a GitHub copy that's newer than the store's.
    if not confirmed:
        try:
            conflicts = detect_push_conflicts(folder, names)
        except Exception:  # noqa: BLE001
            conflicts = []
        if conflicts:
            return _sync_conflict_response(
                request, action="push", folder=folder, names=names, conflicts=conflicts)

    try:
        outcome = push_files(folder, names, commit_message=message)
        result = {"action": "push", **outcome}
    except Exception as e:  # noqa: BLE001
        logger.error(f"Push failed: {e}", exc_info=True)
        result = {"action": "push", "error": str(e)}

    ctx = _sync_body_ctx(request, folder, result=result)
    return templates.TemplateResponse("partials/admin_sync_body.html", ctx)


@router.post("/admin/volume-sync/restore", response_class=HTMLResponse)
async def admin_volume_sync_restore(request: Request):
    if not is_authed(request):
        return HTMLResponse('<p class="error">Session expired — please reload and log in.</p>', status_code=401)

    from teg_analysis.io import restore_backup

    form = await request.form()
    folder = form.get("folder", "data")
    backup_rel = form.get("backup_rel", "")

    try:
        original = restore_backup(backup_rel)
        deps.clear_all_data_caches()
        result = {"action": "restore", "original": original}
    except Exception as e:  # noqa: BLE001
        logger.error(f"Restore failed for {backup_rel}: {e}", exc_info=True)
        result = {"action": "restore", "error": str(e)}

    ctx = _sync_body_ctx(request, folder, result=result)
    return templates.TemplateResponse("partials/admin_sync_body.html", ctx)
