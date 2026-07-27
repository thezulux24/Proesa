import os
import sys
import json
import re
import time
import difflib
import argparse
import datetime
from dotenv import load_dotenv

# Reconfigurar stdout para Unicode en Windows con flush por defecto
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    from openai import OpenAI
except ImportError:
    print("Error: Por favor instala la libreria openai (pip install openai)", flush=True)
    sys.exit(1)

from database import DataSuiteDB

STOP_WORDS = {
    'de', 'del', 'la', 'el', 'los', 'las', 'un', 'una', 'con', 'sin', 'para', 'por', 'en',
    'ml', 'l', 'cc', 'gr', 'g', 'kg', 'lata', 'botella', 'caja', 'pack', 'x', 'vol', 'alc'
}

LOG_FILE = "match_invima.log"

def log(msg):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass

def clean_text(text):
    if not text: return ""
    text = re.sub(r'\(.*?\)', '', str(text)) # Remover paréntesis
    text = re.sub(r'[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s]', ' ', text)
    tokens = [w for w in text.lower().split() if w not in STOP_WORDS and len(w) > 1]
    return " ".join(tokens)

def find_best_candidates(prod_nombre, prod_marca, invima_records, top_n=15):
    cleaned_prod = clean_text(f"{prod_marca} {prod_nombre}")
    prod_tokens = set(cleaned_prod.split())
    
    scored_candidates = []
    
    for inv in invima_records:
        inv_id, inv_nombre, inv_reg, inv_cod = inv
        cleaned_inv = clean_text(inv_nombre)
        inv_tokens = set(cleaned_inv.split())
        
        # Coincidencia de tokens y difflib ratio
        common_tokens = prod_tokens.intersection(inv_tokens)
        token_score = len(common_tokens) / (max(len(prod_tokens), 1))
        diff_score = difflib.SequenceMatcher(None, cleaned_prod, cleaned_inv).ratio()
        combined_score = (token_score * 0.6) + (diff_score * 0.4)
        
        if combined_score > 0.05: # Umbral más amplio para capturar más candidatos potenciales
            scored_candidates.append({
                "id": inv_id,
                "nombre_invima": inv_nombre,
                "registro_sanitario": inv_reg,
                "codigo_unico": inv_cod,
                "score": round(combined_score, 3)
            })
            
    scored_candidates.sort(key=lambda x: x['score'], reverse=True)
    return scored_candidates[:top_n]

