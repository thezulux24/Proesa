import os
import sys
import traceback

# Import modules
from database import DataSuiteDB
from notifier import Notifier

# Import Scrapers
from scraper_exito.scraper import ExitoScraper
from scraper_carulla.scraper import CarullaScraper
from scraper_jumbo.scraper import JumboScraper
from scraper_d1.scraper import D1Scraper
from scraper_canaveral.scraper import CanaveralScraper
from scraper_olimpica.scraper import OlimpicaScraper
from scraper_makro.scraper import MakroScraper

def main():
    print("Iniciando Suite Data Universal...")
    
    # Initialize DB & Notifier
    db = DataSuiteDB()
    notifier = Notifier()
    
    # Init tables
    try:
        db.init_db()
    except Exception as e:
        print(f"Error fatal inicializando la BD: {e}")
        # Enviar alerta de falla critica si es posible
        notifier.enviar_reporte_ejecucion({}, {"Base de Datos": f"Error de inicialización: {e}"})
        sys.exit(1)
        
    stats = {}
    errores = {}
    
    # ==========================
    # 1. EXITO
    # ==========================
    print("\n--- Ejecutando Scraper Éxito ---")
    try:
        exito = ExitoScraper(output_file="data/exito_historico.csv")
        # Define categories to scrape
        facets = [{"key": "category-1", "value": "vinos-y-licores"}]
        all_exito = exito.fetch_products_for_facets(facets, "Vinos y Licores")
        
        inserted = db.insert_products("Exito", all_exito)
        if inserted > 0:
            stats["Exito"] = inserted
        else:
            errores["Exito"] = "Fallo silencioso: Se extrajeron 0 productos. Posible cambio en el diseño de la web o bloqueo."
    except Exception as e:
        errores["Exito"] = str(e)
        traceback.print_exc()

    # ==========================
    # 2. CARULLA
    # ==========================
    print("\n--- Ejecutando Scraper Carulla ---")
    try:
        carulla = CarullaScraper(output_file="data/carulla_historico.csv")
        query_licores = {
            "term": "",
            "selectedFacets": [{"key": "category-1", "value": "vinos-y-licores"}]
        }
        all_carulla = carulla.fetch_products(query_licores, "Vinos y Licores", "Alcohol")
        
        inserted = db.insert_products("Carulla", all_carulla)
        if inserted > 0:
            stats["Carulla"] = inserted
        else:
            errores["Carulla"] = "Fallo silencioso: Se extrajeron 0 productos. Posible cambio en el diseño de la web o bloqueo."
    except Exception as e:
        errores["Carulla"] = str(e)
        traceback.print_exc()

    # ==========================
    # 3. JUMBO
    # ==========================
    print("\n--- Ejecutando Scraper Jumbo ---")
    try:
        jumbo = JumboScraper(output_file="data/jumbo_historico.csv")
        licores_path = "/supermercado/vinos-y-licores"
        all_jumbo = jumbo.fetch_products(licores_path, "Vinos y Licores", "Alcohol")
        
        inserted = db.insert_products("Jumbo", all_jumbo)
        if inserted > 0:
            stats["Jumbo"] = inserted
        else:
            errores["Jumbo"] = "Fallo silencioso: Se extrajeron 0 productos. Posible cambio en el diseño de la web o bloqueo."
    except Exception as e:
        errores["Jumbo"] = str(e)
        traceback.print_exc()

    # ==========================
    # 4. D1
    # ==========================
    print("\n--- Ejecutando Scraper D1 ---")
    try:
        d1 = D1Scraper(output_file="data/d1_historico.csv")
        licores_url = "https://domicilios.tiendasd1.com/ca/bebidas/BEBIDAS?categories=Vinos%7E%7ELicores%7E%7ECervezas"
        tabacos_url = "https://domicilios.tiendasd1.com/ca/otros/cigarrillos/OTROS/CIGARRILLOS"
        
        p1 = d1.fetch_products(licores_url, "Vinos y Licores", "Alcohol")
        p2 = d1.fetch_products(tabacos_url, "Cigarrillos y Tabacos", "Tabaco")
        
        all_d1 = p1 + p2
        inserted = db.insert_products("D1", all_d1)
        if inserted > 0:
            stats["D1"] = inserted
        else:
            errores["D1"] = "Fallo silencioso: Se extrajeron 0 productos. Posible cambio en el diseño de la web o bloqueo."
    except Exception as e:
        errores["D1"] = str(e)
        traceback.print_exc()

    # ==========================
    # 5. CAÑAVERAL
    # ==========================
    print("\n--- Ejecutando Scraper Cañaveral ---")
    try:
        canaveral = CanaveralScraper(output_file="data/canaveral_historico.csv")
        licores_url = "https://www.domicilioscanaveral.com/ca/licores/03"
        # Optional: Other URLs if they have tobacco or ultra-processed
        
        p1 = canaveral.fetch_products(licores_url, "Licores", "Alcohol", max_pages=20)
        
        inserted = db.insert_products("Canaveral", p1)
        if inserted > 0:
            stats["Canaveral"] = inserted
        else:
            errores["Canaveral"] = "Fallo silencioso: Se extrajeron 0 productos. Posible cambio en el diseño de la web o bloqueo."
    except Exception as e:
        errores["Canaveral"] = str(e)
        traceback.print_exc()

    # ==========================
    # 6. OLIMPICA
    # ==========================
    print("\n--- Ejecutando Scraper Olimpica ---")
    try:
        olimpica = OlimpicaScraper(output_file="data/olimpica_historico.csv")
        olimpica_paths = [
            ("/supermercado/licores", "Vinos y Licores"),
            ("/supermercado/cigarrillos-y-vaporizadores", "Cigarrillos y Vaporizadores")
        ]
        
        all_olimpica = []
        for path, name in olimpica_paths:
            all_olimpica.extend(olimpica.fetch_products(path, name))
        
        inserted = db.insert_products("Olimpica", all_olimpica)
        if inserted > 0:
            stats["Olimpica"] = inserted
        else:
            errores["Olimpica"] = "Fallo silencioso: Se extrajeron 0 productos. Posible cambio en el diseño de la web o bloqueo."
    except Exception as e:
        errores["Olimpica"] = str(e)
        traceback.print_exc()

    # ==========================
    # 7. MAKRO
    # ==========================
    print("\n--- Ejecutando Scraper Makro ---")
    try:
        makro = MakroScraper(output_file="data/makro_historico.csv")
        makro_url = "https://tienda.makro.com.co/ca/bebidas/CP_03?categories=Cervezas%2C+Vinos+y+Licores"
        
        all_makro = makro.fetch_products(makro_url, max_pages=15)
        
        inserted = db.insert_products("Makro", all_makro)
        if inserted > 0:
            stats["Makro"] = inserted
        else:
            errores["Makro"] = "Fallo silencioso: Se extrajeron 0 productos. Posible cambio en el diseño de la web o bloqueo."
    except Exception as e:
        errores["Makro"] = str(e)
        traceback.print_exc()

    # ==========================
    # FINAL REPORT
    # ==========================
    print("\n--- Finalizando Extracción ---")
    print("Estadísticas:", stats)
    print("Errores:", errores)
    
    # Enviar correo de reporte
    notifier.enviar_reporte_ejecucion(stats, errores)
    print("Proceso finalizado.")

if __name__ == "__main__":
    # Ensure data dir exists for any fallback CSVs
    os.makedirs("data", exist_ok=True)
    main()
