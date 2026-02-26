import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output
import unicodedata
import json
import os
# =======================
# 1) Cargar datos
# =======================
# Ruta base = carpeta donde está app.py (dashboard/)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Usar rutas absolutas
df = pd.read_csv(os.path.join(BASE_DIR, "data", "caldas_data_clean.csv"))

with open(os.path.join(BASE_DIR, "data", "caldas_municipios.geojson"), "r", encoding="utf-8") as f:
    geo_muns = json.load(f)
print(df["estu_genero"].unique())
print(df["estu_genero"].value_counts())

##revisemos las coordenadas
def geo_bounds(geo):
    xs, ys = [], []
    for ft in geo["features"]:
        geom = ft["geometry"]
        if geom is None:
            continue
        coords_list = []
        if geom["type"] == "Polygon":
            coords_list = geom["coordinates"]
        elif geom["type"] == "MultiPolygon":
            # lista de polígonos, cada uno con anillos
            for poly in geom["coordinates"]:
                coords_list += poly

        for ring in coords_list:
            for x, y in ring:
                xs.append(x); ys.append(y)
    return (min(xs), max(xs), min(ys), max(ys))

mnx, mxx, mny, mxy = geo_bounds(geo_muns)
print("BOUNDS X:", mnx, mxx)
print("BOUNDS Y:", mny, mxy)
# --- Normalizar nombres en GeoJSON para que coincidan con el CSV ---
def norm_mun(x):
    if x is None:
        return None
    x = str(x).strip()
    x = unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode("ascii")
    return x.upper()
# Normalizar municipios en GeoJSON (crear llave estándar)
for f in geo_muns["features"]:
    f["properties"]["MUN_NORM"] = norm_mun(f["properties"].get("MUN_NORM") or f["properties"].get("MPIO_CNMBR"))
# 1) Identificar el campo de nombre del municipio dentro del GeoJSON
#    (si no sabes cuál es, imprime las llaves)
print(geo_muns["features"][0]["properties"])

# 2) CAMBIA ESTA VARIABLE si el nombre de la llave es distinto
GEO_MUN_KEY = "MPIO_CNMBR"   # <- si en el print sale otro, cámbialo aquí


def limpiar_texto(x):
    if pd.isna(x):
        return x
    x = str(x).strip()
    x = unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode("ascii")
    return x.upper()

# Normalizar municipios
df["cole_mcpio_ubicacion"] = df["cole_mcpio_ubicacion"].apply(limpiar_texto)

#geo_names = {f["properties"]["MUN_NORM"] for f in geo_muns["features"]}
#df_names  = set(df["cole_mcpio_ubicacion"].dropna().unique())

#print("Coincidencias:", len(df_names & geo_names))
#print("En DF pero no en GeoJSON:", sorted(df_names - geo_names))
#print("En GeoJSON pero no en DF:", sorted(geo_names - df_names))

geo_names_check = {f["properties"]["MUN_NORM"] for f in geo_muns["features"]}
df_names_check = set(df["cole_mcpio_ubicacion"].dropna().unique())
print("Matches:", len(df_names_check & geo_names_check))
print("Sin match en GeoJSON:", df_names_check - geo_names_check)

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
    html.Div([
        html.Img(
            src="/assets/logo-uniandes.png",
            style={
                "height": "60px",
                "marginRight": "15px"
        }
    ),
    html.H2(
        "Tablero Saber 11 – Caldas",
        style={"margin": "0"}
    )
    ], style={
        "display": "flex",
        "alignItems": "center",
        "marginBottom": "15px",
        "borderBottom": "2px solid #e0e0e0",
        "paddingBottom": "10px"
    }),
    html.P("Explora brechas por estrato, educación de padres, tipo de colegio, zona y género."),

    dcc.Tabs(id="tabs", value="tab1", children=[
        dcc.Tab(label="Pregunta 1: Brechas socioeconómicas", value="tab1"),
        dcc.Tab(label="Pregunta 2: Bajo rendimiento", value="tab2"),
        dcc.Tab(label="Pregunta 3: Brecha de género", value="tab3"),
    ]),
    html.Div(id="contenido-tab"),
], style={"maxWidth": "1200px", "margin": "0 auto", "padding": "10px", "fontFamily": "Arial"})


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

            html.Div([
                dcc.Graph(id="p1_brecha_bar"),

                html.Div(
                    "Esta gráfica muestra el promedio del puntaje global por municipio en tres grupos socioeconómicos: "
                    "bajo (estratos 1–2), medio (3–4) y alto (5–6). "
                    "La distancia entre los puntos bajo y alto refleja la brecha socioeconómica en desempeño académico. "
                    "Solo se incluyen municipios con tamaño de muestra suficiente en los grupos comparados.",
                    style={
                        "fontSize": "0.85rem",
                        "color": "#555",
                        "marginTop": "10px",
                        "lineHeight": "1.5",
                        "textAlign": "justify",
                    }
                )

            ], style={"flex": "1"}),

        ], style={"display": "flex"}),

        
    ])

