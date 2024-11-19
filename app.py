import streamlit as st
import pandas as pd
import plotly.express as px

import geopandas as gpd
import folium

# Forma antigua
from streamlit_folium import folium_static

# ----- Fuentes de datos -----

# URL del archivo de datos. El archivo original está en: 
# https://covid.ourworldindata.org/data/owid-covid-data.csv
URL_DATOS_COVID = 'datos/owid-covid-data.zip'

# URL del archivo de países. El archivo original está en:
# https://www.naturalearthdata.com/http//www.naturalearthdata.com/download/10m/cultural/ne_10m_admin_0_sovereignty.zip
URL_DATOS_PAISES = 'datos/paises.gpkg'

# Fecha máxima a considerar en los datos de COVID-19
FECHA_MAXIMA_DATOS_COVID = '2024-08-04'


# ----- Funciones para recuperar los datos -----

# Función para cargar los datos y almacenarlos en caché 
# para mejorar el rendimiento
@st.cache_data
def cargar_datos_covid():
    # Leer el archivo CSV y cargarlo en un DataFrame de pandas
    datos = pd.read_csv(URL_DATOS_COVID, compression='zip')
    return datos

# Función para cargar los datos geoespaciales de países
@st.cache_data
def cargar_datos_paises():
    paises = gpd.read_file(URL_DATOS_PAISES)
    return paises


# Título de la aplicación
st.title('Datos de COVID-19')


# ----- Carga de datos -----

# Mostrar un mensaje mientras se cargan los datos de COVID-19
estado_carga_covid = st.text('Cargando datos de COVID-19...')
# Cargar los datos
datos = cargar_datos_covid()
# Actualizar el mensaje una vez que los datos han sido cargados
estado_carga_covid.text('Los datos de COVID-19 fueron cargados.')

# Cargar datos geoespaciales de países
estado_carga_paises = st.text('Cargando datos de países...')
paises = cargar_datos_paises()
estado_carga_paises.text('Los datos de países fueron cargados.')


# ----- Filtrado inicial de datos -----

# Eliminar los datos de COVID posteriores a la fecha máxima
datos = datos[datos['date'] <= FECHA_MAXIMA_DATOS_COVID]

# Eliminar los datos de COVID con código ISO que comienza con "OWID"
# los cuales corresponden a regiones
datos = datos[~datos['iso_code'].str.startswith('OWID')]


# ----- Preparación de datos -----

# Columnas relevantes del conjunto de datos
columnas = [
    'iso_code', 
    'location', 
    'date', 
    'total_cases', 
    'total_deaths'
]
datos = datos[columnas]

# Nombres de las columnas en español
columnas_espaniol = {
    'iso_code': 'Código ISO',
    'location': 'País',
    'date': 'Fecha',
    'total_cases': 'Casos totales',
    'total_deaths': 'Muertes totales'
}
datos = datos.rename(columns=columnas_espaniol)

# Convertir la columna 'Fecha' a tipo datetime
datos['Fecha'] = pd.to_datetime(datos['Fecha']).dt.date


# ----- Lista de selección en la barra lateral -----

# Obtener la lista de países únicos
lista_paises = datos['País'].unique().tolist()
lista_paises.sort()

# Añadir la opción "Todos" al inicio de la lista
opciones_paises = ['Todos'] + lista_paises

# Crear el selectbox en la barra lateral
pais_seleccionado = st.sidebar.selectbox(
    'Selecciona un país',
    opciones_paises
)


# ----- Filtrar datos según la selección -----

if pais_seleccionado != 'Todos':
    # Filtrar los datos para el país seleccionado
    datos_filtrados = datos[datos['País'] == pais_seleccionado]
    # Obtener el Código ISO del país seleccionado
    codigo_iso_seleccionado = datos_filtrados['Código ISO'].iloc[0]
else:
    # No aplicar filtro
    datos_filtrados = datos.copy()
    codigo_iso_seleccionado = None


# ----- Tabla de casos totales y muertes totales por país y por día -----

