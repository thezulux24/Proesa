import json
import csv
import time
import re
import urllib.parse
from bs4 import BeautifulSoup
from scrapling.fetchers import Fetcher

class CarullaScraper:
    def __init__(self, output_file="../data/productos_carulla.csv"):
        self.output_file = output_file
        # Base headers as required
        self.base_headers = [
            "ID", "Nombre", "Marca", "Referencia", "Categoria", "Tipo de Producto", "Grados de alcohol", 
            "Medida", "Precio_Original", "Precio_Final", "Descuento_%", "Precio_Unidad", "URL_Producto", "Descripcion"
        ]
        self.all_extracted_headers = set(self.base_headers)
        
    def fetch_products(self, query_params, category_name, tipo_producto):
        print(f"Scraping category/search: {category_name} ({tipo_producto})...")
        first = 50
        after = 0
        total_fetched = 0
        
        results = []
        
        while True:
            # Query params dict already has term or facets
            variables = {
                "first": first,
                "after": str(after),
                "sort": "score_desc",
                "term": query_params.get("term", ""),
                "selectedFacets": query_params.get("selectedFacets", []) + [
                    {"key": "channel", "value": "{\"salesChannel\":\"1\",\"regionId\":\"\"}"},
                    {"key": "locale", "value": "es-CO"}
                ]
            }
            
            encoded_vars = urllib.parse.quote(json.dumps(variables))
            url = f"https://www.carulla.com/api/graphql?operationName=SearchQuery&variables={encoded_vars}"
            
            try:
                # REGLA ESTRICTA: HTTP ONLY usando Scrapling
                page = Fetcher.get(url, headers={"accept": "application/json", "X-Bot-Project": "Observatorio de Precios PROESA", "X-Bot-Purpose": "Investigacion Academica - Extraccion de datos publica 1 vez al dia (Consumo de Tabaco y Alcohol)", "X-Bot-Contact": "data@bzuluaga.site"}, impersonate='chrome')
                if page.status == 429:
                    print('Rate limited (429)! Sleeping for 30 seconds before retrying...')
                    time.sleep(30)
                    continue
                if page.status != 200:
                    print(f"Error fetching page, status: {page.status}")
                    break
                    
                data = page.json()
                products = data.get('data', {}).get('search', {}).get('products', {}).get('edges', [])
                
                if not products:
                    break
                
                for edge in products:
                    node = edge.get('node', {})
                    product_data = self._extract_product_data(node, category_name, tipo_producto)
                    if product_data:
                        results.append(product_data)
                
                total_fetched += len(products)
                print(f"[{category_name}] Fetched {total_fetched} products so far...")
                
                after += first
                time.sleep(3) # Delay polite
                
            except Exception as e:
                print(f"Failed to fetch or parse products: {e}")
                break
                
        return results

    def _extract_product_data(self, node, default_category, tipo_producto):
        try:
            name = node.get('name', 'N/A')
            slug = node.get('slug', '')
            url_producto = f"https://www.carulla.com/{slug}/p" if slug else ""
            
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
            
            offers_array = node.get('offers', {}).get('offers', [])
            if offers_array and len(offers_array) > 0:
                price_final = offers_array[0].get('price', "N/A")
                price_original = offers_array[0].get('listPrice', "N/A")
            elif node.get('sellers'):
                commertial = node['sellers'][0].get('commertialOffer', {})
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

            props = node.get('properties', [])
            props_dict = {p.get('name', ''): p.get('values', ['N/A'])[0] for p in props}
            
            referencia = props_dict.get('Referencia', "N/A")
            grados = props_dict.get('Grados de alcohol', "N/A")
            
            unidad = props_dict.get('Unidad de Medida PUM Calculado', props_dict.get('Unidad de Medida', "N/A"))
            factor_neto = props_dict.get('Factor Neto PUM', "N/A")
            
            medida_str = f"{factor_neto} {unidad}" if factor_neto != "N/A" else "N/A"
            
            breadcrumbs = node.get('breadcrumbList', {}).get('itemListElement', [])
            categoria = default_category
            if len(breadcrumbs) >= 2:
                categoria = breadcrumbs[1].get('name', default_category)
                if len(breadcrumbs) >= 3 and categoria == "Vinos y licores":
                    categoria = breadcrumbs[2].get('name', default_category)
                    
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
                "ID": node.get('id', ''),
                "Nombre": name,
                "Marca": node.get('brand', {}).get('name', ''),
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
                'sellerId', 'Prime', 'Vendido por', 'Ump del Empaque 1 (Out)',
                'Unidad de Medida PUM Calculado', 'Factor Escurrido PUM',
                'Unidad de Medida', 'Número de Piezas', 'Capacidad de almacenamiento',
                'Grasa saturada (por porción)', 'ID'
            }
            
            for p in props:
                p_name = p.get('name', '')
                if p_name == 'País De Origen':
                    p_name = 'País de Origen'
                if p_name and p_name not in result_dict and p_name not in blacklisted_props:
                    result_dict[p_name] = p.get('values', [''])[0]
                    self.all_extracted_headers.add(p_name)
                    
            return result_dict
        except Exception as e:
            print(f"Error parsing product {node.get('name', '')}: {e}")
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

    def save_to_json(self, all_products, json_file="../data/productos_carulla.json"):
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
    scraper = CarullaScraper(output_file="../data/productos_carulla.csv")
    
    # Facets for Vinos y Licores
    query_licores = {
        "term": "",
        "selectedFacets": [
            {"key": "category-1", "value": "vinos-y-licores"}
        ]
    }
    
    # Run the extractions (We only need the main Licores search, it includes Tobacco)
    all_products = scraper.fetch_products(query_licores, "Vinos y Licores", "Alcohol")
    
    if all_products:
        scraper.save_to_csv(all_products)
        scraper.save_to_json(all_products)
    else:
        print("No products found.")

if __name__ == '__main__':
    main()
