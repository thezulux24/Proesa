import os
import sys
import re
import pandas as pd
from database import DataSuiteDB, run_normalization_etl

# Reconfigurar stdout para Unicode en Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def normalize_manual_code(val):
    if pd.isna(val):
        return None
    val_str = str(val).strip()
    if not val_str or val_str.upper() in ['NAN', 'NONE', 'NULL', '']:
        return None
    # Si es -1 o -1.0
    if val_str in ['-1', '-1.0', '-1.0 ']:
        return 'NO_APLICA'
    # Estandarizar "2011L-0005661" -> "INVIMA 2011L-0005661" si empieza con año+L
    if re.match(r'^\d{4}L-', val_str, re.IGNORECASE):
        val_str = f"INVIMA {val_str.upper()}"
    return val_str

def import_manual_invima_excel(excel_path="productos_pendientes_invima.xlsx"):
    if not os.path.exists(excel_path):
        print(f"ERROR: El archivo '{excel_path}' no existe.")
        return 0

    print(f"Leyendo registros manuales desde '{excel_path}'...")
    df = pd.read_excel(excel_path)
    
    col_codigo = [c for c in df.columns if 'Codigo Universal' in c or 'codigo_universal' in c][0]
    col_manual = [c for c in df.columns if 'REGISTRO_SANITARIO_INVIMA_MANUAL' in c or 'INVIMA' in c][0]
    
    db = DataSuiteDB()
    db.init_db()

    updated_count = 0
    with db.get_connection() as conn:
        cur = conn.cursor()
        
        # Cargar tabla de certificados para búsqueda inteligente
        cur.execute("SELECT registro_sanitario, nombre_bebida_alcoholica, codigo_unico FROM invima_certificados")
        cert_rows = cur.fetchall()
        
        # Mapa para búsqueda rápida
        cert_map = {}
        for r_reg, r_nom, r_cod in cert_rows:
            if r_reg:
                norm_key = re.sub(r'\s+', ' ', str(r_reg)).strip().upper()
                clean_key = re.sub(r'INVIMA\s*', '', norm_key).strip()
                cert_map[norm_key] = (r_reg, r_nom, r_cod)
                cert_map[clean_key] = (r_reg, r_nom, r_cod)

        for _, row in df.iterrows():
            cod_uni = str(row.get(col_codigo, "")).strip()
            raw_manual = row.get(col_manual)
            
            reg_manual = normalize_manual_code(raw_manual)
            
            # Si la celda está vacía (incompleto) -> ignorar para no sobrescribir nada
            if not cod_uni or reg_manual is None:
                continue

            if reg_manual == 'NO_APLICA':
                # -1 Indica un Falso Positivo (Kit, accesorio, mezclador sin alcohol, etc.)
                # Aplicamos Soft Delete (deleted = 1) según el protocolo del proyecto
                cur.execute("""
                    UPDATE maestro_productos
                    SET deleted = 1,
                        registro_sanitario_invima = 'FALSO_POSITIVO (-1)',
                        codigo_unico_invima = NULL,
                        nombre_invima = 'FALSO_POSITIVO'
                    WHERE codigo_universal = ?
                """, (cod_uni,))
                
                # También marcar como deleted = 1 en el histórico cruzando por mapeo
                cur.execute("""
                    UPDATE productos_historico
                    SET deleted = 1
                    WHERE (comercio, producto_id) IN (
                        SELECT comercio, producto_id FROM mapeo_productos WHERE codigo_universal = ?
                    )
                """, (cod_uni,))
                
                updated_count += 1
                print(f"  [MANUAL - FALSO POSITIVO (-1)] {cod_uni} -> Soft Delete (deleted = 1)")
            else:
                # Buscar en catálogo oficial certificado
                search_key = re.sub(r'\s+', ' ', reg_manual).strip().upper()
                clean_search = re.sub(r'INVIMA\s*', '', search_key).strip()

                matched_cert = cert_map.get(search_key) or cert_map.get(clean_search)
                
                if matched_cert:
                    official_reg, official_name, official_code = matched_cert
                    cur.execute("""
                        UPDATE maestro_productos
                        SET registro_sanitario_invima = ?,
                            codigo_unico_invima = ?,
                            nombre_invima = ?
                        WHERE codigo_universal = ?
                    """, (official_reg, official_code, str(official_name) if official_name else "", cod_uni))
                    updated_count += 1
                    print(f"  [MANUAL - INVIMA CERTIFICADO] {cod_uni} -> {official_reg} ({str(official_name)[:35]}...)")
                else:
                    cur.execute("""
                        UPDATE maestro_productos
                        SET registro_sanitario_invima = ?,
                            codigo_unico_invima = NULL,
                            nombre_invima = 'ASIGNACION_MANUAL'
                        WHERE codigo_universal = ?
                    """, (reg_manual, cod_uni))
                    updated_count += 1
                    print(f"  [MANUAL - CODIGO NUEVO] {cod_uni} -> {reg_manual}")

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

