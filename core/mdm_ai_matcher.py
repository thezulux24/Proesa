#!/usr/bin/env python3
"""
Módulo de Inteligencia Artificial para Matching y Vinculación MDM Automatizada
Ubicación: core/mdm_ai_matcher.py

- Aprendizaje RAG de 6,631 vinculaciones humanas previas en base de datos.
- Indexación en memoria directa de 4,436 productos crudos ya aprobados.
- Reglas inviolables de sub-líneas (Fusión, Atardecer, etc.) y marcas independientes (Líder, Caucano, etc.).
- Omite productos con precio $0.
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

def extract_volume(text):
    if not text:
        return None
    t = str(text).lower()
    if '1750' in t or '1.75' in t or 'garrafa' in t:
        return 1750
    if '1050' in t or '1.05' in t:
        return 1050
    if '1000' in t or '1 lt' in t or '1l' in t or '1000ml' in t:
        return 1000
    if '750' in t or '3/4' in t:
        return 750
    if '375' in t or 'media' in t or '1/2' in t:
        return 375
    if '250' in t or 'tetrabik' in t or 'tetrapak' in t:
        return 250
    if '330' in t or '355' in t:
        return 330
    m = re.search(r'(\d+)\s*(ml|cc)', t)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass
    return None

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

def clean_text(text):
    return normalize_text_for_search(text).upper()

def compute_similarity(raw_name, raw_brand, master_name, master_brand):
    n1 = normalize_text_for_search(raw_name)
    n2 = normalize_text_for_search(master_name)
    if not n1 or not n2:
        return 0.0
    seq_ratio = SequenceMatcher(None, n1, n2).ratio()
    t1, t2 = set(n1.split()), set(n2.split())
    jaccard = len(t1 & t2) / len(t1 | t2) if (t1 and t2) else 0.0
    score = 0.5 * seq_ratio + 0.5 * jaccard
    
    b1 = normalize_text_for_search(raw_brand)
    b2 = normalize_text_for_search(master_brand)
    if b1 and b2 and (b1 in b2 or b2 in b1 or b1 in n2):
        score += 0.10

    # Ponderación estricta por volumen/presentación
    v1 = extract_volume(raw_name)
    v2 = extract_volume(master_name)
    if v1 and v2:
        if v1 == v2:
            score += 0.20
        else:
            score -= 0.45

    # Penalización estricta por modificadores de variante / sub-línea incompatibles
    VARIANT_MODIFIERS = [
        'fusion', 'atardecer', 'origen', 'azul', 'verde', 'rojo', 'amarillo', 'manzanares', 
        'rosado', 'tamarindo', 'lulo', 'ice', 'night', 'especial', 'premium', 'reserva', 
        '3 anos', '5 anos', '8 anos', '12 anos', '18 anos', 'caucano', 'lider', 'doble anis', 
        'fiesta', 'real', 'centenario'
    ]
    for mod in VARIANT_MODIFIERS:
        if mod in n1 and mod not in n2:
            score -= 0.50

    # Bonus por coincidencia exacta de variante
    keywords = ['fiesta', 'amarillo', 'caucano', 'lider', 'nectar', 'cristal', 'doble anis', 'garrafa', 'tetrabik', 'fusion', 'atardecer', 'azul', 'verde', 'rojo']
    for kw in keywords:
        if kw in n1 and kw in n2:
            score += 0.20

    return min(max(score, 0.0), 1.0)

def get_historical_verified_mappings(raw_name, limit=5):
    """Consulta la base de datos de 6,631 mapeos validados para encontrar antecedentes idénticos o muy similares."""
    raw_norm = normalize_text_for_search(raw_name)
    ignore_words = {'aguardiente', 'cerveza', 'whisky', 'botella', 'garrafa', 'lata', 'tetrabik', 'sin', 'con', 'azucar', 'para', 'del', 'las', 'los'}
    tokens = [t for t in raw_norm.split() if len(t) > 2 and t not in ignore_words]
    
    if not tokens:
        return []

    db = database.DataSuiteDB()
    with db.get_connection() as conn:
        cur = conn.cursor()
        
        distinctive_tokens = tokens[:3]
        token_conditions = " AND ".join(["LOWER(h.nombre) LIKE ?" for _ in distinctive_tokens])
        params = [f"%{t}%" for t in distinctive_tokens]

        query = f"""
            SELECT DISTINCT h.nombre AS raw_anterior, m.codigo_universal, mp.nombre_estandar, mp.marca_estandar
            FROM productos_historico h
            JOIN mapeo_productos m ON h.comercio = m.comercio AND h.producto_id = m.producto_id
            JOIN maestro_productos mp ON m.codigo_universal = mp.codigo_universal
            WHERE ({token_conditions}) AND mp.deleted = 0
            LIMIT ?
        """
        try:
            cur.execute(query, params + [limit])
            rows = cur.fetchall()
            if not rows and len(distinctive_tokens) > 1:
                token_conditions_or = " OR ".join(["LOWER(h.nombre) LIKE ?" for _ in distinctive_tokens])
                query_or = f"""
                    SELECT DISTINCT h.nombre AS raw_anterior, m.codigo_universal, mp.nombre_estandar, mp.marca_estandar
                    FROM productos_historico h
                    JOIN mapeo_productos m ON h.comercio = m.comercio AND h.producto_id = m.producto_id
                    JOIN maestro_productos mp ON m.codigo_universal = mp.codigo_universal
                    WHERE ({token_conditions_or}) AND mp.deleted = 0
                    LIMIT ?
                """
                cur.execute(query_or, params + [limit])
                rows = cur.fetchall()

            history = []
            for raw_ant, cod, nom_est, marca_est in rows:
                history.append({
                    "ejemplo_crudo_anterior_validado": raw_ant,
                    "codigo_universal_vinculado": cod,
                    "nombre_estandar_maestro": nom_est,
                    "marca_estandar": marca_est
                })
            return history
        except Exception:
            return []

def get_top_candidates(raw_item, df_master, top_n=15):
    if df_master.empty:
        return []
    
    raw_name = raw_item.get('nombre', '')
    raw_brand = raw_item.get('marca', '')

    history = get_historical_verified_mappings(raw_name, limit=5)
    forced_codes = {h["codigo_universal_vinculado"] for h in history}
    
    scored = []
    for _, r in df_master.iterrows():
        code = str(r.get('codigo_universal', ''))
        score = compute_similarity(raw_name, raw_brand, r.get('nombre_estandar', ''), r.get('marca_estandar', ''))
        
        if code in forced_codes:
            score += 0.50

        scored.append((score, r))
        
    scored.sort(key=lambda x: x[0], reverse=True)
    
    candidates = []
    for score, r in scored[:top_n]:
        candidates.append({
            "codigo_universal": str(r.get('codigo_universal', '')),
            "nombre_estandar": str(r.get('nombre_estandar', '')),
            "marca_estandar": str(r.get('marca_estandar', '')),
            "tipo_producto_estandar": str(r.get('tipo_producto_estandar', '')),
            "subcategoria_estandar": str(r.get('subcategoria_estandar', '')),
            "volumen_estandar": str(r.get('volumen_estandar', '')),
            "grados_alcohol_estandar": str(r.get('grados_alcohol_estandar', '')),
            "ultimo_precio_aprox": float(r.get('ultimo_precio', 0))
        })
    return candidates

def format_currency(val):
    try:
        if val is None or float(val) <= 0:
            return "$ 0"
        return f"$ {float(val):,.0f}".replace(",", ".")
    except Exception:
        return "$ 0"

def evaluate_with_deepseek(raw_item, candidates, history=None, model_name="deepseek-chat"):
    if not client:
        print("Error: No hay cliente DeepSeek configurado (verificar DEEPSEEK_API_KEY).")
        return None

    system_prompt = """
