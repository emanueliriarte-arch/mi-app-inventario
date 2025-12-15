import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

# Nombre de la base de datos.
DB_NAME = 'inventario_final.db' 
# NOTA: Cambié el nombre del archivo DB para forzar la creación de la tabla con la nueva estructura (sin 'precio').

# --- Funciones de la Base de Datos ---

@st.cache_resource
def get_connection():
    """Establece y devuelve la conexión a la base de datos."""
    conn = sqlite3.connect(DB_NAME)
    return conn

def init_db(conn):
    """Inicializa la tabla de productos con la estructura exacta solicitada."""
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY,
            nombre TEXT NOT NULL,
            cantidad INTEGER,
            unidad_medida TEXT,       
            fecha_caducidad TEXT      
        )
    ''')
    conn.commit()

def add_product(conn, nombre, cantidad, unidad_medida, fecha_caducidad):
    """Inserta un nuevo producto con los cuatro detalles solicitados."""
    c = conn.cursor()
    # Ejecutamos la inserción con los cuatro campos
    c.execute("INSERT INTO productos (nombre, cantidad, unidad_medida, fecha_caducidad) VALUES (?, ?, ?, ?)", 
              (nombre, cantidad, unidad_medida, fecha_caducidad))
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

# Usamos st.form para agrupar los inputs
with st.form("add_product_form"):
    
    # Campo 1: Nombre del producto
    nombre = st.text_input("Nombre del Producto:")
    
    # Campo 2: Cantidad
    cantidad = st.number_input("Cantidad:", min_value=1, step=1)
    
    # Campo 3: Unidad de Medida (Selectbox con opciones exactas)
    unidad = st.selectbox(
        "Unidad de Medida:",
        ("Unitario", "Kg", "Gramo", "Ml")
    )
    
    # Campo 4: Lógica de Fecha de Caducidad
    tiene_caducidad = st.radio(
        "¿Tiene fecha de caducidad?",
        ("No", "Sí"),
        index=0 # Por defecto, selecciona "No"
    )
    
    fecha_caducidad_valor = None # Inicializa como nulo
    fecha_str = None # Valor que se guardará en la base de datos

    # El campo de fecha SOLO se muestra si el usuario selecciona "Sí"
    if tiene_caducidad == "Sí":
        # Usamos st.date_input para pedir la fecha
        fecha_caducidad_valor = st.date_input(
            "Selecciona la Fecha de Caducidad:",
            min_value=date.today()
        )
        # Convertimos a string para guardar en la DB si hay valor
        fecha_str = str(fecha_caducidad_valor)

    
    # Botón de Submit
    submitted = st.form_submit_button("Guardar Producto")

    if submitted:
        if nombre:
            try:
                # La fecha_str será None si no tiene caducidad, cumpliendo la lógica
                add_product(conn, nombre, cantidad, unidad, fecha_str)
                st.success(f"Producto '{nombre}' añadido con éxito.")
                st.experimental_rerun() # Refresca la tabla después de guardar
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
