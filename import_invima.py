import os
import sys
import pandas as pd
from database import DataSuiteDB

# Configurar encoding para consola de Windows si es necesario
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def import_invima_anexo(excel_path="Anexo-2024.xlsx"):
    if not os.path.exists(excel_path):
        print(f"ERROR: El archivo '{excel_path}' no existe.")
        return 0

    print(f"Leyendo {excel_path}...")
    # El archivo contiene encabezados en la fila 6 (index=6)
    df = pd.read_excel(excel_path, header=6)
    
    # Limpiar nombres de columnas
    df.columns = [str(col).strip() for col in df.columns]
    
    # Seleccionar y renombrar columnas
    col_nro = [c for c in df.columns if 'Nro' in c or 'nro' in c][0]
    col_reg = [c for c in df.columns if 'Registro' in c or 'INVIMA' in c][0]
    col_cod = [c for c in df.columns if 'C' in c and 'digo' in c or 'Único' in c or 'nico' in c][0]
    col_nom = [c for c in df.columns if 'Nombre' in c or 'Bebida' in c][0]
    col_pre = [c for c in df.columns if 'Precio' in c or '750' in c][0]

    records_to_insert = []
    for _, row in df.iterrows():
        try:
            nro = int(row[col_nro]) if pd.notnull(row[col_nro]) else None
        except Exception:
            nro = None
            
        reg_sanitario = str(row[col_reg]).strip() if pd.notnull(row[col_reg]) else ""
        cod_unico = str(row[col_cod]).strip() if pd.notnull(row[col_cod]) else ""
        nombre = str(row[col_nom]).strip() if pd.notnull(row[col_nom]) else ""
        
        try:
            precio = float(row[col_pre]) if pd.notnull(row[col_pre]) else 0.0
        except Exception:
            precio = 0.0
            
        if reg_sanitario or nombre:
            records_to_insert.append((nro, reg_sanitario, cod_unico, nombre, precio))

    print(f"Registros validos encontrados: {len(records_to_insert)}")

    db = DataSuiteDB()
    db.init_db()

    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM invima_certificados") # Limpieza completa para importación fresca
        cur.executemany("""
            INSERT INTO invima_certificados (nro, registro_sanitario, codigo_unico, nombre_bebida_alcoholica, precio_referencia_750cc)
            VALUES (?, ?, ?, ?, ?)
        """, records_to_insert)
        conn.commit()

    print(f"OK: Se insertaron exitosamente {len(records_to_insert)} registros de INVIMA en SQLite.")
    return len(records_to_insert)

if __name__ == "__main__":
    import_invima_anexo()
