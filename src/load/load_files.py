"""CARGA - Escritura de cada capa Medallion en disco (CSV).
"""
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def guardar_csv(df: pd.DataFrame, carpeta: str | Path, nombre_archivo: str) -> Path:
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / nombre_archivo
    df.to_csv(ruta, index=False, encoding="utf-8-sig")
    logger.info("Guardado %s/%s (%s filas)", carpeta.name, ruta.name, len(df))
    return ruta