# layout de 2
def layout_tab2():
    return html.Div([
        html.H3("P2. Municipios con bajo rendimiento y factores asociados"),

        html.Div([
            # Métrica del mapa
            html.Div([
                html.Label("Métrica para el mapa"),
                dcc.Dropdown(
                    id="p2_metric",
                    options=[
                        {"label": "Promedio puntaje global",    "value": "avg"},
                        {"label": "% con puntaje global < umbral", "value": "pct_low"},
                    ],
                    value="avg",
                    clearable=False,
                ),
            ], style={"flex": "1", "paddingRight": "15px"}),

            # Umbral (solo activo si métrica = pct_low)
            html.Div([
                html.Label("Umbral bajo desempeño (solo aplica al %)"),
                dcc.Slider(
                    id="p2_threshold",
                    min=200, max=300, step=5, value=250,
                    marks={200: "200", 225: "225", 250: "250", 275: "275", 300: "300"},
                ),
            ], style={"flex": "2"}),
        ], style={"display": "flex", "marginBottom": "15px", "alignItems": "flex-end"}),
                # Mapa
        dcc.Graph(id="p2_map"),

        # Nota dinámica debajo del mapa
        html.Div(id="p2_note", style={"fontSize": "0.85rem", "color": "#555", "marginTop": "6px"}),

        # Hint de click
        html.P(
            "💡 Haz clic en un municipio del mapa para ver su desagregación por tipo de colegio y zona en la gráfica de barras de la parte inferior.",
            style={"fontSize": "0.82rem", "color": "#888", "marginTop": "4px"}
        ),
                # NUEVO GRAFICOOOOO
        html.Hr(style={"margin": "24px 0", "borderColor": "#e0e0e0"}),

        html.Div([
            html.Label("Variable de desigualdad interna",
                       style={"fontWeight": "600", "marginBottom": "6px", "display": "block"}),
            dcc.RadioItems(
                id="p2_scatter_modo",
                options=[
                    {"label": "Público vs Privado", "value": "oficial"},
                    {"label": "Rural vs Urbano",    "value": "zona"},
                ],
                value="oficial",
                inline=True,
                style={"marginBottom": "10px"}
            ),
            dcc.Graph(id="p2_scatter"),
            html.Div(
                "Eje X: promedio general del municipio. "
                "Eje Y: diferencia de puntaje entre privado y oficial (o urbano y rural). "
                "Los puntos rojos son los municipios con bajo rendimiento general.",
                style={"fontSize": "0.82rem", "color": "#555",
                       "marginTop": "8px", "lineHeight": "1.5"}
            ),
        ], style={"background": "#f9f9f9", "borderRadius": "10px",
                  "padding": "16px", "border": "1px solid #e0e0e0"}),
        # FIN DEL GRAFICO
        html.Div(id="p2_mun_seleccionado", style={
        "background": "#eef4fb",
        "borderLeft": "4px solid #1a3a5c",
        "padding": "10px 16px",
        "borderRadius": "0 8px 8px 0",
        "fontSize": "0.88rem",
        "color": "#1a3a5c",
        "fontWeight": "600",
        "marginBottom": "10px",
        "marginTop": "16px",
        }),

        # Gráficas de detalle (se actualizan al hacer click)
        html.Div([
            html.Div([dcc.Graph(id="p2_official_private")], style={"flex": "1", "paddingRight": "10px"}),
            html.Div([dcc.Graph(id="p2_rural_urban")],      style={"flex": "1"}),
        ], style={"display": "flex", "marginTop": "10px"}),
    ])
