"""
Scraper de Rappi para Proesa (Tabaco, Alcohol y Ultraprocesados).
Arquitectura HTTP-Only pura mediante simulación de headers y extracción de JSON __NEXT_DATA__.
Especializado en Bogotá con agregación multitienda, atribución de tienda en 'Referencia' y control estricto de duplicados.
"""

import csv
import json
import logging
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

try:
    from config import KNOWN_BRANDS, LOCATIONS, TARGET_CATEGORIES
except ImportError:
    from .config import KNOWN_BRANDS, LOCATIONS, TARGET_CATEGORIES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ScraperRappi")


class RappiScraper:
    def __init__(self, output_file: str = "data/productos_rappi.csv", location_key: str = "bogota_norte"):
        self.output_file = output_file
        self.location_key = location_key if location_key in LOCATIONS else "bogota_norte"
        self.location = LOCATIONS.get(self.location_key, next(iter(LOCATIONS.values())))
        
        # Base headers requeridos por la suite de base de datos
        self.base_headers = [
            "ID", "Nombre", "Marca", "Referencia", "Categoria", "Tipo de Producto", "Grados de alcohol", 
            "Medida", "Precio_Original", "Precio_Final", "Descuento_%", "Precio_Unidad", "URL_Producto", "Descripcion"
        ]
        self.all_extracted_headers = set(self.base_headers)

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "es-419,es;q=0.9,en;q=0.8",
            "country_code": "CO",
            "latitude": str(self.location["lat"]),
            "longitude": str(self.location["lng"]),
        }

    def _clean_text(self, text: str) -> str:
        if not text or not isinstance(text, str):
            return ""
        # Limpiar espacios invisibles de Unicode (zero-width spaces, non-breaking spaces)
        cleaned = re.sub(r'[\u200b\u200e\u200f\ufeff\xa0\u202f]', ' ', text)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.strip()

    def _extract_brand(self, title: str, raw_brand: Optional[str]) -> str:
        if raw_brand and isinstance(raw_brand, str):
            rb = self._clean_text(raw_brand)
            if rb and rb.lower() not in ["genérico", "generico", "generic", "none", "null", "n/a", ""]:
                return rb

        title_lower = title.lower()
        for b in KNOWN_BRANDS:
            if re.search(r'\b' + re.escape(b.lower()) + r'\b', title_lower):
                return b

        words = title.split()
        return words[0].strip() if words else "Genérico"

    def _is_excluded_store(self, store_info: dict) -> bool:
        s_name = (store_info.get("storeName") or "").lower()
        b_name = (store_info.get("brandName") or "").lower()
        s_type = (store_info.get("storeType") or "").lower()
        combined = f"{s_name} {b_name} {s_type}"
        
        excluded_kw = [
            "restaurante", "starbucks", "kfc", "frisby", "mcdonald", "pizza", 
            "burger", "hamburgues", "sushi", "panader", "arepa", "postre", 
            "helader", "yogurt", "pasteler", "florister", "papeler", "ropa", 
            "pet", "veterinar", "tintorer", "pollo", "parrilla", "wok", 
            "crepes", "waffle", "subway", "domino", "bbq", "tacos", "burrito",
            "asadero", "churreria", "deli", "sandwiches", "obelisco", "fritanga",
            "birrier", "costillota", "llanera", "wings"
        ]
        return any(k in combined for k in excluded_kw)

    def _is_authentic_alcohol_or_tobacco(self, name: str, node: dict) -> tuple[bool, str]:
        n = name.lower()
        
        # 1. Blacklist estricta de comidas preparadas, postres, abarrotes y hogar
        blacklist = [
            "arroz", "combo", "pollo", "costilla", "hamburguesa", "burger", "pizza", 
            "taco", "tacos", "carne", "croissant", "torta", "cafe", "café", "latte", 
            "frappuccino", "chocolate", "soda", "limonada", "jugo", "agua", "gaseosa", 
            "pechuga", "chicharron", "panini", "postre", "helado", "papas", "nachos", 
            "empanada", "empanaditas", "arepa", "arepas", "huggies", "pañal", "panal", 
            "shampoo", "jabon", "jabón", "detergente", "crema dental", "cepillo", 
            "toalla", "toallitas", "proteina", "proteína", "vitamina", "gomitas", 
            "peluche", "flores", "floristeria", "papeleria", "cuaderno", "alitas", 
            "sandwich", "sandwiches", "almuerzo", "desayuno", "sopa", "bowl", "acai", 
            "wrap", "crepe", "crepes", "waffle", "waffles", "pasta", "lasagna", "ensalada",
            "queso", "jamon", "mantequilla", "leche", "aceite", "pan", "tostada"
        ]
        for bad in blacklist:
            if re.search(r'\b' + re.escape(bad) + r'\b', n):
                if not any(k in n for k in ["cerveza", "whisky", "vodka", "ron", "tequila", "vino", "aguardiente", "cigarrillo", "vape", "vapeador", "cigarro", "puro"]):
                    return False, ""

        # 2. Chequeo de Tabaco / Vapeo (los vapos con o sin nicotina son estrictamente Tabaco)
        tabaco_kw = [
            "cigarrillo", "cigarrillos", "cigarro", "cigarros", "cajetilla", "tabaco", 
            "puro", "puros", "habano", "habanos", "vape", "vapeador", "vapes", "vapo", 
            "pod", "pods", "vuse", "relx", "waka", "elf bar", "ignite", "lost mary", 
            "geek bar", "smok", "iqos", "iluma", "terea", "heets", "e-liquid", 
            "sales de nicotina", "papel de fumar", "blunt", "rolling paper", "carlton",
            "marlboro", "lucky strike", "rothmans", "chesterfield", "dunhill", "camel",
            "parliament", "kent", "l&m", "starlite", "boston", "montecristo", "cohiba",
            "romeo y julieta", "sedas raw", "sedas ocb", "papel smoking", "filtros ocb", "picadura"
        ]
        if bool(node.get("hasAntismoking", False)) or any(re.search(r'\b' + re.escape(k) + r'\b', n) for k in tabaco_kw):
            return True, "Tabaco"

        # 3. Chequeo de Alcohol
        alcohol_kw = [
            "cerveza", "cervezas", "beer", "aguardiente", "ron", "whisky", "whiskey", 
            "bourbon", "scotch", "tequila", "mezcal", "vodka", "ginebra", "gin", 
            "vino", "vinos", "champagne", "champana", "prosecco", "cava", "espumoso", 
            "aperol", "campari", "baileys", "jagermeister", "licor", "licores", 
            "crema de whisky", "sangria", "smirnoff ice", "four loko", "hard seltzer",
            "coctel", "cocktail", "aguila", "poker", "club colombia", "heineken", 
            "corona", "costeña", "pilsen", "stella artois", "budweiser", "bbc", 
            "bogota beer company", "andina", "cusqueña", "miller", "peroni", "michelob", 
            "antioqueño", "néctar", "nectar", "amarillo de manzanares", "blanco del valle", 
            "viejo de caldas", "ron medellín", "ron medellin", "zacapa", "havana club", 
            "bacardi", "flor de caña", "flor de cana", "la hechicera", "buchanan", 
            "old parr", "johnnie walker", "chivas", "jack daniel", "black & white", 
            "black and white", "glenfiddich", "macallan", "singleton", "jameson", 
            "ballantine", "grant's", "grants", "jim beam", "don julio", "jose cuervo", 
            "patron", "1800", "herradura", "olmeca", "400 conejos", "ojo de tigre", 
            "smirnoff", "absolut", "grey goose", "belvedere", "ketel one", "tanqueray", 
            "bombay", "beefeater", "hendrick", "gordon's", "gordons", "gato negro", 
            "casillero del diablo", "santa rita", "concha y toro", "navarro correas", 
            "trapiche", "las moras", "undurraga", "frontera", "marqués de riscal"
        ]
        if bool(node.get("alcoholicBeverage", False)) or any(re.search(r'\b' + re.escape(k) + r'\b', n) for k in alcohol_kw):
            return True, "Alcohol"

        return False, ""

    def _infer_tipo_producto(self, name: str, category: str, has_antismoking: bool = False, is_alcoholic: bool = False) -> str:
        combined = f"{name} {category}".lower()
        
        tabaco_kw = [
            "cigarrillo", "cigarros", "cigarro", "tabaco", "puro", "puros", "habano",
            "vape", "vapeador", "vapes", "vapo", "pod", "pods", "vuse", "relx",
            "waka", "elf bar", "ignite", "lost mary", "geek bar", "iqos", "iluma",
            "terea", "heets", "picadura", "nicotina", "sales de nicotina"
        ]
        if has_antismoking or any(w in combined for w in tabaco_kw):
            return "Tabaco"
            
        return "Alcohol"

    def _extract_medida(self, name: str, quantity: any, unit_type: any) -> str:
        # 1. Probar primero extracción precisa desde el nombre (ej. 750 ml, 20 Und, x10, x20)
        vol_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(ml|l|cc|cm3|g|gr|kg|und|unidades|piezas|cigarrillos)\b', name, re.IGNORECASE)
        if vol_match:
            qty = vol_match.group(1).replace(',', '.')
            unit = vol_match.group(2).upper()
            if unit == "CIGARRILLOS":
                unit = "UND"
            return f"{qty} {unit}"
            
        pack_match = re.search(r'(?:caja\s*x|x\s*)(\d+)\b', name, re.IGNORECASE)
        if pack_match:
            qty = pack_match.group(1)
            return f"{qty} UND"

        # 2. Probar con los campos directos quantity y unitType de Rappi
        if quantity and str(quantity).strip() not in ("0", "None", ""):
            unit = str(unit_type).strip().upper() if unit_type else "UND"
            if unit in ("ML", "L", "CC", "GR", "G", "KG", "UND", "UN", "UNIDADES"):
                return f"{quantity} {unit}"
            elif unit:
                return f"{quantity} {unit}"
            else:
                return f"{quantity} UND"
                
        return "N/A"

    def _extract_alcohol_degrees(self, name: str) -> str:
        deg_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:°|º|%|grados|g\.l\.)\b', name, re.IGNORECASE)
        if deg_match:
            try:
                num = float(deg_match.group(1).replace(',', '.'))
                if 0 < num <= 100.0:
                    return str(round(num, 2))
            except ValueError:
                pass
        return ""

    def _parse_product_node(self, node: dict, store_info: dict, search_term: str, category_group: str) -> Optional[Dict]:
        try:
            raw_name = node.get("name") or node.get("title") or ""
            name = self._clean_text(str(raw_name))
            
            pid = str(node.get("productId") or node.get("product_id") or "")
            store_id = str(store_info.get("storeId") or store_info.get("store_id") or "")
            
            # Formato estándar de ID unívoco por tienda: {storeId}_{productId}
            unique_id = str(node.get("id") or (f"{store_id}_{pid}" if store_id and pid else pid))
            if not name or not unique_id or unique_id == "_":
                return None

            # 1. Filtro estricto a nivel de tienda (ignorar restaurantes y locales de comida)
            if self._is_excluded_store(store_info):
                return None

            # 2. Filtro estricto a nivel de producto (descartar comidas, abarrotes, etc. y validar Alcohol/Tabaco)
            is_valid, inferred_type = self._is_authentic_alcohol_or_tobacco(name, node)
            if not is_valid:
                return None

            # Validación de disponibilidad y precio
            is_available = bool(node.get("isAvailable", True) and node.get("inStock", True))
            price = node.get("price") or node.get("realPrice") or node.get("real_price") or 0.0
            orig_price = node.get("realPrice") or node.get("originalPrice") or node.get("original_price") or price

            try:
                price = float(price)
            except (ValueError, TypeError):
                price = 0.0

            try:
                orig_price = float(orig_price)
            except (ValueError, TypeError):
                orig_price = price

            if price <= 0 or not is_available:
                return None

            # Cálculo de descuento
            discount_pct = "0%"
            if orig_price > price and orig_price > 0:
                desc_num = ((orig_price - price) / orig_price) * 100
                discount_pct = f"{round(desc_num)}%"

            # Tienda y metadata
            store_name = self._clean_text(
                store_info.get("storeName")
                or store_info.get("brandName")
                or store_info.get("name")
                or "Rappi"
            )
            store_brand = self._clean_text(store_info.get("brandName") or "")

            # Marca
            brand = self._extract_brand(name, node.get("brand") or node.get("trademark"))
            
            # Clasificación de Tipo de Producto garantizada (Vapes son Tabaco)
            tipo_producto = inferred_type

            # Categoría legible
            categoria = search_term.capitalize() if search_term else category_group.capitalize()

            # Medida y Grados de alcohol
            medida = self._extract_medida(name, node.get("quantity"), node.get("unitType"))
            grados_alcohol = self._extract_alcohol_degrees(name)

            # Precio por unidad / PUM
            raw_pum = node.get("pum")
            precio_unidad = ""
            if raw_pum and isinstance(raw_pum, str) and "/" in raw_pum:
                precio_unidad = self._clean_text(raw_pum)
            else:
                from core.database import calculate_unit_price
                precio_unidad = calculate_unit_price(price, medida)

            # URL del Producto
            slug = node.get("slug") or node.get("friendly_url") or ""
            if slug:
                url_producto = f"https://www.rappi.com.co/p/{slug}"
            else:
                url_producto = f"https://www.rappi.com.co/search?query={urllib.parse.quote(search_term)}"

            # Descripción enriquecida con datos de la tienda
            zona_desc = self.location.get("zone", self.location["city"])
            desc_text = f"Tienda Rappi: {store_name}"
            if store_brand and store_brand.lower() != store_name.lower():
                desc_text += f" ({store_brand})"
            desc_text += f" | Zona: {zona_desc}"

            return {
                "ID": unique_id,
                "Nombre": name,
                "Marca": brand,
                "Referencia": store_name,  # Guardamos la tienda en 'Referencia' según arquitectura
                "Categoria": categoria,
                "Tipo de Producto": tipo_producto,
                "Grados de alcohol": grados_alcohol,
                "Medida": medida,
                "Precio_Original": orig_price,
                "Precio_Final": price,
                "Descuento_%": discount_pct,
                "Precio_Unidad": precio_unidad,
                "URL_Producto": url_producto,
                "Descripcion": desc_text,
            }
        except Exception as e:
            logger.debug(f"Error parseando nodo de producto: {e}")
            return None

    def scrape_term_http(self, term: str, category_group: str, seen_ids: Set[str]) -> List[Dict]:
        encoded = urllib.parse.quote(term)
        url = f"https://www.rappi.com.co/search?query={encoded}"
        req = urllib.request.Request(url, headers=self.headers)
        
        products = []
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                html = resp.read().decode("utf-8", errors="replace")
                match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', html)
                if not match:
                    return []

                data = json.loads(match.group(1))
                fallback = data.get("props", {}).get("pageProps", {}).get("fallback", {})
                
                for fb_val in fallback.values():
                    if isinstance(fb_val, dict) and "stores" in fb_val:
                        for store in fb_val["stores"]:
                            for p in store.get("products", []):
                                item = self._parse_product_node(p, store, term, category_group)
                                if item and item["ID"] not in seen_ids:
                                    seen_ids.add(item["ID"])
                                    products.append(item)
        except Exception as e:
            logger.warning(f"Aviso HTTP consultando '{term}' en {self.location.get('zone', self.location['city'])}: {e}")

        return products

    def fetch_products(self, categories: Optional[List[str]] = None, max_terms: Optional[int] = None, multi_zone: bool = True) -> List[Dict]:
        """
        Método estándar de extracción masiva deduplicada compatible con el orquestador DataSuite.
        """
        cats_to_run = {}
        if not categories or "ALL" in [c.upper() for c in categories]:
            cats_to_run = TARGET_CATEGORIES
        else:
            for c in categories:
                key = c.upper()
                if key in TARGET_CATEGORIES:
                    cats_to_run[key] = TARGET_CATEGORIES[key]

        all_products = []
        seen_ids = set()

        zones = [self.location_key]
        if multi_zone and self.location["city"].lower() == "bogotá":
            # Usar zonas clave para no sobrecargar y maximizar cobertura
            zones = list(LOCATIONS.keys())

        logger.info(f"=== INICIANDO SCRAPER RAPPI [BOGOTÁ: {len(zones)} ZONAS] ===")
        start_time = time.time()

        for z_key in zones:
            self.location_key = z_key
            self.location = LOCATIONS[z_key]
            self.headers["latitude"] = str(self.location["lat"])
            self.headers["longitude"] = str(self.location["lng"])

            logger.info(f"📍 Consultando Zona: {self.location.get('zone', z_key)}")

            for cat_name, terms in cats_to_run.items():
                if max_terms:
                    terms = terms[:max_terms]

                for term in terms:
                    items = self.scrape_term_http(term, cat_name, seen_ids)
                    if items:
                        all_products.extend(items)
                        logger.info(f"   ✓ '{term}': +{len(items)} únicos (Acumulado: {len(all_products)})")
                    time.sleep(0.4)

        elapsed = round(time.time() - start_time, 2)
        tab_count = sum(1 for p in all_products if p["Tipo de Producto"] == "Tabaco")
        alc_count = sum(1 for p in all_products if p["Tipo de Producto"] == "Alcohol")
        snack_count = sum(1 for p in all_products if p["Tipo de Producto"] == "Ultraprocesados")

        logger.info(f"\n=======================================================")
        logger.info(f"🎉 EXTRACCIÓN RAPPI FINALIZADA en {elapsed}s")
        logger.info(f"📦 Total productos ÚNICOS: {len(all_products)}")
        logger.info(f"   -> TABACO: {tab_count}")
        logger.info(f"   -> ALCOHOL: {alc_count}")
        logger.info(f"   -> ULTRAPROCESADOS: {snack_count}")
        logger.info(f"=======================================================")

        return all_products

    def run(self, categories: Optional[List[str]] = None, max_terms: Optional[int] = None, multi_zone_bogota: bool = True) -> List[Dict]:
        """Alias para mantener compatibilidad."""
        return self.fetch_products(categories=categories, max_terms=max_terms, multi_zone=multi_zone_bogota)

    def save_to_csv(self, all_products: List[Dict], output_file: Optional[str] = None):
        target_file = output_file or self.output_file
        os.makedirs(os.path.dirname(target_file) or ".", exist_ok=True)
        logger.info(f"Guardando {len(all_products)} productos en {target_file}...")
        
        final_headers = self.base_headers + sorted(list(self.all_extracted_headers - set(self.base_headers)))
        
        for row in all_products:
            for header in final_headers:
                if header not in row or row[header] == "" or row[header] is None:
                    row[header] = "NULL"
                    
        with open(target_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=final_headers, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(all_products)
        logger.info("CSV guardado correctamente.")

    def save_to_json(self, all_products: List[Dict], json_file: str = "data/productos_rappi.json"):
        os.makedirs(os.path.dirname(json_file) or ".", exist_ok=True)
        logger.info(f"Guardando {len(all_products)} productos en {json_file}...")
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(all_products, f, indent=4, ensure_ascii=False)
        logger.info("JSON guardado correctamente.")

    def export(self, products: List[Dict], prefix: str = "rappi_proesa"):
        """Exportador con timestamp para ejecuciones CLI aisladas."""
        if not products:
            logger.warning("No hay productos para exportar.")
            return
        os.makedirs("output", exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.save_to_json(products, f"output/{prefix}_bogota_{stamp}.json")
        self.save_to_csv(products, f"output/{prefix}_bogota_{stamp}.csv")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scraper Rappi Tabaco y Alcohol Proesa")
    parser.add_argument("--category", choices=["TABACO", "ALCOHOL", "ALL"], default="ALL")
    parser.add_argument("--limit", type=int, default=None, help="Límite de términos por categoría")
    parser.add_argument("--single-zone", action="store_true", help="Desactiva barrido multizona")
    args = parser.parse_args()

    scraper = RappiScraper(output_file="data/productos_rappi.csv")
    data = scraper.fetch_products(
        categories=[args.category],
        max_terms=args.limit,
        multi_zone=not args.single_zone
    )
    if data:
        scraper.save_to_csv(data)
        scraper.save_to_json(data)
