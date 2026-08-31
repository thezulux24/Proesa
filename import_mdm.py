#!/usr/bin/env python3
"""
Script para Importar y Restaurar el Estado del MDM
Importa maestro_productos, mapeo_productos, soft deletes y memoria humana desde el JSON a suite_data.db
y ejecuta automáticamente el ETL de normalización.
CERO DUPLICADOS: Utiliza llaves primarias unificadas (INSERT OR REPLACE / UPSERT).
"""
import os
import sys
import time
import json
import sqlite3
import database

INPUT_FILE = "data/mdm_export.json"
if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
    INPUT_FILE = sys.argv[1]

SKIP_ETL = "--skip-etl" in sys.argv

def import_mdm():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: No se encontró el archivo de exportación MDM: {INPUT_FILE}")
        return

    t_start = time.time()
    print(f"Cargando datos desde {INPUT_FILE}...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    maestro = data.get("maestro_productos", [])
    mapeo = data.get("mapeo_productos", [])
    deleted = data.get("deleted_historico", [])
    human_mem = data.get("human_corrections_memory", [])

    db = database.DataSuiteDB()
    db.init_db()  # Asegurar que todas las tablas y columnas existan

    with db.get_connection() as conn:
        cur = conn.cursor()
        
        # Obtener conteos previos para medir lo nuevo vs actualizado
        cur.execute("SELECT COUNT(*) FROM maestro_productos")
        maestro_prev_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM mapeo_productos")
        mapeo_prev_count = cur.fetchone()[0]
        
        # 1. Importar maestro_productos en batch (INSERT OR REPLACE)
        if maestro:
            t0 = time.time()
            print(f"Procesando {len(maestro):,} productos maestros...")
            all_cols = list(maestro[0].keys())
            placeholders = ", ".join(["?"] * len(all_cols))
            col_names = ", ".join(all_cols)
            sql_maestro = f"INSERT OR REPLACE INTO maestro_productos ({col_names}) VALUES ({placeholders})"
            
            records_maestro = [
                tuple(r.get(col, None) for col in all_cols)
                for r in maestro
            ]
            cur.executemany(sql_maestro, records_maestro)
            print(f"  [OK] Productos maestros guardados en {time.time() - t0:.2f}s")

        # 2. Importar mapeo_productos en batch (Primary Key: comercio, producto_id)
        if mapeo:
            t0 = time.time()
            print(f"Procesando {len(mapeo):,} vinculaciones mapeo...")
            sql_mapeo = """
                INSERT OR REPLACE INTO mapeo_productos (comercio, producto_id, codigo_universal)
                VALUES (?, ?, ?)
            """
            records_mapeo = [
                (r["comercio"], str(r["producto_id"]), r["codigo_universal"])
                for r in mapeo
            ]
            cur.executemany(sql_mapeo, records_mapeo)
            print(f"  [OK] Vinculaciones de mapeo guardadas en {time.time() - t0:.2f}s")

        # 3. Restaurar soft-deletes en productos_historico usando tabla temporal indexada (ultra-rápido)
        if deleted:
            t0 = time.time()
            print(f"Aplicando {len(deleted):,} flags de depuración (modo optimizado)...")
            cur.execute("""
                CREATE TEMP TABLE IF NOT EXISTS temp_soft_deletes (
                    comercio TEXT NOT NULL,
                    producto_id TEXT NOT NULL,
                    PRIMARY KEY (comercio, producto_id)
                )
            """)
            cur.execute("DELETE FROM temp_soft_deletes")
            
            records_deleted = [
                (r["comercio"], str(r["producto_id"]))
                for r in deleted
            ]
            cur.executemany(
                "INSERT OR IGNORE INTO temp_soft_deletes (comercio, producto_id) VALUES (?, ?)",
                records_deleted
            )
            
            # Ejecutar update en bloque utilizando el índice
            cur.execute("""
                UPDATE productos_historico 
                SET deleted = 1 
                WHERE deleted = 0 
                  AND EXISTS (
                      SELECT 1 FROM temp_soft_deletes t 
                      WHERE t.comercio = productos_historico.comercio 
                        AND t.producto_id = productos_historico.producto_id
                  )
            """)
            cur.execute("DROP TABLE IF EXISTS temp_soft_deletes")
            print(f"  [OK] Banderas de depuración aplicadas en {time.time() - t0:.2f}s")

        conn.commit()

        # Obtener conteos finales
        cur.execute("SELECT COUNT(*) FROM maestro_productos")
        maestro_final_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM mapeo_productos")
        mapeo_final_count = cur.fetchone()[0]

    # 4. Restaurar archivo de memoria humana si está presente
    if human_mem:
        os.makedirs("data", exist_ok=True)
        human_mem_file = "data/human_corrections_memory.json"
        with open(human_mem_file, "w", encoding="utf-8") as f:
            json.dump(human_mem, f, ensure_ascii=False, indent=2)
        print(f"[OK] Memoria de correcciones humanas restaurada ({len(human_mem):,} reglas en {human_mem_file}).")

    if not SKIP_ETL:
        t_etl = time.time()
        print("Ejecutando proceso ETL de normalización...")
        database.run_normalization_etl()
        print(f"  [OK] Proceso ETL finalizado en {time.time() - t_etl:.2f}s")
    else:
        print("[AVISO] Proceso ETL omitido por bandera --skip-etl.")

    new_maestro = max(0, maestro_final_count - maestro_prev_count)
    new_mapeo = max(0, mapeo_final_count - mapeo_prev_count)

    print("=" * 60)
    print(" SINCRONIZACIÓN MDM COMPLETADA CON ÉXITO ")
    print("=" * 60)
    print(f"[OK] Total Productos Maestros: {maestro_final_count:,} ({new_maestro:,} nuevos agregados)")
    print(f"[OK] Total Mapeos Vinculados: {mapeo_final_count:,} ({new_mapeo:,} nuevos agregados)")
    print(f"[OK] Total Depuraciones (Soft Delete): {len(deleted):,}")
    if not SKIP_ETL:
        print("[OK] Tabla `productos_normalizados` actualizada correctamente.")
    print(f"[OK] Tiempo total de sincronización: {time.time() - t_start:.2f}s")
    print("=" * 60)


if __name__ == "__main__":
    import_mdm()
