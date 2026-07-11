import os
import json
from database import DataSuiteDB

def restore_database():
    db = DataSuiteDB()
    db.init_db() # Ensures all tables exist
    
    comercios = ["Jumbo", "Éxito", "Carulla", "Makro", "Cañaveral", "D1", "Olímpica"]
    
    total_inserted = 0
    for c in comercios:
        filename = f"data/productos_{c.lower().replace('é', 'e').replace('ñ', 'n')}.json"
        if not os.path.exists(filename):
            continue
            
        print(f"Restaurando {c} desde {filename}...")
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Clean up if some JSONs have top level list or dictionary
                if isinstance(data, list):
                    inserted = db.insert_products(c, data)
                    total_inserted += inserted
        except Exception as e:
            print(f"Error cargando {c}: {e}")
            
    print(f"\n¡Restauración completada! Se insertaron {total_inserted} registros en productos_historico.")

if __name__ == "__main__":
    restore_database()
