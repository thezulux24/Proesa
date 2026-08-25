import argparse
import os
import sys
import time
import traceback

# Import modules
from core import DataSuiteDB, Notifier, database
from export_mdm import export_mdm

# Import Scrapers desde el paquete scrapers/
from scrapers import (
    ExitoScraper,
    CarullaScraper,
    JumboScraper,
    D1Scraper,
    CanaveralScraper,
    OlimpicaScraper,
    MakroScraper,
    RappiScraper
)

def run_single_scraper(store_key, db):
    """
    Ejecuta un scraper individual y guarda los resultados en la base de datos SQLite.
    Retorna la cantidad de productos insertados/actualizados.
    """
    key = store_key.lower().strip()
    
    if key in ["exito", "éxito"]:
        exito = ExitoScraper(output_file="data/exito_historico.csv")
        facets = [{"key": "category-1", "value": "vinos-y-licores"}]
        all_exito = exito.fetch_products_for_facets(facets, "Vinos y Licores")
        return db.insert_products("Exito", all_exito)

    elif key == "carulla":
        carulla = CarullaScraper(output_file="data/carulla_historico.csv")
        query_licores = {
            "term": "",
            "selectedFacets": [{"key": "category-1", "value": "vinos-y-licores"}]
        }
        all_carulla = carulla.fetch_products(query_licores, "Vinos y Licores", "Alcohol")
        return db.insert_products("Carulla", all_carulla)

    elif key == "jumbo":
        jumbo = JumboScraper(output_file="data/jumbo_historico.csv")
        licores_path = "/supermercado/vinos-y-licores"
        tabacos_path = "/supermercado/cigarrillos-y-tabacos"
        all_jumbo = jumbo.fetch_products(licores_path, "Vinos y Licores", "Alcohol")
        tabaco_products = jumbo.fetch_products(tabacos_path, "Cigarrillos y Tabacos", "Tabaco")
        if tabaco_products:
            all_jumbo.extend(tabaco_products)
        return db.insert_products("Jumbo", all_jumbo)

    elif key == "d1":
        d1 = D1Scraper(output_file="data/d1_historico.csv")
        all_d1 = d1.fetch_products()
        return db.insert_products("D1", all_d1)

    elif key in ["canaveral", "cañaveral"]:
        canaveral = CanaveralScraper(output_file="data/canaveral_historico.csv")
        licores_url = "https://www.domicilioscanaveral.com/ca/licores/03"
        p1 = canaveral.fetch_products(licores_url, "Licores", "Alcohol", max_pages=20)
        return db.insert_products("Canaveral", p1)

    elif key in ["olimpica", "olímpica"]:
        olimpica = OlimpicaScraper(output_file="data/olimpica_historico.csv")
        olimpica_paths = [
            ("/supermercado/licores", "Vinos y Licores"),
            ("/supermercado/cigarrillos-y-vaporizadores", "Cigarrillos y Vaporizadores")
        ]
        all_olimpica = []
        for path, name in olimpica_paths:
            all_olimpica.extend(olimpica.fetch_products(path, name))
        return db.insert_products("Olimpica", all_olimpica)

    elif key == "makro":
        makro = MakroScraper(output_file="data/makro_historico.csv")
        makro_url = "https://tienda.makro.com.co/ca/bebidas/CP_03?categories=Cervezas%2C+Vinos+y+Licores"
        all_makro = makro.fetch_products(makro_url, max_pages=15)
        return db.insert_products("Makro", all_makro)

    elif key == "rappi":
        rappi = RappiScraper(output_file="data/rappi_historico.csv")
        all_rappi = rappi.fetch_products()
        return db.insert_products("Rappi", all_rappi)

    else:
        raise ValueError(f"Comercio no reconocido: {store_key}")