Eres un Ingeniero de Datos Senior y Experto en Inteligencia de Mercado para Alcohol y Tabaco en Colombia.
Tu tarea es clasificar y vincular un producto crudo extraído de una tienda o comercio digital (Éxito, Jumbo, Carulla, D1, Olímpica, Makro, Cañaveral, Rappi) con el Maestro de Productos MDM con TOLERANCIA CERO A FALSO POSITIVO.

APRENDIZAJE DE BASE DE DATOS E HISTORIAL DE MAPEOS VALIDADOS (6,631 REGISTROS):
Se te proporciona un campo "ejemplos_historicos_validados_en_base_de_datos". Son vinculaciones idénticas o muy similares validadas previamente por el equipo humano.
- Si ves que un producto crudo anterior (ej. "Aguardiente Blanco Del Valle Fiesta sin Azúcar 1750 Ml") fue previamente vinculado al maestro EXI_3007269 ("Aguardiente BLANCO del valle fiesta sin azúcar garrafa (1750 ml)", marca BLANCO), UTILIZA ESE APRENDIZAJE Y HAZ "LINK" a ese código maestro.
- NO crees un nuevo maestro con marcas inventadas como "FIESTA" si en la base de datos validada "Fiesta" es la línea de Aguardiente BLANCO del Valle.

