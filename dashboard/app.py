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

    # 3) Brecha por municipio — Lollipop: grupo bajo vs grupo alto
    grupo_bajo = ["Estrato 1", "Estrato 2"]
    grupo_medio = ["Estrato 3", "Estrato 4"]
    grupo_alto = ["Estrato 5", "Estrato 6"]

    def media_grupo(df_fil, grupos, col_mun="cole_mcpio_ubicacion"):
        sub = df_fil[df_fil["fami_estratovivienda"].isin(grupos)]
        return sub.groupby(col_mun)["punt_global"].agg(["mean", "count"])

    stats_bajo  = media_grupo(d, grupo_bajo)
    stats_medio = media_grupo(d, grupo_medio)
    stats_alto  = media_grupo(d, grupo_alto)

    # Unir en un DataFrame por municipio
    brecha_df = pd.DataFrame({
        "media_bajo":  stats_bajo["mean"],
        "n_bajo":      stats_bajo["count"],
        "media_medio": stats_medio["mean"],
        "n_medio":     stats_medio["count"],
        "media_alto":  stats_alto["mean"],
        "n_alto":      stats_alto["count"],
    }).dropna(subset=["media_bajo", "media_alto"]).reset_index()
    brecha_df = brecha_df.rename(columns={"cole_mcpio_ubicacion": "municipio"})
    # Si el usuario selecciona 1 municipio, no usamos un filtro tan estricto
    if isinstance(muns_sel, str):
        muns_sel = [muns_sel]

    min_n = 1 if len(muns_sel) == 1 else 20

    brecha_df = brecha_df[
        (brecha_df["n_bajo"] >= min_n) & (brecha_df["n_alto"] >= min_n)
    ]
    # Filtro mínimo de muestra en bajo y alto
    min_n = 20
    brecha_df = brecha_df[
        (brecha_df["n_bajo"] >= min_n) & (brecha_df["n_alto"] >= min_n)
    ]

    # Brecha = alto - bajo, ordenar
    brecha_df["brecha"] = brecha_df["media_alto"] - brecha_df["media_bajo"]
    brecha_df = brecha_df.sort_values("brecha", ascending=True)  # ascending=True para que mayor quede arriba en horizontal

    import plotly.graph_objects as go

    fig_brecha = go.Figure()

    # ── Línea de rango bajo–alto por municipio ──────────────────────────────
    for _, row in brecha_df.iterrows():
        puntos_x = [row["media_bajo"], row["media_alto"]]
        tiene_medio = not pd.isna(row["media_medio"])
        if tiene_medio:
            puntos_x_linea = [row["media_bajo"], row["media_medio"], row["media_alto"]]
        else:
            puntos_x_linea = [row["media_bajo"], row["media_alto"]]

        fig_brecha.add_trace(go.Scatter(
            x=puntos_x_linea,
            y=[row["municipio"]] * len(puntos_x_linea),
            mode="lines",
            line=dict(color="#c0d0e0", width=2.5),
            showlegend=False,
            hoverinfo="skip",
        ))

    # ── Punto grupo BAJO (E1–E2) ────────────────────────────────────────────
    fig_brecha.add_trace(go.Scatter(
        x=brecha_df["media_bajo"],
        y=brecha_df["municipio"],
        mode="markers",
        name="Bajo (E1–E2)",
        marker=dict(color="#e05c5c", size=13, line=dict(color="white", width=1.5)),
        customdata=np.stack([
            brecha_df["n_bajo"],
            brecha_df["media_bajo"].round(1)
        ], axis=1),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Grupo bajo (E1–E2)<br>"
            "Media: %{customdata[1]}<br>"
            "n: %{customdata[0]}<extra></extra>"
        ),
    ))

    # ── Punto grupo MEDIO (E3–E4) ───────────────────────────────────────────
    fig_brecha.add_trace(go.Scatter(
        x=brecha_df["media_medio"],
        y=brecha_df["municipio"],
        mode="markers",
        name="Medio (E3–E4)",
        marker=dict(color="#d4c034", size=10, line=dict(color="white", width=1.5)),
        customdata=np.stack([
            brecha_df["n_medio"].fillna(0).astype(int),
            brecha_df["media_medio"].round(1)
        ], axis=1),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Grupo medio (E3–E4)<br>"
            "Media: %{customdata[1]}<br>"
            "n: %{customdata[0]}<extra></extra>"
        ),
    ))

    # ── Punto grupo ALTO (E5–E6) ────────────────────────────────────────────
    fig_brecha.add_trace(go.Scatter(
        x=brecha_df["media_alto"],
        y=brecha_df["municipio"],
        mode="markers",
        name="Alto (E5–E6)",
        marker=dict(color="#7c6fcd", size=13, line=dict(color="white", width=1.5)),
        customdata=np.stack([
            brecha_df["n_alto"],
            brecha_df["media_alto"].round(1),
            brecha_df["brecha"].round(1),
        ], axis=1),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Grupo alto (E5–E6)<br>"
            "Media: %{customdata[1]}<br>"
            "n: %{customdata[0]}<br>"
            
        ),
    ))

    

    fig_brecha.update_layout(
    title=dict(
        text="Brecha por municipio: Alto (E5–E6) vs Bajo (E1–E2)",
        font=dict(size=14),
        x=0,
        xanchor="left",
    ),                          # ← cierra title=dict() aquí ✓
    template="plotly_white",
    font=dict(family="Inter, Arial", size=12),
    margin=dict(l=10, r=60, t=50, b=10),
    xaxis_title="Promedio puntaje global",
    yaxis_title="",
    legend=dict(
        orientation="h",
        yanchor="top",
        y=-0.15,
        xanchor="left",
        x=0
    ),
    
    height=max(350, len(brecha_df) * 28 + 80),
)                               
    return fig_box, fig_heat, fig_brecha


if __name__ == "__main__":
    app.run(debug=True)