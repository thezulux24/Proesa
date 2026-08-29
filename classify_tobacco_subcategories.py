#!/usr/bin/env python3
"""
Script de Clasificación y Separación Inteligente de Subcategorías de Tabaco.
Separa la categoría 'Cigarrillos y vapeadores' en:
  1. Cigarrillos (cigarrillos tradicionales, puros, cigarros, habanos, picadura)
  2. Vapeadores (vapes descartables, pods, e-líquidos, esencias)
  3. Tabaco calentado (IQOS, HEETS, TEREA, Iluma, Glo, Fiit)
  4. Bolsas de nicotina (ZYN, VELO, etc.)
  5. Accesorios para tabaco (papel de liar, filtros, grinders, blunts, narguila)

Utiliza DeepSeek AI + Heurística Determinística para máxima precisión.
"""
import os
import sys
import json
import sqlite3
import unicodedata
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DB_PATH = "suite_data.db"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

def strip_accents(text):
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(text))
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower().strip()

def rule_based_classify(name, marca):
    """Clasificación determinística ultra-rápida y de alta precisión (sin usar subcategoría previa)."""
    combined = f"{name} {marca}"
    n = strip_accents(combined)
    
    # 1. Tabaco calentado
    heat_kw = [
        "heets", "iqos", "terea", "iluma", "calentado", "heatstick", 
        "heat stick", "heatsticks", "fiit", "neo stick", "glo ", "ploom"
    ]
    if any(k in n for k in heat_kw):
        return "Tabaco calentado"
        
    # 2. Bolsas de nicotina
    if any(k in n for k in ["bolsa de nicotina", "bolsas de nicotina", "nicotine pouch", "pouches", "zyn", "velo", "on!"]):
        return "Bolsas de nicotina"
    if "nicotina" in n and not any(k in n for k in ["vape", "pod", "liquid", "e-liquido", "cigarrillo", "puro", "cigarro"]):
        return "Bolsas de nicotina"
        
    # 3. Accesorios para tabaco
    acc_kw = [
        "papel", "envolver", "liar", "fumar", "accesorio", "filtro", "grinder", 
        "narguila", "cuero", "blunt", "rolling paper", "ocb", "raw ", "smoking ", "hornet"
    ]
    if any(k in n for k in acc_kw):
        if not any(k in n for k in ["cigarrillo", "cigarro", "puro", "habano", "vape", "pod"]):
            return "Accesorios para tabaco"
        if any(k in n for k in ["papel", "blunt", "cuero", "filtro", "envolver", "liar", "grinder", "ocb", "raw"]):
            return "Accesorios para tabaco"
            
    # 4. Cigarrillos (Prioridad a nombres explícitos de cigarrillos tradicionales)
    is_vape = any(k in n for k in ["vape", "pod", "e-liquid", "e-liquido", "esencia", "desechable", "disposable", "puff", "cartucho", "eliquid"])
    
    cigar_names = [
        "cigarrillo", "cigarrillos", "cigarro", "cigarros", "puro", "puros", "habano", "habanos", 
        "cajetilla", "carton", "picadura"
    ]
    if any(k in n for k in cigar_names) and not is_vape:
        return "Cigarrillos"
        
    cigar_brands = [
        "marlboro", "lucky strike", "rothmans", "chesterfield", "boston", "mustang", "dunhill", 
        "cohiba", "montecristo", "romeo y julieta", "partagas", "guantanamera", "starlite", 
        "president", "premier", "celta", "monterrey", "davidoff", "pall mall", "camel", 
        "winston", "kent", "benson", "sobranie", "parliament"
    ]
    if any(k in n for k in cigar_brands) and not is_vape:
        return "Cigarrillos"
            
    # 5. Vapeadores
    vape_kw = [
        "vape", "vapeador", "vapeadores", "pod", "pods", "e-liquido", "e-liquid", "e-juice", "esencia", 
        "desechable", "disposable", "elf bar", "elf pro", "vuse", "maskking", "geekbar", "oxbar", "vozol", 
        "ignite", "lost mary", "smok", "iplay", "vapr", "puff", "vaporizador", "air bar", "air lux", "airfuze",
        "aokit", "archer", "baddie bar", "beyond", "croxx", "czar", "death row", "dozo", "dummy", "elux",
        "escobars", "evobar", "fresor", "fume", "geek bar", "geekvape", "gold bar", "hqd", "hyppe", "juul",
        "kado", "kangvape", "kraze", "lost vape", "luffbar", "moti", "mr fog", "myblu", "nasty", "novo",
        "off-stamp", "orion", "priv", "priv bar", "pyne", "rabbeats", "relx", "rifbar", "spaceman",
        "suorin", "swft", "tarobar", "typhoon", "uwell", "vaporesso", "voopoo", "vaptio", "waka", "yoop"
    ]
    if any(k in n for k in vape_kw):
        return "Vapeadores"
        
    return None

