#!/usr/bin/env python3
"""
Módulo y Script de Deduplicación y Fusión de Productos Maestros MDM con IA (DeepSeek)
Ubicación: deduplicate_mdm_deepseek.py

- Identifica productos maestros duplicados o casi-idénticos generados en creaciones concurrentes.
- Realiza fusión determinística para duplicados exactos (mismo nombre normalizado y volumen).
- Utiliza DeepSeek AI para evaluar variantes semánticas dudosas (sinónimos, mayúsculas, orden de palabras).
- Re-vincula automáticamente los mapeos de tiendas (`mapeo_productos`) hacia el código maestro canónico.
- Marca los maestros duplicados como `deleted = 1` (Soft Delete).
- Reconstruye `productos_normalizados` y actualiza `data/mdm_export.json`.
"""

import os
import sys
import json
import re
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

from core import database
from export_mdm import export_mdm

load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")

client = None
if API_KEY:
    client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")

def normalize_text_for_dedup(text):
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

def extract_volume_simple(text):
    if not text:
        return ""
    t = str(text).lower()
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*(ml|l|lt|cc|g|gr|kg|und|cajetillas|unidades)\b', t)
    if m:
        return f"{m.group(1)} {m.group(2).upper()}"
    return ""

def evaluate_cluster_with_deepseek(canonical_item, candidate_items, model_name="deepseek-chat"):
    if not client:
        return []

    system_prompt = """
Eres un Ingeniero de Datos Senior experto en Master Data Management (MDM) de Tabaco y Alcohol en Colombia.
Se te presenta un Producto Maestro Principal (Canónico) y una lista de Candidatos Maestros Sospechosos de ser DUPLICADOS.
Tu objetivo es determinar cuáles candidatos representan EXACTAMENTE el mismo producto físico (misma marca, misma sub-línea, misma variedad y mismo volumen/presentación) para fusionarlos al código del Maestro Principal.

REGLAS DE DECISIÓN ESTRICTAS:
1. FUSIONAR (MERGE = TRUE):
   - Mismo producto con ligeras variaciones de redacción, mayúsculas, signos de puntuación o sinónimos (Ej: "Cartón de cigarrillos SCARLET Iluma (10 cajetillas)" vs "Cartón de cigarrillos SCARLET ILUMA (10 cajetillas)").
   - "Vapeador GLUCLOUD Bateria Boxpod (1 und)" vs "Vapeador GLUCLOUD Box Pod Bateria (1 und)".
   - "Cerveza Corona Extra 355 ml" vs "Cerveza Corona Extra Botella (355 ml)".

2. NO FUSIONAR / MANTENER SEPARADOS (MERGE = FALSE):
   - Volúmenes o presentaciones distintas (Ej: 750 ml vs 1 Lt, 10 cajetillas vs 20 unidades, lata vs botella si la marca las maneja separadas).
   - Sabores, variedades o sub-líneas distintas (Ej: Sin Azúcar vs Tradicional, Antioqueño Verde 24° vs Azul 29°, Whisky 12 Años vs 18 Años, Sabor Mora vs Sandía).
   - Marcas distintas (Ej: Marlboro vs Lucky Strike, Caucano vs Antioqueño).

RESPONDE ÚNICAMENTE EN FORMATO JSON CON ESTA ESTRUCTURA:
{
  "evaluaciones": [
    {
      "codigo_candidato": "MST_XXXXX",
      "should_merge": true | false,
      "razon": "Explicación breve"
    }
  ]
}
"""

    user_payload = {
        "maestro_canonico": {
            "codigo_universal": canonical_item["codigo_universal"],
            "nombre_estandar": canonical_item["nombre_estandar"],
            "marca_estandar": canonical_item["marca_estandar"],
            "volumen_estandar": canonical_item["volumen_estandar"],
            "tipo_producto_estandar": canonical_item["tipo_producto_estandar"],
            "grados_alcohol_estandar": canonical_item["grados_alcohol_estandar"]
        },
        "candidatos_sospechosos_de_duplicado": [
            {
                "codigo_universal": c["codigo_universal"],
                "nombre_estandar": c["nombre_estandar"],
                "marca_estandar": c["marca_estandar"],
                "volumen_estandar": c["volumen_estandar"],
                "tipo_producto_estandar": c["tipo_producto_estandar"],
                "grados_alcohol_estandar": c["grados_alcohol_estandar"]
            }
            for c in candidate_items
        ]
    }

    try:
        response = client.chat.completions.create(
            model=model_name,
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, indent=2)}
            ]
        )
        content = response.choices[0].message.content.strip()
        data = json.loads(content)
        return data.get("evaluaciones", [])
    except Exception as e:
        print(f"Error al consultar DeepSeek: {e}")
        return []

