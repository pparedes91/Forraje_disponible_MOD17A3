import streamlit as st
import ee
import geemap.foliumap as geemap
import fiona
import shapely.geometry as geom
import pandas as pd

# Inicializar Earth Engine
try:
    ee.Initialize()
except Exception:
    ee.Authenticate()
    ee.Initialize()

st.title("🌱 Forraje Disponible con MOD17A3 (500m)")

st.write("""
Subí un archivo **KML o SHP** con tus polígonos.
La app calculará el **promedio y desvío estándar de NPP (kgC/ha/año)**
para cada polígono, y además podrás verlos en un mapa.
""")

uploaded_file = st.file_uploader("📂 Subí tu archivo (KML o SHP)", type=["kml", "shp"])

def read_polygons(file):
    """Leer polígonos de un archivo KML/SHP y devolver lista shapely"""
    polygons = []
    with fiona.BytesCollection(file.read()) as src:
        for feature in src:
            shape = geom.shape(feature["geometry"])
            polygons.append(shape)
    return polygons

if uploaded_file is not None:
    try:
        # Leer polígonos
        polygons = read_polygons(uploaded_file)
        ee_polygons = [ee.Geometry.Polygon(list(poly.exterior.coords)) for poly in polygons]

        # Crear mapa
        m = geemap.Map(center=[-40, -65], zoom=4)

        # Cargar dataset MOD17A3 (NPP anual 500m)
        dataset = ee.ImageCollection("MODIS/061/MOD17A3HGF").select("Npp")
        latest = dataset.sort("system:time_start", False).first()

        vis_params = {
            "min": 0,
            "max": 19000,
            "palette": ["bbe029", "0a9501", "074b03"],
        }

        m.addLayer(latest, vis_params, "NPP más reciente")

        # Añadir polígonos al mapa
        for i, poly in enumerate(ee_polygons):
            m.addLayer(poly, {"color": "red"}, f"Polígono {i+1}")

        st.subheader("🗺️ Mapa interactivo")
        m.to_streamlit(height=500)

        # Botón para calcular estadísticas
        if st.button("📊 Calcular promedio y desvío por polígono"):
            results = []
            for i, poly in enumerate(ee_polygons):
                stats = dataset.mean().reduceRegion(
                    reducer=ee.Reducer.mean().combine(
                        reducer2=ee.Reducer.stdDev(), sharedInputs=True
                    ),
                    geometry=poly,
                    scale=500,
                    maxPixels=1e13,
                )
                results.append({
                    "Polígono": f"Polígono {i+1}",
                    "NPP_promedio": stats.getInfo().get("Npp_mean"),
                    "NPP_desvío": stats.getInfo().get("Npp_stdDev"),
                })

            df = pd.DataFrame(results)
            st.dataframe(df)

            # Botón descarga CSV
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Descargar resultados en CSV",
                data=csv,
                file_name="resultados_mod17a3.csv",
                mime="text/csv",
            )

    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