# layout de 3
def layout_tab3():
    return html.Div([
        html.H3("P3. Brecha de género en Matemáticas y Lectura Crítica (Caldas)"),

        # Violin arriba completo
        html.Div([dcc.Graph(id="p3_violin")]),

        # Dot plot + texto descriptivo abajo
        html.Div([
            html.Div([dcc.Graph(id="p3_dotplot")], style={"flex": "2"}),

            html.Div([
                html.H4("¿Qué muestra esta gráfica?",
                        style={"color": "#1a3a5c", "marginBottom": "10px"}),
                html.P(
                    "Cada fila representa un municipio de Caldas. "
                    "Los puntos muestran la diferencia de puntaje promedio entre hombres y mujeres "
                    "en cada materia (Hombres − Mujeres).",
                    style={"fontSize": "0.85rem", "lineHeight": "1.6", "color": "#444"}
                ),
                html.Br(),
                html.P(
                    "- Puntos a la derecha del cero → hombres obtienen mayor puntaje.",
                    style={"fontSize": "0.85rem", "lineHeight": "1.6", "color": "#444"}
                ),
                html.P(
                    "- Puntos a la izquierda del cero → mujeres obtienen mayor puntaje.",
                    style={"fontSize": "0.85rem", "lineHeight": "1.6", "color": "#444"}
                ),
                html.Br(),
                html.P(
                    "- Hallazgo clave: la brecha masculina en Matemáticas es consistente "
                    "en todos los municipios. En Lectura Crítica el patrón es más mixto.",
                    style={"fontSize": "0.85rem", "lineHeight": "1.6",
                           "color": "#1a3a5c", "fontWeight": "600"}
                ),
                html.Br(),
                html.P(
                    "La magnitud de la brecha es pequeña (1–5 puntos) lo que indica que "
                    "a nivel de promedio, ambos géneros rinden de forma similar en Caldas, "
                    "pero el patrón es sistemático.",
                    style={"fontSize": "0.83rem", "lineHeight": "1.6",
                           "color": "#666", "fontStyle": "italic"}
                ),
            ], style={
                "flex": "1",
                "paddingLeft": "24px",
                "paddingTop": "40px",
                "borderLeft": "3px solid #e0e0e0",
                "marginLeft": "10px",
            }),

        ], style={"display": "flex", "marginTop": "20px", "alignItems": "flex-start"}),
    ])
# =======================
# 4) Router Tabs
# =======================
@app.callback(Output("contenido-tab", "children"), Input("tabs", "value"))
def render_tab(tab):
    if tab == "tab1":
        return layout_tab1()
    if tab == "tab2":
        return layout_tab2()
    if tab == "tab3":
        return layout_tab3()
    


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

    #  FORZAR ORDEN EN EL EJE (esto es lo que lo arregla SIEMPRE)
    fig_box.update_xaxes(
        type="category",
        categoryorder="array",
        categoryarray=orden_estratos
    )
    fig_box.update_layout(
        template="plotly_white",
        margin=dict(l=10, r=10, t=50, b=10),
        font=dict(family="Arial", size=12),
        title=dict(x=0, xanchor="left"),
        xaxis_title="Estrato socioeconómico",
        yaxis_title="Puntaje global (Saber 11)",
    )
    
    # 2) Heatmap

    orden_edu = [
    "Ninguno",
    "Primaria incompleta",
    "Primaria completa",
    "Secundaria (Bachillerato) incompleta",
    "Secundaria (Bachillerato) completa",
    "Técnica o tecnológica incompleta",
    "Técnica o tecnológica completa",
    "Educación profesional incompleta",
    "Educación profesional completa",
    "Postgrado",
    "No sabe",
    "No aplica",
    ]

    piv = d.pivot_table(
    index="fami_estratovivienda",
    columns=edu_var,
    values="punt_global",
    aggfunc="mean"
    ).sort_index()

