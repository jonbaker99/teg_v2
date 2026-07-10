"""webapp.tables.df_to_html rendering.

Regression coverage for NaN cells: pages built on pivots (e.g. GrossVP by
TEG x Player, where a player missed a TEG) used to render the literal
string "nan" via str(val) instead of a blank placeholder.
"""

import numpy as np
import pandas as pd

from webapp.tables import df_to_html


def test_nan_cell_renders_as_dash():
    df = pd.DataFrame({"Player": ["Alice", "Bob"], "TEG 1": [72, np.nan]})

    html = df_to_html(df)

    assert "nan" not in html
    assert "<td>-</td>" in html


def test_none_cell_renders_as_dash():
    df = pd.DataFrame({"Player": ["Alice"], "Note": [None]})

    html = df_to_html(df)

    assert "nan" not in html
    assert "None" not in html
    assert "<td>-</td>" in html


def test_non_nan_values_still_render_normally():
    df = pd.DataFrame({"Player": ["Alice"], "TEG 1": [72]})

    html = df_to_html(df)

    assert "<td>72</td>" in html
