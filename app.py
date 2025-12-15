import streamlit as st
import sqlite3
import pandas as pd

# Nombre de la base de datos.
DB_NAME = 'inventario_final_v6.db' 

# --- Funciones de la Base de Datos ---

@st.cache_resource
def get_connection():
    """Establece y devuelve la conexión a la base de datos."""
    conn = sqlite3.connect(DB_NAME)
    return conn

def init_db(conn):
    """
    Inicializa la tabla de productos.
    Usamos DROP TABLE para asegurar que la estructura sea la correcta (nombre, cantidad, unidad_medida).
    """
    c = conn.cursor()
    
    # 1. ELIMINAR la tabla vieja (si existe) para evitar conflictos de estructura.
    c.execute('DROP TABLE IF EXISTS productos')
    
    # 2. CREAR la tabla con la estructura limpia y correcta.
    c.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY,
            nombre TEXT NOT NULL,
            cantidad INTEGER,
            unidad_medida TEXT       
        )
    ''')
    conn.commit()

def add_product(conn, nombre, cantidad, unidad_medida):
    """Inserta un nuevo producto con los tres detalles solicitados."""
    c = conn.cursor()
    c.execute("INSERT INTO productos (nombre, cantidad, unidad_medida) VALUES (?, ?, ?)", 
              (nombre, cantidad, unidad_medida))
    conn.commit()

def view_all_products(conn):
    """Recupera todos los productos y los devuelve como DataFrame."""
    df = pd.read_sql_query("SELECT id, nombre, cantidad, unidad_medida FROM productos", conn)
    return df

# --- Configuración y Lógica de la Aplicación Streamlit ---

# 1. Conexión e Inicialización
conn = get_connection()
init_db(conn)

st.title("Gestión de Inventario Simple (Streamlit + SQLite)")
st.caption(f"Base de datos SQLite: {DB_NAME}")


# =================================================================
# FORMULARIO
# =================================================================

st.header("Añadir Nuevo Producto")

with st.form("add_product_form"):
    
    # Campo 1: Nombre del producto
    nombre = st.text_input("Nombre del Producto:")
    
    # Campo 2: Cantidad
    cantidad = st.number_input("Cantidad:", min_value=1, step=1)
    
    # Campo 3: Unidad de Medida
    unidad = st.selectbox(
        "Unidad de Medida:",
        ("Unitario", "Kg", "Gramo", "Ml")
    )
    
    # Botón de Submit
    submitted = st.form_submit_button("Guardar Producto")

    if submitted:
        if nombre:
            try:
                add_product(conn, nombre, cantidad, unidad)
                st.success(f"Producto '{nombre}' añadido con éxito.")
                
                # ¡¡¡CORRECCIÓN AQUÍ!!!
                st.rerun() # Usamos la función actualizada para recargar
                
            except Exception as e:
                # Muestra el error de Python en la web si falla (útil para depurar)
                st.error(f"Error al guardar: {e}") 
        else:
            st.error("El nombre del producto no puede estar vacío.")

# 3. Visualización del Inventario
st.header("Inventario Actual")
productos_df = view_all_products(conn)

if productos_df.empty:
    st.info("El inventario está vacío. Añade un producto arriba.")
else:
    st.dataframe(productos_df, use_container_width=True)
