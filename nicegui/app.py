# app.py — fixed: all UI lives inside the page function

from nicegui import ui
import pandas as pd
import plotly.express as px
import random

# ----- demo data (non-UI; safe at global scope) -----
PLAYERS = ['JB', 'AB', 'SN', 'HM', 'JP', 'GW']
COURSES = ['Garda', 'Dolomites', 'Augusta? (Wishful)', 'Local Park']

def make_demo_df(rows=200) -> pd.DataFrame:
    random.seed(42)
    data = []
    for _ in range(rows):
        data.append({
            'Player': random.choice(PLAYERS),
            'Course': random.choice(COURSES),
            'Round': random.randint(1, 4),
            'Stableford': random.randint(20, 44),
            'GrossVP': random.randint(-8, 18),
        })
    return pd.DataFrame(data)

DF = make_demo_df()

def filtered_df(course: str, player: str) -> pd.DataFrame:
    df = DF.copy()
    if course != 'All':
        df = df[df['Course'] == course]
    if player != 'All':
        df = df[df['Player'] == player]
    return df

def make_chart(df: pd.DataFrame, metric: str):
    if df.empty:
        return px.bar(pd.DataFrame({'Nothing': ['No data'], metric: [0]}), x='Nothing', y=metric, title='No data')
    agg = df.groupby('Player', as_index=False)[metric].sum()
    fig = px.bar(agg, x='Player', y=metric, title=f'{metric} by Player (sum)')
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
    fig.update_traces(text=agg[metric], textposition='outside')
    return fig

@ui.page('/')
def main():
    # --- all UI must be inside this function ---
    ui.add_head_html('''
    <style>
      .page { max-width: 1100px; margin: 0 auto; padding: 16px; }
      .dashline { border: none; border-top: 1px dashed #bbb; margin: 1rem 0; }
      .card { padding: 16px; border-radius: 12px; background: white; box-shadow: 0 1px 8px rgba(0,0,0,0.06); }
      .tight-table thead th { border-bottom: 1px solid #e7e7e7; }
      .tight-table td, .tight-table th { padding: 8px; }
    </style>
    ''')

    with ui.column().classes('page'):
        with ui.row().classes('w-full items-center justify-between'):
            ui.markdown('### NiceGUI Starter — Interactive Table + Chart')
            with ui.row().classes('items-center gap-3'):
                dm = ui.dark_mode()
                ui.switch('Dark mode', value=False, on_change=lambda e: dm.enable() if e.value else dm.disable())
                ui.button('Show dialog', on_click=lambda: dialog.open())
                ui.button('Toast', on_click=lambda: ui.notify('This is a toast 👍', position='top'))

        ui.html('<hr class="dashline">', sanitize=False)
        ui.separator().classes('my-dashed')

        tabs = ui.tabs().classes('w-full')
        with tabs:
            tab_dash = ui.tab('Dashboard')
            tab_data = ui.tab('Data')
            tab_help = ui.tab('Help')
        panels = ui.tab_panels(tabs, value=tab_dash).classes('w-full')

        # --- dashboard tab ---
        with panels:
            with ui.tab_panel(tab_dash):
                with ui.row().classes('w-full items-end gap-4'):
                    course = ui.select(['All', *COURSES], value='All', label='Course').classes('w-64')
                    player = ui.select(['All', *PLAYERS], value='All', label='Player').classes('w-64')
                    metric = ui.radio(['Stableford', 'GrossVP'], value='Stableford').props('inline')

                ui.separator()

                status = ui.label().classes('text-sm text-gray-600')
                with ui.row().classes('w-full'):
                    table_card = ui.element('div').classes('card w-1/2')
                    chart_card = ui.element('div').classes('card w-1/2')

                def render():
                    df_view = filtered_df(course.value, player.value)
                    view = (df_view
                            .groupby(['Player', 'Course'], as_index=False)[metric.value]
                            .sum()
                            .sort_values(metric.value, ascending=(metric.value == 'GrossVP')))

                    table_card.clear()
                    with table_card:
                        ui.label(f'Table — metric: {metric.value}').classes('text-lg font-medium')
                        if view.empty:
                            ui.label('No rows to display').classes('text-red-600')
                        else:
                            # ✅ add a serialisable key column before building the table
                            view['__rowid__'] = [f"{p}|{c}|{i}" for i, (p, c) in enumerate(zip(view['Player'], view['Course']))]

                            ui.table(
                                columns=[
                                    {'name': 'Player', 'label': 'Player', 'field': 'Player'},
                                    {'name': 'Course', 'label': 'Course', 'field': 'Course'},
                                    {'name': metric.value, 'label': metric.value, 'field': metric.value, 'align': 'right'},
                                ],
                                rows=view.to_dict(orient='records'),
                                row_key='__rowid__',   # ✅ string key instead of function
                            ).classes('tight-table')


                    chart_card.clear()
                    with chart_card:
                        fig = make_chart(df_view, metric.value)
                        ui.plotly(fig).classes('w-full')

                    status.text = f'Filtered rows: {len(df_view)}  |  Unique players: {df_view.Player.nunique()}'

                course.on('update:model-value', lambda e: render())
                player.on('update:model-value', lambda e: render())
                metric.on('update:model-value', lambda e: render())
                render()

            # --- data tab ---
            with ui.tab_panel(tab_data):
                ui.markdown('#### Raw data (first 25 rows)')
                ui.table(
                    columns=[{'name': c, 'label': c, 'field': c} for c in DF.columns],
                    rows=DF.head(25).to_dict(orient='records'),
                    row_key='__rowid__',
                ).classes('tight-table')

            # --- help tab ---
            with ui.tab_panel(tab_help):
                ui.markdown("""
### What changed (and why the error?)
- You used `@ui.page('/')` **and** created UI at the top level.
- In NiceGUI, when you use `@ui.page`, **all** UI must be created **inside** the page function.
- This version moves the CSS and dialog into the page, so it runs cleanly.

**Tip:** If you prefer global UI instead, remove the `@ui.page` decorator and build the UI at module scope, then call `ui.run()`.
                """.strip())

        # dialog must also live inside the page function
        with ui.dialog() as dialog, ui.card():
            ui.label('Hello from a dialog!')
            ui.button('Close', on_click=dialog.close)

ui.run(title='NiceGUI Starter', reload=True, host='0.0.0.0', port=8080)