def batch_ai_classify(items):
    """Clasifica un lote de productos con DeepSeek AI."""
    if not DEEPSEEK_API_KEY:
        print("[WARN] DEEPSEEK_API_KEY no encontrada, usando fallback determinístico.")
        return {item["codigo"]: rule_based_classify(item["nombre"], item["marca"]) or "Cigarrillos" for item in items}
        
    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )
    
    prompt = """Eres un experto en clasificación de mercado para la categoría de TABACO Y PRODUCTOS DE NICOTINA.
Debes clasificar cada uno de los productos de la lista en EXACTAMENTE UNA de estas 5 subcategorías canónicas:
- "Cigarrillos" (Cigarrillos convencionales en cajetilla o cartón, cigarros, puros, habanos, picadura de tabaco para pipa/liar).
- "Vapeadores" (Vapeadores electrónicos desechables, recargables, pods, cartuchos, e-líquidos, esencias para vapeo).
- "Tabaco calentado" (Sistemas de calentamiento de tabaco como IQOS, Glo, Ploom, y consumibles como HEETS, TEREA, Fiit, Neo sticks).
- "Bolsas de nicotina" (Bolsas o pouches de nicotina sin tabaco para uso oral, ej. ZYN, VELO, On!, Lucy).
- "Accesorios para tabaco" (Papel de liar/fumar, filtros, blunts, cueros, grinders, narguila, encendedores, accesorios de fumador).

Devuelve ÚNICAMENTE un objeto JSON válido con el siguiente formato:
{
  "CÓDIGO_1": "Subcategoría",
  "CÓDIGO_2": "Subcategoría"
}
"""
    items_text = json.dumps([{"codigo": it["codigo"], "nombre": it["nombre"], "marca": it["marca"]} for it in items], ensure_ascii=False)
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Clasifica los siguientes productos:\n{items_text}"}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content.strip()
        parsed = json.loads(content)
        return parsed
    except Exception as e:
        print(f"[ERROR AI] Error llamando a DeepSeek: {e}. Aplicando fallback de reglas.")
        return {item["codigo"]: rule_based_classify(item["nombre"], item["marca"]) or "Cigarrillos" for item in items}

def run_tobacco_classification():
    print("=" * 70)
    print(" INICIANDO SEPARACIÓN DE CIGARRILLOS, VAPEADORES Y TABACO CALENTADO ")
    print("=" * 70)
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT codigo_universal, nombre_estandar, marca_estandar, subcategoria_estandar
        FROM maestro_productos
        WHERE tipo_producto_estandar = 'Tabaco' 
           OR subcategoria_estandar LIKE '%cigarrillo%' 
           OR subcategoria_estandar LIKE '%vape%' 
           OR subcategoria_estandar LIKE '%tabaco%'
    """)
    rows = cur.fetchall()
    print(f"[INFO] Total productos de Tabaco a clasificar: {len(rows):,}")
    
    classification_map = {}
    ambiguous_items = []
    
    for code, name, marca, cur_subcat in rows:
        cat = rule_based_classify(name, marca)
        if cat:
            classification_map[code] = cat
        else:
            ambiguous_items.append({"codigo": code, "nombre": name, "marca": marca})
            
    print(f"[INFO] Clasificados con alta confianza por reglas: {len(classification_map):,}")
    print(f"[INFO] Items para verificación con DeepSeek AI: {len(ambiguous_items):,}")
    
    # Procesar items ambiguos con IA en lotes de 40
    if ambiguous_items:
        batch_size = 40
        for i in range(0, len(ambiguous_items), batch_size):
            batch = ambiguous_items[i:i+batch_size]
            print(f"  -> Procesando lote IA {i+1} a {min(i+batch_size, len(ambiguous_items))}...")
            ai_res = batch_ai_classify(batch)
            for it in batch:
                code = it["codigo"]
                pred = ai_res.get(code, "Cigarrillos")
                valid_cats = ["Cigarrillos", "Vapeadores", "Tabaco calentado", "Bolsas de nicotina", "Accesorios para tabaco"]
                if pred not in valid_cats:
                    pred = rule_based_classify(it["nombre"], it["marca"]) or "Cigarrillos"
                classification_map[code] = pred
            
    # Ejecutar actualización en la base de datos
    print("\n[INFO] Guardando subcategorías actualizadas en maestro_productos...")
    updated_counts = {}
    for code, subcat in classification_map.items():
        cur.execute("UPDATE maestro_productos SET subcategoria_estandar = ?, tipo_producto_estandar = 'Tabaco' WHERE codigo_universal = ?", (subcat, code))
        updated_counts[subcat] = updated_counts.get(subcat, 0) + 1
        
    conn.commit()
    conn.close()
    
    print("=" * 70)
    print(" DISTRIBUCIÓN FINAL DE SUBCATEGORÍAS DE TABACO ")
    print("=" * 70)
    for cat, count in sorted(updated_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {cat}: {count:,} productos")
        
    print("\n[INFO] Re-ejecutando proceso ETL de normalización...")
    import database
    database.run_normalization_etl()
    print("[OK] Tabla `productos_normalizados` sincronizada.")
    
    print("\n[INFO] Regenerando archivo data/mdm_export.json...")
    import export_mdm
    export_mdm.export_mdm()
    print("[OK] data/mdm_export.json actualizado.")
    print("=" * 70)

if __name__ == "__main__":
    run_tobacco_classification()
