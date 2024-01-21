import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go

# 显示可供使用的renders
print(plotly.io.renderers)

fig = go.Figure(
    data=[
        go.Scatter(x=[1, 2, 3, 4, 5], y=[1, 2, 3, 4, 5], mode='lines+markers')
    ],
    layout=go.Layout(title='Test')
)

print(fig)
fig.show(renderer='browser')

iris_df = px.data.iris()
fig = px.scatter(iris_df, x='sepal_width', y='sepal_length', color='species')
fig.show(renderer='browser')
