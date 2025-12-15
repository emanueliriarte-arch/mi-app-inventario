import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

# Nombre de la base de datos.
DB_NAME = 'inventario.db'

# --- Funciones de la Base de Datos ---

@st.cache_resource
def get_connection():
    """Establece y devuelve la conexión a la base de datos."""
    conn = sqlite3.connect(DB_NAME)
    return conn

def init_db(conn):
    """Inicializa la tabla de productos con las nuevas columnas."""
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY,
            nombre TEXT NOT NULL,
            cantidad INTEGER,
            precio REAL,
            unidad_medida TEXT,       
            fecha_caducidad TEXT      
        )
    ''')
    conn.commit()

def add_product(conn, nombre, cantidad, precio, unidad_medida, fecha_caducidad):
    """Inserta un nuevo producto con todos los detalles."""
    c = conn.cursor()
    c.execute("INSERT INTO productos (nombre, cantidad, precio, unidad_medida, fecha_caducidad) VALUES (?, ?, ?, ?, ?)", 
              (nombre, cantidad, precio, unidad_medida, fecha_caducidad))
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

# 2. Formulario para Añadir Productos
st.header("Añadir Nuevo Producto")

# Usamos st.form para agrupar los inputs
with st.form("add_product_form"):
    
    # CAMPOS ORIGINALES
    nombre = st.text_input("Nombre del Producto:")
    cantidad = st.number_input("Cantidad:", min_value=1, step=1)
    precio = st.number_input("Precio:", min_value=0.01, format="%.2f")
    
    # NUEVO CAMPO 1: UNIDAD DE MEDIDA
    unidad = st.selectbox(
        "Unidad de Medida:",
        ("Unidades (Und)", "Kilogramos (Kg)", "Litros (L)", "Metros (m)", "Otros")
    )
    
    # NUEVO CAMPO 2 & 3: FECHA DE CADUCIDAD
    tiene_caducidad = st.checkbox("¿Tiene fecha de caducidad?")
    
    fecha_caducidad_valor = "" # Valor por defecto

    # El campo de fecha SOLO se muestra si el checkbox está marcado
    if tiene_caducidad:
        # Usamos st.date_input para pedir la fecha
        fecha_caducidad_valor = st.date_input(
            "Fecha de Caducidad:",
            min_value=date.today()
        )
    
    # Botón de Submit
    submitted = st.form_submit_button("Guardar Producto")

    if submitted:
        if nombre:
            # Convertimos la fecha a texto para guardarla en SQLite
            fecha_str = str(fecha_caducidad_valor) if fecha_caducidad_valor else None
            
            try:
                add_product(conn, nombre, cantidad, precio, unidad, fecha_str)
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
