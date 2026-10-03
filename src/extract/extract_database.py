"""EXTRACCIÓN - Fuente 1: sistema comercial (MySQL, base de datos `clientes`).

Se usa mysql.connector con un cursor:
se ejecuta la consulta, se leen todas las filas con fetchall() y se arma el
DataFrame con los nombres de columna que entrega cursor.description."""

import logging
import os

import mysql.connector
import pandas as pd
from dotenv import load_dotenv

from src.config import RAIZ_PROYECTO

logger = logging.getLogger(__name__)


def obtener_credenciales() -> dict:
    """Lee las credenciales desde el archivo .env (no quedan escritas en el código)."""
    load_dotenv(RAIZ_PROYECTO / ".env")
    return {
        "host": os.getenv("DB_HOST"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME"),
    }


def extraer_tabla(tabla: str = "ventas") -> pd.DataFrame:
    """Extrae todos los registros de la tabla indicada y devuelve un DataFrame."""
    if not tabla.isidentifier():  # evita inyección SQL por el nombre de la tabla
        raise ValueError(f"Nombre de tabla no válido: {tabla}")

    conexion = mysql.connector.connect(**obtener_credenciales())
    try:
        cursor = conexion.cursor()
        cursor.execute(f"SELECT * FROM {tabla}")
        registros = cursor.fetchall()
        columnas = [descripcion[0] for descripcion in cursor.description]
        cursor.close()
    finally:
        conexion.close()

    df = pd.DataFrame(registros, columns=columnas)
    logger.info("Extracción MySQL: tabla '%s' -> %s filas x %s columnas", tabla, *df.shape)
    return df
