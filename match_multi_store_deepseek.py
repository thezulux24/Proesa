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

from database import DataSuiteDB, run_normalization_etl

STOP_WORDS = {
    'de', 'del', 'la', 'el', 'los', 'las', 'un', 'una', 'con', 'sin', 'para', 'por', 'en',
    'ml', 'l', 'cc', 'gr', 'g', 'kg', 'lata', 'botella', 'caja', 'pack', 'x', 'vol', 'alc', 'und', 'uds'
}

LOG_FILE = "match_multistore.log"

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
    tokens = [w.lower() for w in text.split() if w.lower() not in STOP_WORDS and len(w) > 1]
    return " ".join(tokens)

def find_best_master_candidates(raw_nombre, raw_marca, master_list, top_n=10):
    clean_raw = clean_text(f"{raw_marca or ''} {raw_nombre or ''}")
    raw_tokens = set(clean_raw.split())
    
    scored = []
    
    for m in master_list:
        cod, m_nom, m_mar, m_vol, m_reg, m_inv = m
        clean_m = clean_text(f"{m_mar or ''} {m_nom or ''} {m_inv or ''}")
        m_tokens = set(clean_m.split())
        
        common = raw_tokens.intersection(m_tokens)
        token_score = len(common) / max(len(raw_tokens), 1)
        diff_score = difflib.SequenceMatcher(None, clean_raw, clean_m).ratio()
        
        # Ponderación combinada
        score = (token_score * 0.6) + (diff_score * 0.4)
        
        # Aumentar levemente si la marca coincide explícitamente
        if raw_marca and m_mar and raw_marca.lower() in m_mar.lower():
            score += 0.10
            
        if score > 0.12:
            scored.append({
                "codigo_universal": cod,
                "nombre_maestro": m_nom,
                "marca_maestro": m_mar,
                "volumen_maestro": m_vol,
                "registro_invima": m_reg,
                "nombre_invima": m_inv,
                "score": round(score, 3)
            })
            
    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored[:top_n]