def run_mdm_deduplication(dry_run=False, workers=3, min_similarity=0.82):
    print("=" * 70)
    print(" DEDUPLICACIÓN Y FUSIÓN DE PRODUCTOS MAESTROS (MDM AI) ")
    print("=" * 70)

    db = database.DataSuiteDB()
    with db.get_connection() as conn:
        # Cargar todos los maestros activos y el conteo de mapeos
        df_masters = pd.read_sql_query("""
            SELECT mp.codigo_universal, mp.nombre_estandar, mp.marca_estandar, 
                   mp.volumen_estandar, mp.tipo_producto_estandar, mp.grados_alcohol_estandar,
                   mp.registro_sanitario_invima,
                   COALESCE(map_cnt.total_mappings, 0) as total_mappings
            FROM maestro_productos mp
            LEFT JOIN (
                SELECT codigo_universal, COUNT(*) as total_mappings
                FROM mapeo_productos
                GROUP BY codigo_universal
            ) map_cnt ON mp.codigo_universal = map_cnt.codigo_universal
            WHERE mp.deleted = 0
            ORDER BY total_mappings DESC, mp.codigo_universal ASC
        """, conn)

    print(f"Total maestros activos en catálogo: {len(df_masters):,}")

    # =========================================================================
    # FASE 1: FUSIÓN DETERMINÍSTICA DE DUPLICADOS EXACTOS (Mismo nombre normalizado)
    # =========================================================================
    print("\n--- FASE 1: Detección y Fusión de Duplicados Exactos ---")
    df_masters["norm_name"] = df_masters["nombre_estandar"].apply(normalize_text_for_dedup)
    
    exact_groups = df_masters.groupby("norm_name")
    exact_merges = []  # list of (keep_code, dup_code, name)
    already_merged_codes = set()

    for norm_name, group in exact_groups:
        if len(group) > 1 and norm_name:
            # Ordenar por: tiene registro INVIMA > mayor cantidad de mappings > código más antiguo/EXI
            sorted_group = group.sort_values(
                by=["total_mappings"], 
                ascending=[False]
            )
            canonical = sorted_group.iloc[0]
            can_code = canonical["codigo_universal"]
            
            for _, dup in sorted_group.iloc[1:].iterrows():
                dup_code = dup["codigo_universal"]
                exact_merges.append((can_code, dup_code, canonical["nombre_estandar"], dup["nombre_estandar"]))
                already_merged_codes.add(dup_code)

    print(f"[FASE 1] Duplicados exactos encontrados para fusionar: {len(exact_merges):,}")
    for can_code, dup_code, can_name, dup_name in exact_merges[:15]:
        print(f"  [MERGE EXACT] {dup_code} ('{dup_name}') -> {can_code} ('{can_name}')")

    # =========================================================================
    # FASE 2: CLUSTERIZACIÓN POR MARCA Y EVALUACIÓN CON DEEPSEEK AI
    # =========================================================================
    print("\n--- FASE 2: Detección de Similitud Semántica y Validación con DeepSeek AI ---")
    active_masters = df_masters[~df_masters["codigo_universal"].isin(already_merged_codes)].to_dict(orient="records")
    
    # Agrupar por tokens principales de marca / nombre
    brand_clusters = {}
    for m in active_masters:
        b = (m.get("marca_estandar") or "").upper().strip()
        if not b or b in ("GENÉRICO", "GENERICO", "GENERIC", "N/A"):
            tokens = m["norm_name"].split()
            b = tokens[0].upper() if tokens else "GENÉRICO"
        brand_clusters.setdefault(b, []).append(m)

    # Identificar pares sospechosos dentro del mismo cluster de marca
    ai_tasks = []  # list of (canonical_item, [candidate_items])
    paired_seen = set()

    for brand, items in brand_clusters.items():
        if len(items) < 2:
            continue
        
        # Ordenar dentro del cluster por total_mappings descendente
        items_sorted = sorted(items, key=lambda x: x.get("total_mappings", 0), reverse=True)
        
        for i in range(len(items_sorted)):
            canonical = items_sorted[i]
            c_code = canonical["codigo_universal"]
            if c_code in already_merged_codes or c_code in paired_seen:
                continue
                
            c_norm = canonical["norm_name"]
            c_vol = extract_volume_simple(canonical["nombre_estandar"])
            c_type = str(canonical.get("tipo_producto_estandar", "")).lower()
            
            candidates = []
            for j in range(i + 1, len(items_sorted)):
                cand = items_sorted[j]
                cand_code = cand["codigo_universal"]
                if cand_code in already_merged_codes or cand_code in paired_seen:
                    continue
                
                cand_type = str(cand.get("tipo_producto_estandar", "")).lower()
                if c_type and cand_type and c_type != cand_type:
                    continue
                    
                cand_norm = cand["norm_name"]
                ratio = SequenceMatcher(None, c_norm, cand_norm).ratio()
                
                # Token overlap
                t1, t2 = set(c_norm.split()), set(cand_norm.split())
                jaccard = len(t1 & t2) / len(t1 | t2) if (t1 and t2) else 0.0
                
                cand_vol = extract_volume_simple(cand["nombre_estandar"])
                
                if (ratio >= min_similarity or jaccard >= 0.70) and (not c_vol or not cand_vol or c_vol == cand_vol):
                    candidates.append(cand)
                    paired_seen.add(cand_code)
            
            if candidates:
                ai_tasks.append((canonical, candidates))

    print(f"[FASE 2] Grupos semánticos sospechosos a evaluar con DeepSeek: {len(ai_tasks):,}")

    ai_merges = []
    if ai_tasks and client:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_task = {
                executor.submit(evaluate_cluster_with_deepseek, can, cands): (can, cands)
                for can, cands in ai_tasks
            }
            for i, future in enumerate(as_completed(future_to_task), 1):
                can, cands = future_to_task[future]
                evals = future.result()
                for ev in evals:
                    cand_code = ev.get("codigo_candidato")
                    should_merge = ev.get("should_merge", False)
                    razon = ev.get("razon", "")
                    
                    cand_obj = next((c for c in cands if c["codigo_universal"] == cand_code), None)
                    cand_name = cand_obj["nombre_estandar"] if cand_obj else cand_code
                    
                    if should_merge:
                        print(f"  [AI MERGE] {cand_code} ('{cand_name}') -> {can['codigo_universal']} ('{can['nombre_estandar']}') | {razon}")
                        ai_merges.append((can["codigo_universal"], cand_code, can["nombre_estandar"], cand_name, razon))
                    else:
                        print(f"  [AI KEEP]  {cand_code} ('{cand_name}') != {can['codigo_universal']} ('{can['nombre_estandar']}') | {razon}")
                
                if i % 10 == 0 or i == len(ai_tasks):
                    print(f"  --- Progreso IA: {i}/{len(ai_tasks)} ({(i/len(ai_tasks))*100:.1f}%) | Fusiones aprobadas: {len(ai_merges)} ---")

    # =========================================================================
    # APLICACIÓN DE FUSIONES EN BASE DE DATOS
    # =========================================================================
    all_merges = []
    for can_code, dup_code, can_name, dup_name in exact_merges:
        all_merges.append((can_code, dup_code, "Duplicado exacto de nombre"))
    for can_code, dup_code, can_name, dup_name, razon in ai_merges:
        all_merges.append((can_code, dup_code, razon))

    print("\n" + "=" * 70)
    print(f" TOTAL FUSIONES MDM APLICADAS: {len(all_merges):,} ")
    print("=" * 70)

    if not dry_run and all_merges:
        with db.get_connection() as conn:
            cur = conn.cursor()
            
            relinked_mappings = 0
            for can_code, dup_code, _ in all_merges:
                # 1. Re-vincular mapeos hacia el código canónico
                cur.execute("UPDATE OR REPLACE mapeo_productos SET codigo_universal = ? WHERE codigo_universal = ?", (can_code, dup_code))
                relinked_mappings += cur.rowcount
                
                # 2. Marcar maestro duplicado como deleted = 1
                cur.execute("UPDATE maestro_productos SET deleted = 1 WHERE codigo_universal = ?", (dup_code,))

            conn.commit()

        print(f"[OK] {relinked_mappings:,} registros de tiendas re-vinculados al maestro canónico.")
        print(f"[OK] {len(all_merges):,} productos maestros duplicados marcados como deleted = 1.")

        print("\nRe-ejecutando ETL de normalización...")
        database.run_normalization_etl()
        print("[OK] Tabla `productos_normalizados` actualizada.")

        print("\nActualizando paquete de datos en `data/mdm_export.json`...")
        export_mdm()
        print("[OK] Archivo `data/mdm_export.json` listo y actualizado.")
    elif dry_run:
        print("[DRY-RUN] No se realizaron cambios en la base de datos.")

    print("=" * 70)

def main():
    parser = argparse.ArgumentParser(description="Deduplicador y Fusión de Productos Maestros MDM con IA")
    parser.add_argument("--workers", type=int, default=3, help="Número de hilos concurrentes para DeepSeek")
    parser.add_argument("--min-sim", type=float, default=0.82, help="Umbral de similitud mínima para candidatos (0.0 - 1.0)")
    parser.add_argument("--dry-run", action="store_true", help="Simular sin modificar la base de datos")

    args = parser.parse_args()
    run_mdm_deduplication(dry_run=args.dry_run, workers=args.workers, min_similarity=args.min_sim)

if __name__ == "__main__":
    main()
