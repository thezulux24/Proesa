import requests
import re
import json
import csv
import os

class MakroScraper:
    def __init__(self, output_file="../data/productos_makro.csv"):
        self.output_file = output_file
        self.headers = {
            "X-Bot-Project": "Observatorio de Precios PROESA",
            "X-Bot-Purpose": "Investigacion Academica - Extraccion de datos publica 1 vez al dia (Consumo de Tabaco y Alcohol)",
            "X-Bot-Contact": "data@bzuluaga.site",

            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "es-CO,es;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    def fetch_products(self, category_url, max_pages=10):
        results = []
        seen_names = set()
        
        print(f"Scraping Makro category...")
        
        for page_num in range(1, max_pages + 1):
            # Makro Next.js URL pagination uses `currentPage=`
            if "currentPage" in category_url:
                url = category_url
            else:
                url = f"{category_url}&currentPage={page_num}" if "?" in category_url else f"{category_url}?currentPage={page_num}"
            
            try:
                r = requests.get(url, headers=self.headers, timeout=15)
                if r.status_code != 200:
                    print(f"Failed to fetch page {page_num}. Status code: {r.status_code}")
                    break
                    
                html = r.text
                
                chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"]\)', html)
                if not chunks:
                    print("No chunks found in page.")
                    break
                    
                c_str = "".join([c.encode('utf-8').decode('unicode_escape', errors='ignore') for c in chunks])
                
                # Extract clean CatalogProductModel JSON blocks
                product_blocks = re.findall(r'\{[^{}]*"name":"[^"]+"[^{}]*"price":\d+[^{}]*"sku":"[^"]+"[^{}]*\}', c_str)
                
                products_found = 0
                for block in product_blocks:
                    try:
                        p = json.loads(block)
                        
                        name = p.get("name", "")
                        if name in seen_names or not name:
                            continue
                            
                        sku = p.get("sku", "")
                        brand = p.get("brand", "N/A")
                        slug = p.get("slug", sku)
                        url_producto = f"https://tienda.makro.com.co/p/{slug}"
                        
                        price_final = p.get("price", "N/A")
                        price_original = p.get("previousPrice")
                        if not price_original:
                            price_original = price_final
                        
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
                        
                        subQty = p.get("subQty", "")
                        subUnit = p.get("subUnit", "")
                        medida = f"{subQty} {subUnit}" if subQty and subUnit else "N/A"
                        
                        # Apply dynamic classification
                        name_lower = name.lower()
                        if "cigarrillo" in name_lower or "vapeador" in name_lower or "tabaco" in name_lower or "puros" in name_lower:
                            tipo_producto = "Tabaco"
                        elif "pasaboca" in name_lower or "snack" in name_lower or "papas" in name_lower:
                            tipo_producto = "Ultraprocesados"
                        else:
                            tipo_producto = "Alcohol"
                        
                        results.append({
                            "ID": sku,
                            "Nombre": name,
                            "Marca": brand,
                            "Descripcion": "N/A",
                            "Referencia": sku,
                            "Categoria": "Vinos y Licores", # Fallback, as category is lost in block
                            "Tipo de Producto": tipo_producto,
                            "Grados de alcohol": "N/A",
                            "Medida": medida,
                            "Precio_Original": price_original,
                            "Precio_Final": price_final,
                            "Descuento_%": descuento_porcentaje,
                            "Precio_Unidad": p.get("pricePerSubUnit", "N/A"),
                            "URL_Producto": url_producto
                        })
                        seen_names.add(name)
                        products_found += 1
                        
                    except Exception as e:
                        pass
                        
                print(f"[Makro] Page {page_num}: Found {products_found} new products.")
                if products_found == 0:
                    print("No more products found, stopping pagination.")
                    break
                    
            except Exception as e:
                print(f"Error on page {page_num}: {e}")
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
    scraper = MakroScraper()
    url = "https://tienda.makro.com.co/ca/bebidas/CP_03?categories=Cervezas%2C+Vinos+y+Licores"
    licores = scraper.fetch_products(url, max_pages=10)
    scraper.save_to_csv(licores)
    scraper.save_to_json(licores)
