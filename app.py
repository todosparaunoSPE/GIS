import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import os
import pandas as pd
import matplotlib.pyplot as plt
from folium.plugins import MeasureControl, MousePosition, Draw, Fullscreen, MarkerCluster

# Configuración de la página
st.set_page_config(layout="wide")
st.title("🌍 Mapa Interactivo de México - Tipo ArcGIS")

# Verificar existencia del archivo
estados_file = "georef-mexico-state.geojson"

if not os.path.exists(estados_file):
    st.error(f"""
    No se encontró el archivo GeoJSON. Por favor asegúrate de que:
    1. El archivo esté en el mismo directorio que este script
    2. Se llame exactamente: {estados_file}
    """)
    st.stop()

@st.cache_data
def load_local_geojson(filepath):
    try:
        return gpd.read_file(filepath)
    except Exception as e:
        st.error(f"Error al cargar {filepath}: {str(e)}")
        return None

# Cargar solo los datos de estados
gdf_estados = load_local_geojson(estados_file)

if gdf_estados is None:
    st.stop()

# ================== SECCIÓN DE FILTRO DE ESTADOS ==================

# Barra lateral con filtros
with st.sidebar:
    # Agregar tu nombre y la fecha
    st.markdown("---")
    st.markdown(f"**Desarrollado por:**  \n*Javier Horacio Pérez Ricárdez*")
    

st.sidebar.header("🔍 Filtro por Estado")
estados_disponibles = gdf_estados['sta_name'].sort_values().unique()

estado_seleccionado = st.sidebar.multiselect(
    "Selecciona uno o más estados (deja vacío para todos)",
    options=estados_disponibles,
    default=estados_disponibles  # Por defecto selecciona todos
)

# Filtrar según selección múltiple
if estado_seleccionado:
    gdf_filtrado = gdf_estados[gdf_estados['sta_name'].isin(estado_seleccionado)]
else:
    gdf_filtrado = gdf_estados

# ================== SECCIÓN DE ANÁLISIS DE DATOS ==================
st.sidebar.header("📊 Análisis de Datos")

st.subheader("📋 Información Estadística por Estado")
if not gdf_filtrado.empty:
    # Crear DataFrame con información relevante
    df_estados = pd.DataFrame({
        'Estado': gdf_filtrado['sta_name'],
        'Código': gdf_filtrado['sta_code'],
        'Tipo': gdf_filtrado['sta_type'],
        'Área (km²)': round(gdf_filtrado.geometry.to_crs(epsg=6933).area / 10**6, 2)  # Convertir a km² usando proyección métrica
    })

    # Mostrar DataFrame con filtros
    col1, col2 = st.columns([3, 1])
    with col1:
        st.dataframe(df_estados.sort_values('Área (km²)', ascending=False),
                    height=400,
                    use_container_width=True)
    with col2:
        st.metric("Estado más extenso", df_estados.loc[df_estados['Área (km²)'].idxmax(), 'Estado'])
        st.metric("Área máxima (km²)", df_estados['Área (km²)'].max())
        st.metric("Área promedio (km²)", round(df_estados['Área (km²)'].mean(), 2))

# 2. Gráfico de áreas por estado
st.subheader("📈 Distribución de Áreas por Estado")
fig, ax = plt.subplots(figsize=(10, 6))
df_estados.sort_values('Área (km²)', ascending=True).plot.barh(
    x='Estado',
    y='Área (km²)',
    ax=ax,
    color='#3186cc',
    legend=False
)
ax.set_xlabel('Área (kilómetros cuadrados)')
ax.set_title('Área Territorial por Estado')
st.pyplot(fig)

# 3. Análisis por tipo de estado
st.subheader("🧩 Distribución por Tipo de Estado")
if 'sta_type' in gdf_filtrado.columns:
    tipo_counts = gdf_filtrado['sta_type'].value_counts()
    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(tipo_counts.rename("Cantidad"), width=300)
    with col2:
        fig2, ax2 = plt.subplots()
        tipo_counts.plot.pie(
            autopct='%1.1f%%',
            startangle=90,
            ax=ax2,
            colors=['#4c72b0', '#55a868', '#c44e52']
        )
        ax2.set_ylabel('')
        st.pyplot(fig2)

# ================== SECCIÓN DEL MAPA INTERACTIVO ==================
st.subheader("🗺️ Mapa Interactivo")

