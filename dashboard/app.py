import pandas as pd
import numpy as np
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import unicodedata
# =======================
# 1) Cargar datos
# =======================
df = pd.read_csv("data/caldas_data_clean.csv")
def limpiar_texto(x):
    if pd.isna(x):
        return x
    x = str(x).strip()  # quitar espacios
    x = unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode("ascii")  # quitar tildes
    return x.upper()

df["cole_mcpio_ubicacion"] = df["cole_mcpio_ubicacion"].apply(limpiar_texto)
# (opcional) ordenar estratos para que no queden raros
orden_estratos = ["Estrato 1","Estrato 2","Estrato 3","Estrato 4","Estrato 5","Estrato 6"]
if "fami_estratovivienda" in df.columns:
    df["fami_estratovivienda"] = pd.Categorical(df["fami_estratovivienda"], categories=orden_estratos, ordered=True)

municipios = sorted(df["cole_mcpio_ubicacion"].dropna().unique())
estratos = [e for e in orden_estratos if e in df["fami_estratovivienda"].dropna().unique()]

# =======================
# 2) App
# =======================
app = Dash(__name__, suppress_callback_exceptions=True)
app.title = "Saber 11 - Caldas"

app.layout = html.Div([
    html.H2("Tablero Saber 11 – Caldas"),
    html.P("Explora brechas por estrato, educación de padres, tipo de colegio, zona y género."),

    # Tabs con id="tabs"
    dcc.Tabs(id="tabs", value="tab1", children=[
        dcc.Tab(label="Pregunta 1: Brechas socioeconómicas", value="tab1"),
        dcc.Tab(label="Pregunta 2: Bajo rendimiento", value="tab2"),
        dcc.Tab(label="Pregunta 3: Brecha de género", value="tab3"),
        ]),


    html.Div(id="contenido-tab")
], style={"maxWidth": "1200px", "margin": "0 auto", "padding": "10px"})


# =======================
# 3) Layout Tab 1
# =======================
def layout_tab1():
    return html.Div([
        html.H3("P1. Desempeño vs Estrato y educación de padres (Caldas)"),

        html.Div([
            html.Div([
                html.Label("Municipios"),
                dcc.Dropdown(
                    options=[{"label": m, "value": m} for m in municipios],
                    value=municipios,  # default: todos
                    multi=True,
                    id="p1_municipios"
                ),
            ], style={"flex": "2", "paddingRight": "10px"}),

            html.Div([
                html.Label("Variable educación"),
                dcc.RadioItems(
                    options=[
                        {"label": "Educación madre", "value": "fami_educacionmadre"},
                        {"label": "Educación padre", "value": "fami_educacionpadre"},
                    ],
                    value="fami_educacionmadre",
                    id="p1_edu_var",
                    inline=True
                ),
                html.Br(),
                html.Label("Estratos a comparar"),
                dcc.Dropdown(
                    options=[{"label": e, "value": e} for e in estratos],
                    value=estratos,
                    multi=True,
                    id="p1_estratos"
                ),
            ], style={"flex": "1"}),
        ], style={"display": "flex", "marginBottom": "15px"}),

        html.Div([
            dcc.Graph(id="p1_box"),
        ]),

        html.Div([
            html.Div([dcc.Graph(id="p1_heatmap")], style={"flex": "1", "paddingRight": "10px"}),
            html.Div([dcc.Graph(id="p1_brecha_bar")], style={"flex": "1"}),
        ], style={"display": "flex"}),

        html.P("Nota: la gráfica de brechas por municipio muestra (promedio estrato alto – promedio estrato bajo). "
               "Luego la convertimos a mapa cuando tengamos el GeoJSON de municipios de Caldas.",
               style={"fontSize": "0.9rem", "color": "#444"})
    ])


# =======================
# 4) Router Tabs
# =======================
@app.callback(Output("contenido-tab", "children"), Input("tabs", "value"))
def render_tab(tab):
    if tab == "tab1":
        return layout_tab1()
    if tab == "tab2":
        return html.Div([html.H3("Tab 2 (pendiente)"), html.P("Aquí va el mapa + explicaciones oficial/privado y rural/urbano.")])
    return html.Div([html.H3("Tab 3 (pendiente)"), html.P("Aquí va la brecha por género en matemáticas vs lectura crítica.")])

# OJO: falta asignar id="tabs" al componente Tabs:
# En el layout arriba, cambia dcc.Tabs(...) por dcc.Tabs(id="tabs", ...)

# =======================
# 5) Callbacks Tab 1
# =======================
@app.callback(
    Output("p1_box", "figure"),
    Output("p1_heatmap", "figure"),
    Output("p1_brecha_bar", "figure"),
    Input("p1_municipios", "value"),
    Input("p1_edu_var", "value"),
    Input("p1_estratos", "value"),
)
def actualizar_tab1(muns_sel, edu_var, estr_sel):
    d = df[df["cole_mcpio_ubicacion"].isin(muns_sel)].copy()
    d = d[d["fami_estratovivienda"].isin(estr_sel)].copy()

    # 1) Boxplot punt_global vs estrato
    fig_box = px.box(
        d,
        x="fami_estratovivienda",
        y="punt_global",
        points=False,
        title="Distribución de puntaje global por estrato"
    )
    fig_box.update_layout(margin=dict(l=10, r=10, t=50, b=10))

    # 2) Heatmap estrato x educación (promedio punt_global)
    piv = (
        d.pivot_table(
            index="fami_estratovivienda",
            columns=edu_var,
            values="punt_global",
            aggfunc="mean"
        )
        .sort_index()
    )

    fig_heat = px.imshow(
        piv,
        aspect="auto",
        title=f"Promedio puntaje global: Estrato vs {edu_var.replace('fami_', '')}"
    )
    fig_heat.update_layout(margin=dict(l=10, r=10, t=50, b=10))

    # 3) Brecha por municipio (estrato alto - estrato bajo)
    # definimos “bajo” como Estrato 1 si existe, si no el mínimo; “alto” como el máximo disponible
    estratos_disp = [e for e in orden_estratos if e in d["fami_estratovivienda"].dropna().unique()]
    if len(estratos_disp) >= 2:
        estr_bajo = estratos_disp[0]
        estr_alto = estratos_disp[-1]
    else:
        estr_bajo, estr_alto = None, None

    if estr_bajo and estr_alto:
        low = d[d["fami_estratovivienda"] == estr_bajo].groupby("cole_mcpio_ubicacion")["punt_global"].mean()
        high = d[d["fami_estratovivienda"] == estr_alto].groupby("cole_mcpio_ubicacion")["punt_global"].mean()
        brecha = (high - low).dropna().sort_values(ascending=False).reset_index()
        brecha.columns = ["municipio", "brecha"]
        titulo = f"Brecha por municipio: {estr_alto} – {estr_bajo} (promedio puntaje global)"
    else:
        brecha = pd.DataFrame({"municipio": [], "brecha": []})
        titulo = "Brecha por municipio (no hay suficientes estratos en selección)"

    fig_brecha = px.bar(
        brecha.head(15),
        x="brecha",
        y="municipio",
        orientation="h",
        title=titulo
    )
    fig_brecha.update_layout(margin=dict(l=10, r=10, t=50, b=10))

    return fig_box, fig_heat, fig_brecha


if __name__ == "__main__":
    app.run(debug=True)