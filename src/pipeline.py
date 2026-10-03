"""Pipeline ETL completo con arquitectura Medallion.

    EXTRACCIÓN            BRONZE                 SILVER                        GOLD
    MySQL.ventas   ->  ventas_bronze.csv  ->  ventas_silver.csv      \
                                                                       -> gold_pedidos + KPIs (CSV y SQLite)
    Excel logística -> logistica_bronze.csv -> logistica_silver.csv  /
"""
import logging
import time

import pandas as pd

from src.config import cargar_config, ruta_absoluta
from src.extract.extract_database import extraer_tabla
from src.extract.extract_excel import extraer_excel
from src.load.load_database import cargar_sqlite
from src.load.load_files import guardar_csv
from src.transform.clean_database import limpiar_ventas
from src.transform.clean_excel import limpiar_logistica
from src.transform.gold_transformations import construir_gold

logger = logging.getLogger(__name__)


def ejecutar_pipeline(config: dict | None = None) -> dict[str, pd.DataFrame]:
    """Ejecuta Extracción -> Bronze -> Silver -> Gold y devuelve los DataFrames."""
    config = config or cargar_config()
    rutas = {capa: ruta_absoluta(config["rutas"][capa]) for capa in ("bronze", "silver", "gold")}
    inicio = time.perf_counter()
    logger.info("===== Inicio del pipeline ETL =====")

    # ---------------- EXTRACCIÓN ----------------
    df_ventas = extraer_tabla(config["fuentes"]["mysql"]["tabla"])
    df_logistica = extraer_excel(ruta_absoluta(config["fuentes"]["excel"]["ruta"]),
                                 config["fuentes"]["excel"]["hoja"])

    # ---------------- BRONZE: datos crudos sin modificar ----------------
    guardar_csv(df_ventas, rutas["bronze"], "ventas_bronze.csv")
    guardar_csv(df_logistica, rutas["bronze"], "logistica_bronze.csv")

    # ---------------- SILVER: limpieza por fuente ----------------
    df_ventas_transformado, bitacora_ventas = limpiar_ventas(df_ventas)
    df_logisitica_transformado, bitacora_logistica = limpiar_logistica(df_logistica)
    bitacora = pd.concat([bitacora_ventas, bitacora_logistica], ignore_index=True)

    guardar_csv(df_ventas_transformado, rutas["silver"], "ventas_silver.csv")
    guardar_csv(df_logisitica_transformado, rutas["silver"], "logistica_silver.csv")
    guardar_csv(bitacora, rutas["silver"], "bitacora_limpieza.csv")

    # ---------------- GOLD: integración y KPIs ----------------
    tablas_gold = construir_gold(df_ventas_transformado, df_logisitica_transformado)
    for nombre, tabla in tablas_gold.items():
        guardar_csv(tabla, rutas["gold"], f"{nombre}.csv")
    cargar_sqlite(tablas_gold, ruta_absoluta(config["gold"]["base_datos_sqlite"]))

    logger.info("===== Pipeline finalizado en %.1f s =====", time.perf_counter() - inicio)
    return {
        "df_ventas": df_ventas,
        "df_logistica": df_logistica,
        "df_ventas_transformado": df_ventas_transformado,
        "df_logisitica_transformado": df_logisitica_transformado,
        "bitacora": bitacora,
        **tablas_gold,
    }