# ← NUEVO: filtrar y reordenar solo las columnas que existen en los datos
    cols_ordenadas = [c for c in orden_edu if c in piv.columns]
    piv = piv[cols_ordenadas]


    if piv.empty:
        fig_heat = fig_mensaje("Promedio puntaje global: Estrato vs educación", "No hay combinaciones disponibles con estos filtros.")
    else:
        fig_heat = px.imshow(
            piv, aspect="auto",
            title=f"Promedio puntaje global: Estrato vs {edu_var.replace('fami_', '')}"
        )
        fig_heat.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=50, b=10),
                               font=dict(family="Inter, Arial", size=12),
                               title=dict(x=0, xanchor="left"),
                               xaxis_title="Nivel educativo de la madre",
                                yaxis_title="Estrato socioeconómico",
                                )

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
            "Brecha por municipio",
            f"No hay datos suficientes para Bajo (E1–E2) y Alto (E5–E6)"
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
            text=f"Brecha por municipio: Bajo (E1–E2), Medio (E3–E4), Alto (E5–E6)",
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


from dash import State

# =======================
# 5b) Callback Tab 2
# =======================
@app.callback(
    Output("p2_map",            "figure"),
    Output("p2_official_private","figure"),
    Output("p2_rural_urban",    "figure"),
    Output("p2_note",           "children"),
    Output("p2_mun_seleccionado", "children"),
    Input("p2_metric",    "value"),
    Input("p2_threshold", "value"),
    Input("p2_map",       "clickData"),
)
def actualizar_tab2(metric, thr, clickData):

    d = df.copy()

    # ── Métrica agregada por municipio ──────────────────────────────────────
    if metric == "avg":
        agg = d.groupby("cole_mcpio_ubicacion")["punt_global"].mean().reset_index(name="value")
        agg["value"] = agg["value"].round(1)
        color_label = "Promedio"
        titulo_mapa = "Promedio puntaje global por municipio (Caldas)"
        nota = "Mapa coloreado por promedio de puntaje global Saber 11. Haz clic en un municipio para ver detalle."
    else:
        d["_low"] = (d["punt_global"] < thr).astype(int)
        agg = d.groupby("cole_mcpio_ubicacion")["_low"].mean().reset_index(name="value")
        agg["value"] = (agg["value"] * 100).round(1)
        color_label = f"% < {thr}"
        titulo_mapa = f"% estudiantes con puntaje global < {thr} por municipio (Caldas)"
        nota = f"Mapa coloreado por porcentaje de estudiantes con puntaje menor a {thr}."

    # ── Mapa coroplético ────────────────────────────────────────────────────
    fig_map = px.choropleth_mapbox(
    agg,
    geojson=geo_muns,
    locations="cole_mcpio_ubicacion",
    featureidkey="properties.MUN_NORM",
    color="value",
    color_continuous_scale="Blues" if metric == "avg" else "Reds",
    labels={"value": color_label},
    title=titulo_mapa,
    hover_name="cole_mcpio_ubicacion",
    hover_data={"cole_mcpio_ubicacion": False, "value": True},
    mapbox_style="carto-positron",   # mapa base sin token
    center={"lat": 5.3, "lon": -75.3},
    zoom=7,
    opacity=0.75,
    )
    fig_map.update_layout(
    template="plotly_white",
    margin=dict(l=0, r=0, t=60, b=10),
    font=dict(family="Arial", size=12),
    title=dict(x=0, xanchor="left"),
    height=480,
    coloraxis_colorbar=dict(title=color_label, thickness=14, len=0.6),
    )

    # ── Municipio seleccionado vía click (default: el de mayor/menor valor) ─
    if clickData and "points" in clickData and clickData["points"]:
        pt = clickData["points"][0]
        # px.choropleth devuelve el municipio en "location"
        mun_sel = pt.get("location") or pt.get("hovertext")
    else:
        # Default: municipio con mayor valor de la métrica
        mun_sel = agg.sort_values("value", ascending=(metric != "avg"))["cole_mcpio_ubicacion"].iloc[0]

    dm = d[d["cole_mcpio_ubicacion"] == mun_sel].copy()

    col_nat  = "cole_naturaleza"       # Público / Privado
    col_area = "cole_area_ubicacion"   # URBANO / RURAL

    # ── Barras: Oficial vs Privado ──────────────────────────────────────────
    if col_nat in dm.columns and not dm.empty:
        nat = (
            dm.groupby(col_nat)["punt_global"]
            .agg(["mean", "count"])
            .reset_index()
            .rename(columns={"mean": "Promedio", "count": "n"})
        )
        nat["Promedio"] = nat["Promedio"].round(1)
        fig_nat = px.bar(
            nat, x=col_nat, y="Promedio",
            text="Promedio",
            color=col_nat,
            color_discrete_sequence=["#4878CF", "#E05C5C"],
            title=f"Promedio por naturaleza del colegio",
            labels={col_nat: "Naturaleza", "Promedio": "Puntaje global promedio"},
        )
        fig_nat.update_traces(textposition="outside")
        fig_nat.update_layout(
            template="plotly_white",
            showlegend=False,
            margin=dict(l=10, r=10, t=60, b=10),
            font=dict(family="Arial", size=12),
            title=dict(x=0, xanchor="left"),
            yaxis=dict(range=[0, nat["Promedio"].max() * 1.15]),
        )
    else:
        fig_nat = fig_mensaje(
            f"{mun_sel}: naturaleza del colegio",
            "No hay datos suficientes o la columna no existe."
        )

    # ── Barras: Rural vs Urbano ─────────────────────────────────────────────
    if col_area in dm.columns and not dm.empty:
        area = (
            dm.groupby(col_area)["punt_global"]
            .agg(["mean", "count"])
            .reset_index()
            .rename(columns={"mean": "Promedio", "count": "n"})
        )
        area["Promedio"] = area["Promedio"].round(1)
        area[col_area] = area[col_area].str.capitalize()
        fig_area = px.bar(
            area, x=col_area, y="Promedio",
            text="Promedio",
            color=col_area,
            color_discrete_sequence=["#5abe7a", "#d4c034"],
            title=f"Promedio por zona (rural / urbana)",
            labels={col_area: "Zona", "Promedio": "Puntaje global promedio"},
        )
        fig_area.update_traces(textposition="outside")
        fig_area.update_layout(
            template="plotly_white",
            showlegend=False,
            margin=dict(l=10, r=10, t=60, b=10),
            font=dict(family="Arial", size=12),
            title=dict(x=0, xanchor="left"),
            yaxis=dict(range=[0, area["Promedio"].max() * 1.15]),
        )
    else:
        fig_area = fig_mensaje(
            f"{mun_sel}: zona del colegio",
            "No hay datos suficientes o la columna no existe."
        )
    # ← NUEVO mensaje
    if clickData and clickData["points"]:
        msg = f"📍 Municipio seleccionado: {mun_sel}"
    else:
        msg = f"📍 Mostrando por defecto: {mun_sel} — haz clic en el mapa para cambiar"

    return fig_map, fig_nat, fig_area, nota, msg