def run_multistore_matching(store="all", limit=2000, batch_size=10, model_name="deepseek-v4-flash"):
    load_dotenv()
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        log("ERROR: Falta DEEPSEEK_API_KEY en el archivo .env")
        return

    db = DataSuiteDB()
    db.init_db()

    log("="*70)
    log("🔗 CRUCE MULTI-TIENDA MDM ASISTIDO POR DEEPSEEK AI")
    log("="*70)

    with db.get_connection() as conn:
        cur = conn.cursor()
        log("Cargando lista completa de productos maestros activos (maestro_productos)...")
        cur.execute("""
            SELECT codigo_universal, nombre_estandar, marca_estandar, volumen_estandar,
                   registro_sanitario_invima, nombre_invima
            FROM maestro_productos
            WHERE deleted = 0
        """)
        master_list = cur.fetchall()
        log(f"Total productos maestros activos disponibles para ligar: {len(master_list)}")

        log("Consultando productos sin mapear en productos_historico...")
        if store and store.lower() != "all":
            store_filter = "AND h.comercio LIKE ?"
            params = (f"%{store}%", limit)
        else:
            store_filter = ""
            params = (limit,)

        query_unmapped = f"""
            SELECT h.comercio, h.producto_id, h.nombre, h.marca, h.medida, h.categoria, h.tipo_producto
            FROM productos_historico h
            LEFT JOIN mapeo_productos m ON h.comercio = m.comercio AND h.producto_id = m.producto_id
            WHERE m.codigo_universal IS NULL 
              AND h.deleted = 0
              {store_filter}
            GROUP BY h.comercio, h.producto_id
            LIMIT ?
        """
        cur.execute(query_unmapped, params)
        unmapped_prods = cur.fetchall()

    total_prods = len(unmapped_prods)
    log(f"Tienda(s) objetivo: {store}")
    log(f"Modelo seleccionado: {model_name}")
    log(f"Productos sin mapear a procesar en esta ejecucion: {total_prods}")

    if total_prods == 0:
        log("OK: No hay productos pendientes por mapear.")
        return

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    total_matched = 0
    total_unmatched = 0
    start_time = time.time()

    for i in range(0, total_prods, batch_size):
        batch = unmapped_prods[i:i+batch_size]
        items_payload = []
        
        for p in batch:
            com, pid, nom, marca, med, cat, tipo = p
            candidates = find_best_master_candidates(nom, marca, master_list, top_n=10)
            
            items_payload.append({
                "comercio": com,
                "producto_id": pid,
                "producto_bruto_tienda": nom,
                "marca_tienda": marca,
                "categoria_tienda": cat,
                "medida_tienda": med,
                "candidatos_maestros_existentes": candidates
            })

        batch_num = (i // batch_size) + 1
        total_batches = (total_prods + batch_size - 1) // batch_size
        pct = round(((i + len(batch)) / total_prods) * 100, 1)

        log(f"=== Bloque {batch_num}/{total_batches} ({pct}%) | Modelo: {model_name} | Procesando {i+1} a {min(i+batch_size, total_prods)} de {total_prods} ===")

        prompt = f"""
Eres un auditor experto de Inteligencia de Mercado y MDM de bebidas alcohólicas y tabaco en Colombia (Banco Mundial / PROESA).
Tu objetivo es emparejar productos sin clasificar extraídos de supermercados (Jumbo, Olímpica, Carulla, D1, Makro, Cañaveral, etc.) con el catálogo oficial de Productos Maestros (`maestro_productos`).

REGLAS ESTRICTAS DE CALIDAD Y CERO IMPRECISIÓN:
1. NO PUEDES CREAR PRODUCTOS NUEVOS. Únicamente puedes asociar el producto a una clave `codigo_universal` que figure explícitamente en la lista de `candidatos_maestros_existentes`.
2. EXIGENCIA DE ALTA PRECISIÓN: Debe ser el MISMO producto físico, misma marca, mismo sabor/variante y mismo volumen.
3. EQUIVALENCIAS COLOMBIANAS:
   - "Tapa Roja" = "Rojo" = 29°
   - "Tapa Azul" = "Azul" = "Sin Azúcar"
   - "Tapa Verde" = "Verde" = "24°" = "Sin Azúcar 24°"
   - "750ml" = "750cc" = "750 c.c." = "750" (PERO 750ml NO es 375ml ni 1000ml ni 1.5L. Si el volumen no coincide, NO MATCHAR).
   - "Red Label" != "Black Label" != "Blue Label" (Son variantes totalmente diferentes).
   - "Aguardiente Blanco" != "Aguardiente Amarillo".
   - "Cabernet Sauvignon" != "Merlot" != "Carmenere" != "Malbec".
4. SI TIENES CUALQUIER DUDA, si el volumen difiere o la variante no es idéntica, DEBES responder con `matched_codigo_universal: null`. CERO FALSOS POSITIVOS. Es preferible dejar sin mapear que mapear incorrectamente.

Productos a auditar:
{json.dumps(items_payload, ensure_ascii=False, indent=2)}

DEBES responder UNICAMENTE con un arreglo JSON puro (sin bloques de codigo markdown ```json) estructurado asi:
[
  {{
    "comercio": "Olimpica",
    "producto_id": "12345",
    "matched_codigo_universal": "EXI_100033",
    "confianza": "ALTA",
    "razon": "Coincidencia exacta de Aguardiente Antioqueño Tapa Roja 750ml"
  }}
]
"""
        t0 = time.time()
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a strict product matcher for Colombian retail MDM. Output JSON array only."},
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
                    com_res = res.get("comercio")
                    pid_res = res.get("producto_id")
                    matched_cod = res.get("matched_codigo_universal")
                    razon = res.get("razon", "")

                    if matched_cod and matched_cod != "null" and matched_cod != "NULL":
                        # Verificar que el código existe en master
                        cur.execute("SELECT nombre_estandar FROM maestro_productos WHERE codigo_universal = ? AND deleted = 0", (matched_cod,))
                        master_row = cur.fetchone()
                        if master_row:
                            cur.execute("""
                                INSERT OR REPLACE INTO mapeo_productos (comercio, producto_id, codigo_universal)
                                VALUES (?, ?, ?)
                            """, (com_res, pid_res, matched_cod))
                            batch_matched += 1
                            log(f"  [LIGADO OK] [{com_res}] ID:{pid_res} -> {matched_cod} ({master_row[0][:35]}...) | {razon[:40]}")
                        else:
                            batch_no_match += 1
                            log(f"  [OMITIDO - CODIGO NO EXISTE] [{com_res}] ID:{pid_res} -> {matched_cod}")
                    else:
                        batch_no_match += 1
                        log(f"  [SIN LIGAR] [{com_res}] ID:{pid_res} -> Dejado sin mapear (Baja confianza o sin candidato)")

                conn.commit()

            total_matched += batch_matched
            total_unmatched += batch_no_match
            log(f"  [OK] Bloque completado en {elapsed_api}s. Acumulado en esta ejecucion: {total_matched} ligados a MDM, {total_unmatched} sin ligar.\n")

        except Exception as e:
            log(f"  [ERROR] Error procesando bloque con DeepSeek: {e}\n")

    # Ejecutar ETL para refrescar productos normalizados al finalizar
    log("Refrescando la tabla productos_normalizados mediante ETL...")
    run_normalization_etl()

    elapsed_total = round(time.time() - start_time, 2)
    log("="*70)
    log(f"CRUCE MULTI-TIENDA FINALIZADO ({elapsed_total}s)")
    log(f"  Tienda(s) procesada(s) : {store}")
    log(f"  Modelo utilizado       : {model_name}")
    log(f"  Productos ligados a MDM : {total_matched}")
    log(f"  Dejados sin mapear     : {total_unmatched}")
    log("="*70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cruce de Productos Multi-Tienda contra MDM con DeepSeek AI")
    parser.add_argument("--store", type=str, default="all", help="Nombre del comercio (ej: Olimpica, Carulla, Jumbo, Canaveral, D1, Makro, all)")
    parser.add_argument("--limit", type=int, default=2000, help="Cantidad maxima de productos a procesar")
    parser.add_argument("--batch-size", type=int, default=10, help="Tamano de lote por peticion a DeepSeek")
    parser.add_argument("--model", type=str, default="deepseek-v4-flash", help="Nombre del modelo de DeepSeek")
    args = parser.parse_args()

    run_multistore_matching(store=args.store, limit=args.limit, batch_size=args.batch_size, model_name=args.model)
