import urllib.request, json, unicodedata

url = "https://raw.githubusercontent.com/caticoa3/colombia_mapa/master/co_2018_MGN_MPIO_POLITICO.geojson"
print("Descargando... (puede tardar unos segundos)")
with urllib.request.urlopen(url) as r:
    geo_col = json.loads(r.read().decode())

def norm_mun(x):
    if x is None: return None
    x = str(x).strip()
    x = unicodedata.normalize("NFKD", x).encode("ascii","ignore").decode("ascii")
    return x.upper()

caldas = {
    "type": "FeatureCollection",
    "features": [f for f in geo_col["features"]
                 if str(f["properties"].get("DPTO_CCDGO","")) == "17"]
}
for f in caldas["features"]:
    f["properties"]["MUN_NORM"] = norm_mun(f["properties"].get("MPIO_CNMBR",""))

with open("data/caldas_municipios.geojson", "w", encoding="utf-8") as f:
    json.dump(caldas, f, ensure_ascii=False)

print("✅ Municipios:", len(caldas["features"]))
