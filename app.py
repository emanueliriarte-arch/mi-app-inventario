import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import pandas as pd
from datetime import datetime
import os

class InventarioApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Control de Insumos e Inventario")
        self.root.geometry("1100x700")

        # Conexión a Base de Datos
        self.conn = sqlite3.connect("inventario_insumos.db")
        self.crear_tablas()

        # --- Variables ---
        self.var_nombre = tk.StringVar()
        self.var_cantidad = tk.DoubleVar()
        self.var_unidad = tk.StringVar()
        self.var_caducidad = tk.StringVar()
        self.var_ubicacion = tk.StringVar()
        self.var_accion_cantidad = tk.DoubleVar() # Para sumar/restar

        # --- Interfaz Gráfica ---
        self.crear_widgets()
        self.cargar_datos()

    def crear_tablas(self):
        cursor = self.conn.cursor()
        # Tabla Inventario
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS insumos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT,
                nombre TEXT,
                cantidad REAL,
                unidad TEXT,
                caducidad TEXT,
                ubicacion TEXT
            )
        ''')
        # Tabla Historial
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT,
                nombre TEXT,
                tipo_movimiento TEXT,
                cantidad_movida REAL,
                fecha TEXT
            )
        ''')
        self.conn.commit()

    def crear_widgets(self):
        # Marco de Registro
        frame_registro = tk.LabelFrame(self.root, text="Nuevo Insumo", padx=10, pady=10)
        frame_registro.pack(fill="x", padx=10, pady=5)

        # Campos
        tk.Label(frame_registro, text="Nombre:").grid(row=0, column=0)
        tk.Entry(frame_registro, textvariable=self.var_nombre).grid(row=0, column=1)

        tk.Label(frame_registro, text="Cantidad Inicial:").grid(row=0, column=2)
        tk.Entry(frame_registro, textvariable=self.var_cantidad).grid(row=0, column=3)

        tk.Label(frame_registro, text="Unidad (kg, lts, pza):").grid(row=0, column=4)
        tk.Entry(frame_registro, textvariable=self.var_unidad).grid(row=0, column=5)

        tk.Label(frame_registro, text="Caducidad (DD/MM/AAAA):").grid(row=0, column=6)
        tk.Entry(frame_registro, textvariable=self.var_caducidad).grid(row=0, column=7)

        tk.Label(frame_registro, text="Ubicación:").grid(row=0, column=8)
        tk.Entry(frame_registro, textvariable=self.var_ubicacion).grid(row=0, column=9)

        tk.Button(frame_registro, text="Guardar Insumo", command=self.agregar_insumo, bg="#4CAF50", fg="white").grid(row=0, column=10, padx=10)

        # Marco de Gestión (Tabla y Acciones)
        frame_gestion = tk.LabelFrame(self.root, text="Gestión de Inventario", padx=10, pady=10)
        frame_gestion.pack(fill="both", expand=True, padx=10, pady=5)

        # Tabla (Treeview)
        columns = ("SKU", "Nombre", "Cantidad", "Unidad", "Caducidad", "Ubicación")
        self.tree = ttk.Treeview(frame_gestion, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)
        self.tree.pack(side="left", fill="both", expand=True)

        # Scrollbar
        scrollbar = ttk.Scrollbar(frame_gestion, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # Marco de Acciones (Sumar/Restar/Exportar)
        frame_acciones = tk.LabelFrame(self.root, text="Acciones", padx=10, pady=10)
        frame_acciones.pack(fill="x", padx=10, pady=5)

        tk.Label(frame_acciones, text="Cantidad a Mover:").pack(side="left")
        tk.Entry(frame_acciones, textvariable=self.var_accion_cantidad, width=10).pack(side="left", padx=5)
        
        tk.Button(frame_acciones, text="➕ Agregar Stock", command=lambda: self.actualizar_stock("entrada")).pack(side="left", padx=5)
        tk.Button(frame_acciones, text="➖ Restar Stock", command=lambda: self.actualizar_stock("salida")).pack(side="left", padx=5)
        
        tk.Button(frame_acciones, text="📊 Ver Historial", command=self.ver_historial).pack(side="left", padx=20)
        tk.Button(frame_acciones, text="📥 Exportar Excel", command=self.exportar_excel, bg="#2196F3", fg="white").pack(side="right", padx=10)

    def agregar_insumo(self):
        if self.var_nombre.get() == "":
            messagebox.showerror("Error", "El nombre es obligatorio")
            return

        cursor = self.conn.cursor()
        # Insertamos primero para obtener el ID
        cursor.execute('''
            INSERT INTO insumos (nombre, cantidad, unidad, caducidad, ubicacion)
            VALUES (?, ?, ?, ?, ?)
        ''', (self.var_nombre.get(), self.var_cantidad.get(), self.var_unidad.get(), self.var_caducidad.get(), self.var_ubicacion.get()))
        
        id_insertado = cursor.lastrowid
        sku_generado = f"A{id_insertado}" # Genera A1, A2, A3...

        # Actualizamos el registro con el SKU generado
        cursor.execute('UPDATE insumos SET sku = ? WHERE id = ?', (sku_generado, id_insertado))
        
        # Guardar en historial (Entrada inicial)
        self.registrar_historial(sku_generado, self.var_nombre.get(), "Entrada Inicial", self.var_cantidad.get())

        self.conn.commit()
        self.cargar_datos()
        self.limpiar_campos()
        messagebox.showinfo("Éxito", f"Insumo agregado con SKU: {sku_generado}")

    def cargar_datos(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT sku, nombre, cantidad, unidad, caducidad, ubicacion FROM insumos")
        rows = cursor.fetchall()
        for row in rows:
            self.tree.insert("", "end", values=row)

    def actualizar_stock(self, tipo):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atención", "Selecciona un insumo de la lista primero")
            return
        
        item = self.tree.item(selected)
        sku_actual = item['values'][0]
        nombre_actual = item['values'][1]
        cantidad_actual = float(item['values'][2])
        cantidad_mover = self.var_accion_cantidad.get()

        if cantidad_mover <= 0:
            messagebox.showerror("Error", "La cantidad debe ser mayor a 0")
            return

        nueva_cantidad = 0
        if tipo == "entrada":
            nueva_cantidad = cantidad_actual + cantidad_mover
        elif tipo == "salida":
            if cantidad_mover > cantidad_actual:
                messagebox.showerror("Error", "No hay suficiente stock")
                return
            nueva_cantidad = cantidad_actual - cantidad_mover

        cursor = self.conn.cursor()
        cursor.execute("UPDATE insumos SET cantidad = ? WHERE sku = ?", (nueva_cantidad, sku_actual))
        
        # Registrar en historial
        self.registrar_historial(sku_actual, nombre_actual, tipo.capitalize(), cantidad_mover)
        
        self.conn.commit()
        self.cargar_datos()
        self.var_accion_cantidad.set(0)

    def registrar_historial(self, sku, nombre, tipo, cantidad):
        cursor = self.conn.cursor()
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            INSERT INTO historial (sku, nombre, tipo_movimiento, cantidad_movida, fecha)
            VALUES (?, ?, ?, ?, ?)
        ''', (sku, nombre, tipo, cantidad, fecha_actual))

    def ver_historial(self):
        hist_window = tk.Toplevel(self.root)
        hist_window.title("Historial de Movimientos")
        hist_window.geometry("600x400")

        cols = ("SKU", "Nombre", "Movimiento", "Cantidad", "Fecha")
        tree_hist = ttk.Treeview(hist_window, columns=cols, show="headings")
        for col in cols:
            tree_hist.heading(col, text=col)
            tree_hist.column(col, width=100)
        tree_hist.pack(fill="both", expand=True)

        cursor = self.conn.cursor()
        cursor.execute("SELECT sku, nombre, tipo_movimiento, cantidad_movida, fecha FROM historial ORDER BY id DESC")
        for row in cursor.fetchall():
            tree_hist.insert("", "end", values=row)

    def exportar_excel(self):
        try:
            cursor = self.conn.cursor()
            # Exportar Inventario
            df_inv = pd.read_sql_query("SELECT * FROM insumos", self.conn)
            # Exportar Historial
            df_hist = pd.read_sql_query("SELECT * FROM historial", self.conn)

            file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
            
            if file_path:
                with pd.ExcelWriter(file_path) as writer:
                    df_inv.to_excel(writer, sheet_name='Inventario Actual', index=False)
                    df_hist.to_excel(writer, sheet_name='Historial Movimientos', index=False)
                messagebox.showinfo("Éxito", "Archivo exportado correctamente")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar: {e}")

    def limpiar_campos(self):
        self.var_nombre.set("")
        self.var_cantidad.set(0)
        self.var_unidad.set("")
        self.var_caducidad.set("")
        self.var_ubicacion.set("")

if __name__ == "__main__":
    root = tk.Tk()
    app = InventarioApp(root)
    root.mainloop()