import streamlit as st
import pandas as pd
import io
import hashlib
from google.cloud import bigquery
from google.oauth2 import service_account

# Configuracion de pagina
st.set_page_config(
    page_title="Pyme-Analytics Peru S.A.C.",
    layout="wide",
    initial_sidebar_state="expanded"
)

PROJECT_ID = "pyme-analytics-peru"
DATASET_ID = "pyme_datos"

# --------------------------------------------------
# CUS01 - AUTENTICACION
# --------------------------------------------------
USUARIOS_VALIDOS = {
    "admin@pyme-analytics.pe":    hashlib.sha256("CorpDoc3.@".encode()).hexdigest(),
    "gerencia@pyme-analytics.pe": hashlib.sha256("Gerencia2026#".encode()).hexdigest(),
    "analista@pyme-analytics.pe": hashlib.sha256("Analista2026#".encode()).hexdigest(),
}

def verificar_credenciales(correo, password):
    hashed = hashlib.sha256(password.encode()).hexdigest()
    return USUARIOS_VALIDOS.get(correo.strip().lower()) == hashed

def pantalla_login():
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        st.markdown("## Pyme-Analytics Peru S.A.C.")
        st.markdown("### Acceso Seguro para Clientes PYME")
        st.markdown("---")
        with st.form("form_login", clear_on_submit=False):
            correo   = st.text_input("Correo Corporativo:", placeholder="tucorreo@pyme-analytics.pe")
            password = st.text_input("Contrasena:", type="password", placeholder="**********")
            enviado  = st.form_submit_button("INGRESAR", use_container_width=True)
            if enviado:
                if not correo or not password:
                    st.error("Ingrese correo y contrasena.")
                elif verificar_credenciales(correo, password):
                    st.session_state["autenticado"] = True
                    st.session_state["usuario"]     = correo
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas. Verifique e intente nuevamente.")
        st.markdown("---")
        st.caption("Su informacion esta protegida. Entorno seguro y privado.")
        st.caption("2026 Pyme-Analytics Peru S.A.C. Todos los derechos reservados.")

# Control de sesion
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    pantalla_login()
    st.stop()

# --------------------------------------------------
# CONEXION A BIGQUERY
# --------------------------------------------------
@st.cache_resource
def obtener_cliente_bq():
    try:
        if "project_id" in st.secrets:
            creds = service_account.Credentials.from_service_account_info(dict(st.secrets))
        else:
            creds = service_account.Credentials.from_service_account_file("credenciales.json")
        return bigquery.Client(credentials=creds, project=PROJECT_ID)
    except Exception as e:
        st.error(f"Error de conexion con BigQuery: {e}")
        st.stop()

client = obtener_cliente_bq()

@st.cache_data(ttl=300)
def ejecutar_consulta(query):
    return client.query(query).to_dataframe()

# --------------------------------------------------
# CABECERA PRINCIPAL
# --------------------------------------------------
col_titulo, col_sesion = st.columns([5, 1])
with col_titulo:
    st.title("Sistema Analitico Pyme-Analytics Peru S.A.C.")
    st.markdown("#### Estadisticas de Produccion, Empleo y Demografia Empresarial (2020-2025)")
with col_sesion:
    st.markdown(f"Usuario: **{st.session_state['usuario']}**")
    if st.button("Cerrar sesion", use_container_width=True):
        st.session_state["autenticado"] = False
        st.session_state["usuario"]     = ""
        st.rerun()

st.markdown("---")

# --------------------------------------------------
# CUS03 - CONFIGURAR HORIZONTE DE ANALISIS
# --------------------------------------------------
st.sidebar.header("Filtros del Horizonte de Analisis")
st.sidebar.markdown("Seleccione los parametros para acotar el analisis.")

ano_seleccionado    = st.sidebar.selectbox("Anno:", list(range(2020, 2026)), index=5)
sector_seleccionado = st.sidebar.selectbox(
    "Sector Industrial:",
    ["Comercio", "Manufactura", "Servicios", "Textil", "Tecnologia", "Construccion"]
)
region_seleccionada = st.sidebar.selectbox(
    "Region:",
    ["Lima", "Arequipa", "Piura", "La Libertad", "Cusco", "Ica"]
)

st.sidebar.markdown("---")

