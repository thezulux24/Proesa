import sqlite3
import pandas as pd

conn = sqlite3.connect('suite_data.db')
print("=== TABLAS Y COLUMNAS ===")
tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table';", conn)
print(tables)

print("\n=== VALORES DISTINTOS PARA FILTROS ===")

print("1. Comercios (Fuentes):")
print(pd.read_sql_query("SELECT DISTINCT comercio FROM productos_historico WHERE deleted=0;", conn)['comercio'].tolist())

print("\n2. Tipos de Producto (Alcohol, Tabaco, etc.):")
print(pd.read_sql_query("SELECT DISTINCT tipo_producto FROM productos_historico WHERE deleted=0;", conn)['tipo_producto'].tolist())

print("\n3. Categorías Crudas (Top 15):")
print(pd.read_sql_query("SELECT categoria, COUNT(*) as c FROM productos_historico WHERE deleted=0 GROUP BY categoria ORDER BY c DESC LIMIT 15;", conn))

print("\n4. Subcategorías Estándar (Maestro MDM):")
print(pd.read_sql_query("SELECT subcategoria_estandar, COUNT(*) as c FROM maestro_productos WHERE deleted=0 GROUP BY subcategoria_estandar ORDER BY c DESC;", conn))

print("\n5. Marcas Más Comunes (Maestro MDM):")
print(pd.read_sql_query("SELECT marca_estandar, COUNT(*) as c FROM maestro_productos WHERE deleted=0 GROUP BY marca_estandar ORDER BY c DESC LIMIT 15;", conn))

print("\n6. Estado INVIMA (Maestro MDM):")
print(pd.read_sql_query("""
    SELECT 
        CASE 
            WHEN registro_sanitario_invima LIKE 'INVIMA%' OR registro_sanitario_invima LIKE 'L-%' OR registro_sanitario_invima LIKE 'RSA-%' THEN 'Ligado INVIMA'
            WHEN registro_sanitario_invima = 'N/A - TABACO' THEN 'Tabaco (N/A)'
            WHEN registro_sanitario_invima = 'NO_APLICA' THEN 'No Aplica (-1)'
            ELSE 'Sin Registro (Pendiente)'
        END AS estado_invima,
        COUNT(*) as cantidad
    FROM maestro_productos 
    WHERE deleted=0 
    GROUP BY estado_invima;
""", conn))

print("\n7. Clasificaciones INVIMA (Certificados):")
print(pd.read_sql_query("SELECT clasificacion, COUNT(*) as c FROM invima_certificados WHERE clasificacion IS NOT NULL AND clasificacion != '' GROUP BY clasificacion ORDER BY c DESC LIMIT 15;", conn))

print("\n8. Grados de Alcohol (°):")
print(pd.read_sql_query("SELECT DISTINCT grados_alcohol_estandar FROM maestro_productos WHERE deleted=0 LIMIT 15;", conn))

conn.close()
