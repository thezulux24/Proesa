"""
Base MAESTRA, RÉPLICA de consulta y BACKUPS.

Todo vive en la carpeta db/ del proyecto:
    db/suite_data_maestra.db   -> la modifican SOLO el scraping (main.py) y la suite (suite_app.py)
    db/suite_data_replica.db   -> copia de solo lectura que abren los usuarios desde su gestor
    db/backups/                -> copias fechadas de la maestra (se conservan las últimas N)

Cada vez que la maestra cambia, se vuelve a publicar la réplica:
    - main.py la publica al final de cada corrida.
    - la suite la publica sola cuando detecta cambios (y al cerrarse).
"""
import datetime
import glob
import os
import sqlite3
import stat

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(PROJECT_DIR, "db")
MASTER_DB = os.path.join(DB_DIR, "suite_data_maestra.db")
REPLICA_DB = os.path.join(DB_DIR, "suite_data_replica.db")
BACKUP_DIR = os.path.join(DB_DIR, "backups")
BACKUPS_A_CONSERVAR = 7


def _copiar_maestra(destino):
    """Copia consistente de la maestra (sirve aunque la suite o el scraping la tengan abierta)."""
    tmp = f"{destino}.{os.getpid()}.tmp"
    if os.path.exists(tmp):
        os.remove(tmp)
    conn = sqlite3.connect(MASTER_DB, timeout=60.0)
    try:
        conn.execute("VACUUM INTO ?", (tmp,))
    finally:
        conn.close()
    return tmp


def firma_maestra():
    """Cambia cada vez que alguien escribe en la maestra (archivo principal o su -wal)."""
    firma = []
    for ruta in (MASTER_DB, MASTER_DB + "-wal"):
        try:
            st = os.stat(ruta)
            firma.append((st.st_mtime_ns, st.st_size))
        except FileNotFoundError:
            firma.append(None)
    return tuple(firma)


def publicar_replica():
    """
    Regenera db/suite_data_replica.db a partir de la maestra.
    Si un usuario tiene la réplica abierta en Windows, lanza PermissionError y queda la versión anterior.
    """
    if not os.path.exists(MASTER_DB):
        raise FileNotFoundError(f"No existe la base maestra: {MASTER_DB}")

    tmp = _copiar_maestra(REPLICA_DB)
    try:
        # Sin archivos -wal/-shm: los gestores la abren como un archivo simple.
        conn = sqlite3.connect(tmp)
        try:
            conn.execute("PRAGMA journal_mode=DELETE")
        finally:
            conn.close()
        os.chmod(tmp, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)

        # En Windows no se puede reemplazar un archivo marcado como solo lectura.
        if os.path.exists(REPLICA_DB):
            os.chmod(REPLICA_DB, stat.S_IREAD | stat.S_IWRITE)
        try:
            os.replace(tmp, REPLICA_DB)
        except PermissionError:
            if os.path.exists(REPLICA_DB):
                os.chmod(REPLICA_DB, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
            raise PermissionError(
                "La réplica está abierta en algún gestor y no se pudo reemplazar; sigue la versión anterior. "
                "Cierre el gestor y ejecute: python publicar_replica.py"
            )
    finally:
        if os.path.exists(tmp):
            os.chmod(tmp, stat.S_IREAD | stat.S_IWRITE)
            os.remove(tmp)
    return REPLICA_DB


def hacer_backup(solo_si_no_hay_hoy=False):
    """
    Guarda una copia fechada de la maestra en db/backups/ y borra las más viejas
    (se conservan las últimas BACKUPS_A_CONSERVAR). Retorna la ruta, o None si se omitió.
    """
    if not os.path.exists(MASTER_DB):
        return None
    os.makedirs(BACKUP_DIR, exist_ok=True)

    hoy = datetime.date.today().strftime("%Y-%m-%d")
    if solo_si_no_hay_hoy and glob.glob(os.path.join(BACKUP_DIR, f"suite_data_maestra_{hoy}_*.db")):
        return None

    marca = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    destino = os.path.join(BACKUP_DIR, f"suite_data_maestra_{marca}.db")
    tmp = _copiar_maestra(destino)
    os.replace(tmp, destino)

    backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "suite_data_maestra_*.db")))
    for viejo in backups[:-BACKUPS_A_CONSERVAR]:
        os.remove(viejo)
    return destino
