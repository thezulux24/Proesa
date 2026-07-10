import os
import datetime
import sqlite3
from dotenv import load_dotenv

class DataSuiteDB:
    def __init__(self, db_name="suite_data.db"):
        load_dotenv() # Load from .env file
        self.db_name = db_name
        
    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def init_db(self):
        """Creates the necessary tables for tracking product prices over time."""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS productos_historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_extraccion DATE NOT NULL,
            comercio VARCHAR(50) NOT NULL,
            producto_id VARCHAR(100) NOT NULL,
            nombre TEXT NOT NULL,
            marca VARCHAR(200),
            referencia VARCHAR(200),
            categoria VARCHAR(100),
            tipo_producto VARCHAR(100),
            grados_alcohol VARCHAR(50),
            medida VARCHAR(100),
            precio_original NUMERIC(12,2),
            precio_final NUMERIC(12,2),
            descuento_porcentaje VARCHAR(50),
            precio_unidad VARCHAR(50),
            url_producto TEXT,
            descripcion TEXT,
            deleted INTEGER DEFAULT 0,
            UNIQUE (fecha_extraccion, comercio, producto_id)
        );
        """
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(create_table_query)
                conn.commit()
            print("Database tables initialized successfully.")
        except Exception as e:
            print(f"Failed to initialize database: {e}")
            raise e

    def insert_products(self, comercio, products):
        """
        Inserts a list of product dictionaries into the database.
        Uses executemany for bulk insertion.
        """
        if not products:
            return 0
            
        today = datetime.date.today()
        
        insert_query = """
        INSERT INTO productos_historico (
            fecha_extraccion, comercio, producto_id, nombre, marca, referencia, 
            categoria, tipo_producto, grados_alcohol, medida, precio_original, 
            precio_final, descuento_porcentaje, precio_unidad, url_producto, descripcion
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (fecha_extraccion, comercio, producto_id) 
        DO UPDATE SET 
            nombre = EXCLUDED.nombre,
            precio_original = EXCLUDED.precio_original,
            precio_final = EXCLUDED.precio_final,
            descuento_porcentaje = EXCLUDED.descuento_porcentaje;
        """
        
        # Prepare the tuple list
        values = []
        for p in products:
            # Handle possible string NULLs or N/A for numeric fields
            po = p.get('Precio_Original')
            pf = p.get('Precio_Final')
            
            po = None if po in ('NULL', 'N/A', '') else po
            pf = None if pf in ('NULL', 'N/A', '') else pf
            
            val = (
                today,
                comercio,
                str(p.get('ID', '')),
                str(p.get('Nombre', '')),
                str(p.get('Marca', '')),
                str(p.get('Referencia', '')),
                str(p.get('Categoria', '')),
                str(p.get('Tipo de Producto', '')),
                str(p.get('Grados de alcohol', '')),
                str(p.get('Medida', '')),
                po,
                pf,
                str(p.get('Descuento_%', '')),
                str(p.get('Precio_Unidad', '')),
                str(p.get('URL_Producto', '')),
                str(p.get('Descripcion', ''))
            )
            values.append(val)
            
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.executemany(insert_query, values)
                conn.commit()
            print(f"Successfully inserted/updated {len(values)} products for {comercio}.")
            return len(values)
        except Exception as e:
            print(f"Failed to insert products for {comercio}: {e}")
            raise e

# ==========================================
# Funciones helper para suite_app.py
# ==========================================
import pandas as pd

def get_available_sources():
    db = DataSuiteDB()
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT comercio FROM productos_historico WHERE deleted = 0")
        return [row[0] for row in cur.fetchall()]

def get_available_dates():
    db = DataSuiteDB()
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT fecha_extraccion FROM productos_historico WHERE deleted = 0 ORDER BY fecha_extraccion DESC")
        return [str(row[0]) for row in cur.fetchall()]

def get_data_as_dataframe(fuente="Todas", fecha="Todas", tipo="Todos"):
    db = DataSuiteDB()
    query = "SELECT * FROM productos_historico WHERE deleted = 0"
    params = []
    
    if fuente != "Todas":
        query += " AND comercio = ?"
        params.append(fuente)
    if fecha != "Todas":
        query += " AND fecha_extraccion = ?"
        params.append(fecha)
    if tipo != "Todos":
        query += " AND tipo_producto = ?"
        params.append(tipo)
        
    with db.get_connection() as conn:
        df = pd.read_sql_query(query, conn, params=params)
    if not df.empty:
        df.rename(columns={'comercio': 'fuente', 'descuento_porcentaje': 'descuento'}, inplace=True)
    return df

def delete_false_positive(db_id):
    db = DataSuiteDB()
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE productos_historico SET deleted = 1 WHERE id = ?", (db_id,))
        conn.commit()

if __name__ == '__main__':
    # Quick test initialization
    db = DataSuiteDB()
    # db.init_db() # Uncomment when credentials are set
