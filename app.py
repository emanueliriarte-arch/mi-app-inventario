import streamlit as st
import sqlite3
import pandas as pd

# Nombre de la base de datos.
DB_NAME = 'inventario_final.db' 

# --- Funciones de la Base de Datos ---

@st.cache_resource
def get_connection():
    """Establece la conexión a la base de datos."""
    conn = sqlite3.connect(DB_NAME)
    return conn

def init_db(conn):
    """Inicializa la tabla de productos."""
    c = conn.cursor()
    
    # Asegura la estructura correcta eliminando la tabla vieja si existe.
    c.execute('DROP TABLE IF EXISTS productos')
    
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
    """Inserta un nuevo producto."""
    c = conn.cursor()
    c.execute("INSERT INTO productos (nombre, cantidad, unidad_medida) VALUES (?, ?, ?)", 
              (nombre, cantidad, unidad_medida))
    conn.commit()

def view_all_products(conn):
    """Recupera todos los productos."""
    df = pd.read_sql_query("SELECT id, nombre, cantidad, unidad_medida FROM productos", conn)
    return df

# --- Configuración de la Aplicación Streamlit ---

conn = get_connection()
init_db(conn)

st.title("Gestión de Inventario Simple")


# =================================================================
# FORMULARIO
# =================================================================

st.header("Añadir Nuevo Producto")

with st.form("add_product_form"):
    
    nombre = st.text_input("Nombre del Producto:")
    cantidad = st.number_input("Cantidad:", min_value=1, step=1)
    
    unidad = st.selectbox(
        "Unidad de Medida:",
        ("Unitario", "Kg", "Gramo", "Ml")
    )
    
    submitted = st.form_submit_button("Guardar Producto")

    if submitted:
        if nombre:
            try:
                add_product(conn, nombre, cantidad, unidad)
                st.success(f"Producto '{nombre}' añadido con éxito.")
                st.rerun() 
            except Exception as e:
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