#--------------------------
# Callback para scatter plot
#--------------------------
@app.callback(
    Output("p2_scatter", "figure"),
    Input("p2_scatter_modo", "value"),
)
def actualizar_scatter(modo):
    d = df.copy()
    col_nat  = "cole_naturaleza"
    col_area = "cole_area_ubicacion"

    prom_general = (
        d.groupby("cole_mcpio_ubicacion")["punt_global"]
        .mean()
        .reset_index(name="prom_general")
    )

    if modo == "oficial":
        prom_tipo = (
            d.groupby(["cole_mcpio_ubicacion", col_nat])["punt_global"]
            .mean().unstack(col_nat).reset_index()
        )
        col_of   = [c for c in prom_tipo.columns if str(c) == "Público"]
        col_priv = [c for c in prom_tipo.columns if str(c) == "Privado"]

        if not col_of or not col_priv:
            return fig_mensaje("Scatter desigualdad", f"Columnas no encontradas: {list(prom_tipo.columns)}")

        prom_tipo["brecha"]        = prom_tipo[col_priv[0]] - prom_tipo[col_of[0]]
        prom_tipo["tiene_privado"] = prom_tipo[col_priv[0]].notna()
        etiqueta_y = "Diferencia Privado − Público (puntos)"

        scatter_df = prom_general.merge(
            prom_tipo[["cole_mcpio_ubicacion", "brecha", "tiene_privado"]],
            on="cole_mcpio_ubicacion", how="left"
        )
        scatter_df["brecha"] = scatter_df["brecha"].fillna(0)

        # ← UMBRAL aquí, antes de usarlo
        UMBRAL_BAJO = scatter_df["prom_general"].quantile(0.33)

        scatter_df["color"] = scatter_df.apply(
            lambda r: "Sin colegio privado" if not r["tiene_privado"]
            else ("Bajo rendimiento" if r["prom_general"] <= UMBRAL_BAJO
                  else "Rendimiento medio-alto"),
            axis=1
        )

    else:  # zona
        prom_tipo = (
            d.groupby(["cole_mcpio_ubicacion", col_area])["punt_global"]
            .mean().unstack(col_area).reset_index()
        )
        col_urb = [c for c in prom_tipo.columns if "URB" in str(c).upper()]
        col_rur = [c for c in prom_tipo.columns if "RUR" in str(c).upper()]

        if not col_urb or not col_rur:
            return fig_mensaje("Scatter desigualdad", f"Columnas no encontradas: {list(prom_tipo.columns)}")

        prom_tipo["brecha"] = prom_tipo[col_urb[0]] - prom_tipo[col_rur[0]]
        etiqueta_y = "Diferencia Urbano − Rural (puntos)"

        scatter_df = prom_general.merge(
            prom_tipo[["cole_mcpio_ubicacion", "brecha"]],
            on="cole_mcpio_ubicacion", how="left"
        )
        scatter_df["brecha"] = scatter_df["brecha"].fillna(0)

        # ← UMBRAL aquí también
        UMBRAL_BAJO = scatter_df["prom_general"].quantile(0.33)

        scatter_df["color"] = scatter_df["prom_general"].apply(
            lambda x: "Bajo rendimiento" if x <= UMBRAL_BAJO else "Rendimiento medio-alto"
        )

    scatter_df["prom_general"] = scatter_df["prom_general"].round(1)
    scatter_df["brecha"]       = scatter_df["brecha"].round(1)

    fig = px.scatter(
        scatter_df,
        x="prom_general", y="brecha",
        text="cole_mcpio_ubicacion",
        color="color",
        color_discrete_map={
            "Bajo rendimiento":       "#c0392b",
            "Rendimiento medio-alto": "#1a3a5c",
            "Sin colegio privado":    "#b0b0b0",
        },
        labels={
            "prom_general": "Promedio puntaje global (municipio)",
            "brecha": etiqueta_y,
            "color": "",
        },
        title=f"Promedio general vs Desigualdad interna ({etiqueta_y})",
    )

