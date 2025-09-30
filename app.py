import streamlit as st
import ee
import json
import geopandas as gpd
import pandas as pd
from google.oauth2 import service_account
from io import BytesIO

# =====================
# 🔐 Autenticación EE
# =====================
service_account = st.secrets["ee_service_account"]
key_dict = json.loads(st.secrets["ee_service_account_key"])
credentials = ee.ServiceAccountCredentials(service_account, key_dict)
ee.Initialize(credentials)

# =====================
# 🌍 Título de la app
# =====================
st.title("🌱 MOD17A3 NPP - Promedio y Desvío por Polígono")
st.write("Subí un archivo **KML** con tus polígonos para calcular estadísticas.")

# =====================
# 📂 Upload de archivo
# =====================
uploaded_file = st.file_uploader("📤 Subir archivo KML", type=["kml"])

if uploaded_file is not None:
    # Leer archivo KML con geopandas
    gdf = gpd.read_file(uploaded_file, driver="KML")
    st.success(f"✅ Se cargaron {len(gdf)} polígonos del archivo.")

    # Colección MOD17A3 (NPP)
    dataset = ee.ImageCollection("MODIS/061/MOD17A3HGF").select("Npp")
    latest = dataset.sort("system:time_start", False).first()

    results = []

    for idx, row in gdf.iterrows():
        geom = row.geometry.__geo_interface__
        ee_geom = ee.Geometry(geom)

        stats = latest.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                reducer2=ee.Reducer.stdDev(), sharedInputs=True
            ),
            geometry=ee_geom,
            scale=500,
            maxPixels=1e13
        ).getInfo()

        results.append({
            "Poligono": idx + 1,
            "Promedio_NPP": stats.get("Npp_mean"),
            "Desvio_NPP": stats.get("Npp_stdDev")
        })

    # Convertir a DataFrame
    df = pd.DataFrame(results)
    st.dataframe(df)

    # Botón para descargar CSV
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Descargar resultados en CSV",
        data=csv,
        file_name="estadisticas_npp.csv",
        mime="text/csv"
    )