RAZONAMIENTO SEMÁNTICO Y COMPRENSIÓN DE VARIACIONES DE NOMBRES EN COLOMBIA:
1. SINÓNIMOS DE AZÚCAR / VARIEDAD:
   - "s.a.", "sin azúcar", "sin azucar", "sugar free", "0 azúcar", "cero azúcar", "sugarfree" -> Todos significan la misma variedad "sin azúcar".
2. VARIEDADES POPULARES EN COLOMBIA:
   - "Fiesta", "Blanco Fiesta" -> Aguardiente Blanco del Valle Fiesta (Marca: BLANCO / BLANCO DEL VALLE).
   - "Verde", "24°", "24 grados", "Tapa Verde" -> Variedad Aguardiente Antioqueño Verde 24°.
   - "Rojo", "Tradicional", "Tapa Roja", "29°" -> Variedad Aguardiente Antioqueño Tradicional.
   - "Azul", "Real", "Centenario" -> Variedad Aguardiente Antioqueño Real/Azul.
   - "Amarillo", "Manzanares", "Real de Manzanares" -> Aguardiente Amarillo de Manzanares.
3. EQUIVALENCIAS DE VOLUMEN Y PRESENTACIÓN:
   - "750 ml", "750ml", "750 cc", "750cc", "3/4" -> Mismo volumen (750 ml).
   - "1050 ml", "1.05 Lt", "1,05 L", "1050cc" -> Mismo volumen (1.05 Lt / 1050 ml).
   - "375 ml", "375ml", "375 cc", "media", "1/2" -> Mismo volumen (375 ml).
   - "1750 ml", "1.75 Lt", "garrafa", "1750ml" -> Mismo volumen (1750 ml).
   - "250 ml", "tetrabik", "tetrapak", "caja" -> Presentación en caja 250 ml.
4. SIGLAS Y MARCAS HABLADAS:
   - "FLA" -> Fábrica de Licores de Antioquia (marca Antioqueño).
   - "ILC" -> Industria Licorera de Caldas (Ron Viejo de Caldas / Aguardiente Cristal).
   - "Buchanans", "Buchanan's", "Buchanan" -> Marca BUCHANAN'S.
   - "Old Parr", "Oldparr" -> Marca OLD PARR.

REGLAS INVIOLABLES DE LÍNEAS DE PRODUCTO Y MARCAS EN COLOMBIA:
1. SUB-LÍNEAS Y SABORES SON UN BLOQUEO ABSOLUTO:
   - Si el producto crudo menciona una sub-línea o sabor específico como "Fusion", "Fusión", "Atardecer", "Tamarindo", "Lulo", "Rosado", "Ice", "Night", "Especial", "Reserva", NUNCA lo vincules a un candidato maestro tradicional que NO tenga esa palabra de sub-línea. Si no existe el candidato exacto (ej. Origen Del Valle Fusión), DEBES usar "CREATE".
