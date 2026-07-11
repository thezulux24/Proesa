import pandas as pd
import sqlite3
import os
from database import DataSuiteDB

def limpiar_inconsistencias():
    archivo_excel = "reporte_mapeos_inconsistentes.xlsx"
    
    if not os.path.exists(archivo_excel):
        print(f"❌ No se encontró el archivo '{archivo_excel}'.")
        print("Asegúrate de correr primero 'validador_semantico_ia.py' y que este encuentre errores.")
        return

    print("Leyendo reporte de inconsistencias...")
    df = pd.read_excel(archivo_excel)
    
    if df.empty or 'id' not in df.columns:
        print("El reporte está vacío o no tiene el formato esperado (falta la columna 'id').")
        return

    db = DataSuiteDB()
    eliminados = 0
    with db.get_connection() as conn:
        cur = conn.cursor()
        
        # Iterar sobre las inconsistencias y borrar los mapeos
        for index, row in df.iterrows():
            mapeo_id = str(row['id'])
            if "__" in mapeo_id:
                comercio, producto_id = mapeo_id.split("__", 1)
                
                # Borrar de la tabla de cruce
                cur.execute("DELETE FROM mapeo_productos WHERE comercio = ? AND producto_id = ?", (comercio, producto_id))
                eliminados += 1
                
        conn.commit()

    print("="*60)
    print(f"✅ ÉXITO: Se han desconectado {eliminados} mapeos incorrectos.")
    print("="*60)
    print("\n👉 PRÓXIMO PASO:")
    print("1. Abre la 'Suite Data' (py .\suite_app.py).")
    print("2. Ve a la pestaña 'Normalización'.")
    print("3. Haz clic en 'Auto-Mapeo (DeepSeek)'.")
    print("\nComo los productos volvieron a quedar 'Crudos / Sin Mapear', la IA los procesará nuevamente. Si realmente no pertenecen a ningún maestro actual, ¡el sistema creará un código Maestro Nuevo para ellos automáticamente!")

if __name__ == '__main__':
    limpiar_inconsistencias()
