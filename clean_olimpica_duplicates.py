#!/usr/bin/env python3
"""
Script para Depurar Productos Fantasma / Duplicados de Olímpica
Marca con `deleted = 1` los productos crudos antiguos e inactivos de Olímpica
que comparten el mismo nombre exacto, conservando únicamente la variante más reciente/activa.
Actualiza la ETL y exporta automáticamente el respaldo actualizado a `data/mdm_export.json`.
"""
import os
import sys
import database
from export_mdm import export_mdm

def clean_olimpica_duplicates():
    print("=" * 60)
    print(" DEPURACIÓN DE DUPLICADOS INACTIVOS - OLÍMPICA ")
    print("=" * 60)
    print("Analizando productos crudos en productos_historico...")
    
    db = database.DataSuiteDB()
    with db.get_connection() as conn:
        cur = conn.cursor()
        
        # Marcar deleted = 1 en productos_historico para duplicados no mapeados de Olímpica
        cur.execute("""
            UPDATE productos_historico
            SET deleted = 1
            WHERE comercio = 'Olimpica'
              AND deleted = 0
              AND (comercio, producto_id) NOT IN (SELECT comercio, producto_id FROM mapeo_productos)
              AND id NOT IN (
                  SELECT MAX(h.id)
                  FROM productos_historico h
                  LEFT JOIN mapeo_productos m ON h.comercio = m.comercio AND h.producto_id = m.producto_id
                  WHERE h.comercio = 'Olimpica' AND h.deleted = 0 AND m.codigo_universal IS NULL
                  GROUP BY h.nombre
              )
              AND nombre IN (
                  SELECT h2.nombre
                  FROM productos_historico h2
                  LEFT JOIN mapeo_productos m2 ON h2.comercio = m2.comercio AND h2.producto_id = m2.producto_id
                  WHERE h2.comercio = 'Olimpica' AND h2.deleted = 0 AND m2.codigo_universal IS NULL
                  GROUP BY h2.nombre
                  HAVING COUNT(*) > 1
              )
        """)
        cleaned_count = cur.rowcount
        conn.commit()

    print(f"[OK] Registros depurados (deleted = 1): {cleaned_count:,}")
    
    print("\nRe-ejecutando proceso ETL de normalización...")
    database.run_normalization_etl()
    print("[OK] Tabla `productos_normalizados` actualizada.")
    
    print("\nActualizando paquete de datos en `data/mdm_export.json`...")
    export_mdm()
    print("\n[OK] Proceso completado exitosamente.")
    print("El archivo `data/mdm_export.json` está listo para ser copiado al servidor.")
    print("=" * 60)


if __name__ == "__main__":
    clean_olimpica_duplicates()
