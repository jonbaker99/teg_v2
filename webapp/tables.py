"""Shared DataFrame -> HTML table rendering for webapp routes.

Every route file used to carry its own copy-pasted ``_df_to_html`` (or, in
player.py, ``_build_simple_table_html``) with inconsistent escaping — some
escaped cell values via markupsafe, most did not. This is the single
replacement; every cell (and column header) is escaped.
"""

from typing import Callable, Optional

import pandas as pd
from markupsafe import escape

from teg_analysis.core.players import get_name_to_code

DEFAULT_TABLE_CLASS = "teg-table"
EMPTY_TABLE_HTML = "<p class='text-muted text-sm'>No data available.</p>"


def df_to_html(
    df: pd.DataFrame,
    table_class: str = DEFAULT_TABLE_CLASS,
    col_class: Optional[Callable[[int, str], Optional[str]]] = None,
    cell_classes: Optional[dict] = None,
    link_players: bool = False,
    highlight_col: Optional[str] = None,
    highlight_val=None,
) -> str:
    """Render a DataFrame as an escaped HTML table.

    - ``col_class(i, col)`` -> optional CSS class applied to every cell
      (header + body) in column ``col`` at position ``i``.
    - ``cell_classes[(row_idx, col)]`` -> optional CSS class for one body
      cell, overriding ``col_class`` for that cell.
    - ``link_players``: wrap the ``Player`` column's value in a link to its
      profile (``/player/{code}``) when the name resolves to a known code.
    - ``highlight_col``/``highlight_val``: rows where
      ``str(row[highlight_col]) == str(highlight_val)`` get a ``top-rank``
      row class.
    """
    if df is None or df.empty:
        return EMPTY_TABLE_HTML

    cols = list(df.columns)
    name_to_code = get_name_to_code() if link_players else None

    def _class_attr(cls: Optional[str]) -> str:
        return f" class='{cls}'" if cls else ""

    rows = [f"<table class='{table_class}'><thead><tr>"]
    for i, col in enumerate(cols):
        cls = col_class(i, col) if col_class else None
        rows.append(f"<th{_class_attr(cls)}>{escape(str(col))}</th>")
    rows.append("</tr></thead><tbody>")

    for row_idx, (_, row) in enumerate(df.iterrows()):
        row_cls = ""
        if highlight_col and highlight_val is not None and \
                str(row.get(highlight_col, "")) == str(highlight_val):
            row_cls = " class='top-rank'"
        rows.append(f"<tr{row_cls}>")
        for i, col in enumerate(cols):
            cls = col_class(i, col) if col_class else None
            if cell_classes:
                override = cell_classes.get((row_idx, col))
                if override:
                    cls = override
            val = row[col]
            if link_players and col == "Player":
                code = name_to_code.get(str(val))
                text = escape(str(val))
                cell_html = f"<a href='/player/{code}'>{text}</a>" if code else text
            else:
                cell_html = escape(str(val))
            rows.append(f"<td{_class_attr(cls)}>{cell_html}</td>")
        rows.append("</tr>")
    rows.append("</tbody></table>")
    return "".join(rows)
