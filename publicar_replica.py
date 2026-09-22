#!/usr/bin/env python3
"""
Publica a mano la RÉPLICA de consulta (db/suite_data_replica.db) a partir de la maestra (db/suite_data_maestra.db).

Normalmente no hace falta: main.py la publica al final de cada corrida y la suite la publica sola
cuando detecta cambios. Úselo si la réplica no se pudo reemplazar porque alguien la tenía abierta:
    python publicar_replica.py
"""
import sys

from core.replica import publicar_replica

if __name__ == "__main__":
    try:
        print(f"[OK] Réplica publicada en {publicar_replica()}")
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
