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
