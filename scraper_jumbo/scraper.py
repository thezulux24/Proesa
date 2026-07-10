import json
import csv
import time
import re
from bs4 import BeautifulSoup
from scrapling.fetchers import Fetcher

class JumboScraper:
    def __init__(self, output_file="../data/productos_jumbo.csv"):
        self.output_file = output_file
        self.base_headers = [
            "ID", "Nombre", "Marca", "Referencia", "Categoria", "Tipo de Producto", "Grados de alcohol", 
            "Medida", "Precio_Original", "Precio_Final", "Descuento_%", "Precio_Unidad", "URL_Producto", "Descripcion"
        ]
        self.all_extracted_headers = set(self.base_headers)
        
    def fetch_products(self, category_path, category_name, tipo_producto):
        print(f"Scraping category: {category_name} ({tipo_producto})...")
        step = 49
        _from = 0
        _to = step
        total_fetched = 0
        
        results = []
        
        while True:
            # Jumbo uses VTEX Legacy Search API
            url = f"https://www.jumbocolombia.com/api/catalog_system/pub/products/search{category_path}?_from={_from}&_to={_to}"
            
            try:
                # REGLA ESTRICTA: HTTP ONLY usando Scrapling
                page = Fetcher.get(url, headers={"accept": "application/json", "X-Bot-Project": "Observatorio de Precios PROESA", "X-Bot-Purpose": "Investigacion Academica - Extraccion de datos publica 1 vez al dia (Consumo de Tabaco y Alcohol)", "X-Bot-Contact": "data@bzuluaga.site"}, impersonate='chrome')
                if page.status == 429:
                    print('Rate limited (429)! Sleeping for 30 seconds before retrying...')
                    time.sleep(30)
                    continue
                if page.status not in (200, 206):
                    print(f"Error fetching page, status: {page.status}")
                    break
                    
                products = page.json()
                
                if not products or len(products) == 0:
                    break
                
                for node in products:
                    product_data = self._extract_product_data(node, category_name, tipo_producto)
                    if product_data:
                        results.append(product_data)
                
                total_fetched += len(products)
                print(f"[{category_name}] Fetched {total_fetched} products so far...")
                
                # if the returned products are less than step + 1, it means we hit the end
                if len(products) < (step + 1):
                    break
                
                _from += step + 1
                _to += step + 1
                time.sleep(3) # Delay polite
                
            except Exception as e:
                print(f"Failed to fetch or parse products: {e}")
                break
                
        return results

    def _extract_product_data(self, node, default_category, tipo_producto):
        try:
            name = node.get('productName', 'N/A')
            url_producto = node.get('link', '')
            
            raw_desc = node.get('description', '')
            clean_desc = "N/A"
            if raw_desc and isinstance(raw_desc, str):
                try:
                    soup = BeautifulSoup(raw_desc, "html.parser")
                    for script_or_style in soup(["script", "style"]):
                        script_or_style.extract()
                    clean_desc = soup.get_text(separator=" ", strip=True)
                    clean_desc = re.sub(r'\s+', ' ', clean_desc).strip()
                    if not clean_desc:
                        clean_desc = "N/A"
                except Exception:
                    clean_desc = raw_desc
            
            price_final = "N/A"
            price_original = "N/A"
            
            items = node.get('items', [])
            if items and len(items) > 0:
                sellers = items[0].get('sellers', [])
                if sellers and len(sellers) > 0:
                    commertial = sellers[0].get('commertialOffer', {})
                    price_final = commertial.get('Price', "N/A")
                    price_original = commertial.get('ListPrice', "N/A")

            descuento_porcentaje = "0%"
            if price_final != "N/A" and price_original != "N/A":
                try:
                    pf = float(price_final)
                    po = float(price_original)
                    if po > pf and po > 0:
                        descuento = ((po - pf) / po) * 100
                        descuento_porcentaje = f"{round(descuento)}%"
                except ValueError:
                    pass

            # VTEX Legacy properties are typically lists mapped to the property name directly in the JSON root
            referencia = node.get('productReference', 'N/A')
            
            # Helper to safely extract single string from VTEX Legacy property lists
            def get_prop(key, default="N/A"):
                val = node.get(key, None)
                if val and isinstance(val, list) and len(val) > 0:
                    return str(val[0])
                return default
                
            grados = get_prop('Grados de alcohol')
            if grados == "N/A":
                grados = get_prop('% Alcohol')
            if grados == "N/A":
                grados = get_prop('Graduación Alcohólica')
                
            unidad = get_prop('Unidad de Medida PUM')
            if unidad == "N/A":
                unidad = get_prop('Unidad de Medida')
                
            factor_neto = get_prop('Factor Neto PUM')
            if factor_neto == "N/A":
                factor_neto = get_prop('Factor Neto')
            
            medida_str = f"{factor_neto} {unidad}" if factor_neto != "N/A" else "N/A"
            if medida_str == "N/A" or medida_str == "N/A N/A":
                medida_str = get_prop('Contenido Neto')
                if medida_str == "N/A":
                    medida_str = get_prop('Contenido')
            
            # Use categories array from VTEX
            categories = node.get('categories', [])
            categoria = default_category
            if categories and len(categories) > 0:
                # categories are like "/Supermercado/Vinos Y Licores/Cervezas/"
                parts = [p for p in categories[0].split('/') if p]
                if len(parts) >= 3:
                    categoria = parts[2]
                    
            precio_unidad = "N/A"
            if price_final != "N/A" and factor_neto != "N/A":
                try:
                    price_val = float(price_final)
                    factor_val = float(factor_neto)
                    if factor_val > 0:
                        precio_unidad = round(price_val / factor_val, 2)
                except ValueError:
                    pass
            
            # Tipo de Producto dinámico basado en la categoría extraída
            cat_lower = categoria.lower()
            if "cigarrillo" in cat_lower or "vapeador" in cat_lower or "tabaco" in cat_lower or "puros" in cat_lower:
                tipo_producto = "Tabaco"
            elif "pasaboca" in cat_lower or "snack" in cat_lower or "papas" in cat_lower:
                tipo_producto = "Ultraprocesados"
            else:
                tipo_producto = "Alcohol"
            
            result_dict = {
                "ID": node.get('productId', ''),
                "Nombre": name,
                "Marca": node.get('brand', ''),
                "Descripcion": clean_desc,
                "Referencia": referencia,
                "Categoria": categoria,
                "Tipo de Producto": tipo_producto,
                "Grados de alcohol": grados,
                "Medida": medida_str,
                "Precio_Original": price_original,
                "Precio_Final": price_final,
                "Descuento_%": descuento_porcentaje,
                "Precio_Unidad": precio_unidad,
                "URL_Producto": url_producto
            }
            
            blacklisted_props = {
                'productId', 'productName', 'brand', 'description', 'link', 'categories',
                'items', 'categoryId', 'categoriesIds', 'linkText', 'productReference',
                'clusterHighlights', 'productClusters', 'searchableClusters', 'allSpecifications',
                'Unidad de Medida PUM', 'Factor Neto PUM', 'Unidad de Medida', 'Factor Neto'
            }
            
            # Legacy VTEX puts all specs in a list called 'allSpecifications', 
            # and then the keys exist at the root
            all_specs = node.get('allSpecifications', [])
            for spec_name in all_specs:
                if spec_name not in result_dict and spec_name not in blacklisted_props:
                    val = get_prop(spec_name, "")
                    if val:
                        result_dict[spec_name] = val
                        self.all_extracted_headers.add(spec_name)
                    
            return result_dict
        except Exception as e:
            print(f"Error parsing product {node.get('productName', '')}: {e}")
            return None

    def save_to_csv(self, all_products):
        print(f"Saving {len(all_products)} products to {self.output_file}...")
        final_headers = self.base_headers + sorted(list(self.all_extracted_headers - set(self.base_headers)))
        
        for row in all_products:
            for header in final_headers:
                if header not in row or row[header] == "" or row[header] == "N/A":
                    row[header] = "NULL"
                    
        with open(self.output_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=final_headers, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(all_products)
        print("CSV Done!")

    def save_to_json(self, all_products, json_file="../data/productos_jumbo.json"):
        import os
        os.makedirs(os.path.dirname(json_file), exist_ok=True)
        print(f"Saving {len(all_products)} products to {json_file}...")
        
        final_headers = self.base_headers + sorted(list(self.all_extracted_headers - set(self.base_headers)))
        for row in all_products:
            for header in final_headers:
                if header not in row or row[header] == "" or row[header] == "N/A":
                    row[header] = "NULL"
                    
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(all_products, f, indent=4, ensure_ascii=False)
        print("JSON Done!")

def main():
    import os
    os.makedirs('../data', exist_ok=True)
    scraper = JumboScraper(output_file="../data/productos_jumbo.csv")
    
    # Path inside API
    licores_path = "/supermercado/vinos-y-licores"
    
    # Run the extractions (We only need the main Licores search, it includes Tobacco)
    all_products = scraper.fetch_products(licores_path, "Vinos y Licores", "Alcohol")
    
    if all_products:
        scraper.save_to_csv(all_products)
        scraper.save_to_json(all_products)
    else:
        print("No products found.")

if __name__ == '__main__':
    main()
