#!/usr/bin/env python3
"""
Módulo de Inteligencia Artificial para Vincular Registros Sanitarios INVIMA a Productos Maestros
Ubicación: core/invima_ai_matcher.py

- Busca en el catálogo oficial de 10,972 certificados sanitarios INVIMA (`invima_certificados`).
- Indexa en memoria de base de datos vinculaciones INVIMA validadas en `maestro_productos`.
- Aplica TOLERANCIA CERO A FALSO POSITIVO. Si no está seguro con confianza >= 90%, responde "LEAVE" y deja el registro quieto.
- Ejecuta automáticamente ETL y exportación de respaldo `data/mdm_export.json`.
"""

import os
import sys
import json
import time
import re
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
from dotenv import load_dotenv
from openai import OpenAI

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core import database
from export_mdm import export_mdm

# Cargar API Key desde .env
load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")

client = None
if API_KEY:
    client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")

def normalize_text_for_search(text):
    if not text:
        return ""
    text = str(text).lower()
    text = re.sub(r'\bs\.?a\.?\b', 'sin azucar', text)
    text = re.sub(r'\bsugar\s*free\b', 'sin azucar', text)
    text = re.sub(r'\b0\s*azucar\b', 'sin azucar', text)
    text = re.sub(r'\bcero\s*azucar\b', 'sin azucar', text)
    text = re.sub(r'(\d+)\s*ml\b', r'\1 ml', text)
    text = re.sub(r'(\d+)\s*lt\b', r'\1 lt', text)
    text = re.sub(r'(\d+)\s*cc\b', r'\1 ml', text)
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return ' '.join(text.split())

def load_db_invima_mapped_memory():
    """Indexa productos maestros que YA TIENEN Registro INVIMA para aprendizaje y coincidencia directa."""
    db = database.DataSuiteDB()
    memory_map = {}
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT LOWER(nombre_estandar) as nom_norm, 
                       registro_sanitario_invima, codigo_unico_invima, nombre_invima, precio_referencia_invima
                FROM maestro_productos
                WHERE deleted = 0 
                  AND registro_sanitario_invima IS NOT NULL 
                  AND registro_sanitario_invima != '' 
                  AND registro_sanitario_invima != 'N/A'
            """)
            for nom_norm, reg, cod, nom_inv, prec in cur.fetchall():
                key = normalize_text_for_search(nom_norm)
                if key:
                    memory_map[key] = {
                        "action": "LINK_INVIMA",
                        "registro_sanitario_invima": reg,
                        "codigo_unico_invima": cod,
                        "nombre_invima": nom_inv,
                        "precio_referencia_invima": prec,
                        "razon": f"Coincidencia exacta en nombre estandar con maestro existente con INVIMA -> {reg} ({nom_inv})."
                    }
    except Exception as e:
        print(f"Advertencia al cargar memoria INVIMA de base de datos: {e}")
    return memory_map

DB_INVIMA_MEMORY = load_db_invima_mapped_memory()

def search_invima_candidates(master_item, top_n=15):
    """Busca los mejores candidatos en la tabla invima_certificados (10,972 registros)."""
    db = database.DataSuiteDB()
    name = master_item.get('nombre_estandar', '')
    brand = master_item.get('marca_estandar', '')
    subcat = master_item.get('subcategoria_estandar', '')

    brand_norm = normalize_text_for_search(brand)
    name_norm = normalize_text_for_search(name)

    ignore_words = {'aguardiente', 'cerveza', 'whisky', 'botella', 'garrafa', 'lata', 'tetrabik', 'sin', 'con', 'azucar', 'para', 'del', 'las', 'los', 'vino', 'ron', 'vodka'}
    tokens = [t for t in name_norm.split() if len(t) > 2 and t not in ignore_words]

    candidates = []
    seen_regs = set()

    with db.get_connection() as conn:
        cur = conn.cursor()

        # Búsqueda 1: Por marca y tokens clave
        where_clauses = []
        params = []
        if brand_norm and len(brand_norm) > 2:
            where_clauses.append("LOWER(marca) LIKE ? OR LOWER(nombre_bebida_alcoholica) LIKE ?")
            params.extend([f"%{brand_norm}%", f"%{brand_norm}%"])

        if tokens:
            token_likes = " OR ".join(["LOWER(nombre_bebida_alcoholica) LIKE ?" for _ in tokens[:2]])
            where_clauses.append(f"({token_likes})")
            params.extend([f"%{t}%" for t in tokens[:2]])

        if where_clauses:
            where_sql = " OR ".join(where_clauses)
            query = f"""
                SELECT registro_sanitario, codigo_unico, nombre_bebida_alcoholica, marca, clasificacion, grados_alcohol, precio_referencia_750cc
                FROM invima_certificados
                WHERE {where_sql}
                LIMIT 50
            """
            try:
                cur.execute(query, params)
                for reg, cod, nom, mrc, clas, grad, prec in cur.fetchall():
                    if reg and reg not in seen_regs:
                        seen_regs.add(reg)
                        candidates.append({
                            "registro_sanitario": reg,
                            "codigo_unico": cod or "",
                            "nombre_bebida_alcoholica": nom or "",
                            "marca": mrc or "",
                            "clasificacion": clas or "",
                            "grados_alcohol": grad or "",
                            "precio_referencia_750cc": float(prec) if prec is not None else None
                        })
            except Exception:
                pass

    # Calcular puntuación de similitud
    scored = []
    for c in candidates:
        nom_c = normalize_text_for_search(c['nombre_bebida_alcoholica'])
        mrc_c = normalize_text_for_search(c['marca'])

        sim = SequenceMatcher(None, name_norm, nom_c).ratio()
        if brand_norm and (brand_norm in mrc_c or mrc_c in brand_norm or brand_norm in nom_c):
            sim += 0.25

        # Penalización si difieren variantes conocidas
        for var_word in ['sin azucar', 'amarillo', 'fiesta', 'verde', 'rojo', 'azul', 'fusion', 'atardecer']:
            if var_word in name_norm and var_word not in nom_c:
                sim -= 0.35

        scored.append((sim, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:top_n]]

def evaluate_invima_with_deepseek(master_item, candidates, model_name="deepseek-chat"):
    if not client:
        return None

    system_prompt = """
