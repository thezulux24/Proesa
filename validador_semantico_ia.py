import os
import sys
import json
import sqlite3
import pandas as pd
from dotenv import load_dotenv

try:
    from openai import OpenAI
except ImportError:
    print("Por favor instala openai: pip install openai")
    sys.exit(1)

from database import DataSuiteDB

def validate_mappings_with_ai():
    load_dotenv()
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("Falta DEEPSEEK_API_KEY en .env")
        return
        
    db = DataSuiteDB()
    with db.get_connection() as conn:
        print("="*70)
        print("🧠 AUDITORIA SEMANTICA DE MAPEOS (DEEPSEEK AI)")
        print("="*70)
        print("Extrayendo mapeos actuales de la base de datos...")
        df = pd.read_sql_query("""
            SELECT m.comercio, m.producto_id, h.nombre as raw_nombre, mp.nombre_estandar, mp.marca_estandar
            FROM mapeo_productos m
            JOIN productos_historico h ON m.comercio = h.comercio AND m.producto_id = h.producto_id
            JOIN maestro_productos mp ON m.codigo_universal = mp.codigo_universal
            WHERE h.deleted = 0 AND mp.deleted = 0
        """, conn)
        
    total_mappings = len(df)
    print(f"Total de mapeos a revisar: {total_mappings}\n")
    if total_mappings == 0:
        return
        
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    chunk_size = 50
    bad_mappings = []
    
    for i in range(0, total_mappings, chunk_size):
        chunk = df.iloc[i:i+chunk_size]
        pairs_to_check = []
        for _, row in chunk.iterrows():
            pairs_to_check.append({
                "id": f"{row['comercio']}__{row['producto_id']}",
                "crudo": row['raw_nombre'],
                "maestro": f"{row['nombre_estandar']} ({row['marca_estandar']})"
            })
            
        print(f"Analizando bloque {i+1} a {min(i+chunk_size, total_mappings)} de {total_mappings}...")
        prompt = f"""
Eres un auditor experto en calidad de datos MDM.
A continuacion tienes una lista de mapeos entre un producto "crudo" (nombre original del supermercado) y su "maestro" (nombre estandarizado asignado en la base de datos central).
Evalua semanticamente si el mapeo es correcto. 
Un mapeo es correcto si se refieren claramente al mismo producto, marca y variante, permitiendo diferencias en la gramatica, orden de palabras o detalles de volumen menores (mientras no sean contradictorios).

Mapeos a auditar:
{json.dumps(pairs_to_check, ensure_ascii=False)}

Devuelve UNICAMENTE un arreglo JSON con los mapeos que consideres CLARAMENTE INCORRECTOS o ALTAMENTE DUDOSOS.
Si todos son correctos, devuelve un arreglo vacio [].
Formato esperado:
[
  {{"id": "Comercio__123", "crudo": "...", "maestro": "...", "razon": "Explicacion breve del error semantico"}}
]
No incluyas markdown. Solo JSON puro.
"""
        try:
            response = client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=[
                    {"role": "system", "content": "You are a strict data auditor. Output pure JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )
            text_response = response.choices[0].message.content.strip()
            text_response = text_response.replace("```json", "").replace("```", "").strip()
            
            if text_response:
                errores = json.loads(text_response)
                if errores:
                    print(f"  [!] Se encontraron {len(errores)} inconsistencias en este bloque.")
                    bad_mappings.extend(errores)
                else:
                    print(f"  [OK] Bloque impecable.")
            else:
                print(f"  [OK] Bloque impecable.")
            
        except Exception as e:
            print(f"  [ERROR] Procesando el bloque {i}: {e}")
            
    if bad_mappings:
        print("\n" + "="*70)
        print("🚨 REPORTE DE INCONSISTENCIAS SEMANTICAS (IA)")
        print("="*70)
        for m in bad_mappings[:10]: # Solo imprimir los primeros 10 en consola
            print(f"❌ ID: {m.get('id')}")
            print(f"   Crudo  : {m.get('crudo')}")
            print(f"   Maestro: {m.get('maestro')}")
            print(f"   Razon  : {m.get('razon')}\n")
            
        if len(bad_mappings) > 10:
            print(f"... y {len(bad_mappings) - 10} inconsistencias mas.")
            
        df_bad = pd.DataFrame(bad_mappings)
        df_bad.to_excel("reporte_mapeos_inconsistentes.xlsx", index=False)
        print(f"\n📁 El reporte completo se ha guardado en 'reporte_mapeos_inconsistentes.xlsx'")
        print("Por favor revisa el Excel, borra los mapeos incorrectos en la base de datos y vuelve a normalizar.")
    else:
        print("\n✅ ¡Felicitaciones! DeepSeek ha determinado que el 100% de los mapeos son semanticamente coherentes.")

if __name__ == '__main__':
    validate_mappings_with_ai()