def main():
    parser = argparse.ArgumentParser(description="Orquestador de Scrapers, ETL y Suite Data PROESA")
    parser.add_argument(
        "--comercio",
        default="todos",
        help="Comercio específico a extraer (exito, carulla, jumbo, d1, canaveral, olimpica, makro, rappi, todos)"
    )
    parser.add_argument(
        "--skip-ai",
        action="store_true",
        help="Omitir etapas de matching y deduplicación con IA (DeepSeek)"
    )
    parser.add_argument(
        "--with-invima",
        action="store_true",
        default=False,
        help="Ejecutar asignación de registros sanitarios INVIMA con IA (desactivado por defecto)"
    )
    parser.add_argument(
        "--rondas",
        type=int,
        default=3,
        help="Número de rondas de scrapeo a ejecutar (por defecto: 3)"
    )
    args = parser.parse_args()

    target = args.comercio.lower().strip()
    total_rondas = max(1, args.rondas)
    print("=" * 75)
    print(f" PROESA - SUITE DATA SCRAPING & ANALYTICS ")
    print(f" Objetivo: {target.upper()} | Rondas programadas: {total_rondas} ")
    print("=" * 75)
    
    # Inicializar Base de Datos y Notificador
    db = DataSuiteDB()
    notifier = Notifier()
    
    try:
        db.init_db()
    except Exception as e:
        print(f"Error fatal inicializando la BD: {e}")
        notifier.enviar_reporte_ejecucion({}, {"Base de Datos": f"Error de inicializacion: {e}"})
        sys.exit(1)
        
    stats = {}
    errores = {}
    
    # Determinar comercios a procesar
    ALL_STORES = ["Exito", "Carulla", "Jumbo", "D1", "Canaveral", "Olimpica", "Makro", "Rappi"]
    if target in ["todos", "all"]:
        stores_to_run = ALL_STORES
    else:
        matched = [s for s in ALL_STORES if s.lower() == target or (target in ["cañaveral", "canaveral"] and s == "Canaveral") or (target in ["éxito", "exito"] and s == "Exito") or (target in ["olímpica", "olimpica"] and s == "Olimpica")]
        stores_to_run = matched if matched else [target.capitalize()]

    # =========================================================================
    # FASE 1: RONDA DE 3 SCRAPEOS CON TOLERANCIA A FALLOS Y REINTENTOS
    # =========================================================================
    print(f"\n[FASE 1] INICIANDO RONDA DE {total_rondas} PASADAS DE EXTRACCIÓN...")
    
    for round_num in range(1, total_rondas + 1):
        print(f"\n>>> INICIANDO RONDA {round_num}/{total_rondas} DE SCRAPEO <<<")
        
        for store in stores_to_run:
            # Regla estricta: Rappi ejecuta solo 1 pasada completa por su amplia cobertura multizona (Bogotá 6 zonas)
            if store.lower() == "rappi" and round_num > 1:
                print(f"  [RONDA {round_num}] {store}: Omitido (Rappi configurado para 1 sola pasada).")
                continue

            print(f"  [RONDA {round_num}] Ejecutando Scraper {store}...")
            try:
                inserted = run_single_scraper(store, db)
                if inserted > 0:
                    stats[store] = inserted
                    if store in errores:
                        del errores[store]  # Limpiar error previo si tuvo éxito en reintento
                    print(f"  [RONDA {round_num}] [OK] {store}: {inserted:,} productos insertados/actualizados.")
                else:
                    msg = f"Fallo silencioso en Ronda {round_num}: Se extrajeron 0 productos."
                    print(f"  [RONDA {round_num}] [ALERTA] {store}: {msg}")
                    if store not in stats or stats[store] == 0:
                        errores[store] = msg
            except Exception as e:
                err_msg = f"Error en Ronda {round_num}: {str(e)}"
                print(f"  [RONDA {round_num}] [ERROR] {store}: {err_msg}")
                traceback.print_exc()
                if store not in stats or stats[store] == 0:
                    errores[store] = err_msg

            # Pausa breve de cortesía entre comercios
            time.sleep(1.5)

    print(f"\n[FASE 1 COMPLETADA] Extracción finalizada. Resultados por tienda: {stats}")

    # =========================================================================
    # FASE 2: EJECUCIÓN DEL ETL DE NORMALIZACIÓN INICIAL
    # =========================================================================
    print("\n" + "=" * 75)
    print("[FASE 2] EJECUTANDO ETL DE NORMALIZACIÓN (CONSOLIDACIÓN DE MAPEOS)")
    print("=" * 75)
    try:
        database.run_normalization_etl()
        print("[OK] ETL de normalización completado. Catálogo conocido sincronizado.")
    except Exception as e:
        err_msg = f"Error en ETL de Normalización: {str(e)}"
        print(f"[ERROR] {err_msg}")
        errores["ETL_Inicial"] = err_msg
        traceback.print_exc()

    # =========================================================================
    # FASE 3: INTELIGENCIA ARTIFICIAL (SIEMPRE VA AL FINAL)
    # =========================================================================
    if not args.skip_ai:
        print("\n" + "=" * 75)
        print("[FASE 3] PROCESAMIENTO DE INTELIGENCIA ARTIFICIAL (AL FINAL DEL FLUJO)")
        print("=" * 75)

        # 3.1 Matching MDM Automatizado con IA (LINK / CREATE / DISCARD Falsos Positivos)
        print("\n--- 3.1 Clasificación y Vinculación MDM con DeepSeek AI ---")
        try:
            from core.mdm_ai_matcher import run_auto_mdm_matching
            ai_stats = run_auto_mdm_matching(workers=5)
            if ai_stats and sum(ai_stats.values()) > 0:
                stats["MDM_AI_Matcher"] = f"Vinculados: {ai_stats.get('LINK', 0):,} | Creados: {ai_stats.get('CREATE', 0):,} | Descartados: {ai_stats.get('DISCARD', 0):,}"
                print(f"[OK] MDM AI Matcher completado: {stats['MDM_AI_Matcher']}")
        except Exception as e:
            err_msg = f"Error en MDM AI Matcher: {str(e)}"
            print(f"[ERROR] {err_msg}")
            errores["MDM_AI_Matcher"] = err_msg
            traceback.print_exc()

        # 3.2 Deduplicación y Fusión de Maestros MDM con IA
        print("\n--- 3.2 Deduplicación y Fusión de Catálogo Maestro con IA ---")
        try:
            from deduplicate_mdm_deepseek import run_mdm_deduplication
            dedup_merges = run_mdm_deduplication(workers=5)
            stats["MDM_Deduplication"] = "Catalogo Maestro consolidado sin duplicados"
            print("[OK] Deduplicación MDM completada exitosamente.")
        except Exception as e:
            err_msg = f"Error en Deduplicación MDM: {str(e)}"
            print(f"[ERROR] {err_msg}")
            errores["MDM_Deduplication"] = err_msg
            traceback.print_exc()

        # 3.3 Asignación de Registros Sanitarios INVIMA con IA (Opcional)
        if args.with_invima:
            print("\n--- 3.3 Asignación de Registros Sanitarios INVIMA con IA ---")
            try:
                from core.invima_ai_matcher import run_auto_invima_matching
                invima_stats = run_auto_invima_matching(workers=3)
                if invima_stats and sum(invima_stats.values()) > 0:
                    stats["INVIMA_AI_Matcher"] = f"Registros Asignados: {invima_stats.get('LINK_INVIMA', 0):,} | Dejados en Espera: {invima_stats.get('LEAVE', 0):,}"
                    print(f"[OK] INVIMA AI Matcher completado: {stats['INVIMA_AI_Matcher']}")
            except Exception as e:
                err_msg = f"Error en INVIMA AI Matcher: {str(e)}"
                print(f"[ERROR] {err_msg}")
                errores["INVIMA_AI_Matcher"] = err_msg
                traceback.print_exc()
        else:
            print("\n--- 3.3 Asignación INVIMA IA omitida (desactivada por defecto) ---")

        # 3.4 ETL Final y Exportación de Respaldo Portable
        print("\n--- 3.4 Sincronización Final y Exportación de Respaldo MDM ---")
        try:
            database.run_normalization_etl()
            export_mdm()
            print("[OK] data/mdm_export.json sincronizado y actualizado.")
        except Exception as e:
            err_msg = f"Error en Exportación Final MDM: {str(e)}"
            print(f"[ERROR] {err_msg}")
            errores["ETL_Final"] = err_msg
            traceback.print_exc()
    else:
        print("\n[FASE 3 OMITIDA] Matching y deduplicación con IA omitidos (--skip-ai).")

    # =========================================================================
    # FASE 4: ENVÍO DE REPORTE POR CORREO ELECTRÓNICO (SIN EMOJIS)
    # =========================================================================
    print("\n" + "=" * 75)
    print("[FASE 4] GENERACIÓN Y ENVÍO DE REPORTE FORMAL POR CORREO (RESEND)")
    print("=" * 75)
    
    try:
        # Obtener lista de falsos positivos descartados recientes
        descartados_recientes = database.get_recent_discarded_products(limit=30)
        notifier.enviar_reporte_ejecucion(stats, errores, descartados=descartados_recientes)
        print("[OK] Notificación por correo enviada exitosamente.")
    except Exception as e:
        print(f"[ERROR] No se pudo enviar el correo de notificación: {e}")
        traceback.print_exc()

    print("\n" + "=" * 75)
    print(" EJECUCIÓN COMPLETA FINALIZADA CON ÉXITO ")
    print("=" * 75)
    print("Estadísticas Finales:", stats)
    if errores:
        print("Alertas / Errores Registrados:", errores)

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    main()
