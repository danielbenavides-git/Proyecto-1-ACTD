import dash
from dash import html

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Dashboard Saber 11 - Caldas"),
    html.P("Tablero en construcción.")
])

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)