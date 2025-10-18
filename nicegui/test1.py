import os
from pathlib import Path
from typing import Optional

import pandas as pd
from nicegui import ui
import plotly.express as px

# --- Config / paths ---
DATA_DIR = Path(os.getenv('DATA_DIR', './data'))
ALL_DATA = DATA_DIR / 'all-data.parquet'
ALL_SCORES = DATA_DIR / 'all-scores.csv'

# --- Data loaders (adjust field names to match your dataset) ---
def load_all_data() -> pd.DataFrame:
    if ALL_DATA.exists():
        return pd.read_parquet(ALL_DATA)
    if ALL_SCORES.exists():
        return pd.read_csv(ALL_SCORES)
    # Safe fallback: empty schema
    return pd.DataFrame(columns=['Player', 'TEGNum', 'Stableford', 'GrossVP', 'Round', 'Course'])

def get_tegs(df: pd.DataFrame) -> list[int]:
    if 'TEGNum' not in df.columns or df.empty:
        return []
    tegs = sorted(pd.to_numeric(df['TEGNum'], errors='coerce').dropna().unique().astype(int).tolist())
    return tegs

def leaderboard_by_stableford(df: pd.DataFrame, teg: Optional[int]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=['Player', 'Stableford'])
    if teg is not None:
        df = df[df['TEGNum'] == teg]
    if df.empty:
        return pd.DataFrame(columns=['Player', 'Stableford'])
    out = (
        df.groupby('Player', as_index=False)['Stableford']
          .sum()
          .sort_values('Stableford', ascending=False)
    )
    return out

# --- Global data (simple; you can add caching if the files are large) ---
ALL_DF = load_all_data()
TEG_OPTIONS = get_tegs(ALL_DF)

# --- Simple styles you control (dashed line, table tweaks, etc.) ---
ui.add_head_html('''
<style>
  .section { max-width: 960px; margin: 0 auto; padding: 16px; }
  .dashline { border: none; border-top: 1px dashed #bbb; margin: 1rem 0; }
  .tight-table thead th { border-bottom: 1px solid #e7e7e7; }
  .tight-table td, .tight-table th { padding: 8px; }
</style>
''')

@ui.page('/')
def home():
    with ui.column().classes('section'):
        ui.markdown('# TEG Leaderboard (NiceGUI)')
        ui.label('A like-for-like demo of Streamlit behaviour, but event-driven.')

        # Controls row
        with ui.row().classes('items-end gap-4'):
            teg_select = ui.select(
                options=TEG_OPTIONS or [],
                label='TEG (optional)',
                with_input=True,
            ).classes('w-40')

            topn = ui.slider(min=5, max=30, value=10, step=1, label='Show Top N').classes('w-64')

            refresh_btn = ui.button('Refresh', icon='refresh')

        ui.html('<hr class="dashline">')

        table_card = ui.card().classes('w-full')
        chart_card = ui.card().classes('w-full')

        status = ui.label().classes('text-grey-600')

        def refresh():
            teg_val = None
            try:
                val = teg_select.value
                if val not in (None, ''):
                    teg_val = int(val)
            except Exception:
                teg_val = None

            df = leaderboard_by_stableford(ALL_DF, teg_val)
            n = int(topn.value or 10)
            view = df.head(n)

            # Table
            table_card.clear()
            with table_card:
                ui.label(f'Leaderboard{f" — TEG {teg_val}" if teg_val else ""} (Top {n})').classes('text-lg font-medium')
                if view.empty:
                    ui.label('No data').classes('text-red-600')
                else:
                    ui.table(
                        columns=[
                            {'name': 'Player', 'label': 'Player', 'field': 'Player'},
                            {'name': 'Stableford', 'label': 'Stableford', 'field': 'Stableford', 'align': 'right'},
                        ],
                        rows=view.to_dict(orient='records'),
                        row_key='Player',
                    ).classes('tight-table')

            # Chart
            chart_card.clear()
            with chart_card:
                if not view.empty:
                    fig = px.bar(view, x='Player', y='Stableford', title='Stableford (Top N)', text='Stableford')
                    fig.update_traces(textposition='outside')
                    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), xaxis_title=None, yaxis_title=None)
                    ui.plotly(fig).classes('w-full')

            status.text = f'Rendered {len(view)} rows' if not view.empty else 'No rows to render'

        # Wire up events (no full script reruns)
        refresh_btn.on('click', refresh)
        teg_select.on('update:model-value', lambda _: refresh())
        topn.on('update:model-value', lambda _: refresh())

        # First render
        refresh()

# Local dev:
# - For Railway, pass host='0.0.0.0', port=int(os.getenv('PORT', '8080'))
ui.run(title='TEG with NiceGUI', reload=True)