Eres un Auditor de Regulaciones Sanitarias e Inteligencia de Mercado para Alcohol y Tabaco en Colombia.
Tu tarea es asignar el Registro Sanitario INVIMA correcto desde el catálogo oficial a un producto maestro con TOLERANCIA CERO A FALSO POSITIVO.

REGLA DE ORO DE DEJAR QUIETO (TOLERANCIA CERO):
- Si no estás seguro con un nivel de confianza alto (>=90%) de que un registro INVIMA corresponde exactamente al producto maestro, O si no existe el certificado adecuado en la lista de candidatos, DEBES responder "action": "LEAVE".
- NUNCA inventes o asocies un registro INVIMA si pertenece a otra marca o a una variedad/sub-línea incompatible (Ej: No asignes INVIMA de Ron Medellín 8 Años a Ron Medellín 3 Años; no asignes INVIMA de Aguardiente Cristal Tradicional a Aguardiente Cristal Sin Azúcar).
- Si el producto es Tabaco o un producto importado sin registro INVIMA en el catálogo -> ACCIÓN: "LEAVE".

ESTRATEGIA DE COINCIDENCIA:
1. "LINK_INVIMA": Solo cuando el candidato en la lista coincide en Marca, Tipo de Licor y Variedad/Sabor de forma inequívoca.
2. "LEAVE": Cuando no hay candidato con suficiente certeza o no existe el registro en la lista.

