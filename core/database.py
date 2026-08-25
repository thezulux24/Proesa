import os
import re
import datetime
import sqlite3
import pandas as pd
from dotenv import load_dotenv

def calculate_unit_price(precio_final, medida):
    """Calcula el precio por unidad/medida ($/ml, $/und, $/g) de forma estandarizada."""
    try:
        if precio_final is None:
            return ""
        price = float(precio_final)
        if price <= 0 or not medida:
            return ""
        
        m_str = str(medida).lower().strip()
        # 1. Litros -> ML
        l_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:l|lt|litro|litros)\b', m_str)
        if l_match:
            val = float(l_match.group(1).replace(',', '.'))
            ml = val * 1000.0
            if ml > 0:
                pum = price / ml
                return f"${pum:,.2f}/ml".replace(',', 'X').replace('.', ',').replace('X', '.')
                
        # 2. ML / CC
        ml_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:ml|cc|cm3)\b', m_str)
        if ml_match:
            val = float(ml_match.group(1).replace(',', '.'))
            if val > 0:
                pum = price / val
                return f"${pum:,.2f}/ml".replace(',', 'X').replace('.', ',').replace('X', '.')
                
        # 3. Unidades / Cigarrillos
        und_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:und|un|unidades|piezas|cajetillas|cigarros|cigarrillos)\b', m_str)
        if und_match:
            val = float(und_match.group(1).replace(',', '.'))
            if val > 0:
                pum = price / val
                return f"${pum:,.2f}/und".replace(',', 'X').replace('.', ',').replace('X', '.')
                
        # 4. Gramos / KG
        kg_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:kg|kilo|kilos)\b', m_str)
        if kg_match:
            val = float(kg_match.group(1).replace(',', '.'))
            g = val * 1000.0
            if g > 0:
                pum = price / g
                return f"${pum:,.2f}/g".replace(',', 'X').replace('.', ',').replace('X', '.')
                
        g_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:g|gr|gramos)\b', m_str)
        if g_match:
            val = float(g_match.group(1).replace(',', '.'))
            if val > 0:
                pum = price / val
                return f"${pum:,.2f}/g".replace(',', 'X').replace('.', ',').replace('X', '.')

        return ""
    except Exception:
        return ""

def parse_alcohol_degrees_numeric(val):
    """Limpia y convierte cualquier graduación alcohólica a valor numérico puro (float o None)."""
    if val is None:
        return None
    s = str(val).strip().lower()
    if s in ("", "n/a", "none", "null", "n/a - tabaco", "0", "0.0", "0%"):
        return None
    s_clean = re.sub(r'[°º%]|grados|g\.l\.', '', s).strip()
    s_clean = s_clean.replace(',', '.')
    m = re.search(r'(\d+(?:\.\d+)?)', s_clean)
    if m:
        try:
            num = float(m.group(1))
            if 0 < num < 1.0:
                num = round(num * 100, 2)
            if 0 < num <= 100.0:
                return round(num, 2)
        except ValueError:
            pass
    return None

