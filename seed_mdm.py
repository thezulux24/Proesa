import json
import os
import difflib
from database import DataSuiteDB

def seed_exact_eans():
    print("=== Fase 1: Anclaje Exacto (Jumbo & Olímpica) ===")
    db = DataSuiteDB()
    
    jumbo_data = []
    if os.path.exists("data/productos_jumbo.json"):
        with open("data/productos_jumbo.json", "r", encoding="utf-8") as f:
            jumbo_data = json.load(f)
            
    olimpica_data = []
    if os.path.exists("data/productos_olimpica.json"):
        with open("data/productos_olimpica.json", "r", encoding="utf-8") as f:
            olimpica_data = json.load(f)

    valid_eans = 0
    mapped = 0

    with db.get_connection() as conn:
        cur = conn.cursor()
        
        # Procesar Jumbo
        for p in jumbo_data:
            if not isinstance(p, dict): continue
            ean = str(p.get("EAN", "")).strip()
            prod_id = str(p.get("ID", "")).strip()
            if ean and prod_id:
                # Insertar en maestro (Ignorar si ya existe el EAN)
                cur.execute("""
                    INSERT OR IGNORE INTO maestro_productos (codigo_universal, nombre_estandar, marca_estandar, tipo_producto_estandar, subcategoria_estandar, volumen_estandar, grados_alcohol_estandar)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (ean, p.get("Nombre", ""), p.get("Marca", ""), p.get("Tipo de Producto", "Alcohol"), "General", p.get("Medida", ""), p.get("Grados de alcohol", "")))
                
                # Insertar en mapeo
                cur.execute("""
                    INSERT OR REPLACE INTO mapeo_productos (comercio, producto_id, codigo_universal)
                    VALUES (?, ?, ?)
                """, ("Jumbo", prod_id, ean))
                
                valid_eans += 1
                mapped += 1

        # Procesar Olímpica
        for p in olimpica_data:
            if not isinstance(p, dict): continue
            ean = str(p.get("ean", "")).strip()
            prod_id = str(p.get("ID", "")).strip()
            if ean and prod_id:
                cur.execute("""
                    INSERT OR IGNORE INTO maestro_productos (codigo_universal, nombre_estandar, marca_estandar, tipo_producto_estandar, subcategoria_estandar, volumen_estandar, grados_alcohol_estandar)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (ean, p.get("Nombre", ""), p.get("Marca", ""), p.get("Tipo de Producto", "Alcohol"), "General", p.get("Medida", ""), p.get("Grados de alcohol", "")))
                
                cur.execute("""
                    INSERT OR REPLACE INTO mapeo_productos (comercio, producto_id, codigo_universal)
                    VALUES (?, ?, ?)
                """, ("Olímpica", prod_id, ean))
                
                valid_eans += 1
                mapped += 1

        conn.commit()
    print(f"Fase 1 completada. {mapped} productos mapeados a {valid_eans} EANs (incluyendo duplicados inter-comercio).")

def seed_fuzzy_matching():
    print("\n=== Fase 2: Auto-Mapeo Básico (Similitud de Nombres) ===")
    db = DataSuiteDB()
    
    # Comercios a procesar
    comercios = ["Éxito", "Carulla", "Makro", "Cañaveral", "D1"]
    
    # Obtener maestro
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT codigo_universal, nombre_estandar FROM maestro_productos")
        maestro = cur.fetchall()
        
    if not maestro:
        print("Maestro vacío. Ejecuta Fase 1 primero.")
        return

    maestro_dict = {row[1]: row[0] for row in maestro}
    maestro_names = list(maestro_dict.keys())
    
    mapped_count = 0

    with db.get_connection() as conn:
        cur = conn.cursor()
        
        for c in comercios:
            filename = f"data/productos_{c.lower().replace('é', 'e').replace('ñ', 'n')}.json"
            if not os.path.exists(filename): continue
                
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            for p in data:
                if not isinstance(p, dict): continue
                prod_id = str(p.get("ID", "")).strip()
                nombre = str(p.get("Nombre", "")).strip()
                
                if not prod_id or not nombre: continue
                
                # Check if already mapped
                cur.execute("SELECT 1 FROM mapeo_productos WHERE comercio = ? AND producto_id = ?", (c, prod_id))
                if cur.fetchone(): continue
                
                # Fuzzy match
                matches = difflib.get_close_matches(nombre, maestro_names, n=1, cutoff=0.85)
                if matches:
                    matched_name = matches[0]
                    ean = maestro_dict[matched_name]
                    
                    cur.execute("""
                        INSERT OR REPLACE INTO mapeo_productos (comercio, producto_id, codigo_universal)
                        VALUES (?, ?, ?)
                    """, (c, prod_id, ean))
                    mapped_count += 1
                    
        conn.commit()
    print(f"Fase 2 completada. {mapped_count} productos mapeados vía similitud de texto.")

if __name__ == "__main__":
    # Asegurarnos de que las tablas existen
    db = DataSuiteDB()
    db.init_db()
    
    seed_exact_eans()
    seed_fuzzy_matching()
    
    # Ejecutamos ETL para llenar la tabla final
    print("\n=== Fase 3: Ejecutando ETL para crear la tabla Normalizada ===")
    from database import run_normalization_etl
    run_normalization_etl()
    print("ETL Completado. Datos listos para análisis.")
