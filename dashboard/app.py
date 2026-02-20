import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output
import unicodedata

# =======================
# 1) Cargar datos
# =======================
df = pd.read_csv("data/caldas_data_clean.csv")

def limpiar_texto(x):
    if pd.isna(x):
        return x
    x = str(x).strip()
    x = unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode("ascii")
    return x.upper()

# Normalizar municipios
df["cole_mcpio_ubicacion"] = df["cole_mcpio_ubicacion"].apply(limpiar_texto)

# Ordenar estratos
orden_estratos = ["Estrato 1","Estrato 2","Estrato 3","Estrato 4","Estrato 5","Estrato 6"]
if "fami_estratovivienda" in df.columns:
    df["fami_estratovivienda"] = pd.Categorical(
        df["fami_estratovivienda"], categories=orden_estratos, ordered=True
    )

municipios = sorted(df["cole_mcpio_ubicacion"].dropna().unique())
estratos = [e for e in orden_estratos if e in df["fami_estratovivienda"].dropna().unique()]

# =======================
# 2) App
# =======================
app = Dash(__name__, suppress_callback_exceptions=True)
app.title = "Saber 11 - Caldas"


def fig_mensaje(titulo, mensaje):
    """Figura vacía con mensaje centrado (para evitar gráficos en blanco)."""
    fig = go.Figure()
    fig.update_layout(
        template="plotly_white",
        title=titulo,
        annotations=[dict(
            text=mensaje,
            x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False,
            font=dict(size=13, color="gray"),
            align="center"
        )],
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=350,
        margin=dict(l=10, r=10, t=60, b=10),
        font=dict(family="Inter, Arial", size=12),
    )
    return fig


