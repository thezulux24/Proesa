import os
import sys
import pandas as pd
from database import DataSuiteDB, run_normalization_etl

def import_manual_invima_excel(excel_path="productos_pendientes_invima.xlsx"):
    if not os.path.exists(excel_path):
        print(f"ERROR: El archivo '{excel_path}' no existe.")
        return 0

    print(f"Leyendo registros manuales desde '{excel_path}'...")
    df = pd.read_excel(excel_path)
    
    col_codigo = [c for c in df.columns if 'Codigo Universal' in c or 'codigo_universal' in c][0]
    col_manual = [c for c in df.columns if 'REGISTRO_SANITARIO_INVIMA_MANUAL' in c or 'INVIMA' in c][0]
    
    updated_count = 0
    db = DataSuiteDB()
    db.init_db()

    with db.get_connection() as conn:
        cur = conn.cursor()
        for _, row in df.iterrows():
            cod_uni = str(row.get(col_codigo, "")).strip()
            reg_manual = str(row.get(col_manual, "")).strip()
            
            if cod_uni and reg_manual and reg_manual.upper() not in ['NAN', 'NONE', 'NULL', '']:
                cur.execute("""
                    UPDATE maestro_productos
                    SET registro_sanitario_invima = ?,
                        nombre_invima = 'ASIGNACION_MANUAL'
                    WHERE codigo_universal = ?
                """, (reg_manual, cod_uni))
                updated_count += 1
                print(f"  [MANUAL] {cod_uni} -> {reg_manual}")

        conn.commit()

    if updated_count > 0:
        print(f"Refrescando tabla normalizada...")
        run_normalization_etl()
        print(f"OK: Se actualizaron exitosamente {updated_count} productos en la base de datos.")
    else:
        print("No se encontraron nuevos registros manuales diligenciados en la columna REGISTRO_SANITARIO_INVIMA_MANUAL.")

    return updated_count

if __name__ == "__main__":
    import_manual_invima_excel()
