import sqlite3
import pandas as pd
from database import DataSuiteDB

def validate_mdm():
    db = DataSuiteDB()
    
    print("="*70)
    print(" VALIDACION DEFINITIVA DEL MASTER DATA MANAGEMENT (MDM)")
    print("="*70)
    
    with db.get_connection() as conn:
        issues_found = 0
        warnings_found = 0
        
        # 1. RAW Huérfanos (Orphans)
        print("\n[1/5] Verificando productos RAW sin mapear (Huerfanos)...")
        orphans = pd.read_sql_query("""
            SELECT h.comercio, h.producto_id, h.nombre
            FROM productos_historico h
            LEFT JOIN mapeo_productos m ON h.comercio = m.comercio AND h.producto_id = m.producto_id
            WHERE m.codigo_universal IS NULL AND h.deleted = 0
        """, conn)
        if not orphans.empty:
            print(f"  [ERROR] Se encontraron {len(orphans)} productos RAW sin mapear.")
            print(f"          Ejemplos: {orphans.head(2).to_dict(orient='records')}")
            issues_found += 1
        else:
            print("  [OK] 100% de los productos RAW estan mapeados.")

        # 2. Mapeos Rotos (Broken Mappings)
        print("\n[2/5] Verificando integridad referencial de los mapeos...")
        broken = pd.read_sql_query("""
            SELECT m.comercio, m.producto_id, m.codigo_universal
            FROM mapeo_productos m
            LEFT JOIN maestro_productos mp ON m.codigo_universal = mp.codigo_universal
            WHERE mp.codigo_universal IS NULL OR mp.deleted = 1
        """, conn)
        if not broken.empty:
            print(f"  [ERROR] Hay {len(broken)} mapeos apuntando a un Maestro inexistente o eliminado.")
            print(f"          Esto causara que el ETL pierda estos productos.")
            print(f"          Ejemplos: {broken.head(2).to_dict(orient='records')}")
            issues_found += 1
        else:
            print("  [OK] Todos los mapeos apuntan a un producto Maestro valido.")

        # 3. Datos Maestros Incompletos (Data Quality)
        print("\n[3/5] Verificando calidad de datos en el Diccionario Maestro...")
        quality = pd.read_sql_query("""
            SELECT codigo_universal, nombre_estandar
            FROM maestro_productos
            WHERE deleted = 0 AND (
                nombre_estandar IS NULL OR nombre_estandar = '' OR
                marca_estandar IS NULL OR marca_estandar = '' OR
                tipo_producto_estandar IS NULL OR tipo_producto_estandar = ''
            )
        """, conn)
        if not quality.empty:
            print(f"  [ADVERTENCIA] Hay {len(quality)} productos Maestro con campos clave vacios (Nombre, Marca o Tipo).")
            print(f"                Ejemplos: {quality.head(2).to_dict(orient='records')}")
            warnings_found += 1
        else:
            print("  [OK] El Diccionario Maestro tiene todos sus campos clave completos.")

        # 4. Duplicidad de Cruces (One-to-Many Mappings)
        print("\n[4/5] Verificando duplicidad en la tabla de mapeo...")
        duplicates = pd.read_sql_query("""
            SELECT comercio, producto_id, COUNT(*) as mapeos
            FROM mapeo_productos
            GROUP BY comercio, producto_id
            HAVING mapeos > 1
        """, conn)
        if not duplicates.empty:
            print(f"  [ERROR CRITICO] Hay {len(duplicates)} productos RAW apuntando a MAS DE UN Maestro.")
            print(f"                  Ejemplos: {duplicates.head(2).to_dict(orient='records')}")
            issues_found += 1
        else:
            print("  [OK] No existen mapeos duplicados (Relacion 1 a 1 conservada).")

        # 5. Volumetría de Salida (Cruce Final)
        print("\n[5/5] Simulando la inyeccion a la tabla Normalizada...")
        etl_sim = pd.read_sql_query("""
            SELECT COUNT(*) as c
            FROM productos_historico h
            JOIN mapeo_productos m ON h.comercio = m.comercio AND h.producto_id = m.producto_id
            JOIN maestro_productos mp ON m.codigo_universal = mp.codigo_universal
            WHERE h.deleted = 0 AND mp.deleted = 0
        """, conn)
        valid_raw = pd.read_sql_query("SELECT COUNT(*) as c FROM productos_historico WHERE deleted = 0", conn)
        
        c_etl = etl_sim.iloc[0]['c']
        c_raw = valid_raw.iloc[0]['c']
        print(f"  - Total RAW validos: {c_raw}")
        print(f"  - Total Normalizados resultantes: {c_etl}")
        
        if c_etl < c_raw:
            diff = c_raw - c_etl
            print(f"  [ADVERTENCIA] Tu tabla normalizada tendra {diff} filas menos que tu RAW.")
            print(f"                Causa: Productos huerfanos o mapeos apuntando a Maestros eliminados.")
            warnings_found += 1
        elif c_etl > c_raw:
            print(f"  [ERROR] El ETL genera mas filas ({c_etl}) que los crudos originales ({c_raw}).")
            issues_found += 1
        else:
            print("  [OK] Perfecta correspondencia 1:1. Ningun producto valido se quedara por fuera.")

        print("\n" + "="*70)
        if issues_found == 0:
            print(" DICTAMEN FINAL: [APROBADO PARA PRODUCCION]")
            if warnings_found > 0:
                print(f"   Nota: Estructuralmente es perfecto, pero tienes {warnings_found} advertencia(s) menores de calidad.")
        else:
            print(f" DICTAMEN FINAL: [RECHAZADO]")
            print(f"   Se encontraron {issues_found} errores estructurales graves.")
            print("   Revisar los logs arriba y corregir la data o los mapeos antes de usar en Produccion.")
        print("="*70)

if __name__ == '__main__':
    validate_mdm()