DEBES RESPONDER ÚNICAMENTE EN FORMATO JSON VÁLIDO CON LA SIGUIENTE ESTRUCTURA ESTRICTA:
{
  "action": "LINK_INVIMA" | "LEAVE",
  "registro_sanitario_invima": "INVIMA XXXXL-XXXXX" (solo si action es LINK_INVIMA, de lo contrario null),
  "codigo_unico_invima": "CÓDIGO_ÚNICO" (solo si action es LINK_INVIMA, de lo contrario null),
  "nombre_invima": "Nombre Oficial de la Bebida en Registro INVIMA" (solo si action es LINK_INVIMA, de lo contrario null),
  "precio_referencia_invima": 47348.0 (o null),
  "razon": "Explicación breve de la decisión"
}
"""

    user_payload = {
        "producto_maestro": {
            "codigo_universal": master_item.get('codigo_universal'),
            "nombre_estandar": master_item.get('nombre_estandar'),
            "marca_estandar": master_item.get('marca_estandar'),
            "tipo_producto_estandar": master_item.get('tipo_producto_estandar'),
            "subcategoria_estandar": master_item.get('subcategoria_estandar'),
            "volumen_estandar": master_item.get('volumen_estandar'),
            "grados_alcohol_estandar": master_item.get('grados_alcohol_estandar')
        },
        "candidatos_certificados_invima": candidates
    }

    try:
        kwargs = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, indent=2)}
            ]
        }
        if model_name == "deepseek-chat":
            kwargs["temperature"] = 0.0
            kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**kwargs)
        msg = response.choices[0].message
        content = msg.content.strip()

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        return json.loads(content)
    except Exception as e:
        print(f"Error al consultar DeepSeek API para INVIMA ({model_name}): {e}")
        return None

def process_single_invima_master(master_item, dry_run=False, model_name="deepseek-chat"):
    code = master_item.get('codigo_universal', '')
    name = master_item.get('nombre_estandar', '')
    brand = master_item.get('marca_estandar', '')

    # 1. Verificar si coincide 100% con un producto maestro que ya tiene INVIMA en DB
    name_norm = normalize_text_for_search(name)
    if name_norm in DB_INVIMA_MEMORY:
        decision = DB_INVIMA_MEMORY[name_norm]
        reg = decision['registro_sanitario_invima']
        nom_inv = decision['nombre_invima']
        print(f"[DB MEMORY INVIMA] [{code}] {name} -> {reg} ({nom_inv})")
        if not dry_run:
            database.update_master_invima(
                codigo_universal=code,
                registro_invima=reg,
                codigo_unico=decision.get('codigo_unico_invima'),
                nombre_invima=nom_inv,
                precio_invima=decision.get('precio_referencia_invima')
            )
        return "LINK_INVIMA"

    # 2. Buscar candidatos en la tabla invima_certificados (10,972 registros)
    candidates = search_invima_candidates(master_item, top_n=15)
    if not candidates:
        print(f"[LEAVE] [{code}] {name}: Sin candidatos en base de datos INVIMA.")
        return "LEAVE"

    # 3. Evaluar con DeepSeek
    decision = evaluate_invima_with_deepseek(master_item, candidates, model_name=model_name)
    if not decision or "action" not in decision:
        print(f"[SKIP] [{code}] {name}: Respuesta inválida de la IA.")
        return "SKIP"

    action = decision.get("action")
    razon = decision.get("razon", "")

    if action == "LINK_INVIMA":
        reg = decision.get("registro_sanitario_invima")
        cod_u = decision.get("codigo_unico_invima")
        nom_inv = decision.get("nombre_invima")
        prec_inv = decision.get("precio_referencia_invima")

        if not reg:
            print(f"[SKIP] [{code}] {name}: Decision LINK_INVIMA sin registro sanitario.")
            return "SKIP"

        print(f"[LINK_INVIMA] [{code}] {name} -> {reg} ({nom_inv}) | {razon}")
        if not dry_run:
            database.update_master_invima(
                codigo_universal=code,
                registro_invima=reg,
                codigo_unico=cod_u,
                nombre_invima=nom_inv,
                precio_invima=prec_inv
            )
        return "LINK_INVIMA"

    elif action == "LEAVE":
        print(f"[LEAVE] [{code}] {name} -> Sin coincidencia segura de INVIMA (Dejado quieto) | {razon}")
        return "LEAVE"

    else:
        print(f"[UNKNOWN] [{code}] {name}: Acción desconocida '{action}'")
        return "SKIP"

def run_auto_invima_matching(subcategoria="Todas", limit=0, workers=3, model_name="deepseek-chat", dry_run=False):
    """
    Función principal para procesar automáticamente registros sanitarios INVIMA pendientes.
    """
    print("=" * 70)
    print(" ASIGNACIÓN Y VINCULACIÓN DE REGISTROS SANITARIOS INVIMA CON IA ")
    print("=" * 70)
    print(f"Modelo: {model_name} | Subcategoría: {subcategoria} | Límite: {limit or 'Sin Límite'} | Dry Run: {dry_run}")
    print("Buscando productos maestros sin Registro INVIMA...")

    df_masters = database.get_unmapped_invima_masters(subcategoria=subcategoria, limit=limit)
    if df_masters.empty:
        print("[OK] Todos los productos maestros tienen Registro INVIMA asignado. No se requieren acciones de IA.")
        return {"LINK_INVIMA": 0, "LEAVE": 0, "SKIP": 0}

    total_items = len(df_masters)
    print(f"Total productos maestros a evaluar: {total_items:,}")
    print(f"Memoria de Base de Datos INVIMA: {len(DB_INVIMA_MEMORY):,} registros indexados.")
    print("Iniciando auditoría e inferencia de Registros INVIMA...\n")

    stats = {"LINK_INVIMA": 0, "LEAVE": 0, "SKIP": 0}
    master_records = df_masters.to_dict(orient="records")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_single_invima_master, item, dry_run, model_name): item for item in master_records}
        for i, future in enumerate(as_completed(futures), 1):
            res = future.result()
            stats[res] = stats.get(res, 0) + 1
            if i % 10 == 0 or i == total_items:
                print(f"--- Progreso: {i}/{total_items} ({(i/total_items)*100:.1f}%) | Vinc INVIMA: {stats['LINK_INVIMA']} | Dejados Quieto: {stats['LEAVE']} ---")

    print("\n" + "=" * 70)
    print(" RESUMEN DE PROCESAMIENTO INVIMA AI ")
    print("=" * 70)
    print(f"[OK] Registros Sanitarios INVIMA Asignados (LINK_INVIMA): {stats['LINK_INVIMA']:,}")
    print(f"[OK] Productos Dejados Quieto (LEAVE): {stats['LEAVE']:,}")
    print(f"[OK] Omitidos por Error (SKIP): {stats['SKIP']:,}")

    if not dry_run and stats['LINK_INVIMA'] > 0:
        print("\nRe-ejecutando proceso ETL de normalización...")
        database.run_normalization_etl()
        print("[OK] Tabla `productos_normalizados` actualizada con INVIMA.")

        print("\nActualizando paquete de datos en `data/mdm_export.json`...")
        export_mdm()
        print("[OK] Archivo `data/mdm_export.json` listo para migrar al servidor.")

    print("=" * 70)
    return stats

def main():
    parser = argparse.ArgumentParser(description="Módulo de Asignación de Registros Sanitarios INVIMA con IA")
    parser.add_argument("--subcategoria", type=str, default="Todas", help="Filtrar por subcategoría de maestro (Ej: Aguardiente, Ron, Vinos, etc.)")
    parser.add_argument("--limit", type=int, default=0, help="Límite de maestros a procesar (0 para todos)")
    parser.add_argument("--workers", type=int, default=3, help="Número de hilos concurrentes para consultar la API")
    parser.add_argument("--model", type=str, default="deepseek-chat", help="Modelo de IA: 'deepseek-chat' (V3) o 'deepseek-reasoner' (R1)")
    parser.add_argument("--dry-run", action="store_true", help="Simular sin modificar la base de datos")

    args = parser.parse_args()
    run_auto_invima_matching(
        subcategoria=args.subcategoria,
        limit=args.limit,
        workers=args.workers,
        model_name=args.model,
        dry_run=args.dry_run
    )

if __name__ == "__main__":
    main()
