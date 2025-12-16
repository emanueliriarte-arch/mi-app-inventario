import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# Nombre de la base de datos.
DB_NAME = 'inventario_final.db' 

# --- Configuración de la aplicación ---
st.set_page_config(
    page_title="Sistema de Inventario",
    page_icon="📦",
    layout="wide"
)

# Lista de departamentos disponibles
DEPARTAMENTOS = ["Logística", "Almacén", "Ático", "Laboratorio", "Oficina", "Taller"]

# --- Funciones de la Base de Datos ---

@st.cache_resource
def get_connection():
    """Establece la conexión a la base de datos."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    return conn

def init_db(conn):
    """Inicializa las tablas de la base de datos."""
    c = conn.cursor()
    
    # Tabla de productos
    c.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            cantidad INTEGER,
            unidad_medida TEXT,
            departamento TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP       
        )
    ''')
    
    # Tabla de historial de movimientos (opcional, para tracking)
    c.execute('''
        CREATE TABLE IF NOT EXISTS historial_movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER,
            producto_nombre TEXT,
            tipo_movimiento TEXT,
            cantidad_anterior INTEGER,
            cantidad_nueva INTEGER,
            departamento_origen TEXT,
            departamento_destino TEXT,
            usuario TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (producto_id) REFERENCES productos (id)
        )
    ''')
    
    conn.commit()

def add_product(conn, nombre, cantidad, unidad_medida, departamento):
    """Inserta un nuevo producto y retorna su ID."""
    c = conn.cursor()
    c.execute("""
        INSERT INTO productos (nombre, cantidad, unidad_medida, departamento) 
        VALUES (?, ?, ?, ?)
    """, (nombre, cantidad, unidad_medida, departamento))
    conn.commit()
    return c.lastrowid

def update_product(conn, product_id, cantidad=None, departamento=None):
    """Actualiza un producto existente."""
    c = conn.cursor()
    
    # Obtener datos actuales del producto
    c.execute("SELECT nombre, cantidad, departamento FROM productos WHERE id = ?", (product_id,))
    producto_actual = c.fetchone()
    
    if not producto_actual:
        return False
    
    nombre_producto, cantidad_actual, depto_actual = producto_actual
    
    # Preparar actualización
    updates = []
    values = []
    
    if cantidad is not None:
        updates.append("cantidad = ?")
        values.append(cantidad)
    
    if departamento is not None:
        updates.append("departamento = ?")
        values.append(departamento)
    
    # Siempre actualizar la fecha de actualización
    updates.append("fecha_actualizacion = CURRENT_TIMESTAMP")
    
    if updates:
        values.append(product_id)
        update_query = f"UPDATE productos SET {', '.join(updates)} WHERE id = ?"
        c.execute(update_query, values)
        conn.commit()
        
        # Registrar en historial si cambió cantidad o departamento
        if cantidad is not None and cantidad != cantidad_actual:
            registrar_movimiento(
                conn, 
                product_id, 
                nombre_producto, 
                "ACTUALIZACION_CANTIDAD" if cantidad != cantidad_actual else "ACTUALIZACION",
                cantidad_actual,
                cantidad if cantidad is not None else cantidad_actual,
                depto_actual,
                departamento if departamento is not None else depto_actual,
                "Sistema"
            )
        
        if departamento is not None and departamento != depto_actual:
            registrar_movimiento(
                conn, 
                product_id, 
                nombre_producto, 
                "CAMBIO_DEPARTAMENTO",
                cantidad_actual,
                cantidad if cantidad is not None else cantidad_actual,
                depto_actual,
                departamento,
                "Sistema"
            )
        
        return True
    return False

def registrar_movimiento(conn, producto_id, producto_nombre, tipo_movimiento, 
                         cantidad_anterior, cantidad_nueva, 
                         departamento_origen, departamento_destino, usuario):
    """Registra un movimiento en el historial."""
    c = conn.cursor()
    c.execute("""
        INSERT INTO historial_movimientos 
        (producto_id, producto_nombre, tipo_movimiento, cantidad_anterior, 
         cantidad_nueva, departamento_origen, departamento_destino, usuario)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (producto_id, producto_nombre, tipo_movimiento, cantidad_anterior,
          cantidad_nueva, departamento_origen, departamento_destino, usuario))
    conn.commit()

