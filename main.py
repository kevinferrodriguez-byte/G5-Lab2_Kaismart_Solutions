"""Punto de entrada del ETL de Kaismart Solutions S.A.S.

Uso:
    python main.py              -> ejecuta el pipeline una sola vez
    python main.py --programar  -> Orquestador con la librería schedule
"""
import argparse
import logging
import sys
import time

import schedule

from src.config import cargar_config, ruta_absoluta
from src.logger import configurar_logging
from src.pipeline import ejecutar_pipeline

logger = logging.getLogger("orquestador")


def tarea_etl(config: dict) -> None:
    """Envuelve el pipeline para que un error no detenga al orquestador.
    """
    try:
        ejecutar_pipeline(config)
    except Exception:
        logger.exception("La ejecución del pipeline falló; se reintentará en la próxima programación")


def iniciar_orquestador(config: dict) -> None:
    """PARTE 8: programa el pipeline cada N minutos con la librería schedule."""
    parametros = config["orquestador"]
    minutos = parametros["intervalo_minutos"]

    schedule.every(minutos).minutes.do(tarea_etl, config=config)
    # Alternativa para producción: schedule.every().day.at("06:00").do(tarea_etl, config=config)
    logger.info("Orquestador iniciado: pipeline cada %s minuto(s). Ctrl+C para detener.", minutos)

    if parametros.get("ejecutar_al_iniciar", True):
        schedule.run_all()  # primera ejecución inmediata

    try:
        while True:
            schedule.run_pending()  # ejecuta las tareas cuya hora ya llegó
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Orquestador detenido por el usuario.")


def main() -> None:
    # Tildes correctas en la consola de Windows (el log se escribe en stderr)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="ETL Kaismart Solutions S.A.S. (Medallion)")
    parser.add_argument("--programar", action="store_true", help="Ejecutar con el orquestador (schedule)")
    args = parser.parse_args()

    config = cargar_config()
    configurar_logging(ruta_absoluta(config["rutas"]["log"]))
    logger.info("Autores: %s", ", ".join(config["proyecto"]["autores"]))

    if args.programar:
        iniciar_orquestador(config)
    else:
        ejecutar_pipeline(config)


if __name__ == "__main__":
    main()
