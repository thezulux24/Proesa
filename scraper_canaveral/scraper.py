import requests
import re
import json
import csv
import os

class CanaveralScraper:
    def __init__(self, output_file="../data/productos_canaveral.csv"):
        self.output_file = output_file
        self.headers = {
            "X-Bot-Project": "Observatorio de Precios PROESA",
            "X-Bot-Purpose": "Investigacion Academica - Extraccion de datos publica 1 vez al dia (Consumo de Tabaco y Alcohol)",
            "X-Bot-Contact": "data@bzuluaga.site",

            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "es-CO,es;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    def fetch_products(self, category_url, category_name, tipo_producto, max_pages=10):
        results = []
        seen_names = set()
        
        print(f"Scraping Cañaveral category: {category_name} ({tipo_producto})...")
        
        for page_num in range(1, max_pages + 1):
            url = f"{category_url}?currentPage={page_num}" if "?" not in category_url else f"{category_url}&currentPage={page_num}"
            
            try:
                response = requests.get(url, headers=self.headers, timeout=15)
                if response.status_code != 200:
                    print(f"Failed to fetch {url} - Status: {response.status_code}")
                    break
                    
                html = response.text
                
                # Next.js App Router payloads
                matches = re.findall(r'self\.__next_f\.push\((.*?)\)', html)
                new_products_found = 0
                
                for m in matches:
                    try:
                        chunk = json.loads(m)
                        if isinstance(chunk, list) and len(chunk) > 1:
                            chunk_str = chunk[1]
                            skus = re.findall(r'"sku":"([^"]+)"', chunk_str)
                            prices = re.findall(r'"price":([0-9.]+)', chunk_str)
                            list_prices = re.findall(r'"priceBeforeTaxes":([0-9.]+)', chunk_str)
                            if not list_prices:
                                list_prices = re.findall(r'"listPrice":([0-9.]+)', chunk_str)
                            brands = re.findall(r'"brand":"([^"]+)"', chunk_str)
                            
                            if skus and prices:
                                names = re.findall(r'"name":"([^"]+)"', chunk_str)
                                valid_names = [n for n in names if n.lower() not in ["vinos", "licores", "cervezas", "bebidas", "otros", "cigarrillos", "inicio", "tabacos"]]
                                
                                if valid_names:
                                    sku = skus[0]
                                    if sku not in seen_names:
                                        seen_names.add(sku)
                                        name = max(valid_names, key=len)
                                        brand = brands[0] if brands else "N/A"
                                        price_final = prices[0]
                                        list_price = list_prices[0] if list_prices else price_final
                                        
                                        if brand == name: brand = "N/A"
                                        
                                        # Extract Subcategory
                                        cat_match = re.search(r'"categoryNamesPath":"/LICORES/([^"]+)"', chunk_str, re.IGNORECASE)
                                        if cat_match:
                                            sub_category = cat_match.group(1).upper()
                                        else:
                                            sub_category = category_name
                                        
                                        # Tipo de producto dinámico
                                        sub_cat_lower = sub_category.lower()
                                        cat_name_lower = category_name.lower()
                                        if ("cigarrillo" in sub_cat_lower or "vapeador" in sub_cat_lower or "tabaco" in sub_cat_lower or "puros" in sub_cat_lower) or \
                                           ("cigarrillo" in cat_name_lower or "vapeador" in cat_name_lower or "tabaco" in cat_name_lower or "puros" in cat_name_lower):
                                            item_tipo_producto = "Tabaco"
                                        elif ("pasaboca" in sub_cat_lower or "snack" in sub_cat_lower or "papas" in sub_cat_lower) or \
                                             ("pasaboca" in cat_name_lower or "snack" in cat_name_lower or "papas" in cat_name_lower):
                                            item_tipo_producto = "Ultraprocesados"
                                        else:
                                            item_tipo_producto = "Alcohol"
                                            
                                        new_products_found += 1
                                        
                                        # Try to find volume (mL, L, g, kg) in name
                                        vol_match = re.search(r'(\d+)\s*(ml|l|g|kg)\b', name, re.IGNORECASE)
                                        if vol_match:
                                            sub_qty = vol_match.group(1)
                                            sub_unit = vol_match.group(2).upper()
                                            medida_str = f"{sub_qty} {sub_unit}"
                                        else:
                                            sub_qty = ""
                                            sub_unit = ""
                                            medida_str = "N/A"
                                                
                                        precio_unidad = "N/A"
                                        if sub_qty and price_final:
                                            try:
                                                precio_unidad = round(float(price_final) / float(sub_qty), 2)
                                            except ValueError:
                                                pass
                                                
                                        result_dict = {
                                            "ID": sku,
                                            "Nombre": name,
                                            "Marca": brand,
                                            "Descripcion": "N/A",
                                            "Referencia": sku,
                                            "Categoria": sub_category,
                                            "Tipo de Producto": item_tipo_producto,
                                            "Grados de alcohol": "N/A", 
                                            "Medida": medida_str,
                                            "Precio_Original": list_price, 
                                            "Precio_Final": price_final,
                                            "Descuento_%": "0%",
                                            "Precio_Unidad": precio_unidad,
                                            "URL_Producto": category_url
                                        }
                                        
                                        # Descuento
                                        try:
                                            pf = float(price_final)
                                            po = float(list_price)
                                            if po > pf and po > 0:
                                                desc = ((po - pf) / po) * 100
                                                result_dict["Descuento_%"] = f"{round(desc)}%"
                                        except:
                                            pass
                                            
                                        results.append(result_dict)
                    except Exception:
                        pass
                
                print(f"[{category_name}] Page {page_num}: Found {new_products_found} new products.")
                
                if new_products_found == 0:
                    break
                    
            except Exception as e:
                print(f"Error fetching page {page_num}: {e}")
                break
                
        return results

    def save_to_csv(self, results):
        if not results:
            print("No products found.")
            return

        print(f"Saving {len(results)} products to {self.output_file}...")
        dirname = os.path.dirname(self.output_file)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        
        fieldnames = ["ID", "Nombre", "Marca", "Descripcion", "Referencia", "Categoria", "Tipo de Producto", 
                      "Grados de alcohol", "Medida", "Precio_Original", "Precio_Final", "Descuento_%", 
                      "Precio_Unidad", "URL_Producto"]
        
        with open(self.output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                writer.writerow(r)
        print("CSV Done!")

    def save_to_json(self, results):
        if not results:
            return
        json_file = self.output_file.replace('.csv', '.json')
        print(f"Saving {len(results)} products to {json_file}...")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print("JSON Done!")

if __name__ == "__main__":
    scraper = CanaveralScraper()
    
    licores = scraper.fetch_products("https://www.domicilioscanaveral.com/ca/licores/03", "Licores", "Alcohol", max_pages=20)
    cigarrillos_1 = scraper.fetch_products("https://www.domicilioscanaveral.com/ca/licores/cigarrillos/03/0143", "Cigarrillos", "Tabaco", max_pages=10)
    cigarrillos_2 = scraper.fetch_products("https://www.domicilioscanaveral.com/ca/licores/03?categories=CIGARRILLOS+Y+VAPEADORES", "Cigarrillos y Vapeadores", "Tabaco", max_pages=10)
    
    # Deduplicate by ID
    all_products = {}
    for item in licores + cigarrillos_1 + cigarrillos_2:
        all_products[item["ID"]] = item
        
    final_list = list(all_products.values())
    
    scraper.save_to_csv(final_list)
    scraper.save_to_json(final_list)