# --------------------------------------------------
# CUS02 - CARGA DE DATOS OPERATIVOS Y FINANCIEROS
# --------------------------------------------------
st.sidebar.subheader("Carga de Datos Operativos")
st.sidebar.markdown("Puede cargar sus propios datos en formato .csv o .xlsx.")

archivo_cargado = st.sidebar.file_uploader(
    "Arrastrar y soltar archivo:",
    type=["csv", "xlsx"],
    help="Formatos aceptados: .csv y .xlsx."
)

COLS_DEMO   = {"Anio", "Mes", "Region", "Sector", "Stock_Empresas", "Natalidad", "Mortalidad"}
COLS_LAB    = {"Anio", "Mes", "Region", "Sector", "Poblacion_Ocupada", "Indice_Formalidad", "Sueldo_Promedio"}
COLS_VENTAS = {"Anio", "Mes", "Region", "Sector", "Ventas_Soles"}

df_cargado = None
if archivo_cargado is not None:
    try:
        if archivo_cargado.name.endswith(".csv"):
            df_cargado = pd.read_csv(archivo_cargado)
        else:
            df_cargado = pd.read_excel(archivo_cargado)

        cols   = set(df_cargado.columns)
        valido = (
            COLS_DEMO.issubset(cols) or
            COLS_LAB.issubset(cols) or
            COLS_VENTAS.issubset(cols)
        )
        if not valido:
            st.sidebar.error("Estructura de archivo invalida. Verifique las columnas requeridas.")
            df_cargado = None
        else:
            st.sidebar.success(f"Archivo cargado: {archivo_cargado.name} ({len(df_cargado):,} registros)")
    except Exception as e:
        st.sidebar.error(f"Error al procesar el archivo: {e}")
        df_cargado = None

st.sidebar.markdown("---")
st.sidebar.caption("2026 Pyme-Analytics Peru S.A.C.")

# --------------------------------------------------
# HELPER - obtener datos desde BigQuery o archivo
# --------------------------------------------------
def filtrar_df(df, anio, sector, region, columnas):
    mask = (
        (df["Anio"].astype(str) == str(anio)) &
        (df["Sector"].str.strip() == sector) &
        (df["Region"].str.strip() == region)
    )
    return df[mask][columnas].sort_values("Mes")

def obtener_demografia(anio, sector, region):
    cols = ["Mes", "Stock_Empresas", "Natalidad", "Mortalidad"]
    if df_cargado is not None and COLS_DEMO.issubset(df_cargado.columns):
        return filtrar_df(df_cargado, anio, sector, region, cols)
    query = f"""
        SELECT Mes, Stock_Empresas, Natalidad, Mortalidad
        FROM `{PROJECT_ID}.{DATASET_ID}.demografia`
        WHERE Anio = {anio} AND Sector = '{sector}' AND Region = '{region}'
        ORDER BY Mes
    """
    return ejecutar_consulta(query)

def obtener_laboral(anio, sector, region):
    cols = ["Mes", "Poblacion_Ocupada", "Indice_Formalidad", "Sueldo_Promedio"]
    if df_cargado is not None and COLS_LAB.issubset(df_cargado.columns):
        return filtrar_df(df_cargado, anio, sector, region, cols)
    query = f"""
        SELECT Mes, Poblacion_Ocupada, Indice_Formalidad, Sueldo_Promedio
        FROM `{PROJECT_ID}.{DATASET_ID}.laboral`
        WHERE Anio = {anio} AND Sector = '{sector}' AND Region = '{region}'
        ORDER BY Mes
    """
    return ejecutar_consulta(query)

def obtener_ventas(anio, sector, region):
    cols = ["Mes", "Ventas_Soles"]
    if df_cargado is not None and COLS_VENTAS.issubset(df_cargado.columns):
        return filtrar_df(df_cargado, anio, sector, region, cols)
    query = f"""
        SELECT Mes, Ventas_Soles
        FROM `{PROJECT_ID}.{DATASET_ID}.ventas`
        WHERE Anio = {anio} AND Sector = '{sector}' AND Region = '{region}'
        ORDER BY Mes
    """
    return ejecutar_consulta(query)

# --------------------------------------------------
# CUS04 - VISUALIZAR DASHBOARD E INTERPRETACIONES
# --------------------------------------------------
tab_demografia, tab_laboral, tab_ventas = st.tabs([
    "Demografia Empresarial",
    "Fuerza Laboral",
    "Ventas Sectoriales"
])

