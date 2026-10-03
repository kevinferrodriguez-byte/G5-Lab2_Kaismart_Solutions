import pandas as pd
import pytest

from src.config import cargar_config, ruta_absoluta

config = cargar_config()
SILVER = ruta_absoluta(config["rutas"]["silver"])
GOLD = ruta_absoluta(config["rutas"]["gold"])


def leer(ruta):
    if not ruta.exists():
        pytest.skip(f"Falta {ruta.name}: ejecute primero python main.py")
    return pd.read_csv(ruta)


def test_ventas_silver_sin_duplicados_ni_nulos_inesperados():
    df = leer(SILVER / "ventas_silver.csv")
    assert df.duplicated().sum() == 0
    assert df["id_venta"].is_unique and df["pedido_id"].is_unique
    # calificacion_cliente es la única variable que conserva nulos a propósito
    con_nulos = set(df.columns[df.isna().any()])
    assert con_nulos <= {"calificacion_cliente"}


def test_ventas_silver_categorias_estandarizadas():
    df = leer(SILVER / "ventas_silver.csv")
    for col in ["ciudad", "canal", "categoria", "medio_pago"]:
        assert (df[col] == df[col].str.upper().str.strip()).all()


def test_logistica_silver_sin_duplicados_y_nulos_solo_validos():
    df = leer(SILVER / "logistica_silver.csv")
    assert df.duplicated().sum() == 0
    assert df["evento_id"].is_unique
    for col in ["centro_logistico", "ciudad_destino", "transportadora", "incidencia", "fecha_evento"]:
        assert df[col].notna().all(), col
    # tiempo_etapa_horas solo puede ser nulo en la primera etapa
    assert (df.loc[df["tiempo_etapa_horas"].isna(), "estado_evento"] == "PEDIDO RECIBIDO").all()


def test_gold_una_fila_por_pedido():
    gold = leer(GOLD / "gold_pedidos.csv")
    ventas = leer(SILVER / "ventas_silver.csv")
    assert gold["pedido_id"].is_unique
    assert len(gold) == len(ventas)  # la unión no duplicó ni perdió ventas
