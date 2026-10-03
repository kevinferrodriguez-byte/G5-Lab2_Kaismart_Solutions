"""Configuración del registro log del pipeline: consola + archivo logs/etl.log."""
import logging
from pathlib import Path


def configurar_logging(ruta_log: str | Path) -> None:
    ruta_log = Path(ruta_log)
    ruta_log.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.FileHandler(ruta_log, encoding="utf-8"), logging.StreamHandler()],
        force=True,
    )