# TAB 1: DEMOGRAFIA
with tab_demografia:
    st.header("Analisis de Stock, Natalidad y Mortalidad de PYMES")
    st.markdown(
        f"**Periodo:** {ano_seleccionado}  |  "
        f"**Sector:** {sector_seleccionado}  |  "
        f"**Region:** {region_seleccionada}"
    )
    try:
        df_demo = obtener_demografia(ano_seleccionado, sector_seleccionado, region_seleccionada)
        if df_demo is not None and not df_demo.empty:
            stock_prom  = int(df_demo["Stock_Empresas"].mean())
            total_altas = int(df_demo["Natalidad"].sum())
            total_bajas = int(df_demo["Mortalidad"].sum())
            tasa_neta   = total_altas - total_bajas

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Stock Promedio de Empresas", f"{stock_prom:,}")
            col2.metric("Total Altas (Natalidad)",    f"{total_altas:,}")
            col3.metric("Total Bajas (Mortalidad)",   f"{total_bajas:,}")
            col4.metric(
                "Tasa Neta de Crecimiento",
                f"{tasa_neta:,}",
                delta="Positiva" if tasa_neta >= 0 else "Negativa"
            )

            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("Evolucion Mensual del Stock de Empresas")
            st.line_chart(data=df_demo.set_index("Mes")["Stock_Empresas"], use_container_width=True)

            st.subheader("Natalidad vs Mortalidad por Mes")
            st.bar_chart(data=df_demo.set_index("Mes")[["Natalidad", "Mortalidad"]], use_container_width=True)

            mes_pico      = int(df_demo.loc[df_demo["Natalidad"].idxmax(), "Mes"])
            natalidad_max = int(df_demo["Natalidad"].max())
            st.info(
                f"Interpretacion Demografia: Durante el anno {ano_seleccionado}, el sector "
                f"{sector_seleccionado} en {region_seleccionada} registro un pico maximo de "
                f"{natalidad_max:,} empresas nuevas inscritas en el mes {mes_pico}. "
                f"La tasa neta de crecimiento fue de {tasa_neta:,} empresas, indicando un ecosistema "
                f"{'en expansion' if tasa_neta >= 0 else 'con contraccion neta'}."
            )

            st.session_state["df_demo"]  = df_demo
            st.session_state["kpi_demo"] = {
                "stock_prom":  stock_prom,
                "total_altas": total_altas,
                "total_bajas": total_bajas,
                "tasa_neta":   tasa_neta
            }
        else:
            st.warning("No se encontraron registros para los filtros seleccionados. Ajuste los parametros.")
    except Exception as e:
        st.error(f"Error al consultar datos de demografia: {e}")

# TAB 2: FUERZA LABORAL
with tab_laboral:
    st.header("Analisis de Poblacion Ocupada, Formalidad y Salarios")
    st.markdown(
        f"**Periodo:** {ano_seleccionado}  |  "
        f"**Sector:** {sector_seleccionado}  |  "
        f"**Region:** {region_seleccionada}"
    )
    try:
        df_laboral = obtener_laboral(ano_seleccionado, sector_seleccionado, region_seleccionada)
        if df_laboral is not None and not df_laboral.empty:
            pob_max      = int(df_laboral["Poblacion_Ocupada"].max())
            pob_prom     = int(df_laboral["Poblacion_Ocupada"].mean())
            formalidad   = round(df_laboral["Indice_Formalidad"].mean() * 100, 1)
            informalidad = round(100 - formalidad, 1)
            sueldo_prom  = round(df_laboral["Sueldo_Promedio"].mean(), 2)
            sueldo_max   = round(df_laboral["Sueldo_Promedio"].max(), 2)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Poblacion Ocupada Maxima",   f"{pob_max:,}")
            col2.metric("Poblacion Ocupada Promedio", f"{pob_prom:,}")
            col3.metric("Indice de Formalidad Prom.", f"{formalidad}%")
            col4.metric("Sueldo Promedio",            f"S/. {sueldo_prom:,.2f}")

            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("Poblacion Ocupada por Mes")
            st.bar_chart(data=df_laboral.set_index("Mes")["Poblacion_Ocupada"], use_container_width=True)

            st.subheader("Evolucion del Indice de Formalidad (%)")
            df_form = df_laboral.copy()
            df_form["Formalidad_%"] = (df_form["Indice_Formalidad"] * 100).round(1)
            st.line_chart(data=df_form.set_index("Mes")["Formalidad_%"], use_container_width=True)

            st.info(
                f"Interpretacion Laboral: El salario promedio en el sector "
                f"{sector_seleccionado} de {region_seleccionada} se ubica en "
                f"S/. {sueldo_prom:,.2f}, con un pico de S/. {sueldo_max:,.2f}. "
                f"El indice de formalidad promedia {formalidad}%, lo que implica que "
                f"{informalidad}% de los trabajadores permanece en condicion de informalidad laboral."
            )

            st.session_state["df_laboral"]  = df_laboral
            st.session_state["kpi_laboral"] = {
                "pob_max":    pob_max,
                "formalidad": formalidad,
                "sueldo_prom": sueldo_prom
            }
        else:
            st.warning("No se encontraron registros para los filtros seleccionados. Ajuste los parametros.")
    except Exception as e:
        st.error(f"Error al consultar datos laborales: {e}")