def view_all_products(conn, departamento_filtro=None):
    """Recupera todos los productos, opcionalmente filtrados por departamento."""
    if departamento_filtro:
        query = """
            SELECT id, nombre, cantidad, unidad_medida, departamento, 
                   fecha_creacion, fecha_actualizacion
            FROM productos 
            WHERE departamento = ?
            ORDER BY nombre
        """
        df = pd.read_sql_query(query, conn, params=(departamento_filtro,))
    else:
        query = """
            SELECT id, nombre, cantidad, unidad_medida, departamento, 
                   fecha_creacion, fecha_actualizacion
            FROM productos 
            ORDER BY departamento, nombre
        """
        df = pd.read_sql_query(query, conn)
    
    # Formatear fechas
    if not df.empty and 'fecha_creacion' in df.columns:
        df['fecha_creacion'] = pd.to_datetime(df['fecha_creacion']).dt.strftime('%d/%m/%Y %H:%M')
        df['fecha_actualizacion'] = pd.to_datetime(df['fecha_actualizacion']).dt.strftime('%d/%m/%Y %H:%M')
    
    return df

def delete_product(conn, product_id):
    """Elimina un producto por ID."""
    c = conn.cursor()
    
    # Obtener información del producto antes de eliminarlo para el historial
    c.execute("SELECT nombre, cantidad, departamento FROM productos WHERE id = ?", (product_id,))
    producto = c.fetchone()
    
    if producto:
        nombre, cantidad, departamento = producto
        
        # Registrar en historial antes de eliminar
        registrar_movimiento(
            conn, 
            product_id, 
            nombre, 
            "ELIMINACION",
            cantidad,
            0,
            departamento,
            "ELIMINADO",
            "Sistema"
        )
    
    # Eliminar el producto
    c.execute("DELETE FROM productos WHERE id = ?", (product_id,))
    conn.commit()
    return c.rowcount

def get_departamento_stats(conn):
    """Obtiene estadísticas por departamento."""
    query = """
        SELECT 
            departamento,
            COUNT(*) as total_productos,
            SUM(cantidad) as total_unidades,
            GROUP_CONCAT(DISTINCT unidad_medida) as unidades_usadas
        FROM productos 
        GROUP BY departamento
        ORDER BY total_productos DESC
    """
    df = pd.read_sql_query(query, conn)
    return df

# --- Configuración de la Aplicación Streamlit ---

conn = get_connection()
init_db(conn)

st.title("📦 Sistema de Gestión de Inventario")

# Barra lateral para filtros y navegación
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3144/3144456.png", width=100)
    st.title("Opciones")
    
    # Filtro por departamento
    st.subheader("🔍 Filtros")
    filtro_departamento = st.selectbox(
        "Filtrar por departamento:",
        ["Todos los departamentos"] + DEPARTAMENTOS
    )
    
    # Estadísticas rápidas
    st.subheader("📊 Resumen")
    stats_df = get_departamento_stats(conn)
    
    if not stats_df.empty:
        total_productos = stats_df['total_productos'].sum()
        total_unidades = stats_df['total_unidades'].sum()
        st.metric("Total Productos", total_productos)
        st.metric("Total Unidades", total_unidades)
        
        # Mostrar por departamento
        with st.expander("Ver por departamento"):
            for _, row in stats_df.iterrows():
                st.caption(f"**{row['departamento']}**: {row['total_productos']} productos, {row['total_unidades']} unidades")
    else:
        st.info("No hay productos registrados")
    
    st.divider()
    
    # Navegación rápida
    st.subheader("🚀 Acciones rápidas")
    if st.button("🔄 Actualizar vista"):
        st.rerun()
    
    if st.button("📥 Exportar todo"):
        st.info("Usa la sección de exportación abajo")

# =================================================================
# SECCIÓN: AÑADIR NUEVO PRODUCTO
# =================================================================
st.header("➕ Añadir Nuevo Producto")

