import streamlit as st
import ee
import geemap
import fiona
import shapely.geometry as geom
import pandas as gpd

# Inicializar Earth Engine
try:
    ee.Initialize()
except Exception as e:
    ee.Authenticate()
    ee.Initialize()

st.title("🌱 Forraje Disponible con MOD17A3 (500m)")

st.write("""
Subí un archivo **KML o SHP** con tus polígonos.
La app calculará el **promedio y desvío estándar de NPP (kgC/ha/año)**
para cada polígono.
""")

uploaded_file = st.file_uploader("📂 Subí tu archivo (KML o SHP)", type=["kml", "shp"])

def read_polygons(file):
    polygons = []
    with fiona.BytesCollection(file.read()) as src:
        for feature in src:
            shape = geom.shape(feature["geometry"])
            polygons.append(shape)
    return polygons

if uploaded_file is not None:
    try:
        # Leer polígonos con fiona
        polygons = read_polygons(uploaded_file)

        # Convertir a geometrías de EE
        ee_polygons = [ee.Geometry.Polygon(list(poly.exterior.coords)) for poly in polygons]

        # Colección MOD17A3 (NPP)
        dataset = ee.ImageCollection("MODIS/061/MOD17A3HGF").select("Npp")

        results = []
        for i, poly in enumerate(ee_polygons):
            # Reducir la colección a la región
            stats = dataset.mean().reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    reducer2=ee.Reducer.stdDev(), sharedInputs=True
                ),
                geometry=poly,
                scale=500,
                maxPixels=1e13
            )
            results.append({
                "Polígono": f"Polígono {i+1}",
                "NPP_promedio": stats.getInfo().get("Npp_mean"),
                "NPP_desvío": stats.getInfo().get("Npp_stdDev")
            })

        # Mostrar resultados en tabla
        df = pd.DataFrame(results)
        st.dataframe(df)

        # Descargar CSV
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Descargar resultados en CSV",
            data=csv,
            file_name="resultados_mod17a3.csv",
            mime="text/csv",
        )

    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")