def run_deepseek_matching(limit=2000, batch_size=10, model_name="deepseek-v4-flash", retry_unmatched=False):
    load_dotenv()
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        log("ERROR: Falta DEEPSEEK_API_KEY en el archivo .env")
        return

    db = DataSuiteDB()
    db.init_db()

    with db.get_connection() as conn:
        cur = conn.cursor()
        log("Cargando productos oficiales de INVIMA desde la base de datos...")
        cur.execute("SELECT id, nombre_bebida_alcoholica, registro_sanitario, codigo_unico FROM invima_certificados")
        invima_records = cur.fetchall()
        log(f"Total registros INVIMA cargados: {len(invima_records)}")

        if retry_unmatched:
            log("Re-evaluando productos en estado 'SIN_REGISTRO_ENCONTRADO' o sin asignar...")
            query_where = "(registro_sanitario_invima IS NULL OR registro_sanitario_invima = '' OR registro_sanitario_invima = 'SIN_REGISTRO_ENCONTRADO')"
        else:
            log("Cargando productos maestros pendientes de Registro INVIMA...")
            query_where = "(registro_sanitario_invima IS NULL OR registro_sanitario_invima = '')"

        cur.execute(f"""
            SELECT codigo_universal, nombre_estandar, marca_estandar, subcategoria_estandar
            FROM maestro_productos
            WHERE {query_where}
              AND tipo_producto_estandar = 'Alcohol'
              AND deleted = 0
            LIMIT ?
        """, (limit,))
        maestro_prods = cur.fetchall()

    total_prods = len(maestro_prods)
    log(f"Modelo seleccionado: {model_name}")
    log(f"Productos a procesar en esta ejecucion: {total_prods}")
    if total_prods == 0:
        log("OK: No hay productos pendientes de matching.")
        return

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    total_matched = 0
    total_not_found = 0
    start_time = time.time()

    for i in range(0, total_prods, batch_size):
        batch = maestro_prods[i:i+batch_size]
        items_payload = []
        
        for p in batch:
            cod_uni, nombre, marca, subcat = p
            candidates = find_best_candidates(nombre, marca, invima_records, top_n=15)
            items_payload.append({
                "codigo_universal": cod_uni,
                "producto_comercial": nombre,
                "marca": marca,
                "categoria": subcat,
                "candidatos_invima_oficiales": candidates
            })

        batch_num = (i // batch_size) + 1
        total_batches = (total_prods + batch_size - 1) // batch_size
        pct = round(((i + len(batch)) / total_prods) * 100, 1)

        log(f"=== Bloque {batch_num}/{total_batches} ({pct}%) | Modelo: {model_name} | Procesando {i+1} a {min(i+batch_size, total_prods)} de {total_prods} ===")

        prompt = f"""
Eres un experto en inteligencia de mercado y regulaciones de bebidas alcoholicas en Colombia (INVIMA).
Tu objetivo es emparejar cada producto comercial de retail con su Registro Sanitario INVIMA oficial exacto basado en la lista de candidatos oficiales proporcionados.

Instrucciones:
1. Revisa detenidamente el nombre del producto comercial y su marca.
2. Compara con la lista de candidatos oficiales del INVIMA provistos.
3. Si uno de los candidatos corresponde al mismo producto/variante/marca, selecciona ese candidato.
4. Si ninguno de los candidatos es una coincidencia confiable o el producto no esta en el listado oficial, asigna NULL en matched_invima_id.

Productos a evaluar:
{json.dumps(items_payload, ensure_ascii=False, indent=2)}

DEBES responder UNICAMENTE con un arreglo JSON puro (sin bloques de codigo markdown ```json) estructurado asi:
[
  {{
    "codigo_universal": "EXI_123",
    "matched_invima_id": 45,
    "registro_sanitario": "INVIMA 2002L-0000525",
    "codigo_unico": "24131010000100075000",
    "nombre_invima": "Nombre Oficial INVIMA",
    "confianza": "ALTA",
    "razon": "Coincidencia exacta de marca y producto"
  }}
]
"""
        t0 = time.time()
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a strict product matching AI for INVIMA regulatory data. Output JSON array only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )
            elapsed_api = round(time.time() - t0, 2)
            res_text = response.choices[0].message.content.strip()
            res_text = res_text.replace("```json", "").replace("```", "").strip()

            results = json.loads(res_text)

            batch_matched = 0
            batch_no_match = 0

            with db.get_connection() as conn:
                cur = conn.cursor()
                for res in results:
                    cod_uni = res.get("codigo_universal")
                    matched_id = res.get("matched_invima_id")
                    reg_invima = res.get("registro_sanitario")
                    cod_unico = res.get("codigo_unico")
                    nom_invima = res.get("nombre_invima")

                    if matched_id and reg_invima and reg_invima != "NULL":
                        cur.execute("""
                            UPDATE maestro_productos
                            SET registro_sanitario_invima = ?,
                                codigo_unico_invima = ?,
                                nombre_invima = ?
                            WHERE codigo_universal = ?
                        """, (reg_invima, cod_unico, nom_invima, cod_uni))
                        batch_matched += 1
                        log(f"  [MATCH RE-EVALUADO] {cod_uni} -> {reg_invima} ({nom_invima})")
                    else:
                        cur.execute("""
                            UPDATE maestro_productos
                            SET registro_sanitario_invima = 'SIN_REGISTRO_ENCONTRADO'
                            WHERE codigo_universal = ?
                        """, (cod_uni,))
                        batch_no_match += 1
                        log(f"  [NO MATCH] {cod_uni} -> Sin registro certificado")

                conn.commit()

            total_matched += batch_matched
            total_not_found += batch_no_match
            log(f"  [OK] Bloque completado en {elapsed_api}s. Acumulado en esta ronda: {total_matched} nuevos con INVIMA, {total_not_found} sin registro.\n")

        except Exception as e:
            log(f"  [ERROR] Error procesando bloque con DeepSeek: {e}\n")

    # Ejecutar ETL para refrescar productos normalizados al finalizar
    from database import run_normalization_etl
    run_normalization_etl()

    elapsed_total = round(time.time() - start_time, 2)
    log(f"==================================================")
    log(f"PROCESO DE MATCHING DEEPSEEK FINALIZADO ({elapsed_total}s)")
    log(f"  Modelo utilizado       : {model_name}")
    log(f"  Nuevos emparejados     : {total_matched}")
    log(f"  Sin registro certificado: {total_not_found}")
    log(f"==================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Matching de Registro Sanitario INVIMA con DeepSeek AI")
    parser.add_argument("--limit", type=int, default=2000, help="Cantidad de productos a procesar")
    parser.add_argument("--batch-size", type=int, default=10, help="Tamano de lote por peticion a DeepSeek")
    parser.add_argument("--model", type=str, default="deepseek-v4-flash", help="Nombre del modelo de DeepSeek")
    parser.add_argument("--retry-unmatched", action="store_true", help="Re-evaluar productos previamente marcados como SIN_REGISTRO_ENCONTRADO con candidatos mas amplios")
    args = parser.parse_args()

    run_deepseek_matching(limit=args.limit, batch_size=args.batch_size, model_name=args.model, retry_unmatched=args.retry_unmatched)