# Mostrar la tabla
st.subheader('Casos totales y muertes totales por país y por día')
st.dataframe(datos_filtrados, hide_index=True)


# ----- Gráfico de casos totales a lo largo del tiempo -----

# Agrupar por fecha y sumar los casos totales
casos_totales_por_fecha = (
    datos_filtrados
    .groupby('Fecha')['Casos totales']
    .sum()
    .reset_index()
)

# Crear el gráfico de líneas para casos totales
fig_casos = px.line(
    casos_totales_por_fecha, 
    x='Fecha', 
    y='Casos totales', 
    title='Casos totales a lo largo del tiempo',
    labels={'Casos totales': 'Cantidad de casos totales', 'Fecha': 'Fecha'}
)

# Ajustar el formato del eje x para mostrar la fecha completa
fig_casos.update_xaxes(
    tickformat="%Y-%m-%d",  # Formato de año-mes-día
    title_text="Fecha"
)

# Mostrar el gráfico
st.subheader('Casos totales a lo largo del tiempo')
st.plotly_chart(fig_casos)


# ----- Mapa de coropletas con folium -----

# Agrupar los casos totales por país (última fecha disponible o filtrados)
if pais_seleccionado != 'Todos':
    casos_totales_por_pais = (
        datos_filtrados
        .groupby('Código ISO')['Casos totales']
        .max()
        .reset_index()
    )
else:
    casos_totales_por_pais = (
        datos
        .groupby('Código ISO')['Casos totales']
        .max()
        .reset_index()
    )

# Unir los datos de casos con el GeoDataFrame de países
paises_merged = paises.merge(
    casos_totales_por_pais, 
    how='left', 
    left_on='ADM0_ISO', 
    right_on='Código ISO'
)

# Reemplazar valores nulos por cero en 'Casos totales'
paises_merged['Casos totales'] = paises_merged['Casos totales'].fillna(0)

# Crear el mapa base
if pais_seleccionado != 'Todos':
    # Obtener el Código ISO del país seleccionado
    codigo_iso = codigo_iso_seleccionado
    # Filtrar el GeoDataFrame para obtener la geometría del país
    pais_geom = paises_merged[paises_merged['ADM0_ISO'] == codigo_iso]
    if not pais_geom.empty:
        # Obtener el centroide de la geometría del país
        centroid = pais_geom.geometry.centroid.iloc[0]
        coordenadas = [centroid.y, centroid.x]
        zoom_level = 5
    else:
        # Valores por defecto si no se encuentra el país
        coordenadas = [0, 0]
        zoom_level = 2
else:
    coordenadas = [0, 0]
    zoom_level = 1

mapa = folium.Map(location=coordenadas, zoom_start=zoom_level)

# Crear una paleta de colores
from branca.colormap import linear
paleta_colores = linear.YlOrRd_09.scale(paises_merged['Casos totales'].min(), paises_merged['Casos totales'].max())

# Añadir los polígonos al mapa
folium.GeoJson(
    paises_merged,
    name='Casos totales por país',
    style_function=lambda feature: {
        'fillColor': paleta_colores(feature['properties']['Casos totales']),
        'color': 'black',
        'weight': 0.5,
        'fillOpacity': 0.7,
    },
    highlight_function=lambda feature: {
        'weight': 3,
        'color': 'black',
        'fillOpacity': 0.9,
    },
    tooltip=folium.features.GeoJsonTooltip(
        fields=['ADM0_ISO', 'Casos totales'],
        aliases=['Código ISO: ', 'Casos totales: '],
        localize=True
    )
).add_to(mapa)

# Añadir la leyenda al mapa
paleta_colores.caption = 'Casos totales por país'
paleta_colores.add_to(mapa)

# Agregar el control de capas al mapa
folium.LayerControl().add_to(mapa)

# Mostrar el mapa
st.subheader('Mapa de casos totales por país')

# Forma antigua
folium_static(mapa)

# Forma nueva
# st_folium(mapa, width=725)
