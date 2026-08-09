#!/usr/bin/env python3
"""
Script para Importar y Restaurar el Estado del MDM
Importa maestro_productos, mapeo_productos y soft deletes desde el JSON a suite_data.db
y ejecuta automáticamente el ETL de normalización.
CERO DUPLICADOS: Utiliza llaves primarias unificadas (INSERT OR REPLACE / UPSERT).
"""
import os
import sys
import json
import sqlite3
import database

INPUT_FILE = sys.argv[1] if len(sys.argv) > 1 else "data/mdm_export.json"

def import_mdm():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: No se encontró el archivo de exportación MDM: {INPUT_FILE}")
        return

    print(f"Cargando datos desde {INPUT_FILE}...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    maestro = data.get("maestro_productos", [])
    mapeo = data.get("mapeo_productos", [])
    deleted = data.get("deleted_historico", [])

    db = database.DataSuiteDB()
    db.init_db()  # Asegurar que las tablas existan

    with db.get_connection() as conn:
        cur = conn.cursor()
        
        # Obtener conteos previos para medir lo nuevo vs actualizado
        cur.execute("SELECT COUNT(*) FROM maestro_productos")
        maestro_prev_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM mapeo_productos")
        mapeo_prev_count = cur.fetchone()[0]
        
        # 1. Importar maestro_productos sin duplicados
        print(f"Procesando {len(maestro):,} productos maestros...")
        for r in maestro:
            cols = list(r.keys())
            placeholders = ", ".join(["?"] * len(cols))
            col_names = ", ".join(cols)
            vals = [r[k] for k in cols]
            sql = f"INSERT OR REPLACE INTO maestro_productos ({col_names}) VALUES ({placeholders})"
            cur.execute(sql, vals)

        # 2. Importar mapeo_productos sin duplicados (Primary Key: comercio, producto_id)
        print(f"Procesando {len(mapeo):,} vinculaciones mapeo...")
        for r in mapeo:
            cur.execute("""
                INSERT OR REPLACE INTO mapeo_productos (comercio, producto_id, codigo_universal)
                VALUES (?, ?, ?)
            """, (r["comercio"], str(r["producto_id"]), r["codigo_universal"]))

        # 3. Restaurar soft-deletes en productos_historico si existen
        if deleted:
            print(f"Aplicando {len(deleted):,} flags de depuración...")
            for r in deleted:
                cur.execute("""
                    UPDATE productos_historico SET deleted = 1
                    WHERE comercio = ? AND producto_id = ?
                """, (r["comercio"], str(r["producto_id"])))

        conn.commit()

        # Obtener conteos finales
        cur.execute("SELECT COUNT(*) FROM maestro_productos")
        maestro_final_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM mapeo_productos")
        mapeo_final_count = cur.fetchone()[0]

    print("Ejecutando proceso ETL de normalización...")
    database.run_normalization_etl()

    new_maestro = maestro_final_count - maestro_prev_count
    new_mapeo = mapeo_final_count - mapeo_prev_count

    print("=" * 60)
    print(" SINCRONIZACIÓN MDM COMPLETADA (CERO DUPLICADOS) ")
    print("=" * 60)
    print(f"[OK] Total Productos Maestros: {maestro_final_count:,} ({new_maestro:,} nuevos agregados)")
    print(f"[OK] Total Mapeos Vinculados: {mapeo_final_count:,} ({new_mapeo:,} nuevos agregados)")
    print(f"[OK] Total Depuraciones (Soft Delete): {len(deleted):,}")
    print("[OK] Tabla `productos_normalizados` actualizada correctamente.")
    print("=" * 60)


if __name__ == "__main__":
    import_mdm()