# TAB 3: VENTAS
with tab_ventas:
    st.header("Seguimiento de Ingresos y Evolucion Economica Mensual")
    st.markdown(
        f"**Periodo:** {ano_seleccionado}  |  "
        f"**Sector:** {sector_seleccionado}  |  "
        f"**Region:** {region_seleccionada}"
    )
    try:
        df_ventas = obtener_ventas(ano_seleccionado, sector_seleccionado, region_seleccionada)
        if df_ventas is not None and not df_ventas.empty:
            total_ventas = df_ventas["Ventas_Soles"].sum()
            venta_max    = df_ventas["Ventas_Soles"].max()
            venta_min    = df_ventas["Ventas_Soles"].min()
            venta_prom   = df_ventas["Ventas_Soles"].mean()
            mes_pico_v   = int(df_ventas.loc[df_ventas["Ventas_Soles"].idxmax(), "Mes"])
            variacion    = ((venta_max - venta_min) / venta_min * 100) if venta_min > 0 else 0

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Facturado en el Periodo", f"S/. {total_ventas:,.2f}")
            col2.metric("Mes de Mayor Venta",            f"Mes {mes_pico_v}", delta=f"S/. {venta_max:,.0f}")
            col3.metric("Promedio Mensual",              f"S/. {venta_prom:,.2f}")

            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("Comportamiento Mensual de Ingresos (Soles)")
            st.bar_chart(data=df_ventas.set_index("Mes")["Ventas_Soles"], use_container_width=True)

            st.info(
                f"Resumen Estadistico: Las ventas anuales acumuladas en el sector "
                f"{sector_seleccionado} de {region_seleccionada} alcanzaron "
                f"S/. {total_ventas:,.2f} en el anno {ano_seleccionado}. "
                f"El mes de mayor actividad fue el mes {mes_pico_v} con "
                f"S/. {venta_max:,.2f}, representando una variacion de "
                f"{variacion:.1f}% respecto al mes de menor venta."
            )

            st.session_state["df_ventas"]  = df_ventas
            st.session_state["kpi_ventas"] = {
                "total":    total_ventas,
                "prom":     venta_prom,
                "max":      venta_max,
                "mes_pico": mes_pico_v
            }
        else:
            st.warning("No se encontraron registros para los filtros seleccionados. Ajuste los parametros.")
    except Exception as e:
        st.error(f"Error al consultar datos de ventas: {e}")

# --------------------------------------------------
# CUS05 - EXPORTAR INFORME GERENCIAL
# --------------------------------------------------
st.markdown("---")
st.subheader("Exportar Informe Gerencial")

col_exp1, col_exp2, col_exp3 = st.columns(3)