# Sidebar con controles
with st.sidebar:
    st.header("⚙️ Controles del Mapa")
    capa_base = st.selectbox(
        "Capa Base",
        ["CartoDB positron", "OpenStreetMap", "Stamen Terrain", "Stamen Toner"]
    )
    mostrar_capitales = st.checkbox("Mostrar capitales", True)
    mostrar_herramientas = st.checkbox("Mostrar herramientas de dibujo", True)

# Crear el mapa interactivo
try:
    # Configuración inicial del mapa
    m = folium.Map(
        location=[23.6345, -102.5528],
        zoom_start=5,
        tiles=capa_base,
        control_scale=True,
        attr="CartoDB attribution"
    )

    # Definir estilo para los tooltips
    tooltip_style = """
        font-family: Arial;
        font-size: 14px;
        font-weight: bold;
        color: #333333;
        background-color: #ffffff;
        padding: 8px;
        border-radius: 5px;
        border: 1px solid #cccccc;
        box-shadow: 3px 3px 5px rgba(0,0,0,0.2);
    """

    # Capa principal de estados con colores según área
    estados_layer = folium.GeoJson(
        gdf_filtrado,
        name="Estados",
        style_function=lambda x: {
            'fillColor': '#3186cc',
            'color': '#0a4b8c',
            'weight': 1.5,
            'fillOpacity': 0.5
        },
        highlight_function=lambda x: {
            'weight': 3,
            'fillOpacity': 0.7,
            'color': '#ff0000'
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["sta_name", "sta_code", "sta_type"],
            aliases=["<b>Estado</b>:", "<b>Código</b>:", "<b>Tipo</b>:"],
            style=tooltip_style,
            sticky=True
        )
    ).add_to(m)

    # ================== FUNCIONALIDADES AVANZADAS ==================

    # 1. Plugin de Medición
    MeasureControl(
        position='bottomleft',
        primary_length_unit='kilometers',
        secondary_length_unit='miles',
        primary_area_unit='hectares',
        secondary_area_unit='acres'
    ).add_to(m)

    # 2. Plugin de Coordenadas
    MousePosition(
        position='bottomright',
        separator=' | ',
        empty_string="Mueve el mouse sobre el mapa",
        lng_first=True,
        num_digits=4,
        prefix="Coordenadas:"
    ).add_to(m)

    # 3. Plugin de Dibujo (condicional)
    if mostrar_herramientas:
        Draw(
            export=True,
            position='topleft',
            draw_options={
                'polyline': True,
                'polygon': True,
                'circle': False,
                'marker': True,
                'rectangle': True
            }
        ).add_to(m)

    # 4. Plugin de Fullscreen
    Fullscreen(
        position='topright',
        title='Pantalla Completa',
        title_cancel='Salir',
        force_separate_button=True
    ).add_to(m)

    # 5. Marcadores de capitales (condicional)
    if mostrar_capitales:
        marker_cluster = MarkerCluster(name="Capitales").add_to(m)

        # Ejemplo con algunas capitales
        capitales = {
            "CDMX": (19.4326, -99.1332),
            "Guadalajara": (20.6597, -103.3496),
            "Monterrey": (25.6866, -100.3161),
            "Puebla": (19.0414, -98.2063),
            "Tijuana": (32.5149, -117.0382),
            "León": (21.1250, -101.6860)
        }

        for capital, coords in capitales.items():
            folium.Marker(
                location=coords,
                popup=f"<b>{capital}</b>",
                icon=folium.Icon(color='red', icon='star')
            ).add_to(marker_cluster)

    # 6. Múltiples capas base CON ATRIBUCIONES
    folium.TileLayer(
        'OpenStreetMap',
        name='OpenStreetMap',
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    ).add_to(m)

    folium.TileLayer(
        'Stamen Terrain',
        name='Stamen Terrain',
        attr='Map tiles by <a href="http://stamen.com">Stamen Design</a>, under <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a>. Data by <a href="http://openstreetmap.org">OpenStreetMap</a>, under <a href="http://www.openstreetmap.org/copyright">ODbL</a>.'
    ).add_to(m)

    folium.TileLayer(
        'Stamen Toner',
        name='Stamen Toner',
        attr='Map tiles by <a href="http://stamen.com">Stamen Design</a>, under <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a>. Data by <a href="http://openstreetmap.org">OpenStreetMap</a>, under <a href="http://www.openstreetmap.org/copyright">ODbL</a>.'
    ).add_to(m)

    # Control de capas
    folium.LayerControl().add_to(m)

except Exception as e:
    st.error(f"Error al crear el mapa: {str(e)}")

# Mostrar el mapa en Streamlit
st_folium(m, width=1000, height=600)