2. MARCAS INDEPENDIENTES COLOMBIANAS:
   - "Líder" / "Lider" es una marca independiente de la Licorera de Cundinamarca. NUNCA la vincules a la marca ANTIOQUEÑO ni a NÉCTAR.
   - "Caucano" es una marca independiente de la Licorera del Cauca. NUNCA la vincules a ANTIOQUEÑO ni a NÉCTAR.
   - "Llanero" es una marca independiente de Licores del Meta.
3. DISTINCIÓN ANTIOQUEÑO AZUL vs VERDE:
   - En Aguardiente Antioqueño de 1000ml sin azúcar en vidrio o tradicional (sin la palabra "verde" ni "24°"), vincúlalo prioritariamente a Antioqueño Azul 29° (EXI_854131 / EXI_238329), NO a Verde 24°.

REGLAS STRICTAS DE EVALUACIÓN MULTIDIMENSIONAL:
1. ALCOHOL Y TABACO ÚNICAMENTE:
   - Si el producto es Alimento, Comida de restaurante, Combo, Arroz, Carne, Pollo, Pizza, Hamburguesa, Taco, Postre, Café, Gaseosa, Soda, Limonada, Agua, Pañales, Aseo, Pasabocas, Mezclador o Utensilio -> ACCIÓN: "DISCARD".
   - VAPEO Y TABACO: Cigarrillos, Tabaco, Puros, Habanos, Vapeadores, Vapes, Pods, Desechables, E-liquids y Esencias (CON O SIN NICOTINA) -> OBLIGATORIAMENTE TIPO: "Tabaco" (grados_alcohol_estandar: null).
   - BEBIDAS ALCOHÓLICAS: Cerveza, Vino, Aguardiente, Ron, Whisky, Vodka, Tequila, Mezcal, Ginebra, Aperitivo, Licor de Café, Crema de Whisky -> TIPO: "Alcohol".

2. REGLAS PARA "LINK" (VINCULAR):
   - Entiende las variaciones semánticas del nombre. Si el producto crudo dice "Aguardiente Garrafa fiesta x 1750 ml" o "Aguardiente Antioqueño s.a. 750ml" y existe un candidato/histórico maestro coincidente semánticamente, RECONOCE QUE SON EL MISMO PRODUCTO y haz "LINK".
   - Solo vincula si la marca, la variedad y el VOLUMEN/PRESENTACIÓN coinciden semánticamente. Si el volumen difiere (ej. 750ml vs 1Lt) o la variedad/sub-línea difiere (ej. Sin Azúcar vs Fusión, Sin Azúcar vs Amarillo), NO VINCULAR (Acción: CREATE).
   - Compara el precio: Si el candidato cuesta $50.000 y el producto crudo cuesta $15.000, verifica si es una presentación distinta o un producto diferente.

3. REGLAS PARA "CREATE" (CREAR NUEVO MAESTRO):
   - Si es un producto de Alcohol o Tabaco válido pero NINGÚN candidato ni histórico coincide semánticamente en volumen, sabor o variedad -> ACCIÓN: "CREATE".
   - Define un nombre estándar limpio, canónico y legible (Ej: "Aguardiente CAUCANO sin azúcar (750 ml)").
   - Extrae/infiere los grados de alcohol como número decimal puro (sin símbolos '%' ni '°'). Ej: Aguardiente Antioqueño = 29.0, Ron Medellín = 35.0, Cerveza Heineken = 5.0. Si es tabaco o vape, usa null.

