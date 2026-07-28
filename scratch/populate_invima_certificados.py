import sqlite3
import pandas as pd

def populate_invima():
    print("Iniciando la ingesta y complementacion de datos de PP24-7001-INVIMA.xlsx...")
    df_excel = pd.read_excel('PP24-7001-INVIMA.xlsx')
    
    db_path = 'suite_data.db'
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    def clean_reg(val):
        if not val or pd.isna(val): return ''
        s = str(val).upper().strip()
        s = s.replace('INVIMA', '').replace('SANITA', '').replace('REGISTRO', '').strip()
        s = s.replace(' ', '').replace('-', '').replace('_', '')
        return s

    excel_dict = {}
    for _, r in df_excel.iterrows():
        c_reg = clean_reg(r['REGISTRO_SANITARIO'])
        if not c_reg: continue
        
        prod = str(r['PRODUCTO']).strip() if pd.notnull(r['PRODUCTO']) else ''
        clas = str(r['CLASIFICAION_BEBIDA']).strip() if pd.notnull(r['CLASIFICAION_BEBIDA']) else ''
        if not clas and pd.notnull(r.get('CLASIFICAION_BEBIDA2')):
            clas = str(r['CLASIFICAION_BEBIDA2']).strip()
        marca = str(r['MARCA']).strip() if pd.notnull(r['MARCA']) else ''
        grados = str(r['GRADO_ALCOHOLICO']).strip() if pd.notnull(r['GRADO_ALCOHOLICO']) else ''
        if grados and not grados.endswith('%') and not grados.endswith('°'):
            grados = f"{grados}°"

        excel_dict[c_reg] = {
            'registro': str(r['REGISTRO_SANITARIO']).strip(),
            'producto': prod,
            'clasificacion': clas,
            'marca': marca,
            'grados': grados
        }

    cur.execute("SELECT id, registro_sanitario, nombre_bebida_alcoholica, marca, clasificacion, grados_alcohol FROM invima_certificados")
    db_rows = cur.fetchall()

    updated_count = 0
    for row_id, reg, name, current_marca, current_clas, current_grados in db_rows:
        c_reg = clean_reg(reg)
        if c_reg in excel_dict:
            data = excel_dict[c_reg]
            m = data['marca'] or current_marca or ''
            c = data['clasificacion'] or current_clas or ''
            g = data['grados'] or current_grados or ''
            
            cur.execute("""
                UPDATE invima_certificados
                SET marca = ?,
                    clasificacion = ?,
                    grados_alcohol = ?
                WHERE id = ?
            """, (m, c, g, row_id))
            updated_count += 1

    conn.commit()
    print(f"Actualizados {updated_count} registros existentes en invima_certificados.")

    def infer_clasificacion(nombre):
        n = str(nombre).upper()
        if 'VINO' in n: return 'Vino'
        if 'WHISKY' in n or 'WHISKEY' in n: return 'Whisky'
        if 'RON' in n: return 'Ron'
        if 'AGUARDIENTE' in n: return 'Aguardiente'
        if 'CERVEZA' in n: return 'Cerveza'
        if 'TEQUILA' in n or 'MEZCAL' in n: return 'Tequila / Mezcal'
        if 'GINEBRA' in n or 'GIN' in n: return 'Ginebra'
        if 'VODKA' in n: return 'Vodka'
        if 'BRANDY' in n or 'COGNAC' in n: return 'Brandy / Cognac'
        if 'CREMA' in n or 'APERITIVO' in n or 'LICOR' in n: return 'Licores y Aperitivos'
        return 'Otras Bebidas Alcohólicas'

    cur.execute("SELECT id, nombre_bebida_alcoholica, clasificacion FROM invima_certificados WHERE clasificacion IS NULL OR clasificacion = ''")
    unclassified = cur.fetchall()
    for r_id, nom, _ in unclassified:
        inferred = infer_clasificacion(nom)
        cur.execute("UPDATE invima_certificados SET clasificacion = ? WHERE id = ?", (inferred, r_id))

    conn.commit()
    print(f"Inferidas clasificaciones automaticas para {len(unclassified)} registros restantes.")

    cur.execute("SELECT COUNT(*) FROM invima_certificados WHERE clasificacion IS NOT NULL AND clasificacion != ''")
    print(f"Total registros con Clasificacion: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM invima_certificados WHERE marca IS NOT NULL AND marca != ''")
    print(f"Total registros con Marca: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM invima_certificados WHERE grados_alcohol IS NOT NULL AND grados_alcohol != ''")
    print(f"Total registros con Grados de Alcohol: {cur.fetchone()[0]}")

    conn.close()

if __name__ == '__main__':
    populate_invima()
