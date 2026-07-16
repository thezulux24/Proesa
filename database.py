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
        create_maestro_query = """
        CREATE TABLE IF NOT EXISTS maestro_productos (
            codigo_universal VARCHAR(100) PRIMARY KEY,
            nombre_estandar TEXT NOT NULL,
            marca_estandar VARCHAR(200),
            tipo_producto_estandar VARCHAR(100),
            subcategoria_estandar VARCHAR(100),
            volumen_estandar VARCHAR(100),
            grados_alcohol_estandar VARCHAR(50),
            deleted INTEGER DEFAULT 0
        );
        """
        
        create_mapeo_query = """
        CREATE TABLE IF NOT EXISTS mapeo_productos (
            comercio VARCHAR(50) NOT NULL,
            producto_id VARCHAR(100) NOT NULL,
            codigo_universal VARCHAR(100) NOT NULL,
            PRIMARY KEY (comercio, producto_id),
            FOREIGN KEY (codigo_universal) REFERENCES maestro_productos(codigo_universal)
        );
        """
        
        create_normalizado_query = """
        CREATE TABLE IF NOT EXISTS productos_normalizados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_extraccion DATE NOT NULL,
            codigo_universal VARCHAR(100) NOT NULL,
            comercio VARCHAR(50) NOT NULL,
            nombre_estandar TEXT,
            marca_estandar VARCHAR(200),
            tipo_producto_estandar VARCHAR(100),
            subcategoria_estandar VARCHAR(100),
            volumen_estandar VARCHAR(100),
            grados_alcohol_estandar VARCHAR(50),
            precio_original NUMERIC(12,2),
            precio_final NUMERIC(12,2),
            descuento_porcentaje VARCHAR(50),
            precio_unidad VARCHAR(50),
            url_producto TEXT
        );
        """
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(create_table_query)
                cur.execute(create_maestro_query)
                cur.execute(create_mapeo_query)
                cur.execute(create_normalizado_query)
                conn.commit()
                
                # Migración para la tabla maestra si ya existía sin la columna deleted
                try:
                    cur.execute("ALTER TABLE maestro_productos ADD COLUMN deleted INTEGER DEFAULT 0")
                    conn.commit()
                except Exception:
                    pass # La columna ya existe
                    
                print("Database tables initialized successfully.")
        except Exception as e:
            print(f"Error initializing DB: {e}")
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

def get_normalized_data_as_dataframe(fuente="Todas", fecha="Todas"):
    db = DataSuiteDB()
    query = "SELECT * FROM productos_normalizados WHERE 1=1"
    params = []
    
    if fuente != "Todas":
        query += " AND comercio = ?"
        params.append(fuente)
    if fecha != "Todas":
        query += " AND fecha_extraccion = ?"
        params.append(fecha)
        
    with db.get_connection() as conn:
        df = pd.read_sql_query(query, conn, params=params)
        if not df.empty:
            df.drop(columns=['id'], inplace=True, errors='ignore')
            df.rename(columns={'comercio': 'fuente', 'descuento_porcentaje': 'descuento', 'nombre_estandar': 'nombre', 'precio_final': 'precio_final', 'codigo_universal': 'id'}, inplace=True)
        return df

def delete_false_positive(codigo_universal):
    db = DataSuiteDB()
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE maestro_productos SET deleted = 1 WHERE codigo_universal = ?", (codigo_universal,))
        conn.commit()

if __name__ == '__main__':
    # Quick test initialization
    db = DataSuiteDB()
    # db.init_db() # Uncomment when credentials are set

# ==========================================
# Funciones helper para MDM (Normalización)
# ==========================================
import uuid

def get_unmapped_products():
    db = DataSuiteDB()
    query = """
        SELECT DISTINCT h.comercio, h.producto_id, h.nombre, h.marca, h.tipo_producto, h.grados_alcohol, h.medida
        FROM productos_historico h
        LEFT JOIN mapeo_productos m ON h.comercio = m.comercio AND h.producto_id = m.producto_id
        WHERE m.codigo_universal IS NULL AND h.deleted = 0
    """
    with db.get_connection() as conn:
        return pd.read_sql_query(query, conn)

def get_maestro_products():
    db = DataSuiteDB()
    query = "SELECT * FROM maestro_productos"
    with db.get_connection() as conn:
        return pd.read_sql_query(query, conn)

def add_to_maestro(nombre, marca, tipo, subcategoria, volumen, grados, codigo_universal=None):
    if not codigo_universal:
        # Generate a standard ID or UUID
        codigo_universal = "PRD-" + str(uuid.uuid4()).split('-')[0].upper()
    
    db = DataSuiteDB()
    query = """
        INSERT INTO maestro_productos (codigo_universal, nombre_estandar, marca_estandar, tipo_producto_estandar, subcategoria_estandar, volumen_estandar, grados_alcohol_estandar)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, (codigo_universal, nombre, marca, tipo, subcategoria, volumen, grados))
        conn.commit()
    return codigo_universal

def add_mapping(comercio, producto_id, codigo_universal):
    db = DataSuiteDB()
    query = """
        INSERT OR REPLACE INTO mapeo_productos (comercio, producto_id, codigo_universal)
        VALUES (?, ?, ?)
    """
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, (comercio, producto_id, codigo_universal))
        conn.commit()

def run_normalization_etl():
    db = DataSuiteDB()
    with db.get_connection() as conn:
        cur = conn.cursor()
        # Vaciamos la tabla de normalizados
        cur.execute("DELETE FROM productos_normalizados")
        
        # Insertamos cruzando crudo con mapeo y maestro
        insert_query = """
            INSERT INTO productos_normalizados (
                fecha_extraccion, codigo_universal, comercio, nombre_estandar, 
                marca_estandar, tipo_producto_estandar, subcategoria_estandar, 
                volumen_estandar, grados_alcohol_estandar, precio_original, 
                precio_final, descuento_porcentaje, precio_unidad, url_producto
            )
            SELECT 
                h.fecha_extraccion, m.codigo_universal, h.comercio, 
                mp.nombre_estandar, mp.marca_estandar, mp.tipo_producto_estandar, 
                mp.subcategoria_estandar, mp.volumen_estandar, mp.grados_alcohol_estandar,
                h.precio_original, h.precio_final, h.descuento_porcentaje, h.precio_unidad, h.url_producto
            FROM productos_historico h
            JOIN mapeo_productos m ON h.comercio = m.comercio AND h.producto_id = m.producto_id
            JOIN maestro_productos mp ON m.codigo_universal = mp.codigo_universal
            WHERE h.deleted = 0 AND mp.deleted = 0
        """
        cur.execute(insert_query)
        conn.commit()
