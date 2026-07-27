import os
import sys
import re
import pandas as pd
from database import DataSuiteDB

# Configurar encoding para consola de Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def normalize_reg(reg):
    if not reg or pd.isna(reg): return ""
    reg_str = str(reg).strip().upper()
    # Estandarizar espacios extras: "INVIMA L-  004478" -> "INVIMA L-004478"
    reg_str = re.sub(r'\s+', ' ', reg_str)
    reg_str = re.sub(r'L-\s+', 'L-', reg_str)
    return reg_str

def import_pp24_invima(excel_path="PP24-7001-INVIMA.xlsx"):
    if not os.path.exists(excel_path):
        print(f"ERROR: El archivo '{excel_path}' no existe.")
        return 0

    print(f"Leyendo archivo de nuevos registros INVIMA: {excel_path}...")
    df = pd.read_excel(excel_path)
    print(f"Total filas en {excel_path}: {len(df)}")

    db = DataSuiteDB()
    db.init_db()

    with db.get_connection() as conn:
        cur = conn.cursor()
        
        # Cargar registros y nombres existentes para evitar duplicados
        cur.execute("SELECT registro_sanitario, nombre_bebida_alcoholica FROM invima_certificados")
        existing_rows = cur.fetchall()
        
        existing_keys = set()
        for r_reg, r_nom in existing_rows:
            norm_r = normalize_reg(r_reg)
            norm_n = str(r_nom).strip().upper() if r_nom else ""
            if norm_r:
                existing_keys.add((norm_r, norm_n))

        print(f"Registros pre-existentes en DB: {len(existing_rows)}")

        # Obtener el máximo nro actual
        cur.execute("SELECT MAX(nro) FROM invima_certificados")
        max_nro_res = cur.fetchone()[0]
        current_nro = (max_nro_res or 0) + 1

        new_records = []
        added_keys = set()

        for idx, row in df.iterrows():
            reg_raw = row.get("REGISTRO_SANITARIO")
            reg_norm = normalize_reg(reg_raw)
            
            producto = str(row.get("PRODUCTO", "")).strip() if pd.notnull(row.get("PRODUCTO")) else ""
            marca = str(row.get("MARCA", "")).strip() if pd.notnull(row.get("MARCA")) else ""
            clasif = str(row.get("CLASIFICAION_BEBIDA", "")).strip() if pd.notnull(row.get("CLASIFICAION_BEBIDA")) else ""
            
            # Construir nombre compuesto
            parts = []
            if clasif and clasif.lower() not in producto.lower():
                parts.append(clasif)
            if producto:
                parts.append(producto)
            if marca and marca.lower() not in producto.lower():
                parts.append(f"MARCA {marca}")
                
            nombre_compuesto = " ".join(parts).title() if parts else "Bebida Alcoholica"
            norm_nom = nombre_compuesto.strip().upper()

            if not reg_norm and not norm_nom:
                continue

            key = (reg_norm, norm_nom)
            if key not in existing_keys and key not in added_keys:
                added_keys.add(key)
                new_records.append((
                    current_nro,
                    reg_norm if reg_norm else reg_raw,
                    "", # codigo_unico vacio si no aplica
                    nombre_compuesto,
                    0.0 # precio_referencia
                ))
                current_nro += 1

        print(f"Nuevos registros únicos a insertar: {len(new_records)}")

        if new_records:
            cur.executemany("""
                INSERT INTO invima_certificados (nro, registro_sanitario, codigo_unico, nombre_bebida_alcoholica, precio_referencia_750cc)
                VALUES (?, ?, ?, ?, ?)
            """, new_records)
            conn.commit()

        cur.execute("SELECT COUNT(*) FROM invima_certificados")
        total_final = cur.fetchone()[0]

    print(f"OK: Se insertaron exitosamente {len(new_records)} NUEVOS registros en la tabla invima_certificados.")
    print(f"Total registros INVIMA acumulados en DB: {total_final}")
    return len(new_records)

if __name__ == "__main__":
    import_pp24_invima()
