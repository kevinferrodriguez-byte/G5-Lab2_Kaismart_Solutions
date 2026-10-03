"""Utilidades compartidas por las limpiezas de ambas fuentes."""
import logging

import pandas as pd

logger = logging.getLogger(__name__)


def estandarizar_texto(serie: pd.Series) -> pd.Series:
    """Quita espacios sobrantes y convierte a MAYÚSCULAS

    Mayúsculas: evita que 'Cali', 'cali' y 'CALI ' se cuenten como categorías distintas.
    Tildes: se conservan porque son parte del dato original y ambas fuentes las usan igual.
    """
    return serie.str.strip().str.replace(r"\s+", " ", regex=True).str.upper()


class Bitacora:
    """Registro de cada decisión de limpieza y cuántas filas afectó.
    """

    def __init__(self, fuente: str):
        self.fuente = fuente
        self.registros: list[dict] = []

    def registrar(self, paso: str, decision: str, filas_afectadas: int) -> None:
        self.registros.append({
            "fuente": self.fuente,
            "paso": paso,
            "decision": decision,
            "filas_afectadas": int(filas_afectadas),
        })
        logger.info("[%s] %s: %s (filas afectadas: %s)", self.fuente, paso, decision, filas_afectadas)

    def como_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.registros)