class DataSuiteDB:
    def __init__(self, db_name="suite_data.db"):
        load_dotenv()
        self.db_name = db_name
        
    def get_connection(self):
        conn = sqlite3.connect(self.db_name, timeout=60.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=60000;")
        except Exception:
            pass
        return conn

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
            registro_sanitario_invima VARCHAR(200),
            codigo_unico_invima VARCHAR(100),
            nombre_invima TEXT,
            precio_original NUMERIC(12,2),
            precio_final NUMERIC(12,2),
            descuento_porcentaje VARCHAR(50),
            precio_unidad VARCHAR(50),
            url_producto TEXT
        );
        """
        create_invima_query = """
        CREATE TABLE IF NOT EXISTS invima_certificados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nro INTEGER,
            registro_sanitario VARCHAR(200),
            codigo_unico VARCHAR(100),
            nombre_bebida_alcoholica TEXT,
            marca VARCHAR(200),
            clasificacion VARCHAR(200),
            grados_alcohol VARCHAR(50),
            precio_referencia_750cc NUMERIC(12,2)
        );
        """
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(create_table_query)
                cur.execute(create_maestro_query)
                cur.execute(create_mapeo_query)
                cur.execute(create_normalizado_query)
                cur.execute(create_invima_query)
                conn.commit()
                
                for col in [
                    ("deleted", "INTEGER DEFAULT 0"),
                    ("registro_sanitario_invima", "VARCHAR(200)"),
                    ("codigo_unico_invima", "VARCHAR(100)"),
                    ("nombre_invima", "TEXT"),
                    ("precio_referencia_invima", "NUMERIC(12,2)")
                ]:
                    try:
                        cur.execute(f"ALTER TABLE maestro_productos ADD COLUMN {col[0]} {col[1]}")
                        conn.commit()
                    except Exception:
                        pass

                for col in [
                    ("registro_sanitario_invima", "VARCHAR(200)"),
                    ("codigo_unico_invima", "VARCHAR(100)"),
                    ("nombre_invima", "TEXT")
                ]:
                    try:
                        cur.execute(f"ALTER TABLE productos_normalizados ADD COLUMN {col[0]} {col[1]}")
                        conn.commit()
                    except Exception:
                        pass
                    
                for col in [
                    ("grados_alcohol", "VARCHAR(50)"),
                    ("marca", "VARCHAR(200)"),
                    ("clasificacion", "VARCHAR(200)")
                ]:
                    try:
                        cur.execute(f"ALTER TABLE invima_certificados ADD COLUMN {col[0]} {col[1]}")
                        conn.commit()
                    except Exception:
                        pass

                cur.execute("CREATE INDEX IF NOT EXISTS idx_norm_comercio ON productos_normalizados(comercio)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_norm_fecha ON productos_normalizados(fecha_extraccion)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_norm_codigo ON productos_normalizados(codigo_universal)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_invima_reg ON invima_certificados(registro_sanitario)")
                conn.commit()
                
        except Exception as e:
            print(f"Error initializing DB: {e}")
            raise e

    def insert_products(self, comercio, products):
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
        
        values = []
        for p in products:
            po = p.get('Precio_Original')
            pf = p.get('Precio_Final')
            
            po = None if po in ('NULL', 'N/A', '') else po
            pf = None if pf in ('NULL', 'N/A', '') else pf
            
            medida = str(p.get('Medida', '')).strip()
            pum = str(p.get('Precio_Unidad', '')).strip()
            if not pum or pum in ('NULL', 'N/A', ''):
                pum = calculate_unit_price(pf, medida)
                
            raw_grados = p.get('Grados de alcohol')
            num_grados = parse_alcohol_degrees_numeric(raw_grados)
            grados_val = str(num_grados) if num_grados is not None else ""
            
            val = (
                today,
                comercio,
                str(p.get('ID', '')),
                str(p.get('Nombre', '')),
                str(p.get('Marca', '')),
                str(p.get('Referencia', '')),
                str(p.get('Categoria', '')),
                str(p.get('Tipo de Producto', '')),
                grados_val,
                medida,
                po,
                pf,
                str(p.get('Descuento_%', '')),
                pum,
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
# Funciones Helper para suite_app.py
# ==========================================

def get_available_sources():
    db = DataSuiteDB()
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT comercio FROM productos_historico WHERE deleted = 0 ORDER BY comercio")
        return [row[0] for row in cur.fetchall()]

def get_available_dates():
    db = DataSuiteDB()
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT fecha_extraccion FROM productos_historico WHERE deleted = 0 ORDER BY fecha_extraccion DESC")
        return [str(row[0]) for row in cur.fetchall()]

def get_available_subcategories():
    db = DataSuiteDB()
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT subcategoria_estandar FROM maestro_productos WHERE deleted = 0 AND subcategoria_estandar IS NOT NULL ORDER BY subcategoria_estandar")
        res = [row[0] for row in cur.fetchall() if row[0]]
        return ["Todas"] + res

def get_available_categories():
    db = DataSuiteDB()
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT categoria FROM productos_historico WHERE deleted = 0 AND categoria IS NOT NULL ORDER BY categoria")
        res = [row[0] for row in cur.fetchall() if row[0]]
        return ["Todas"] + res

def get_data_as_dataframe(
    fuente="Todas", 
    fecha="Todas", 
    tipo="Todos", 
    categoria="Todas",
    fecha_inicio=None, 
    fecha_fin=None, 
    search_term=None,
    solo_descuento=False,
    precio_min=None,
    precio_max=None
):
    db = DataSuiteDB()
    where_clauses = ["deleted = 0"]
    params = []
    
    if fuente != "Todas" and fuente:
        where_clauses.append("comercio = ?")
        params.append(fuente)
    if fecha != "Todas" and fecha and not (fecha_inicio or fecha_fin):
        where_clauses.append("fecha_extraccion = ?")
        params.append(fecha)
    if fecha_inicio:
        where_clauses.append("fecha_extraccion >= ?")
        params.append(str(fecha_inicio))
    if fecha_fin:
        where_clauses.append("fecha_extraccion <= ?")
        params.append(str(fecha_fin))
    if tipo != "Todos" and tipo:
        where_clauses.append("tipo_producto = ?")
        params.append(tipo)
    if categoria != "Todas" and categoria:
        where_clauses.append("categoria = ?")
        params.append(categoria)
    if search_term and search_term.strip():
        term = f"%{search_term.strip()}%"
        where_clauses.append("(nombre LIKE ? OR marca LIKE ? OR producto_id LIKE ?)")
        params.extend([term, term, term])
    if solo_descuento:
        where_clauses.append("(descuento_porcentaje IS NOT NULL AND descuento_porcentaje != '' AND descuento_porcentaje != '0%' AND descuento_porcentaje != '0')")
    if precio_min is not None:
        where_clauses.append("precio_final >= ?")
        params.append(precio_min)
    if precio_max is not None:
        where_clauses.append("precio_final <= ?")
        params.append(precio_max)
        
    where_sql = " AND ".join(where_clauses)
    query = f"SELECT * FROM productos_historico WHERE {where_sql} ORDER BY id DESC"
    
    with db.get_connection() as conn:
        df = pd.read_sql_query(query, conn, params=params)
    if not df.empty:
        df.rename(columns={'comercio': 'fuente', 'descuento_porcentaje': 'descuento'}, inplace=True)
    return df

def get_normalized_data_paginated(
    fuente="Todas", 
    fecha="Todas", 
    tipo="Todos",
    subcategoria="Todas",
    estado_invima="Todos",
    fecha_inicio=None, 
    fecha_fin=None, 
    search_term=None, 
    solo_descuento=False,
    precio_min=None,
    precio_max=None,
    limit=200, 
    offset=0
):
    db = DataSuiteDB()
    where_clauses = ["1=1"]
    params = []
    
    if fuente != "Todas" and fuente:
        where_clauses.append("comercio = ?")
        params.append(fuente)
    if fecha != "Todas" and fecha and not (fecha_inicio or fecha_fin):
        where_clauses.append("fecha_extraccion = ?")
        params.append(fecha)
    if fecha_inicio:
        where_clauses.append("fecha_extraccion >= ?")
        params.append(str(fecha_inicio))
    if fecha_fin:
        where_clauses.append("fecha_extraccion <= ?")
        params.append(str(fecha_fin))
    if tipo != "Todos" and tipo:
        where_clauses.append("tipo_producto_estandar = ?")
        params.append(tipo)
    if subcategoria != "Todas" and subcategoria:
        where_clauses.append("subcategoria_estandar = ?")
        params.append(subcategoria)
    if estado_invima == "Ligados":
        where_clauses.append("(registro_sanitario_invima LIKE 'INVIMA%' OR registro_sanitario_invima LIKE 'L-%' OR registro_sanitario_invima LIKE 'RSA-%')")
    elif estado_invima == "Sin Registro":
        where_clauses.append("(registro_sanitario_invima = 'SIN_REGISTRO_ENCONTRADO' OR registro_sanitario_invima IS NULL OR registro_sanitario_invima = '')")
    elif estado_invima == "Tabaco":
        where_clauses.append("registro_sanitario_invima = 'N/A - TABACO'")
    elif estado_invima == "No Aplica":
        where_clauses.append("(registro_sanitario_invima = 'NO_APLICA' OR registro_sanitario_invima LIKE 'FALSO_POSITIVO%')")
        
    if search_term and search_term.strip():
        term = f"%{search_term.strip()}%"
        where_clauses.append("(codigo_universal LIKE ? OR nombre_estandar LIKE ? OR marca_estandar LIKE ? OR registro_sanitario_invima LIKE ? OR codigo_unico_invima LIKE ?)")
        params.extend([term, term, term, term, term])
    if solo_descuento:
        where_clauses.append("(descuento_porcentaje IS NOT NULL AND descuento_porcentaje != '' AND descuento_porcentaje != '0%' AND descuento_porcentaje != '0')")
    if precio_min is not None:
        where_clauses.append("precio_final >= ?")
        params.append(precio_min)
    if precio_max is not None:
        where_clauses.append("precio_final <= ?")
        params.append(precio_max)

    where_sql = " AND ".join(where_clauses)
    count_sql = f"SELECT COUNT(*) FROM productos_normalizados WHERE {where_sql}"
    data_sql = f"SELECT * FROM productos_normalizados WHERE {where_sql} ORDER BY id DESC LIMIT ? OFFSET ?"
    
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(count_sql, params)
        total_count = cur.fetchone()[0]
        
        df = pd.read_sql_query(data_sql, conn, params=params + [limit, offset])
        if not df.empty:
            df.drop(columns=['id'], inplace=True, errors='ignore')
            df.rename(columns={'comercio': 'fuente', 'descuento_porcentaje': 'descuento', 'nombre_estandar': 'nombre', 'codigo_universal': 'id'}, inplace=True)
            
    return df, total_count

def get_normalized_data_as_dataframe(
    fuente="Todas", 
    fecha="Todas", 
    tipo="Todos",
    subcategoria="Todas",
    estado_invima="Todos",
    fecha_inicio=None, 
    fecha_fin=None, 
    search_term=None, 
    solo_descuento=False,
    precio_min=None,
    precio_max=None,
    ignore_zero_prices=True
):
    db = DataSuiteDB()
    where_clauses = ["1=1"]
    params = []
    
    if fuente != "Todas" and fuente:
        where_clauses.append("comercio = ?")
        params.append(fuente)
    if fecha != "Todas" and fecha and not (fecha_inicio or fecha_fin):
        where_clauses.append("fecha_extraccion = ?")
        params.append(fecha)
    if fecha_inicio:
        where_clauses.append("fecha_extraccion >= ?")
        params.append(str(fecha_inicio))
    if fecha_fin:
        where_clauses.append("fecha_extraccion <= ?")
        params.append(str(fecha_fin))
    if tipo != "Todos" and tipo:
        where_clauses.append("tipo_producto_estandar = ?")
        params.append(tipo)
    if subcategoria != "Todas" and subcategoria:
        where_clauses.append("subcategoria_estandar = ?")
        params.append(subcategoria)
    if estado_invima == "Ligados":
        where_clauses.append("(registro_sanitario_invima LIKE 'INVIMA%' OR registro_sanitario_invima LIKE 'L-%' OR registro_sanitario_invima LIKE 'RSA-%')")
    elif estado_invima == "Sin Registro":
        where_clauses.append("(registro_sanitario_invima = 'SIN_REGISTRO_ENCONTRADO' OR registro_sanitario_invima IS NULL OR registro_sanitario_invima = '')")
    elif estado_invima == "Tabaco":
        where_clauses.append("registro_sanitario_invima = 'N/A - TABACO'")
    elif estado_invima == "No Aplica":
        where_clauses.append("(registro_sanitario_invima = 'NO_APLICA' OR registro_sanitario_invima LIKE 'FALSO_POSITIVO%')")

    if search_term and search_term.strip():
        term = f"%{search_term.strip()}%"
        where_clauses.append("(codigo_universal LIKE ? OR nombre_estandar LIKE ? OR marca_estandar LIKE ? OR registro_sanitario_invima LIKE ?)")
        params.extend([term, term, term, term])
    if solo_descuento:
        where_clauses.append("(descuento_porcentaje IS NOT NULL AND descuento_porcentaje != '' AND descuento_porcentaje != '0%' AND descuento_porcentaje != '0')")
    if precio_min is not None:
        where_clauses.append("precio_final >= ?")
        params.append(precio_min)
    if precio_max is not None:
        where_clauses.append("precio_final <= ?")
        params.append(precio_max)
    if ignore_zero_prices:
        where_clauses.append("precio_final > 0 AND precio_final IS NOT NULL")
        
    where_sql = " AND ".join(where_clauses)
    query = f"SELECT * FROM productos_normalizados WHERE {where_sql}"
    
    with db.get_connection() as conn:
        df = pd.read_sql_query(query, conn, params=params)
        if not df.empty:
            df.drop(columns=['id'], inplace=True, errors='ignore')
            df.rename(columns={'comercio': 'fuente', 'descuento_porcentaje': 'descuento', 'nombre_estandar': 'nombre', 'codigo_universal': 'id'}, inplace=True)
        return df

def delete_false_positive(codigo_universal):
    db = DataSuiteDB()
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE maestro_productos SET deleted = 1 WHERE codigo_universal = ?", (codigo_universal,))
        cur.execute("""
            UPDATE productos_historico
            SET deleted = 1
            WHERE (comercio, producto_id) IN (
                SELECT comercio, producto_id FROM mapeo_productos WHERE codigo_universal = ?
            )
        """, (codigo_universal,))
        conn.commit()
    run_normalization_etl()

def mark_raw_false_positive(comercio, producto_id, run_etl=False):
    db = DataSuiteDB()
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE productos_historico SET deleted = 1 WHERE comercio = ? AND producto_id = ?", (comercio, str(producto_id)))
        conn.commit()
    if run_etl:
        run_normalization_etl()


def get_unmapped_products(fuente="Todas", tipo="Todos", search_term=None, hide_zero_price=False):
    db = DataSuiteDB()
    where_clauses = ["m.codigo_universal IS NULL AND h.deleted = 0"]
    params = []
    
    if fuente != "Todas" and fuente:
        where_clauses.append("h.comercio = ?")
        params.append(fuente)
    if tipo != "Todos" and tipo:
        where_clauses.append("h.tipo_producto = ?")
        params.append(tipo)
    if hide_zero_price:
        where_clauses.append("(h.precio_final IS NOT NULL AND h.precio_final > 0)")
    if search_term and search_term.strip():
        term = f"%{search_term.strip()}%"
        where_clauses.append("(h.nombre LIKE ? OR h.marca LIKE ? OR h.producto_id LIKE ?)")
        params.extend([term, term, term])
        
    where_sql = " AND ".join(where_clauses)
    query = f"""
        SELECT h.comercio, h.producto_id, h.nombre, h.marca, h.tipo_producto, h.grados_alcohol, h.medida,
               h.precio_final AS ultimo_precio, h.url_producto, h.fecha_extraccion
        FROM productos_historico h
        INNER JOIN (
            SELECT comercio, producto_id, MAX(fecha_extraccion) AS max_fecha, MAX(id) AS max_id
            FROM productos_historico
            WHERE deleted = 0
            GROUP BY comercio, producto_id
        ) latest ON h.comercio = latest.comercio AND h.producto_id = latest.producto_id AND h.id = latest.max_id
        LEFT JOIN mapeo_productos m ON h.comercio = m.comercio AND h.producto_id = m.producto_id
        WHERE {where_sql}
        ORDER BY h.nombre
    """
    with db.get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)

def get_maestro_products(tipo="Todos", subcategoria="Todas", search_term=None, include_prices=True):
    db = DataSuiteDB()
    where_clauses = ["m.deleted = 0"]
    params = []
    
    if tipo != "Todos" and tipo:
        where_clauses.append("m.tipo_producto_estandar = ?")
        params.append(tipo)
    if subcategoria != "Todas" and subcategoria:
        where_clauses.append("m.subcategoria_estandar = ?")
        params.append(subcategoria)
    if search_term and search_term.strip():
        term = f"%{search_term.strip()}%"
        where_clauses.append("(m.codigo_universal LIKE ? OR m.nombre_estandar LIKE ? OR m.marca_estandar LIKE ?)")
        params.extend([term, term, term])
        
    where_sql = " AND ".join(where_clauses)
    
    if include_prices:
        query = f"""
            SELECT m.*, 
                   COALESCE(pn.ultimo_precio, ph.ultimo_precio, 0) AS ultimo_precio,
                   COALESCE(ex.url_producto, '') AS url_producto
            FROM maestro_productos m
            LEFT JOIN (
                SELECT codigo_universal, MAX(precio_final) as ultimo_precio
                FROM productos_normalizados
                WHERE precio_final > 0
                GROUP BY codigo_universal
            ) pn ON m.codigo_universal = pn.codigo_universal
            LEFT JOIN (
                SELECT map.codigo_universal, MAX(h.precio_final) as ultimo_precio
                FROM mapeo_productos map
                JOIN productos_historico h ON map.comercio = h.comercio AND map.producto_id = h.producto_id
                WHERE h.deleted = 0 AND h.precio_final > 0
                GROUP BY map.codigo_universal
            ) ph ON m.codigo_universal = ph.codigo_universal
            LEFT JOIN (
                SELECT codigo_universal, url_producto
                FROM (
                    SELECT map.codigo_universal, h.url_producto,
                           ROW_NUMBER() OVER (
                               PARTITION BY map.codigo_universal 
                               ORDER BY 
                                   CASE h.comercio
                                       WHEN 'Exito' THEN 1
                                       WHEN 'Carulla' THEN 2
                                       WHEN 'Jumbo' THEN 3
                                       WHEN 'Olimpica' THEN 4
                                       WHEN 'Canaveral' THEN 5
                                       WHEN 'D1' THEN 6
                                       WHEN 'Makro' THEN 7
                                       WHEN 'Rappi' THEN 8
                                       ELSE 9
                                   END,
                                   h.fecha_extraccion DESC, h.id DESC
                           ) as rn
                    FROM mapeo_productos map
                    JOIN productos_historico h ON map.comercio = h.comercio AND map.producto_id = h.producto_id
                    WHERE h.deleted = 0 AND h.url_producto IS NOT NULL AND h.url_producto != ''
                )
                WHERE rn = 1
            ) ex ON m.codigo_universal = ex.codigo_universal
            WHERE {where_sql}
            ORDER BY m.codigo_universal
        """
    else:
        query = f"SELECT * FROM maestro_productos m WHERE {where_sql} ORDER BY m.codigo_universal"
        
    with db.get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)

def get_maestro_products_invima(filter_type="Todos", tipo="Todos", subcategoria="Todas", search_term=None):
    db = DataSuiteDB()
    query = "SELECT * FROM maestro_productos WHERE deleted = 0"
    params = []
    
    if filter_type == "Ligados":
        query += " AND (registro_sanitario_invima LIKE 'INVIMA%' OR registro_sanitario_invima LIKE 'L-%' OR registro_sanitario_invima LIKE 'RSA-%')"
    elif filter_type == "Sin Registro":
        query += " AND (registro_sanitario_invima = 'SIN_REGISTRO_ENCONTRADO' OR registro_sanitario_invima IS NULL OR registro_sanitario_invima = '')"
    elif filter_type == "Tabaco":
        query += " AND registro_sanitario_invima = 'N/A - TABACO'"
    elif filter_type == "No Aplica":
        query += " AND (registro_sanitario_invima = 'NO_APLICA' OR registro_sanitario_invima LIKE 'FALSO_POSITIVO%')"

    if tipo != "Todos" and tipo:
        query += " AND tipo_producto_estandar = ?"
        params.append(tipo)
    if subcategoria != "Todas" and subcategoria:
        query += " AND subcategoria_estandar = ?"
        params.append(subcategoria)

    if search_term and search_term.strip():
        term = f"%{search_term.strip()}%"
        query += " AND (codigo_universal LIKE ? OR nombre_estandar LIKE ? OR marca_estandar LIKE ? OR registro_sanitario_invima LIKE ? OR nombre_invima LIKE ?)"
        params.extend([term, term, term, term, term])
        
    query += " ORDER BY marca_estandar, nombre_estandar"
    with db.get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)

def update_master_invima_code(codigo_universal, new_invima_code):
    new_invima_code = new_invima_code.strip() if new_invima_code else ""
    db = DataSuiteDB()
    with db.get_connection() as conn:
        cur = conn.cursor()
        
        cur.execute("""
            SELECT registro_sanitario, codigo_unico, nombre_bebida_alcoholica 
            FROM invima_certificados 
            WHERE UPPER(registro_sanitario) LIKE ? OR UPPER(registro_sanitario) LIKE ?
        """, (f"%{new_invima_code.upper()}%", f"%{new_invima_code.upper().replace('INVIMA', '').strip()}%"))
        found = cur.fetchone()
        
        if found:
            cur.execute("""
                UPDATE maestro_productos
                SET registro_sanitario_invima = ?,
                    codigo_unico_invima = ?,
                    nombre_invima = ?
                WHERE codigo_universal = ?
            """, (found[0], found[1], str(found[2]) if found[2] else "", codigo_universal))
        else:
            cur.execute("""
                UPDATE maestro_productos
                SET registro_sanitario_invima = ?,
                    codigo_unico_invima = NULL,
                    nombre_invima = 'ASIGNACION_MANUAL'
                WHERE codigo_universal = ?
            """, (new_invima_code, codigo_universal))
            
        conn.commit()
    run_normalization_etl()

def get_invima_certificados(search_term=None, limit=200, offset=0):
    db = DataSuiteDB()
    where_sql = "1=1"
    params = []
    
    if search_term and search_term.strip():
        term = f"%{search_term.strip()}%"
        where_sql += " AND (registro_sanitario LIKE ? OR nombre_bebida_alcoholica LIKE ? OR marca LIKE ? OR codigo_unico LIKE ?)"
        params.extend([term, term, term, term])

    count_sql = f"SELECT COUNT(*) FROM invima_certificados WHERE {where_sql}"
    data_sql = f"SELECT * FROM invima_certificados WHERE {where_sql} ORDER BY id DESC LIMIT ? OFFSET ?"
    
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(count_sql, params)
        total_count = cur.fetchone()[0]
        
        df = pd.read_sql_query(data_sql, conn, params=params + [limit, offset])
        
    return df, total_count

def add_invima_certificado(registro_sanitario, codigo_unico, nombre, marca, clasificacion, grados_alcohol):
    db = DataSuiteDB()
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO invima_certificados (registro_sanitario, codigo_unico, nombre_bebida_alcoholica, marca, clasificacion, grados_alcohol)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (registro_sanitario.strip(), codigo_unico.strip(), nombre.strip(), marca.strip(), clasificacion.strip(), grados_alcohol.strip()))
        conn.commit()

def generate_new_master_code():
    import uuid
    db = DataSuiteDB()
    with db.get_connection() as conn:
        cur = conn.cursor()
        while True:
            code = "MST_" + str(uuid.uuid4()).split('-')[0].upper()
            cur.execute("SELECT 1 FROM maestro_productos WHERE codigo_universal = ?", (code,))
            if not cur.fetchone():
                return code

def add_to_maestro(nombre, marca, tipo, subcategoria, volumen, grados, codigo_universal=None):
    if not codigo_universal or not str(codigo_universal).strip():
        codigo_universal = generate_new_master_code()
    else:
        codigo_universal = str(codigo_universal).strip()
    
    db = DataSuiteDB()
    query = """
        INSERT INTO maestro_productos (codigo_universal, nombre_estandar, marca_estandar, tipo_producto_estandar, subcategoria_estandar, volumen_estandar, grados_alcohol_estandar)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM maestro_productos WHERE codigo_universal = ?", (codigo_universal,))
        if cur.fetchone():
            raise ValueError(f"El código maestro '{codigo_universal}' ya existe en la base de datos.")
        
        num_grados = parse_alcohol_degrees_numeric(grados)
        grados_str = str(num_grados) if num_grados is not None else ""

        cur.execute(query, (
            codigo_universal, 
            str(nombre).strip() if nombre else "", 
            str(marca).strip() if marca else "", 
            str(tipo).strip() if tipo else "Alcohol", 
            str(subcategoria).strip() if subcategoria else "", 
            str(volumen).strip() if volumen else "", 
            grados_str
        ))
        conn.commit()
    return codigo_universal

