import os
import pandas as pd
import dash
from dash import html, dcc, dash_table
from dash.dependencies import Input, Output
import plotly.express as px

# ----------------------------
# 1) Cargar datos (prueba varias rutas típicas)
# ----------------------------
CANDIDATE_PATHS = [
    "data/caldas_data_clean.csv",
    "data/caldas_clean.csv",
    "caldas_data_clean.csv",
    "caldas_clean.csv",
]

csv_path = next((p for p in CANDIDATE_PATHS if os.path.exists(p)), None)
if csv_path is None:
    raise FileNotFoundError(
        "No encontré el CSV. Busqué en: " + ", ".join(CANDIDATE_PATHS)
        + ". Ajusta la ruta en CANDIDATE_PATHS."
    )

df = pd.read_csv(csv_path, low_memory=False)

# ----------------------------
# 2) Auto-detección de columnas
# ----------------------------
def pick_col(candidates):
    """Devuelve la primera columna existente (case-insensitive) cuyo nombre contenga alguno de los candidatos."""
    cols = list(df.columns)
    lower_map = {c.lower(): c for c in cols}
    for cand in candidates:
        for c_lower, c_orig in lower_map.items():
            if cand in c_lower:
                return c_orig
    return None

col_municipio = pick_col(["municipio", "mun", "reside_mun", "estu_mun", "presenta_mun"])
col_estrato   = pick_col(["estrato"])
col_puntaje   = pick_col(["punt_global", "puntaje_global", "global", "punt"])

# Si detectó "punt" pero es ambiguo (ej. punt_matematicas), intenta priorizar global
if col_puntaje and "global" not in col_puntaje.lower():
    col_puntaje2 = pick_col(["punt_global", "puntaje_global"])
    if col_puntaje2:
        col_puntaje = col_puntaje2

# ----------------------------
# 3) App
# ----------------------------
app = dash.Dash(__name__)

def header_badge(label, value):
    return html.Div(
        [
            html.Div(label, style={"fontSize": "12px", "opacity": 0.7}),
            html.Div(str(value), style={"fontSize": "14px", "fontWeight": "600"}),
        ],
        style={
            "padding": "10px 12px",
            "border": "1px solid #e6e6e6",
            "borderRadius": "10px",
            "background": "white",
            "display": "inline-block",
            "marginRight": "10px",
            "marginBottom": "10px",
            "minWidth": "220px",
        },
    )

# Opciones de municipio si existe la columna
if col_municipio:
    municipios = sorted(df[col_municipio].dropna().astype(str).unique().tolist())
    default_mun = municipios[0] if municipios else None
else:
    municipios = []
    default_mun = None

app.layout = html.Div(
    style={"fontFamily": "system-ui, -apple-system, Segoe UI, Roboto, Arial", "padding": "18px", "background": "#f6f7f9"},
    children=[
        html.H2("Dashboard mínimo — Saber 11 Caldas", style={"margin": "0 0 6px 0"}),
        html.Div(
            [
                header_badge("CSV cargado", csv_path),
                header_badge("Filas", df.shape[0]),
                header_badge("Columnas", df.shape[1]),
            ]
        ),

        html.Div(
            style={"padding": "12px", "border": "1px solid #e6e6e6", "borderRadius": "12px", "background": "white"},
            children=[
                html.Div("Columnas detectadas:", style={"fontWeight": "600", "marginBottom": "6px"}),
                html.Ul([
                    html.Li(f"municipio: {col_municipio}"),
                    html.Li(f"estrato: {col_estrato}"),
                    html.Li(f"puntaje: {col_puntaje}"),
                ]),
                html.Div(
                    "Si alguna sale como None, abajo te muestro todas las columnas para que ajustes los nombres.",
                    style={"fontSize": "12px", "opacity": 0.75},
                ),
            ],
        ),

        html.Div(style={"height": "12px"}),

        # Controles
        html.Div(
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px"},
            children=[
                html.Div(
                    style={"padding": "12px", "border": "1px solid #e6e6e6", "borderRadius": "12px", "background": "white"},
                    children=[
                        html.Div("Municipio", style={"fontWeight": "600", "marginBottom": "6px"}),
                        dcc.Dropdown(
                            id="mun_dd",
                            options=[{"label": m, "value": m} for m in municipios],
                            value=default_mun,
                            placeholder="(No detecté municipio — revisa columnas)",
                            clearable=False,
                        ),
                    ],
                ),
                html.Div(
                    style={"padding": "12px", "border": "1px solid #e6e6e6", "borderRadius": "12px", "background": "white"},
                    children=[
                        html.Div("Tipo de gráfico", style={"fontWeight": "600", "marginBottom": "6px"}),
                        dcc.RadioItems(
                            id="chart_type",
                            options=[
                                {"label": "Boxplot por estrato", "value": "box"},
                                {"label": "Promedio por estrato (barras)", "value": "bar"},
                            ],
                            value="box",
                            inline=True,
                        ),
                    ],
                ),
            ],
        ),

        html.Div(style={"height": "12px"}),

        # Gráfico
        html.Div(
            style={"padding": "12px", "border": "1px solid #e6e6e6", "borderRadius": "12px", "background": "white"},
            children=[
                dcc.Graph(id="main_graph"),
            ],
        ),

        html.Div(style={"height": "12px"}),

        # Tabla de columnas y muestra de datos para que ajustes rápido
        html.Div(
            style={"padding": "12px", "border": "1px solid #e6e6e6", "borderRadius": "12px", "background": "white"},
            children=[
                html.Div("Vista rápida (primeras 15 filas)", style={"fontWeight": "600", "marginBottom": "8px"}),
                dash_table.DataTable(
                    data=df.head(15).to_dict("records"),
                    columns=[{"name": c, "id": c} for c in df.columns],
                    page_size=15,
                    style_table={"overflowX": "auto"},
                    style_cell={"fontSize": 12, "padding": "6px", "maxWidth": "240px", "whiteSpace": "normal"},
                ),
            ],
        ),
    ],
)

@app.callback(
    Output("main_graph", "figure"),
    Input("mun_dd", "value"),
    Input("chart_type", "value"),
)
def update_graph(mun_value, chart_type):
    # Si faltan columnas clave, muestra un gráfico vacío con mensaje
    if not (col_puntaje and col_estrato):
        fig = px.scatter(title="No pude detectar columnas clave (puntaje/estrato). Revisa la tabla de columnas abajo.")
        fig.update_layout(height=420)
        return fig

    dff = df.copy()

    # Filtrar municipio si existe
    if col_municipio and mun_value is not None:
        dff = dff[dff[col_municipio].astype(str) == str(mun_value)]

    # Asegura que puntaje sea numérico
    dff[col_puntaje] = pd.to_numeric(dff[col_puntaje], errors="coerce")

    if chart_type == "box":
        fig = px.box(
            dff.dropna(subset=[col_estrato, col_puntaje]),
            x=col_estrato,
            y=col_puntaje,
            points="outliers",
            title=f"Puntaje vs Estrato" + (f" — {mun_value}" if mun_value else ""),
        )
    else:
        agg = (
            dff.dropna(subset=[col_estrato, col_puntaje])
            .groupby(col_estrato, as_index=False)[col_puntaje]
            .mean()
            .sort_values(col_estrato)
        )
        fig = px.bar(
            agg,
            x=col_estrato,
            y=col_puntaje,
            title=f"Promedio de puntaje por estrato" + (f" — {mun_value}" if mun_value else ""),
        )

    fig.update_layout(height=420, margin=dict(l=30, r=20, t=60, b=30))
    return fig

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8051)