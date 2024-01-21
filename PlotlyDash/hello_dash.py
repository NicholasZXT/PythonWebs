import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dash import Dash, html, dcc, dash_table, Input, Output, callback

app = Dash(__name__)

markdown_text = '''
### Dash and Markdown

Dash apps can be written in Markdown.
Dash uses the [CommonMark](http://commonmark.org/) specification of Markdown.

```python
import pandas as pd
df = pd.DataFrame({'c1': [1, 2, 3, 4], 'c2': [5, 6, 7]})
df.show()
```
'''

species = ['setosa', 'versicolor', 'virginica']
iris_df = px.data.iris()

app.layout = html.Div(children=[
    html.H1(children='Hello Dash'),

    html.Div(children='''
        Dash: A web application framework for your data.
    '''),

    dcc.Markdown(markdown_text),

    html.Label('Multi-Select Dropdown for Iris Data', style={'textAlign': 'center'}),
    dcc.Dropdown(options=species, value=species, multi=True, id='iris-dropdown'),
    html.Br(),
    dcc.Graph(id='iris-graph')
])


@callback(
    Output(component_id='iris-graph', component_property='figure'),
    Input(component_id='iris-dropdown', component_property='value')
)
def update_iris_graph(species):
    # print(f"species: {species}")
    if isinstance(species, list) and len(species) > 0:
        iris_select_df = iris_df[iris_df['species'].isin(species)]
    else:
        iris_select_df = iris_df
    fig = px.scatter(iris_select_df, x='sepal_width', y='sepal_length', color='species')
    fig.update_layout(
        title=dict(text='Iris Data Visualization', x=0.5),
        showlegend=True,
        margin=dict(l=20, r=20, t=30, b=20),
        autosize=False, width=1000, height=500
    )
    # fig.show(renderer='browser')
    return fig



if __name__ == '__main__':
    app.run(host='localhost', port=8050)