def get_recent_discarded_products(limit=50):
    """Retorna la lista de productos descartados (falsos positivos) recientemente para el reporte por correo."""
    db = DataSuiteDB()
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT comercio, nombre, categoria, descripcion, fecha_extraccion
            FROM productos_historico
            WHERE deleted = 1
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        return [
            {
                "comercio": r[0],
                "nombre": r[1],
                "categoria": r[2],
                "descripcion": r[3],
                "fecha_extraccion": r[4]
            }
            for r in rows
        ]


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
        cur.execute("DELETE FROM productos_normalizados")
        
        insert_query = """
            INSERT INTO productos_normalizados (
                fecha_extraccion, codigo_universal, comercio, nombre_estandar, 
                marca_estandar, tipo_producto_estandar, subcategoria_estandar, 
                volumen_estandar, grados_alcohol_estandar, registro_sanitario_invima,
                codigo_unico_invima, nombre_invima, precio_original, 
                precio_final, descuento_porcentaje, precio_unidad, url_producto
            )
            SELECT 
                h.fecha_extraccion, m.codigo_universal, h.comercio, 
                mp.nombre_estandar, mp.marca_estandar, mp.tipo_producto_estandar, 
                mp.subcategoria_estandar, mp.volumen_estandar, mp.grados_alcohol_estandar,
                mp.registro_sanitario_invima, mp.codigo_unico_invima, mp.nombre_invima,
                h.precio_original, h.precio_final, h.descuento_porcentaje, h.precio_unidad, h.url_producto
            FROM productos_historico h
            JOIN mapeo_productos m ON h.comercio = m.comercio AND h.producto_id = m.producto_id
            JOIN maestro_productos mp ON m.codigo_universal = mp.codigo_universal
            WHERE h.deleted = 0 AND mp.deleted = 0
        """
        cur.execute(insert_query)
        conn.commit()