DEBES RESPONDER ÚNICAMENTE EN FORMATO JSON VÁLIDO CON LA SIGUIENTE ESTRUCTURA ESTRICTA:
{
  "action": "LINK" | "CREATE" | "DISCARD",
  "codigo_universal": "CÓDIGO_DEL_CANDIDATO" (solo si action es LINK, de lo contrario null),
  "nuevo_maestro": {
    "nombre_estandar": "Nombre Estándar Limpio",
    "marca_estandar": "MARCA",
    "tipo_producto_estandar": "Alcohol" | "Tabaco",
    "subcategoria_estandar": "Aguardiente" | "Brandy" | "Cerveza" | "Coctelería" | "Combo" | "Cremas y aperitivos" | "Ginebra" | "Mezcal" | "Ron" | "Tequila" | "Vinos" | "Vodka" | "Whisky" | "Cigarrillos" | "Vapeadores" | "Tabaco calentado" | "Bolsas de nicotina" | "Accesorios para tabaco",
    "volumen_estandar": "750 Mililitro" | "1000 Mililitro" | "355 Mililitro" | "1 Unidad" | "20 Unidad" | etc,
    "grados_alcohol_estandar": 29.0 | 35.0 | null
  } (solo si action es CREATE, de lo contrario null),
  "razon": "Explicación breve de la decisión semántica"
}
"""

    user_payload = {
        "producto_crudo": {
            "comercio": raw_item.get('comercio'),
            "producto_id": str(raw_item.get('producto_id')),
            "nombre": raw_item.get('nombre'),
            "marca": raw_item.get('marca'),
            "precio_crudo": format_currency(raw_item.get('ultimo_precio', 0)),
            "url_producto": raw_item.get('url_producto', ''),
            "medida_extraida": raw_item.get('medida', ''),
            "grados_extraidos": raw_item.get('grados_alcohol', '')
        },
        "marcas_oficiales_registradas_en_mdm": OFFICIAL_MDM_BRANDS[:60],
        "ejemplos_historicos_validados_en_base_de_datos": history or [],
        "candidatos_maestros_sugeridos": candidates
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
        reasoning = getattr(msg, 'reasoning_content', '')

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        result = json.loads(content)
        if reasoning and isinstance(result, dict) and "razon" in result:
            resumen_pensamiento = reasoning[:150].replace("\n", " ") + "..."
            result["razon_pensamiento"] = resumen_pensamiento

        return result
    except Exception as e:
        print(f"Error al consultar DeepSeek API ({model_name}): {e}")
        return None

def load_db_mapped_memory():
    """Carga los mapeos validados por el usuario en la base de datos para búsqueda exacta previa instantánea."""
    db = database.DataSuiteDB()
    memory_map = {}
    official_brands = set()
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT LOWER(h.nombre) as raw_nombre, m.codigo_universal, mp.nombre_estandar, mp.marca_estandar
                FROM productos_historico h
                JOIN mapeo_productos m ON h.comercio = m.comercio AND h.producto_id = m.producto_id
                JOIN maestro_productos mp ON m.codigo_universal = mp.codigo_universal
                WHERE h.deleted = 0 AND mp.deleted = 0
            """)
            for raw_nombre, code, nom_est, marca_est in cur.fetchall():
                memory_map[normalize_text_for_search(raw_nombre)] = {
                    "action": "LINK",
                    "codigo_universal": code,
                    "razon": f"Coincidencia exacta con producto crudo validado por el usuario en la base de datos MDM -> {code} ({nom_est})."
                }
                if marca_est:
                    official_brands.add(marca_est.upper().strip())
    except Exception as e:
        print(f"Advertencia al cargar memoria de base de datos: {e}")
    return memory_map, sorted(list(official_brands))

DB_MAPPED_MEMORY, OFFICIAL_MDM_BRANDS = load_db_mapped_memory()

HUMAN_CORRECTIONS_FILE = os.path.join("data", "human_corrections_memory.json")

def load_human_corrections():
    if os.path.exists(HUMAN_CORRECTIONS_FILE):
        try:
            with open(HUMAN_CORRECTIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"exact_overrides": {}, "keyword_rules": []}

HUMAN_CORRECTIONS = load_human_corrections()

