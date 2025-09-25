import streamlit as st
import geopandas as gpd
import ee
import geemap
import pandas as pd
import tempfile
import zipfile

# Inicializar Earth Engine
try:
    ee.Initialize()
except Exception as e:
    ee.Authenticate()
    ee.Initialize()

st.title("🌱 NPP (MOD17A3, 500m, anual) por polígonos")

# Subida de archivo
uploaded_file = st.file_uploader("Subí tu archivo KML, GeoJSON o Shapefile (.zip)", 
                                 type=["kml", "geojson", "zip"])

if uploaded_file:
    # Guardar archivo temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name) as tmp:
        tmp.write(uploaded_file.read())
        filepath = tmp.name

    # Leer archivo con GeoPandas
    if filepath.endswith(".zip"):
        with zipfile.ZipFile(filepath, "r") as zip_ref:
            zip_ref.extractall("shapefile")
        gdf = gpd.read_file("shapefile")
    else:
        gdf = gpd.read_file(filepath)

    st.success(f"✅ Se leyeron {len(gdf)} polígonos del archivo.")

    # Convertir a EE FeatureCollection
    fc = geemap.geopandas_to_ee(gdf)

    # Colección MOD17A3 (NPP anual, 500m)
    dataset = ee.ImageCollection("MODIS/061/MOD17A3HGF").select("Npp")

    # Función para calcular promedio y desvío
    def zonal_stats(img):
        year = ee.Date(img.get("system:time_start")).get("year")
        stats = img.reduceRegions(
            collection=fc,
            reducer=ee.Reducer.mean().combine(
                reducer2=ee.Reducer.stdDev(), sharedInputs=True
            ),
            scale=500,
        )
        return stats.map(lambda f: f.set("year", year))

    # Aplicar a la colección completa
    results = dataset.map(zonal_stats).flatten()

    # Convertir a pandas DataFrame
    df = geemap.ee_to_pandas(results)

    # Mostrar preview
    st.dataframe(df.head())

    # Botón de descarga CSV
    st.download_button("⬇️ Descargar CSV con NPP por polígono y año",
                       df.to_csv(index=False),
        
