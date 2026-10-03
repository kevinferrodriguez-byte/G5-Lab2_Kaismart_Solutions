"""CARGA - Tablas Gold en una base de datos SQLite local.
"""
import logging
import sqlite3
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def cargar_sqlite(tablas: dict[str, pd.DataFrame], ruta_db: str | Path) -> None:
    """Escribe cada DataFrame como una tabla (se reemplaza en cada ejecución)."""
    ruta_db = Path(ruta_db)
    ruta_db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(ruta_db) as conexion:
        for nombre, df in tablas.items():
            df.to_sql(nombre, conexion, if_exists="replace", index=False)
            logger.info("SQLite: tabla '%s' cargada (%s filas)", nombre, len(df))