app.layout = html.Div([
    html.H2("Tablero Saber 11 – Caldas"),
    html.P("Explora brechas por estrato, educación de padres, tipo de colegio, zona y género."),

    dcc.Tabs(id="tabs", value="tab1", children=[
        dcc.Tab(label="Pregunta 1: Brechas socioeconómicas", value="tab1"),
        dcc.Tab(label="Pregunta 2: Bajo rendimiento", value="tab2"),
        dcc.Tab(label="Pregunta 3: Brecha de género", value="tab3"),
    ]),
    html.Div(id="contenido-tab"),
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
                    value=municipios,
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

        html.Div([dcc.Graph(id="p1_box")]),
        html.Div([
            html.Div([dcc.Graph(id="p1_heatmap")], style={"flex": "1", "paddingRight": "10px"}),
            html.Div([dcc.Graph(id="p1_brecha_bar")], style={"flex": "1"}),
        ], style={"display": "flex"}),

        html.P(
            "Nota: el lollipop compara promedios de puntaje global por municipio entre grupos de estrato "
            "(Bajo: 1–2, Medio: 3–4, Alto: 5–6).",
            style={"fontSize": "0.9rem", "color": "#444"}
        )
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

    # Normalizar entradas (por si vienen None)
    if not muns_sel:
        muns_sel = municipios
    if isinstance(muns_sel, str):
        muns_sel = [muns_sel]
    if not estr_sel:
        estr_sel = estratos

    d = df[df["cole_mcpio_ubicacion"].isin(muns_sel)].copy()
    d = d[d["fami_estratovivienda"].isin(estr_sel)].copy()

    # Si el filtro deja el dataset vacío, devolvemos mensajes
    if d.empty:
        fig_box = fig_mensaje("Distribución por estrato", "No hay datos con los filtros actuales.")
        fig_heat = fig_mensaje("Estrato vs educación", "No hay datos con los filtros actuales.")
        fig_brecha = fig_mensaje("Brecha por municipio", "No hay datos con los filtros actuales.")
        return fig_box, fig_heat, fig_brecha

    # 1) Boxplot
    fig_box = px.box(
        d, x="fami_estratovivienda", y="punt_global",
        points=False, title="Distribución de puntaje global por estrato"
    )
    fig_box.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=50, b=10),
                          font=dict(family="Inter, Arial", size=12),
                          title=dict(x=0, xanchor="left"))

    # 2) Heatmap
    piv = d.pivot_table(
        index="fami_estratovivienda",
        columns=edu_var,
        values="punt_global",
        aggfunc="mean"
    ).sort_index()

    if piv.empty:
        fig_heat = fig_mensaje("Promedio puntaje global: Estrato vs educación", "No hay combinaciones disponibles con estos filtros.")
    else:
        fig_heat = px.imshow(
            piv, aspect="auto",
            title=f"Promedio puntaje global: Estrato vs {edu_var.replace('fami_', '')}"
        )
        fig_heat.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=50, b=10),
                               font=dict(family="Inter, Arial", size=12),
                               title=dict(x=0, xanchor="left"))

    # 3) Lollipop
    grupo_bajo  = ["Estrato 1", "Estrato 2"]
    grupo_medio = ["Estrato 3", "Estrato 4"]
    grupo_alto  = ["Estrato 5", "Estrato 6"]

    def media_grupo(df_fil, grupos, col_mun="cole_mcpio_ubicacion"):
        sub = df_fil[df_fil["fami_estratovivienda"].isin(grupos)]
        return sub.groupby(col_mun)["punt_global"].agg(["mean", "count"])

    stats_bajo  = media_grupo(d, grupo_bajo)
    stats_medio = media_grupo(d, grupo_medio)
    stats_alto  = media_grupo(d, grupo_alto)

    brecha_df = pd.DataFrame({
        "media_bajo":  stats_bajo["mean"],
        "n_bajo":      stats_bajo["count"],
        "media_medio": stats_medio["mean"],
        "n_medio":     stats_medio["count"],
        "media_alto":  stats_alto["mean"],
        "n_alto":      stats_alto["count"],
    }).reset_index().rename(columns={"cole_mcpio_ubicacion": "municipio"})

    # Necesitamos bajo y alto para el lollipop (medio es opcional)
    brecha_df = brecha_df.dropna(subset=["media_bajo", "media_alto"])

    # min_n adaptativo (NO lo vuelvas a pisar)
    min_n = 1 if len(muns_sel) == 1 else (5 if len(muns_sel) <= 5 else 20)

    brecha_df = brecha_df[(brecha_df["n_bajo"] >= min_n) & (brecha_df["n_alto"] >= min_n)]

    if brecha_df.empty:
        fig_brecha = fig_mensaje(
            "Brecha por municipio (lollipop)",
            f"No hay datos suficientes para Bajo (E1–E2) y Alto (E5–E6) con min n={min_n}.<br>"
            "Tip: incluye estratos 5–6 o selecciona más municipios / amplía filtros."
        )
        return fig_box, fig_heat, fig_brecha

    # ordenar por brecha
    brecha_df["brecha"] = brecha_df["media_alto"] - brecha_df["media_bajo"]
    brecha_df = brecha_df.sort_values("brecha", ascending=True)

    fig_brecha = go.Figure()

    # líneas
    for _, row in brecha_df.iterrows():
        puntos = [row["media_bajo"]]
        if not pd.isna(row["media_medio"]):
            puntos.append(row["media_medio"])
        puntos.append(row["media_alto"])

        fig_brecha.add_trace(go.Scatter(
            x=puntos,
            y=[row["municipio"]] * len(puntos),
            mode="lines",
            line=dict(color="#c0d0e0", width=2.5),
            showlegend=False,
            hoverinfo="skip",
        ))

    # Bajo
    fig_brecha.add_trace(go.Scatter(
        x=brecha_df["media_bajo"],
        y=brecha_df["municipio"],
        mode="markers",
        name="Bajo (E1–E2)",
        marker=dict(color="#e05c5c", size=13, line=dict(color="white", width=1.5)),
        customdata=np.stack([brecha_df["n_bajo"], brecha_df["media_bajo"].round(1)], axis=1),
        hovertemplate="<b>%{y}</b><br>Bajo (E1–E2)<br>Media: %{customdata[1]}<br>n: %{customdata[0]}<extra></extra>",
    ))

    # Medio (si es NaN, Plotly no dibuja el punto)
    fig_brecha.add_trace(go.Scatter(
        x=brecha_df["media_medio"],
        y=brecha_df["municipio"],
        mode="markers",
        name="Medio (E3–E4)",
        marker=dict(color="#d4c034", size=10, line=dict(color="white", width=1.5)),
        customdata=np.stack([
            brecha_df["n_medio"].fillna(0).astype(int),
            brecha_df["media_medio"].round(1).fillna(np.nan)
        ], axis=1),
        hovertemplate="<b>%{y}</b><br>Medio (E3–E4)<br>Media: %{customdata[1]}<br>n: %{customdata[0]}<extra></extra>",
    ))

    # Alto (SIN delta)
    fig_brecha.add_trace(go.Scatter(
        x=brecha_df["media_alto"],
        y=brecha_df["municipio"],
        mode="markers",
        name="Alto (E5–E6)",
        marker=dict(color="#1f4e79", size=13, line=dict(color="white", width=1.5)),
        customdata=np.stack([brecha_df["n_alto"], brecha_df["media_alto"].round(1)], axis=1),
        hovertemplate="<b>%{y}</b><br>Alto (E5–E6)<br>Media: %{customdata[1]}<br>n: %{customdata[0]}<extra></extra>",
    ))

    fig_brecha.update_layout(
        title=dict(
            text=f"Brecha por municipio (lollipop): Bajo (E1–E2), Medio (E3–E4), Alto (E5–E6) | min n={min_n}",
            x=0, xanchor="left"
        ),
        template="plotly_white",
        font=dict(family="Inter, Arial", size=12),
        margin=dict(l=10, r=20, t=60, b=10),
        xaxis_title="Promedio puntaje global",
        yaxis_title="",
        legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="left", x=0),
        height=max(380, len(brecha_df) * 28 + 120),
    )

    return fig_box, fig_heat, fig_brecha


if __name__ == "__main__":
    app.run(debug=True)