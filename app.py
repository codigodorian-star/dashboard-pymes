import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account

st.set_page_config(page_title="Pyme-Analytics Peru", page_icon="📊", layout="wide")

PROJECT_ID = "pyme-analytics-peru"
DATASET_ID = "pyme_datos"

try:
    if "project_id" in st.secrets:
        creds = service_account.Credentials.from_service_account_info(st.secrets)
    else:
        creds = service_account.Credentials.from_service_account_file("credenciales.json")
    client = bigquery.Client(credentials=creds, project=PROJECT_ID)
except Exception as e:
    st.error(f"Error de credenciales: {e}")
    st.stop()

@st.cache_data
def ejecutar_consulta(query):
    query_job = client.query(query)
    return query_job.to_dataframe()

st.title("📊 Sistema Analitico Pyme-Analytics Peru S.A.C.")
st.markdown("### Estadisticas de Produccion, Empleo y Demografia Empresarial (2020-2025)")
st.write("---")

st.sidebar.header("Filtros del Horizonte de Analisis")

lista_anios = list(range(2020, 2026))
anio_seleccionado = st.sidebar.selectbox("Seleccione el Anio:", lista_anios, index=len(lista_anios)-1)

lista_sectores = ['Comercio', 'Manufactura', 'Servicios', 'Textil', 'Tecnologia', 'Construccion']
sector_seleccionado = st.sidebar.selectbox("Seleccione el Sector Industrial:", lista_sectores)

lista_regiones = ['Lima', 'Arequipa', 'Piura', 'La Libertad', 'Cusco', 'Ica']
region_seleccionada = st.sidebar.selectbox("Seleccione la Region:", lista_regiones)

tab_demografia, tab_laboral, tab_ventas = st.tabs([
    "📈 Demografia Empresarial", 
    "👥 Fuerza Laboral", 
    "💰 Ventas Sectoriales"
])

with tab_demografia:
    st.header("Analisis de Stock, Natalidad y Mortalidad de PYMES")
    query_demo = f"""
        SELECT Mes, Stock_Empresas, Natalidad, Mortalidad 
        FROM `{PROJECT_ID}.{DATASET_ID}.demografia`
        WHERE Anio = {anio_seleccionado} 
          AND Sector = '{sector_seleccionado}'
          AND Region = '{region_seleccionada}'
        ORDER BY Mes
    """
    try:
        df_demo = ejecutar_consulta(query_demo)
        if not df_demo.empty:
            col1, col2, col3 = st.columns(3)
            col1.metric("Stock Promedio de Empresas", f"{int(df_demo['Stock_Empresas'].mean()):,}")
            col2.metric("Total Altas (Natalidad)", f"{df_demo['Natalidad'].sum():,}")
            col3.metric("Total Bajas (Mortalidad)", f"{df_demo['Mortalidad'].sum():,}")
            
            st.subheader("Evolucion Mensual del Stock de Empresas")
            st.line_chart(data=df_demo, x='Mes', y='Stock_Empresas')
            
            st.info(f"**Interpretacion Demografia:** Durante el anio {anio_seleccionado}, el sector {sector_seleccionado} en {region_seleccionada} registro un pico maximo de {df_demo['Natalidad'].max()} empresas nuevas inscritas en un solo mes.")
        else:
            st.warning("No se encontraron registros para estos filtros.")
    except Exception as e:
        st.error(f"Error en consulta: {e}")

with tab_laboral:
    st.header("Analisis de Poblacion Ocupada, Formalidad y Salarios")
    query_laboral = f"""
        SELECT Mes, Poblacion_Ocupada, Indice_Formalidad, Sueldo_Promedio 
        FROM `{PROJECT_ID}.{DATASET_ID}.laboral`
        WHERE Anio = {anio_seleccionado} 
          AND Sector = '{sector_seleccionado}'
          AND Region = '{region_seleccionada}'
        ORDER BY Mes
    """
    try:
        df_laboral = ejecutar_consulta(query_laboral)
        if not df_laboral.empty:
            col1, col2, col3 = st.columns(3)
            col1.metric("Poblacion Ocupada Maxima", f"{df_laboral['Poblacion_Ocupada'].max():,}")
            col2.metric("Indice de Formalidad Promedio", f"{round(df_laboral['Indice_Formalidad'].mean() * 100, 1)}%")
            col3.metric("Sueldo Promedio", f"S/. {round(df_laboral['Sueldo_Promedio'].mean(), 2)}")
            
            st.subheader("Poblacion Ocupada por Mes")
            st.bar_chart(data=df_laboral, x='Mes', y='Poblacion_Ocupada')
            
            st.info(f"**Interpretacion Laboral:** El salario promedio se ubica en S/. {round(df_laboral['Sueldo_Promedio'].mean(), 2)}. El indice de formalidad en {region_seleccionada} promedia {round(df_laboral['Indice_Formalidad'].mean() * 100, 1)}%.")
        else:
            st.warning("No se encontraron registros para estos filtros.")
    except Exception as e:
        st.error(f"Error en consulta: {e}")

with tab_ventas:
    st.header("Seguimiento de Ingresos y Evolucion Economica Mensual")
    query_ventas = f"""
        SELECT Mes, Ventas_Soles 
        FROM `{PROJECT_ID}.{DATASET_ID}.ventas`
        WHERE Anio = {anio_seleccionado} 
          AND Sector = '{sector_seleccionado}'
          AND Region = '{region_seleccionada}'
        ORDER BY Mes
    """
    try:
        df_ventas = ejecutar_consulta(query_ventas)
        if not df_ventas.empty:
            total_ventas = df_ventas['Ventas_Soles'].sum()
            st.metric("Total Facturado en el Periodo", f"S/. {total_ventas:,.2f}")
            
            st.subheader("Comportamiento Mensual de Ingresos (Soles)")
            st.bar_chart(data=df_ventas, x='Mes', y='Ventas_Soles')
            
            st.info(f"**Resumen Estadistico:** Las ventas anuales acumuladas en el sector {sector_seleccionado} alcanzaron S/. {total_ventas:,.2f} en el anio {anio_seleccionado}.")
        else:
            st.warning("No se encontraron registros para estos filtros.")
    except Exception as e:
        st.error(f"Error en consulta: {e}")

st.write("---")
st.caption("© 2026 Pyme-Analytics Peru S.A.C. Todos los derechos reservados. Sistema automatizado integrado con Google BigQuery.")
