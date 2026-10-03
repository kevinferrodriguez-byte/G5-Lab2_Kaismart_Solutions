"""SILVER - Limpieza de df_ventas (fuente MySQL) -> df_ventas_transformado.
"""
import numpy as np
import pandas as pd

from src.transform.utils_limpieza import Bitacora, estandarizar_texto

COLUMNAS_MONETARIAS = ["precio_unitario", "valor_bruto", "valor_descuento", "valor_neto"]
COLUMNAS_CATEGORICAS = ["ciudad", "canal", "categoria", "producto", "medio_pago"]
COLUMNAS_IDENTIFICADORES = ["pedido_id", "id_cliente", "id_tienda"]
CANAL_TIENDA_FISICA = "TIENDA FÍSICA"


def eliminar_duplicados(df: pd.DataFrame, bitacora: Bitacora) -> pd.DataFrame:
    """Elimina filas idénticas y luego repeticiones de id_venta y pedido_id."""
    antes = len(df)
    df = df.drop_duplicates()
    bitacora.registrar("Duplicados", "Eliminar filas completamente duplicadas", antes - len(df))

    for identificador in ["id_venta", "pedido_id"]:
        antes = len(df)
        df = df.drop_duplicates(subset=identificador, keep="first")
        bitacora.registrar("Duplicados", f"Conservar un solo registro por {identificador}", antes - len(df))
    return df


def convertir_tipos(df: pd.DataFrame, bitacora: Bitacora) -> pd.DataFrame:
    """Asigna a cada variable el tipo coherente con su significado."""
    df["fecha_venta"] = pd.to_datetime(df["fecha_venta"], errors="coerce")

    # Decimal (object) -> float64: permite sumar, promediar y usar describe().
    for col in COLUMNAS_MONETARIAS + ["descuento_pct"]:
        df[col] = pd.to_numeric(df[col].astype(float), errors="coerce").round(2)

    # Int64 (con mayúscula) es el entero de pandas que admite nulos.
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").astype("Int64")
    df["calificacion_cliente"] = pd.to_numeric(df["calificacion_cliente"], errors="coerce").astype("Int64")

    bitacora.registrar(
        "Tipos de datos",
        "Monetarias y descuento_pct de Decimal(object) a float; cantidad y calificacion_cliente a Int64; fecha_venta a datetime",
        len(df),
    )
    return df


def estandarizar_categorias(df: pd.DataFrame, bitacora: Bitacora) -> pd.DataFrame:
    """Categorías e identificadores en mayúsculas y sin espacios sobrantes."""
    for col in COLUMNAS_CATEGORICAS + COLUMNAS_IDENTIFICADORES:
        df[col] = estandarizar_texto(df[col])
    bitacora.registrar(
        "Estandarización",
        f"Texto en MAYÚSCULAS y sin espacios extra en {COLUMNAS_CATEGORICAS + COLUMNAS_IDENTIFICADORES}",
        len(df),
    )
    return df


def tratar_nulos(df: pd.DataFrame, bitacora: Bitacora) -> pd.DataFrame:
    """Imputación justificada variable por variable (no automática)."""
    # --- id_tienda ---------------------------------------------------------
    # Una venta por página web o app NO ocurre en una tienda: el nulo significa
    # "no aplica", no "dato perdido". Por eso no se usa la moda (inventaría una
    # tienda) sino la etiqueta 'NO APLICA'. Si una venta de tienda física no
    # tuviera tienda, eso sí sería un faltante real -> 'NO INFORMADO'.
    sin_tienda = df["id_tienda"].isna()
    es_tienda_fisica = df["canal"] == CANAL_TIENDA_FISICA

    df.loc[sin_tienda & ~es_tienda_fisica, "id_tienda"] = "NO APLICA"
    bitacora.registrar("Nulos id_tienda", "Canal digital sin tienda -> 'NO APLICA'",
                       (sin_tienda & ~es_tienda_fisica).sum())

    df.loc[sin_tienda & es_tienda_fisica, "id_tienda"] = "NO INFORMADO"
    bitacora.registrar("Nulos id_tienda", "Tienda física sin id_tienda -> 'NO INFORMADO'",
                       (sin_tienda & es_tienda_fisica).sum())

    # --- calificacion_cliente ---------------------------------------------
    # El nulo tiene interpretación válida: el cliente no calificó. Imputar con
    # media/moda inventaría opiniones y sesgaría la satisfacción. Se MANTIENE el
    # nulo y se crea una bandera para poder filtrar o contar.
    df["tiene_calificacion"] = df["calificacion_cliente"].notna()
    bitacora.registrar("Nulos calificacion_cliente",
                       "Se mantiene el nulo (cliente no calificó) y se crea 'tiene_calificacion'",
                       (~df["tiene_calificacion"]).sum())
    return df


def validar_reglas_negocio(df: pd.DataFrame, bitacora: Bitacora) -> pd.DataFrame:
    """Verifica la coherencia de los montos (tolerancia de 1 peso por redondeo)."""
    reglas = {
        "valor_bruto = cantidad x precio_unitario": df["cantidad"].astype(float) * df["precio_unitario"],
        "valor_descuento = valor_bruto x descuento_pct / 100": df["valor_bruto"] * df["descuento_pct"] / 100,
        "valor_neto = valor_bruto - valor_descuento": df["valor_bruto"] - df["valor_descuento"],
    }
    columnas = ["valor_bruto", "valor_descuento", "valor_neto"]
    for (regla, esperado), col in zip(reglas.items(), columnas):
        inconsistentes = ~np.isclose(df[col], esperado, atol=1)
        bitacora.registrar("Validación", f"Registros que incumplen: {regla}", inconsistentes.sum())
    return df


def crear_variables_derivadas(df: pd.DataFrame, bitacora: Bitacora) -> pd.DataFrame:
    """Variables de apoyo para el análisis temporal."""
    df["mes_venta"] = df["fecha_venta"].dt.to_period("M").astype(str)
    bitacora.registrar("Variables derivadas", "Se crea 'mes_venta' (AAAA-MM)", len(df))
    return df


def limpiar_ventas(df_ventas: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aplica todos los pasos de limpieza. Devuelve (df_ventas_transformado, bitácora).

    Trabaja sobre una copia: df_ventas (Bronze) queda intacto.
    """
    bitacora = Bitacora("ventas")
    df = df_ventas.copy()

    df = eliminar_duplicados(df, bitacora)
    df = convertir_tipos(df, bitacora)
    df = estandarizar_categorias(df, bitacora)
    df = tratar_nulos(df, bitacora)
    df = validar_reglas_negocio(df, bitacora)
    df = crear_variables_derivadas(df, bitacora)

    return df.reset_index(drop=True), bitacora.como_dataframe()
