import streamlit as st
import sqlite3
import pandas as pd

# Nombre de la base de datos.
DB_NAME = 'inventario_final.db' 

# --- Funciones de la Base de Datos ---

@st.cache_resource
def get_connection():
    """Establece la conexión a la base de datos."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    return conn

def init_db(conn):
    """Inicializa la tabla de productos sin eliminar datos existentes."""
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            cantidad INTEGER,
            unidad_medida TEXT       
        )
    ''')
    conn.commit()

def add_product(conn, nombre, cantidad, unidad_medida):
    """Inserta un nuevo producto y retorna su ID."""
    c = conn.cursor()
    c.execute("""
        INSERT INTO productos (nombre, cantidad, unidad_medida) 
        VALUES (?, ?, ?)
    """, (nombre, cantidad, unidad_medida))
    conn.commit()
    return c.lastrowid

def view_all_products(conn):
    """Recupera todos los productos ordenados por nombre."""
    df = pd.read_sql_query("""
        SELECT id, nombre, cantidad, unidad_medida 
        FROM productos 
        ORDER BY nombre
    """, conn)
    return df

def delete_product(conn, product_id):
    """Elimina un producto por ID."""
    c = conn.cursor()
    c.execute("DELETE FROM productos WHERE id = ?", (product_id,))
    conn.commit()
    return c.rowcount  # Retorna cuántas filas fueron eliminadas

# --- Configuración de la Aplicación Streamlit ---

conn = get_connection()
init_db(conn)

st.title("📦 Gestión de Inventario Simple")

# =================================================================
# SECCIÓN: AÑADIR NUEVO PRODUCTO
# =================================================================
st.header("➕ Añadir Nuevo Producto")

with st.form("add_product_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    
    with col1:
        nombre = st.text_input("Nombre del Producto:", max_chars=100)
        unidad = st.selectbox(
            "Unidad de Medida:",
            ("Unitario", "Kg", "Gramo", "Ml", "Litro", "Metro", "Caja", "Paquete")
        )
    
    with col2:
        cantidad = st.number_input("Cantidad:", min_value=0, step=1, value=1)
        st.write("")  # Espacio en blanco para alineación
        st.write("")  # Más espacio
    
    submitted = st.form_submit_button("💾 Guardar Producto")

if submitted:
    if nombre and nombre.strip():
        try:
            product_id = add_product(conn, nombre.strip(), cantidad, unidad)
            st.success(f"✅ Producto '{nombre}' añadido con éxito (ID: {product_id}).")
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

# Obtener y mostrar productos
productos_df = view_all_products(conn)

if productos_df.empty:
    st.info("📭 El inventario está vacío. Añade un producto arriba.")
else:
    # Mostrar estadísticas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Total de productos", len(productos_df))
    with col2:
        st.metric("📈 Total de unidades", int(productos_df['cantidad'].sum()))
    with col3:
        unidades_unicas = productos_df['unidad_medida'].nunique()
        st.metric("📐 Tipos de unidad", unidades_unicas)
    
    st.divider()
    
    # Mostrar tabla de productos
    st.subheader("Lista de Productos")
    
    # Crear una copia para mostrar (sin el ID si quieres)
    display_df = productos_df.copy()
    display_df.index = range(1, len(display_df) + 1)  # Numeración empezando en 1
    
    st.dataframe(
        display_df,
        use_container_width=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "nombre": "Producto",
            "cantidad": "Cantidad",
            "unidad_medida": "Unidad"
        }
    )
    
    # =================================================================
    # SECCIÓN: ELIMINAR PRODUCTO (OPCIONAL)
    # =================================================================
    st.divider()
    st.subheader("🗑️ Eliminar Producto")
    
    # Crear lista de productos para el selectbox
    productos_lista = productos_df[['id', 'nombre']].apply(
        lambda x: f"ID {x['id']}: {x['nombre']}", axis=1
    ).tolist()
    
    if productos_lista:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            producto_a_eliminar = st.selectbox(
                "Selecciona un producto para eliminar:",
                productos_lista,
                key="delete_select"
            )
        
        with col2:
            st.write("")  # Espacio
            st.write("")  # Espacio
            if st.button("❌ Eliminar", type="secondary", use_container_width=True):
                # Extraer el ID del producto seleccionado
                product_id = int(producto_a_eliminar.split("ID ")[1].split(":")[0])
                product_name = producto_a_eliminar.split(": ")[1]
                
                # Confirmación
                with st.expander("⚠️ Confirmar eliminación", expanded=True):
                    st.warning(f"¿Estás seguro de eliminar el producto '{product_name}' (ID: {product_id})?")
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
    # SECCIÓN: EXPORTAR DATOS
    # =================================================================
    st.divider()
    st.subheader("📥 Exportar Datos")
    
    col_export1, col_export2 = st.columns(2)
    
    with col_export1:
        # Exportar a CSV
        csv = productos_df.to_csv(index=False)
        st.download_button(
            label="📄 Descargar CSV",
            data=csv,
            file_name="inventario.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col_export2:
        # Exportar a Excel
        excel_buffer = pd.ExcelWriter('inventario_temp.xlsx', engine='openpyxl')
        productos_df.to_excel(excel_buffer, index=False, sheet_name='Inventario')
        excel_buffer.close()
        
        with open('inventario_temp.xlsx', 'rb') as f:
            excel_data = f.read()
        
        st.download_button(
            label="📊 Descargar Excel",
            data=excel_data,
            file_name="inventario.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

# =================================================================
# SECCIÓN: INSTRUCCIONES Y AYUDA
# =================================================================
with st.expander("ℹ️ Instrucciones de uso"):
    st.markdown("""
    ### Cómo usar esta aplicación:
    
    1. **Añadir producto**: Completa el formulario arriba y haz clic en "Guardar Producto"
    2. **Ver inventario**: Todos los productos aparecen automáticamente en la tabla
    3. **Eliminar producto**: Selecciona un producto y confirma la eliminación
    4. **Exportar datos**: Descarga tu inventario en formato CSV o Excel
    
    ### Consejos:
    - Usa nombres descriptivos para los productos
    - Revisa el inventario regularmente
    - Exporta una copia de seguridad periódicamente
    """)

# Pie de página
st.divider()
st.caption("© Sistema de Gestión de Inventario - Desarrollado con Streamlit y SQLite")

# Nota: La conexión se cierra automáticamente al finalizar la ejecución
# pero en una app más compleja, deberías manejar el cierre explícito
