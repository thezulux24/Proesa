import json
import csv
import time
import re
import os
from scrapling.fetchers import FetcherSession

class D1Scraper:
    def __init__(self, output_file="../data/productos_d1.csv"):
        self.output_file = output_file
        self.base_headers = [
            "ID", "Nombre", "Marca", "Referencia", "Categoria", "Tipo de Producto", "Grados de alcohol", 
            "Medida", "Precio_Original", "Precio_Final", "Descuento_%", "Precio_Unidad", "URL_Producto", "Descripcion"
        ]
        self.all_extracted_headers = set(self.base_headers)
        
    def infer_tipo_producto(self, categories):
        cat_str = " ".join(categories).lower()
        if any(w in cat_str for w in ["cigarrillo", "tabaco", "puro", "vapeador"]):
            return "Tabaco"
        elif any(w in cat_str for w in ["snack", "pasaboca", "papas", "paquete"]):
            return "Ultraprocesados"
        return "Alcohol"

    def fetch_products(self):
        print("Scraping D1 Vinos, Licores, Tabacos y Ultraprocesados usando Scrapling y API VTEX...")
        results = []
        
        headers = {
            "X-Bot-Project": "Observatorio de Precios PROESA",
            "X-Bot-Purpose": "Investigacion Academica - Extraccion publica diaria",
            "X-Bot-Contact": "data@bzuluaga.site",
            "Accept": "application/json"
        }
        
        seen_ids = set()
        categories_to_scrape = ["7/66/", "7/67/", "7/68/", "7/69/"]  # Vinos, Licores, Cervezas, Cigarrillos
        
        with FetcherSession(impersonate="chrome") as session:
            for cat_id in categories_to_scrape:
                _from = 0
                step = 49
                print(f"\n--- Scraping Categoría {cat_id} ---")
                
                while True:
                    _to = _from + step
                    url = f"https://www.d1.com.co/api/catalog_system/pub/products/search?fq=C:{cat_id}&_from={_from}&_to={_to}"
                    print(f"Fetching: {url}")
                    
                    try:
                        r = session.get(url, headers=headers)
                        status = getattr(r, 'status', getattr(r, 'status_code', 200))
                        if status not in [200, 206]:
                            print(f"Error HTTP {status}")
                            break
                            
                        try:
                            data = r.json()
                        except Exception:
                            print("Error parsing JSON")
                            break
                            
                        if not data or len(data) == 0:
                            break
                            
                        new_products_found = 0
                        
                        for item in data:
                            sku = str(item.get("productId", ""))
                            if sku in seen_ids:
                                continue
                            seen_ids.add(sku)
                            
                            name = item.get("productName", "N/A")
                            brand = item.get("brand", "N/A")
                            
                            cats = item.get("categories", [])
                            tipo_producto = self.infer_tipo_producto(cats)
                            
                            # Find commercial offer
                            price_final = 0
                            list_price = 0
                            try:
                                offer = item["items"][0]["sellers"][0]["commertialOffer"]
                                price_final = offer.get("Price", 0)
                                list_price = offer.get("ListPrice", price_final)
                            except (KeyError, IndexError):
                                pass
                                
                            if price_final == 0:
                                continue
                                
                            new_products_found += 1
                            
                            # Extract volume
                            vol_match = re.search(r'(\d+)\s*(ml|l|g|kg)\b', name, re.IGNORECASE)
                            if vol_match:
                                sub_qty = vol_match.group(1)
                                sub_unit = vol_match.group(2).upper()
                                medida_str = f"{sub_qty} {sub_unit}"
                            else:
                                sub_qty = ""
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
                                "Descripcion": item.get("metaTagDescription", "N/A"),
                                "Referencia": item.get("productReference", sku),
                                "Categoria": cats[0] if cats else "N/A",
                                "Tipo de Producto": tipo_producto,
                                "Grados de alcohol": "N/A", 
                                "Medida": medida_str,
                                "Precio_Original": list_price, 
                                "Precio_Final": price_final,
                                "Descuento_%": "0%",
                                "Precio_Unidad": precio_unidad,
                                "URL_Producto": item.get("link", "") if str(item.get("link", "")).startswith("http") else "https://www.d1.com.co" + item.get("link", "")
                            }
                            
                            try:
                                pf = float(price_final)
                                po = float(list_price)
                                if po > pf and po > 0:
                                    desc = ((po - pf) / po) * 100
                                    result_dict["Descuento_%"] = f"{round(desc)}%"
                            except Exception:
                                pass
                                
                            results.append(result_dict)
                            
                        print(f"Page {_from}-{_to}: Found {new_products_found} new products.")
                        
                        if len(data) < 50:
                            # Reached the end of pagination
                            break
                            
                        _from += 50
                        time.sleep(1)
                        
                    except Exception as e:
                        print(f"Failed to fetch D1: {e}")
                        break
                        
        return results

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

    def save_to_json(self, all_products, json_file="../data/productos_d1.json"):
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
    os.makedirs('../data', exist_ok=True)
    scraper = D1Scraper(output_file="../data/productos_d1.csv")
    
    all_products = scraper.fetch_products()
    
    if all_products:
        scraper.save_to_csv(all_products)
        scraper.save_to_json(all_products)
    else:
        print("No products found.")

if __name__ == '__main__':
    main()