with st.form("add_product_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        nombre = st.text_input("Nombre del Producto:*", max_chars=100, 
                               help="Nombre descriptivo del producto")
        departamento = st.selectbox(
            "Departamento:*",
            DEPARTAMENTOS,
            help="Ubicación física del producto"
        )
    
    with col2:
        cantidad = st.number_input("Cantidad:*", min_value=0, step=1, value=1,
                                   help="Cantidad en stock")
        unidad = st.selectbox(
            "Unidad de Medida:*",
            ["Unitario", "Kg", "Gramo", "Ml", "Litro", "Metro", "Caja", 
             "Paquete", "Rollos", "Juego", "Par", "Docena"],
            help="Unidad de medida del producto"
        )
    
    with col3:
        st.markdown("### Información adicional")
        st.write("Los campos marcados con * son obligatorios")
        st.write("La fecha se registrará automáticamente")
    
    submitted = st.form_submit_button("💾 Guardar Producto", type="primary", use_container_width=True)

if submitted:
    if nombre and nombre.strip():
        try:
            # Validar que se haya seleccionado un departamento
            if not departamento:
                st.error("⚠️ Debes seleccionar un departamento.")
            else:
                product_id = add_product(conn, nombre.strip(), cantidad, unidad, departamento)
                st.success(f"✅ Producto '{nombre}' añadido con éxito al departamento {departamento} (ID: {product_id}).")
                st.rerun()
        except sqlite3.Error as e:
            st.error(f"❌ Error en base de datos: {e}")
        except Exception as e:
            st.error(f"❌ Error inesperado: {e}")
    else:
        st.error("⚠️ El nombre del producto no puede estar vacío.")

# =================================================================
# SECCIÓN: INVENTARIO ACTUAL
# =================================================================
st.header("📋 Inventario Actual")

# Aplicar filtro si se seleccionó uno
if filtro_departamento != "Todos los departamentos":
    st.info(f"Mostrando productos del departamento: **{filtro_departamento}**")
    productos_df = view_all_products(conn, departamento_filtro=filtro_departamento)
else:
    productos_df = view_all_products(conn)

if productos_df.empty:
    st.info("📭 El inventario está vacío o no hay productos en este departamento. Añade un producto arriba.")
