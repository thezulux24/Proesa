#!/usr/bin/env python3
"""
Script para Exportar la Configuración y Estado del MDM
Exporta maestro_productos, mapeo_productos y banderas de depuración a un archivo JSON portable.
"""
import os
import json
import sqlite3
import pandas as pd

DB_PATH = "suite_data.db"
OUTPUT_FILE = "data/mdm_export.json"

def export_mdm():
    if not os.path.exists(DB_PATH):
        print(f"Error: No se encontró la base de datos {DB_PATH}.")
        return

    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Maestro de Productos
    df_maestro = pd.read_sql_query("SELECT * FROM maestro_productos", conn)
    maestro_records = df_maestro.to_dict(orient="records")
    
    # 2. Mapeo de Productos
    df_mapeo = pd.read_sql_query("SELECT * FROM mapeo_productos", conn)
    mapeo_records = df_mapeo.to_dict(orient="records")
    
    # 3. Soft Deletions en productos_historico
    df_deleted = pd.read_sql_query("SELECT comercio, producto_id FROM productos_historico WHERE deleted = 1", conn)
    deleted_records = df_deleted.to_dict(orient="records")
    
    data = {
        "maestro_productos": maestro_records,
        "mapeo_productos": mapeo_records,
        "deleted_historico": deleted_records
    }
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print("=" * 60)
    print(" EXPORTACIÓN DE ESTADO MDM COMPLETADA CON ÉXITO ")
    print("=" * 60)
    print(f"[OK] Productos Maestros: {len(maestro_records):,}")
    print(f"[OK] Vinculaciones (Mapeo): {len(mapeo_records):,}")
    print(f"[OK] Registros Depurados (Soft Delete): {len(deleted_records):,}")
    print(f"[OK] Archivo generado: {os.path.abspath(OUTPUT_FILE)}")
    print("=" * 60)


if __name__ == "__main__":
    export_mdm()
