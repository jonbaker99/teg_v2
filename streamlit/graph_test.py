import altair as alt
import pandas as pd
import numpy as np
from themes import bar_theme, line_theme, PALETTE, PALETTE_SECONDARY

# Sample bar chart with primary palette
bar_df = pd.DataFrame({"Category": list("ABCDEF"),
                       "Value": np.random.randint(20, 120, 6)})

bar_chart = (
    alt.Chart(bar_df)
      .mark_bar()
      .encode(
          x="Category:N",
          y="Value:Q",
          color=alt.Color("Category:N", scale=alt.Scale(range=PALETTE), legend=None)
      )
      .properties(title="Primary Palette Bar")
      .configure(**bar_theme()["config"])
)

# Sample line chart with secondary palette
x = np.arange(1, 73)
line_df = pd.DataFrame({"x": np.tile(x, 6),
                        "y": np.random.randn(72*6).cumsum() + 50,
                        "Category": np.repeat(list("ABCDEF"), 72)})

line_chart = (
    alt.Chart(line_df)
      .mark_line(interpolate="monotone", size=2)
      .encode(
          x="x:Q",
          y="y:Q",
          color=alt.Color("Category:N", scale=alt.Scale(range=PALETTE_SECONDARY), legend=None)
      )
      .properties(title="Secondary Palette Line")
      .configure(**line_theme()["config"])
)