def process_single_product(raw_item, df_master, dry_run=False, model_name="deepseek-chat"):
    comercio = raw_item.get('comercio', '')
    prod_id = str(raw_item.get('producto_id', ''))
    nombre = raw_item.get('nombre', '')
    precio = format_currency(raw_item.get('ultimo_precio', 0))

    # 0. Verificar si existe una corrección manual explícita en human_corrections_memory.json
    override_key = f"{comercio.lower()}|{prod_id}"
    exact_overrides = HUMAN_CORRECTIONS.get("exact_overrides", {})
    if override_key in exact_overrides:
        decision = exact_overrides[override_key]
        print(f"[MEMORY HUMAN OVERRIDE] [{comercio} - ID {prod_id}] Aplicando regla validada por usuario.")
    else:
        # 1. Verificar si el nombre crudo normalizado coincide 100% con un producto que el usuario YA VALIDÓ en la DB
        raw_norm = normalize_text_for_search(nombre)
        if raw_norm in DB_MAPPED_MEMORY:
            decision = DB_MAPPED_MEMORY[raw_norm]
            print(f"[DB MAPPING MEMORY MATCH] [{comercio} - ID {prod_id}] {nombre} -> {decision['codigo_universal']} | {decision['razon']}")
            if not dry_run:
                database.add_mapping(comercio, prod_id, decision['codigo_universal'])
            return "LINK"

        # 2. Si no hay coincidencia exacta de nombre, realizar RAG con antecedentes de DB y consultar DeepSeek
        history = get_historical_verified_mappings(nombre, limit=5)
        candidates = get_top_candidates(raw_item, df_master, top_n=15)
        decision = evaluate_with_deepseek(raw_item, candidates, history=history, model_name=model_name)

    if not decision or "action" not in decision:
        print(f"[SKIP] [{comercio} - ID {prod_id}] {nombre}: No se obtuvo respuesta válida de IA.")
        return "SKIP"

    action = decision.get("action")
    razon = decision.get("razon", "")

    if action == "LINK":
        code = decision.get("codigo_universal")
        if not code:
            print(f"[ERROR] [{comercio} - ID {prod_id}] Decision LINK sin código universal.")
            return "SKIP"
        print(f"[LINK] [{comercio} - ID {prod_id}] {nombre} ({precio}) -> {code} | {razon}")
        if not dry_run:
            database.add_mapping(comercio, prod_id, code)
        return "LINK"

    elif action == "CREATE":
        nm = decision.get("nuevo_maestro", {})
        if not nm or not nm.get("nombre_estandar") or not nm.get("marca_estandar"):
            print(f"[ERROR] [{comercio} - ID {prod_id}] Decision CREATE con metadatos incompletos.")
            return "SKIP"
        
        nom_est = nm.get("nombre_estandar")
        marca_est = nm.get("marca_estandar")
        tipo_est = nm.get("tipo_producto_estandar", "Alcohol")
        subcat_est = nm.get("subcategoria_estandar", "Licores")
        vol_est = nm.get("volumen_estandar", "")
        grados_est = nm.get("grados_alcohol_estandar", "")

        print(f"[CREATE] [{comercio} - ID {prod_id}] {nombre} ({precio}) -> Nuevo Maestro: '{nom_est}' [{marca_est}] ({grados_est}) | {razon}")
        if not dry_run:
            created_code = database.add_to_maestro(
                nombre=nom_est,
                marca=marca_est,
                tipo=tipo_est,
                subcategoria=subcat_est,
                volumen=vol_est,
                grados=grados_est
            )
            database.add_mapping(comercio, prod_id, created_code)
        return "CREATE"

    elif action == "DISCARD":
        print(f"[DISCARD] [{comercio} - ID {prod_id}] {nombre} ({precio}) -> Falso Positivo descartado (deleted = 1) | {razon}")
        if not dry_run:
            database.mark_raw_false_positive(comercio, prod_id)
        return "DISCARD"

    else:
        print(f"[UNKNOWN] [{comercio} - ID {prod_id}] Acción desconocida: {action}")
        return "SKIP"