# Primero el estilo general + hover
    fig.update_traces(
    textposition="top center",
    textfont=dict(size=9),
    marker=dict(size=13, line=dict(color="white", width=1.5)),
    hovertemplate="<b>%{text}</b><br>Promedio: %{x}<br>Brecha: %{y} pts<extra></extra>",
    )
    fig.for_each_trace(
    lambda t: t.update(
        mode="markers",           # ← quita el "text" del modo visual
        marker=dict(symbol="diamond", size=9, opacity=0.5)
    ) if t.name == "Sin colegio privado" else None
    )
    fig.add_hline(y=0, line_dash="dot", line_color="gray",
                  annotation_text="Sin brecha", annotation_position="right")
    fig.add_vline(x=UMBRAL_BAJO, line_dash="dash", line_color="#e74c3c",
                  annotation_text="⚠ Umbral bajo", annotation_position="top left")
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Arial", size=11),
        margin=dict(l=10, r=20, t=60, b=10),
        height=420,
        legend=dict(orientation="h", y=-0.15),
        title=dict(x=0, xanchor="left"),
    )

    return fig


#-------------------------
#Callback tab 3
#-------------------------
from dash.exceptions import PreventUpdate
@app.callback(
    Output("p3_violin",  "figure"),
    Output("p3_dotplot", "figure"),
    Input("tabs", "value")
)
def actualizar_tab3(tab):
    if tab != "tab3":
        raise PreventUpdate

    d = df.copy()
    d["Género"] = d["estu_genero"].map({"F": "Femenino", "M": "Masculino"})
    d = d.dropna(subset=["Género"])

    # ── Violin ──────────────────────────────────────────────────────────────
    d_long = d.melt(
        id_vars="Género",
        value_vars=["punt_matematicas", "punt_lectura_critica"],
        var_name="Materia", value_name="Puntaje"
    )
    d_long["Materia"] = d_long["Materia"].map({
        "punt_matematicas":     "Matemáticas",
        "punt_lectura_critica": "Lectura Crítica"
    })

    fig_violin = px.violin(
        d_long, x="Materia", y="Puntaje", color="Género",
        box=True, points=False,
        color_discrete_map={"Femenino": "#e05c8a", "Masculino": "#1a3a5c"},
        title="Distribución de puntajes por género y materia (Caldas)",
        labels={"Puntaje": "Puntaje", "Materia": ""}
    )
    fig_violin.update_layout(
        template="plotly_white",
        margin=dict(l=10, r=10, t=60, b=10),
        title=dict(x=0, xanchor="left"),
        font=dict(family="Arial", size=12),
        height=380,
    )

    # ── Dot plot ─────────────────────────────────────────────────────────────
    brechas = (
        d.groupby(["cole_mcpio_ubicacion", "estu_genero"])
        [["punt_matematicas", "punt_lectura_critica"]]
        .mean().unstack("estu_genero")
    )
    brechas["brecha_mate"]    = brechas["punt_matematicas"]["M"]     - brechas["punt_matematicas"]["F"]
    brechas["brecha_lectura"] = brechas["punt_lectura_critica"]["M"] - brechas["punt_lectura_critica"]["F"]
    brechas = brechas[["brecha_mate", "brecha_lectura"]].reset_index()
    brechas.columns = ["municipio", "brecha_mate", "brecha_lectura"]
    brechas = brechas.dropna().sort_values("brecha_mate")

    fig_dot = go.Figure()

    for _, row in brechas.iterrows():
        fig_dot.add_trace(go.Scatter(
            x=[row["brecha_mate"], row["brecha_lectura"]],
            y=[row["municipio"], row["municipio"]],
            mode="lines",
            line=dict(color="#c0d0e0", width=1.5),
            showlegend=False, hoverinfo="skip"
        ))

    fig_dot.add_trace(go.Scatter(
        x=brechas["brecha_mate"], y=brechas["municipio"],
        mode="markers", name="Matemáticas",
        marker=dict(color="#e67e22", size=11, line=dict(color="white", width=1.5)),
        hovertemplate="<b>%{y}</b><br>Mate: %{x} pts<extra></extra>",
    ))
    fig_dot.add_trace(go.Scatter(
        x=brechas["brecha_lectura"], y=brechas["municipio"],
        mode="markers", name="Lectura Crítica",
        marker=dict(color="#27ae60", size=11, line=dict(color="white", width=1.5)),
        hovertemplate="<b>%{y}</b><br>Lectura: %{x} pts<extra></extra>",
    ))

    fig_dot.add_vline(x=0, line_dash="dash", line_color="gray",
                      annotation_text="Sin brecha", annotation_position="top right")

    fig_dot.update_layout(
        title="Brecha género (Hombres − Mujeres) por municipio y materia",
        template="plotly_white",
        font=dict(family="Arial", size=11),
        margin=dict(l=10, r=20, t=60, b=10),
        xaxis_title="Diferencia de puntaje (positivo = hombres ganan)",
        yaxis_title="",
        legend=dict(orientation="h", y=-0.08),
        title_x=0,
        height=max(420, len(brechas) * 22 + 120),
    )

    return fig_violin, fig_dot
if __name__ == "__main__":
    app.run(debug=True)