# Opcion 1: Excel con los tres paneles
with col_exp1:
    if st.button("Descargar datos en Excel", use_container_width=True):
        frames = {}
        if "df_demo"    in st.session_state: frames["Demografia"] = st.session_state["df_demo"]
        if "df_laboral" in st.session_state: frames["Laboral"]    = st.session_state["df_laboral"]
        if "df_ventas"  in st.session_state: frames["Ventas"]     = st.session_state["df_ventas"]

        if frames:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                for nombre, df in frames.items():
                    df.to_excel(writer, sheet_name=nombre, index=False)
            buffer.seek(0)
            st.download_button(
                label="Confirmar descarga (Excel)",
                data=buffer,
                file_name=f"Informe_{sector_seleccionado}_{region_seleccionada}_{ano_seleccionado}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        else:
            st.warning("Primero visualice los paneles para generar el informe.")

# Opcion 2: Resumen de KPIs en texto plano
with col_exp2:
    if st.button("Descargar resumen KPIs (TXT)", use_container_width=True):
        lineas = [
            "=" * 55,
            "  INFORME GERENCIAL - PYME-ANALYTICS PERU S.A.C.",
            "=" * 55,
            f"  Anno    : {ano_seleccionado}",
            f"  Sector  : {sector_seleccionado}",
            f"  Region  : {region_seleccionada}",
            f"  Usuario : {st.session_state.get('usuario', 'N/A')}",
            "-" * 55,
        ]
        if "kpi_demo" in st.session_state:
            k = st.session_state["kpi_demo"]
            lineas += [
                "PANEL 1 - DEMOGRAFIA EMPRESARIAL",
                f"  Stock Promedio de Empresas : {k['stock_prom']:,}",
                f"  Total Altas (Natalidad)    : {k['total_altas']:,}",
                f"  Total Bajas (Mortalidad)   : {k['total_bajas']:,}",
                f"  Tasa Neta de Crecimiento   : {k['tasa_neta']:,}",
                "-" * 55,
            ]
        if "kpi_laboral" in st.session_state:
            k = st.session_state["kpi_laboral"]
            lineas += [
                "PANEL 2 - FUERZA LABORAL",
                f"  Poblacion Ocupada Maxima   : {k['pob_max']:,}",
                f"  Indice de Formalidad Prom. : {k['formalidad']}%",
                f"  Sueldo Promedio            : S/. {k['sueldo_prom']:,.2f}",
                "-" * 55,
            ]
        if "kpi_ventas" in st.session_state:
            k = st.session_state["kpi_ventas"]
            lineas += [
                "PANEL 3 - VENTAS SECTORIALES",
                f"  Total Facturado            : S/. {k['total']:,.2f}",
                f"  Promedio Mensual           : S/. {k['prom']:,.2f}",
                f"  Mes de Mayor Venta         : Mes {k['mes_pico']}",
                f"  Venta Maxima Mensual       : S/. {k['max']:,.2f}",
                "-" * 55,
            ]
        lineas += [
            "  Sistema automatizado integrado con Google BigQuery.",
            "  2026 Pyme-Analytics Peru S.A.C.",
            "=" * 55,
        ]
        contenido = "\n".join(lineas)
        st.download_button(
            label="Confirmar descarga (TXT)",
            data=contenido.encode("utf-8"),
            file_name=f"KPIs_{sector_seleccionado}_{region_seleccionada}_{ano_seleccionado}.txt",
            mime="text/plain",
            use_container_width=True
        )

# Opcion 3: CSV de un panel especifico
with col_exp3:
    panel_export = st.selectbox(
        "Exportar panel especifico (CSV):",
        ["Demografia", "Fuerza Laboral", "Ventas"]
    )
    if st.button("Descargar panel seleccionado", use_container_width=True):
        mapa = {
            "Demografia":    "df_demo",
            "Fuerza Laboral":"df_laboral",
            "Ventas":        "df_ventas"
        }
        key = mapa[panel_export]
        if key in st.session_state:
            csv_bytes = st.session_state[key].to_csv(index=False).encode("utf-8")
            st.download_button(
                label=f"Confirmar descarga {panel_export} (CSV)",
                data=csv_bytes,
                file_name=f"{panel_export}_{sector_seleccionado}_{region_seleccionada}_{ano_seleccionado}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.warning(f"Primero visualice el panel {panel_export}.")

# --------------------------------------------------
# PIE DE PAGINA
# --------------------------------------------------
st.markdown("---")
st.caption(
    "2026 Pyme-Analytics Peru S.A.C. "
    "Sistema automatizado integrado con Google BigQuery y Streamlit Cloud. "
    "Todos los derechos reservados. | Soporte | Privacidad"
)
