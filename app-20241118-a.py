import streamlit as st
import pandas as pd
import plotly.express as px

import geopandas as gpd
import folium
from streamlit_folium import folium_static


# URL del archivo de datos. El archivo original está en: 
# https://covid.ourworldindata.org/data/owid-covid-data.csv
URL_DATOS = 'datos/owid-covid-data.csv'

# URL del archivo de países
URL_PAISES = 'datos/paises.gpkg'

# Fecha máxima a considerar en los datos
FECHA_MAXIMA = '2024-08-04'


# Función para cargar los datos y almacenarlos en caché 
# para mejorar el rendimiento
@st.cache_data
def cargar_datos_covid():
    # Leer el archivo CSV y cargarlo en un DataFrame de pandas
    datos = pd.read_csv(URL_DATOS)
    return datos

# Función para cargar los datos geoespaciales de países
@st.cache_data
def cargar_datos_paises():
    paises = gpd.read_file(URL_PAISES)
    return paises


# Título de la aplicación
st.title('Datos de COVID-19')


# ----- Carga de datos -----

# Mostrar un mensaje mientras se cargan los datos de COVID-19
estado_carga_covid = st.text('Cargando datos de COVID-19...')
# Cargar los datos
datos = cargar_datos_covid()
# Actualizar el mensaje una vez que los datos han sido cargados
estado_carga_covid.text('¡Datos de COVID-19 cargados exitosamente!')

# Cargar datos geoespaciales de países
estado_carga_paises = st.text('Cargando datos de países...')
paises = cargar_datos_paises()
estado_carga_paises.text('¡Datos de países cargados exitosamente!')


# ----- Filtrado inicial de datos -----
datos = datos[datos['date'] <= FECHA_MAXIMA]


# ----- Tabla de casos totales y muertes totales por país y por día -----

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

# Mostrar la tabla
st.subheader('Casos totales y muertes totales por país y por día')
st.dataframe(datos, hide_index=True)


# ----- Gráfico de casos totales a lo largo del tiempo -----

# Agrupar por fecha y sumar los casos totales
casos_totales_por_fecha = (
    datos
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


# ----- Mapa de coropletas con Folium -----

# Agrupar los casos totales por país (última fecha disponible)
casos_totales_por_pais = (
    datos
    .groupby('Código ISO')['Casos totales']
    .max()
    .reset_index()
)

# Unir los datos de casos con el GeoDataFrame de países
paises = paises.merge(
    casos_totales_por_pais, 
    how='left', 
    left_on='ADM0_ISO', 
    right_on='Código ISO'
)

# Reemplazar valores nulos por cero en 'Casos totales'
paises['Casos totales'] = paises['Casos totales'].fillna(0)

# Crear el mapa base
mapa = folium.Map(location=[0, 0], zoom_start=1)

# Crear un colormap
from branca.colormap import linear
colormap = linear.YlOrRd_09.scale(paises['Casos totales'].min(), paises['Casos totales'].max())

# Añadir los polígonos al mapa
folium.GeoJson(
    paises,
    name='Casos totales por país',
    style_function=lambda feature: {
        'fillColor': colormap(feature['properties']['Casos totales']),
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
        aliases=['País: ', 'Casos totales: '],
        localize=True
    )
).add_to(mapa)

# Añadir la leyenda al mapa
colormap.caption = 'Casos totales por país'
colormap.add_to(mapa)

# Mostrar el mapa
st.subheader('Mapa de casos totales por país')
folium_static(mapa)