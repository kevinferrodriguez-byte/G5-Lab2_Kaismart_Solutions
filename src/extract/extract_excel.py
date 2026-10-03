"""EXTRACCIÓN - Fuente 2: sistema logístico (archivo Excel `kaismart_eventos_logisticos.xlsx`).
"""
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def extraer_excel(ruta: str | Path, hoja: str | int = 0) -> pd.DataFrame:
    """Lee una hoja de un archivo .xlsx y la devuelve como DataFrame."""
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {ruta}")

    df = pd.read_excel(ruta, sheet_name=hoja, engine="openpyxl")
    logger.info("Extracción Excel: '%s' -> %s filas x %s columnas", ruta.name, *df.shape)
    return df