def get_unmapped_invima_masters(subcategoria="Todas", limit=0):
    """
    Retorna los productos maestros activos que no tienen registro sanitario INVIMA asignado.
    Omite automáticamente los productos de tipo Tabaco.
    """
    db = DataSuiteDB()
    with db.get_connection() as conn:
        query = """
            SELECT codigo_universal, nombre_estandar, marca_estandar, tipo_producto_estandar, 
                   subcategoria_estandar, volumen_estandar, grados_alcohol_estandar
            FROM maestro_productos
            WHERE (registro_sanitario_invima IS NULL OR registro_sanitario_invima = '' OR registro_sanitario_invima = 'N/A')
              AND deleted = 0
              AND LOWER(tipo_producto_estandar) != 'tabaco'
        """
        params = []
        if subcategoria and subcategoria != "Todas":
            query += " AND subcategoria_estandar = ?"
            params.append(subcategoria)

        query += " ORDER BY codigo_universal"
        if limit > 0:
            query += " LIMIT ?"
            params.append(limit)

        import pandas as pd
        return pd.read_sql_query(query, conn, params=params)

def update_master_invima(codigo_universal, registro_invima, codigo_unico=None, nombre_invima=None, precio_invima=None):
    """
    Actualiza la información del Registro Sanitario INVIMA en la tabla maestro_productos.
    """
    db = DataSuiteDB()
    with db.get_connection() as conn:
        cur = conn.cursor()
        precio_val = None
        if precio_invima not in (None, "", "NaN", "null"):
            try:
                precio_val = float(precio_invima)
            except (ValueError, TypeError):
                precio_val = None

        cur.execute("""
            UPDATE maestro_productos
            SET registro_sanitario_invima = ?,
                codigo_unico_invima = ?,
                nombre_invima = ?,
                precio_referencia_invima = ?
            WHERE codigo_universal = ?
        """, (
            str(registro_invima).strip() if registro_invima else None,
            str(codigo_unico).strip() if codigo_unico else None,
            str(nombre_invima).strip() if nombre_invima else None,
            precio_val,
            str(codigo_universal).strip()
        ))
        conn.commit()

