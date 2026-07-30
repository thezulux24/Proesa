"""
Módulo Unificado de Scrapers (Scrapling HTTP Only)
"""
from .scraper_exito.scraper import ExitoScraper
from .scraper_carulla.scraper import CarullaScraper
from .scraper_jumbo.scraper import JumboScraper
from .scraper_d1.scraper import D1Scraper
from .scraper_canaveral.scraper import CanaveralScraper
from .scraper_olimpica.scraper import OlimpicaScraper
from .scraper_makro.scraper import MakroScraper

__all__ = [
    "ExitoScraper",
    "CarullaScraper",
    "JumboScraper",
    "D1Scraper",
    "CanaveralScraper",
    "OlimpicaScraper",
    "MakroScraper"
]
