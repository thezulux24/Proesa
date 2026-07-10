import json
import csv
import time
import re
import requests
import hashlib

class D1Scraper:
    def __init__(self, output_file="../data/productos_d1.csv"):
        self.output_file = output_file
        self.base_headers = [
            "ID", "Nombre", "Marca", "Referencia", "Categoria", "Tipo de Producto", "Grados de alcohol", 
            "Medida", "Precio_Original", "Precio_Final", "Descuento_%", "Precio_Unidad", "URL_Producto", "Descripcion"
        ]
        self.all_extracted_headers = set(self.base_headers)
        
    def fetch_products(self, category_url, category_name, tipo_producto):
        print(f"Scraping D1 category: {category_name} ({tipo_producto})...")
        results = []
        page_num = 1
        
        headers = {
            "X-Bot-Project": "Observatorio de Precios PROESA",
            "X-Bot-Purpose": "Investigacion Academica - Extraccion de datos publica 1 vez al dia (Consumo de Tabaco y Alcohol)",
            "X-Bot-Contact": "data@bzuluaga.site",

            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        
        # Regex to capture the exact product dictionary pattern in D1's Next.js HTML payloads
        # Format usually: {"name":"...","price":12345,...,"unit":"Unidad","subUnit":"mL","subQty":750}
        pattern = re.compile(r'\{"name":"([^"]+)","price":([0-9]+).*?(?:"unit":"([^"]+)","subUnit":"([^"]+)","subQty":([0-9.]+))?')
        
        seen_names = set()
        
        while True:
            url = f"{category_url}&page={page_num}" if "?" in category_url else f"{category_url}?page={page_num}"
            try:
                r = requests.get(url, headers=headers)
                if r.status_code != 200:
                    print(f"Error fetching page {page_num}, status: {r.status_code}")
                    break
                    
                html = r.text
                
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
                            list_prices = re.findall(r'"listPrice":([0-9.]+)', chunk_str)
                            
                            if skus and prices:
                                names = re.findall(r'"name":"([^"]+)"', chunk_str)
                                valid_names = [n for n in names if n.lower() not in ["vinos", "licores", "cervezas", "bebidas", "otros", "cigarrillos", "inicio", "tabacos"]]
                                
                                if valid_names:
                                    sku = skus[0]
                                    if sku not in seen_names:
                                        seen_names.add(sku)
                                        name = max(valid_names, key=len)
                                        brand = min(valid_names, key=len) if len(valid_names) > 1 else "N/A"
                                        price_final = prices[0]
                                        list_price = list_prices[0] if list_prices else price_final
                                        
                                        if brand == name: brand = "N/A"
                                        
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
                                            "Categoria": category_name,
                                            "Tipo de Producto": tipo_producto,
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
                
                page_num += 1
                time.sleep(1) # delay polite
                
            except Exception as e:
                print(f"Failed to fetch or parse D1: {e}")
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
    import os
    os.makedirs('../data', exist_ok=True)
    scraper = D1Scraper(output_file="../data/productos_d1.csv")
    
    # D1 Categories
    licores_url = "https://domicilios.tiendasd1.com/ca/bebidas/BEBIDAS?categories=Vinos%7E%7ELicores%7E%7ECervezas"
    tabacos_url = "https://domicilios.tiendasd1.com/ca/otros/cigarrillos/OTROS/CIGARRILLOS"
    
    # Run extractions
    licores_products = scraper.fetch_products(licores_url, "Vinos y Licores", "Alcohol")
    tabacos_products = scraper.fetch_products(tabacos_url, "Cigarrillos y Tabacos", "Tabaco")
    
    all_products = licores_products + tabacos_products
    
    if all_products:
        scraper.save_to_csv(all_products)
        scraper.save_to_json(all_products)
    else:
        print("No products found.")

if __name__ == '__main__':
    main()