else:
    # Mostrar estadísticas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 Total productos", len(productos_df))
    
    with col2:
        total_unidades = int(productos_df['cantidad'].sum())
        st.metric("📈 Total unidades", total_unidades)
    
    with col3:
        if filtro_departamento == "Todos los departamentos":
            deptos_count = productos_df['departamento'].nunique()
            st.metric("🏢 Departamentos", deptos_count)
        else:
            st.metric("📍 Departamento", filtro_departamento)
    
    with col4:
        unidades_count = productos_df['unidad_medida'].nunique()
        st.metric("📐 Tipos de unidad", unidades_count)
    
    st.divider()
    
    # Mostrar tabla de productos
    st.subheader("📋 Lista de Productos")
    
    # Formatear la tabla para mostrar
    display_df = productos_df.copy()
    display_df = display_df[['id', 'nombre', 'cantidad', 'unidad_medida', 'departamento', 'fecha_actualizacion']]
    display_df.index = range(1, len(display_df) + 1)
    
    # Mostrar tabla con colores por departamento
    st.dataframe(
        display_df,
        use_container_width=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "nombre": "Producto",
            "cantidad": "Cantidad",
            "unidad_medida": "Unidad",
            "departamento": "Departamento",
            "fecha_actualizacion": "Última Actualización"
        },
        hide_index=False
    )
    
    # =================================================================
    # SECCIÓN: GESTIÓN DE PRODUCTOS (EDITAR/ELIMINAR)
    # =================================================================
    st.divider()
    st.subheader("⚙️ Gestión de Productos")
    
    tab1, tab2 = st.tabs(["✏️ Editar Producto", "🗑️ Eliminar Producto"])
    
    with tab1:
        st.write("Actualiza la cantidad o cambia de departamento:")
        
        # Crear lista de productos para editar
        productos_lista_editar = productos_df[['id', 'nombre', 'departamento']].apply(
            lambda x: f"ID {x['id']}: {x['nombre']} ({x['departamento']})", axis=1
        ).tolist()
        
        if productos_lista_editar:
            col_edit1, col_edit2 = st.columns(2)
            
            with col_edit1:
                producto_a_editar = st.selectbox(
                    "Selecciona producto a editar:",
                    productos_lista_editar,
                    key="edit_select"
                )
            
            with col_edit2:
                # Extraer ID del producto seleccionado
                if producto_a_editar:
                    product_id = int(producto_a_editar.split("ID ")[1].split(":")[0])
                    
                    # Obtener datos actuales del producto
                    producto_actual = productos_df[productos_df['id'] == product_id].iloc[0]
                    
                    nueva_cantidad = st.number_input(
                        "Nueva cantidad:",
                        min_value=0,
                        value=int(producto_actual['cantidad']),
                        step=1,
                        key=f"cantidad_{product_id}"
                    )
                    
                    nuevo_departamento = st.selectbox(
                        "Nuevo departamento:",
                        DEPARTAMENTOS,
                        index=DEPARTAMENTOS.index(producto_actual['departamento']) if producto_actual['departamento'] in DEPARTAMENTOS else 0,
                        key=f"depto_{product_id}"
                    )
                    
                    if st.button("✅ Actualizar Producto", type="primary", use_container_width=True):
                        cambios = False
                        
                        if nueva_cantidad != producto_actual['cantidad']:
                            cambios = True
                        
                        if nuevo_departamento != producto_actual['departamento']:
                            cambios = True
                        
                        if cambios:
                            success = update_product(conn, product_id, nueva_cantidad, nuevo_departamento)
                            if success:
                                st.success(f"✅ Producto actualizado correctamente.")
                                st.rerun()
                            else:
                                st.error("❌ No se pudo actualizar el producto.")
                        else:
                            st.info("ℹ️ No se detectaron cambios para actualizar.")
    
    with tab2:
        st.write("Elimina permanentemente un producto del inventario:")
        
        # Crear lista de productos para eliminar
        productos_lista_eliminar = productos_df[['id', 'nombre', 'departamento']].apply(
            lambda x: f"ID {x['id']}: {x['nombre']} ({x['departamento']})", axis=1
        ).tolist()
        
        if productos_lista_eliminar:
            col_del1, col_del2 = st.columns([2, 1])
            
            with col_del1:
                producto_a_eliminar = st.selectbox(
                    "Selecciona producto a eliminar:",
                    productos_lista_eliminar,
                    key="delete_select"
                )
            
            with col_del2:
                st.write("")  # Espacio
                st.write("")  # Espacio
                if st.button("❌ Eliminar Producto", type="secondary", use_container_width=True):
                    # Extraer el ID del producto seleccionado
                    product_id = int(producto_a_eliminar.split("ID ")[1].split(":")[0])
                    product_name = producto_a_eliminar.split(": ")[1].split(" (")[0]
                    
                    # Confirmación
                    with st.expander("⚠️ Confirmar eliminación", expanded=True):
                        st.warning(f"¿Estás seguro de eliminar el producto '{product_name}'?")
                        st.error("**ADVERTENCIA:** Esta acción no se puede deshacer.")
                        
                        col_confirm1, col_confirm2 = st.columns(2)
                        
                        with col_confirm1:
                            if st.button("✅ Sí, eliminar", type="primary", use_container_width=True):
                                rows_deleted = delete_product(conn, product_id)
                                if rows_deleted > 0:
                                    st.success(f"✅ Producto '{product_name}' eliminado correctamente.")
                                    st.rerun()
                                else:
                                    st.error("❌ No se pudo eliminar el producto.")
                        
                        with col_confirm2:
                            if st.button("❌ Cancelar", use_container_width=True):
                                st.info("Eliminación cancelada.")

# =================================================================
# SECCIÓN: VISTA POR DEPARTAMENTOS
# =================================================================
st.divider()
st.header("🏢 Vista por Departamentos")

# Obtener estadísticas por departamento
stats_departamentos = get_departamento_stats(conn)

if not stats_departamentos.empty:
    # Crear tabs para cada departamento
    tabs_departamentos = st.tabs([f"📦 {depto}" for depto in DEPARTAMENTOS])
    
    for i, depto in enumerate(DEPARTAMENTOS):
        with tabs_departamentos[i]:
            # Filtrar productos por departamento
            productos_depto = productos_df[productos_df['departamento'] == depto] if not productos_df.empty else pd.DataFrame()
            
            if not productos_depto.empty:
                # Estadísticas del departamento
                col_depto1, col_depto2, col_depto3 = st.columns(3)
                
                with col_depto1:
                    st.metric("Productos en departamento", len(productos_depto))
                
                with col_depto2:
                    total_unidades_depto = int(productos_depto['cantidad'].sum())
                    st.metric("Total unidades", total_unidades_depto)
                
                with col_depto3:
                    unidades_usadas = productos_depto['unidad_medida'].nunique()
                    st.metric("Tipos de unidad", unidades_usadas)
                
                # Mostrar productos del departamento
                st.dataframe(
                    productos_depto[['nombre', 'cantidad', 'unidad_medida', 'fecha_actualizacion']],
                    use_container_width=True,
                    column_config={
                        "nombre": "Producto",
                        "cantidad": "Cantidad",
                        "unidad_medida": "Unidad",
                        "fecha_actualizacion": "Última Actualización"
                    }
                )
            else:
                st.info(f"No hay productos registrados en el departamento {depto}")
