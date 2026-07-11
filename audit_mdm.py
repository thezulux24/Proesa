import os
import sys
from database import DataSuiteDB
import pandas as pd

def audit():
    db = DataSuiteDB()
    with db.get_connection() as conn:
        print("="*50)
        print(" AUDITORIA DE MASTER DATA MANAGEMENT (MDM)")
        print("="*50)

        # 1. Total Raw Products
        raw = pd.read_sql_query("SELECT COUNT(*) as c FROM productos_historico WHERE deleted = 0", conn)
        total_raw = raw.iloc[0]['c']
        print(f" Total Productos Extraidos (RAW, no eliminados): {total_raw}")

        # 2. Total Master Products
        master = pd.read_sql_query("SELECT COUNT(*) as c FROM maestro_productos WHERE deleted = 0", conn)
        total_master = master.iloc[0]['c']
        print(f" Total Productos en Diccionario Maestro (Validos): {total_master}")

        # 3. Total Normalized (Mapped) Products
        norm = pd.read_sql_query("SELECT COUNT(*) as c FROM productos_normalizados", conn)
        total_norm = norm.iloc[0]['c']
        print(f" Total Productos Normalizados (Cruce exitoso): {total_norm}")

        print("\n--- METRICAS DE COBERTURA ---")
        if total_raw > 0:
            coverage = (total_norm / total_raw) * 100
            print(f" Tasa de Cobertura MDM: {coverage:.2f}%")
        else:
            print(" Tasa de Cobertura MDM: N/A (0 RAW)")

        # 4. Unmapped Products
        unmapped = pd.read_sql_query("""
            SELECT h.comercio, COUNT(*) as faltantes
            FROM productos_historico h
            LEFT JOIN mapeo_productos m ON h.comercio = m.comercio AND h.producto_id = m.producto_id
            WHERE m.codigo_universal IS NULL AND h.deleted = 0
            GROUP BY h.comercio
            ORDER BY faltantes DESC
        """, conn)

        print("\n--- PRODUCTOS HUERFANOS POR COMERCIO ---")
        if unmapped.empty:
            print(" Excelente! No hay productos huerfanos. Todo esta mapeado.")
        else:
            for _, row in unmapped.iterrows():
                print(f"   - {row['comercio']}: {row['faltantes']} sin mapear")
            print("\n RECOMENDACION: Abre la 'Suite Data > Normalizacion' y corre DeepSeek para auto-crear los maestros de estos productos.")

if __name__ == "__main__":
    audit()