def run_auto_mdm_matching(fuente="Todas", tipo="Todos", limit=0, workers=3, model_name="deepseek-chat", dry_run=False):
    """
    Función principal invocable desde main.py o CLI para procesar automáticamente productos sin vincular en MDM.
    """
    print("=" * 70)
    print(" VINCULACIÓN Y MATCHING MDM AUTOMÁTICO CON IA ")
    print("=" * 70)
    print("Ejecutando ETL de normalización inicial (mapeos e históricos conocidos)...")
    database.run_normalization_etl()

    df_raw = database.get_unmapped_products(fuente=fuente, tipo=tipo, hide_zero_price=True)
    if df_raw.empty:
        print("[OK] Todos los productos están vinculados al MDM. No se requieren acciones de IA.")
        return {"LINK": 0, "CREATE": 0, "DISCARD": 0, "SKIP": 0}


    if limit > 0:
        df_raw = df_raw.head(limit)

    total_items = len(df_raw)
    print(f"Total productos a evaluar por IA: {total_items:,}")

    df_master = database.get_maestro_products(include_prices=True)
    print(f"Universo Maestro de Referencia: {len(df_master):,} productos maestros.")
    print(f"Memoria de Base de Datos DB: {len(DB_MAPPED_MEMORY):,} nombres validados indexados.")
    print("Iniciando clasificación multi-dimensional...\n")

    stats = {"LINK": 0, "CREATE": 0, "DISCARD": 0, "SKIP": 0}
    raw_records = df_raw.to_dict(orient="records")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_single_product, item, df_master, dry_run, model_name): item for item in raw_records}
        for i, future in enumerate(as_completed(futures), 1):
            res = future.result()
            stats[res] = stats.get(res, 0) + 1
            if i % 10 == 0 or i == total_items:
                print(f"--- Progreso: {i}/{total_items} ({(i/total_items)*100:.1f}%) | Vinc: {stats['LINK']} | Nuevos: {stats['CREATE']} | Desc: {stats['DISCARD']} ---")

    print("\n" + "=" * 70)
    print(" RESUMEN DE PROCESAMIENTO MDM AI ")
    print("=" * 70)
    print(f"[OK] Productos Vinculados a Maestros Existentes (LINK): {stats['LINK']:,}")
    print(f"[OK] Nuevos Productos Maestros Creados (CREATE): {stats['CREATE']:,}")
    print(f"[OK] Falsos Positivos Descartados (DISCARD): {stats['DISCARD']:,}")
    print(f"[OK] Omitidos por Error (SKIP): {stats['SKIP']:,}")

    if not dry_run and (stats['LINK'] > 0 or stats['CREATE'] > 0 or stats['DISCARD'] > 0):
        print("\nRe-ejecutando proceso ETL de normalización...")
        database.run_normalization_etl()
        print("[OK] Tabla `productos_normalizados` actualizada.")

        print("\nActualizando paquete de datos en `data/mdm_export.json`...")
        export_mdm()
        print("[OK] Archivo `data/mdm_export.json` listo para migrar al servidor.")

    print("=" * 70)
    return stats

def main():
    parser = argparse.ArgumentParser(description="Módulo de Matching y Vinculación MDM con IA (DeepSeek)")
    parser.add_argument("--fuente", type=str, default="Todas", help="Filtrar por comercio (Ej: Olimpica, Exito, Jumbo, D1, etc.)")
    parser.add_argument("--tipo", type=str, default="Todos", help="Filtrar por tipo (Alcohol, Tabaco)")
    parser.add_argument("--limit", type=int, default=0, help="Límite de productos a procesar (0 para todos)")
    parser.add_argument("--workers", type=int, default=3, help="Número de hilos concurrentes para consultar la API")
    parser.add_argument("--model", type=str, default="deepseek-chat", help="Modelo de IA: 'deepseek-chat' (V3) o 'deepseek-reasoner' (R1)")
    parser.add_argument("--dry-run", action="store_true", help="Simular sin modificar la base de datos")

    args = parser.parse_args()
    run_auto_mdm_matching(
        fuente=args.fuente,
        tipo=args.tipo,
        limit=args.limit,
        workers=args.workers,
        model_name=args.model,
        dry_run=args.dry_run
    )

if __name__ == "__main__":
    main()