else:
    st.info("No hay datos de departamentos disponibles")

# =================================================================
# SECCIÓN: EXPORTAR DATOS
# =================================================================
st.divider()
st.header("📥 Exportar Datos")

col_export1, col_export2, col_export3 = st.columns(3)

with col_export1:
    # Exportar a CSV (todo)
    csv = productos_df.to_csv(index=False)
    st.download_button(
        label="📄 Descargar CSV (Todo)",
        data=csv,
        file_name=f"inventario_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True,
        help="Descarga todos los productos en formato CSV"
    )

with col_export2:
    # Exportar por departamento
    if not productos_df.empty and 'departamento' in productos_df.columns:
        departamentos_disponibles = productos_df['departamento'].unique()
        depto_seleccionado = st.selectbox(
            "Exportar departamento:",
            departamentos_disponibles,
            key="export_depto"
        )
        
        productos_depto_export = productos_df[productos_df['departamento'] == depto_seleccionado]
        csv_depto = productos_depto_export.to_csv(index=False)
        
        st.download_button(
            label=f"📁 CSV {depto_seleccionado}",
            data=csv_depto,
            file_name=f"inventario_{depto_seleccionado}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
            help=f"Descarga solo productos del departamento {depto_seleccionado}"
        )

with col_export3:
    # Exportar estadísticas
    if not stats_departamentos.empty:
        csv_stats = stats_departamentos.to_csv(index=False)
        st.download_button(
            label="📊 Estadísticas CSV",
            data=csv_stats,
            file_name=f"estadisticas_inventario_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
            help="Descarga estadísticas por departamento"
        )

# =================================================================
# SECCIÓN: INFORMACIÓN Y AYUDA
# =================================================================
with st.expander("ℹ️ Instrucciones de uso e información", expanded=False):
    st.markdown("""
    ### 📋 Cómo usar esta aplicación:
    
    **1. Añadir nuevo producto:**
    - Completa todos los campos del formulario (marcados con *)
    - Selecciona el departamento donde se encuentra el producto
    - Haz clic en "Guardar Producto"
    
    **2. Navegar por el inventario:**
    - Usa el filtro en la barra lateral para ver productos por departamento
    - Explora la vista por departamentos en la sección inferior
    - Consulta las estadísticas en la barra lateral
    
    **3. Gestionar productos:**
    - **Editar**: Cambia cantidad o mueve productos entre departamentos
    - **Eliminar**: Elimina productos permanentemente (con confirmación)
    
    **4. Exportar datos:**
    - Descarga todo el inventario en CSV
    - Exporta por departamento específico
    - Descarga estadísticas generales
    
    ### 🏢 Departamentos disponibles:
    1. **Logística**: Productos relacionados con transporte y distribución
    2. **Almacén**: Productos de almacenamiento general
    3. **Ático**: Productos en almacenamiento a largo plazo
    4. **Laboratorio**: Materiales y equipos de laboratorio
    5. **Oficina**: Material de oficina y suministros
    6. **Taller**: Herramientas y materiales de taller
    
    ### 💡 Consejos:
    - Usa nombres descriptivos y consistentes
    - Actualiza las cantidades regularmente
    - Exporta copias de seguridad periódicamente
    - Usa el historial para trackear movimientos
    """)

# Pie de página
st.divider()
footer_col1, footer_col2, footer_col3 = st.columns(3)
with footer_col1:
    st.caption(f"Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
with footer_col2:
    st.caption(f"Total productos en sistema: {len(productos_df) if not productos_df.empty else 0}")
with footer_col3:
    st.caption("© Sistema de Gestión de Inventario v2.0")

# Nota: En una aplicación real, considerarías cerrar la conexión apropiadamente
# En Streamlit, el caché_resource maneja esto automáticamente
