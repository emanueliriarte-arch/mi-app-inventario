import streamlit as st
import sqlite3
import pandas as pd

# Nombre de la base de datos.
# ¡RECUERDA!: Los datos se borrarán cuando el servidor se reinicie.
DB_NAME = 'inventario.db'

# --- Funciones de la Base de Datos ---

@st.cache_resource
def get_connection():
    """Establece y devuelve la conexión a la base de datos."""
    conn = sqlite3.connect(DB_NAME)
    return conn

def init_db(conn):
    """Inicializa la tabla de productos si no existe."""
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY,
            nombre TEXT NOT NULL,
            cantidad INTEGER,
            precio REAL
        )
    ''')
    conn.commit()

def add_product(conn, nombre, cantidad, precio):
    """Inserta un nuevo producto en la base de datos."""
    c = conn.cursor()
    c.execute("INSERT INTO productos (nombre, cantidad, precio) VALUES (?, ?, ?)", 
              (nombre, cantidad, precio))
    conn.commit()

def view_all_products(conn):
    """Recupera todos los productos y los devuelve como DataFrame."""
    df = pd.read_sql_query("SELECT * FROM productos", conn)
    return df

# --- Configuración y Lógica de la Aplicación Streamlit ---

# 1. Conexión e Inicialización
conn = get_connection()
init_db(conn)

st.title("Gestión de Inventario (Streamlit + SQLite)")
st.caption(f"Base de datos SQLite: {DB_NAME}")

# 2. Formulario para Añadir Productos (Interfaz Streamlit)
st.header("Añadir Nuevo Producto")

# Usamos st.form para agrupar los inputs y el botón
with st.form("add_product_form"):
    nombre = st.text_input("Nombre del Producto:")
    cantidad = st.number_input("Cantidad:", min_value=1, step=1)
    precio = st.number_input("Precio:", min_value=0.01, format="%.2f")
    
    # El botón de Submit está DENTRO del formulario
    submitted = st.form_submit_button("Guardar Producto")

    if submitted:
        if nombre:
            try:
                add_product(conn, nombre, cantidad, precio)
                st.success(f"Producto '{nombre}' añadido con éxito.")
                # st.rerun() # Esto refresca la página, pero no siempre es necesario
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
    # Muestra los datos en una tabla interactiva de Streamlit
    st.dataframe(productos_df, use_container_width=True)
