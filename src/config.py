
from pathlib import Path

import yaml

# Raíz del proyecto: carpeta que contiene main.py, config/, data/, src/ ...
RAIZ_PROYECTO = Path(__file__).resolve().parents[1]


def cargar_config(ruta: str | Path = RAIZ_PROYECTO / "config" / "config.yaml") -> dict:
    """Lee el archivo YAML de configuración y lo devuelve como diccionario."""
    with open(ruta, encoding="utf-8") as archivo:
        return yaml.safe_load(archivo)


def ruta_absoluta(ruta_relativa: str) -> Path:
    """Convierte una ruta del config (relativa a la raíz) en ruta absoluta."""
    return RAIZ_PROYECTO / ruta_relativa
