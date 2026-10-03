"""Pruebas unitarias de las reglas de limpieza con datos pequeños construidos a mano."""
from decimal import Decimal

import numpy as np
import pandas as pd

from src.transform.clean_database import limpiar_ventas
from src.transform.clean_excel import limpiar_logistica
from src.transform.utils_limpieza import estandarizar_texto


def crear_ventas() -> pd.DataFrame:
    return pd.DataFrame({
        "id_venta": [1, 2, 2],
        "pedido_id": ["PED1", "PED2", "PED2"],
        "fecha_venta": pd.to_datetime(["2026-01-01 10:00:00", "2026-01-02 11:00:00", "2026-01-02 11:00:00"]),
        "id_cliente": ["CLI1", "CLI2", "CLI2"],
        "ciudad": [" Cali", "Bogotá D.C.", "Bogotá D.C."],
        "canal": ["Página web", "Tienda física", "Tienda física"],
        "id_tienda": [None, "BOG-01", "BOG-01"],
        "categoria": ["Hogar", "Oficina", "Oficina"],
        "producto": ["Arrocera", "Silla", "Silla"],
        "cantidad": [2, 1, 1],
        "precio_unitario": [Decimal("100.00"), Decimal("50.00"), Decimal("50.00")],
        "descuento_pct": [Decimal("10.00"), Decimal("0.00"), Decimal("0.00")],
        "valor_bruto": [Decimal("200.00"), Decimal("50.00"), Decimal("50.00")],
        "valor_descuento": [Decimal("20.00"), Decimal("0.00"), Decimal("0.00")],
        "valor_neto": [Decimal("180.00"), Decimal("50.00"), Decimal("50.00")],
        "medio_pago": ["PSE", "Efectivo", "Efectivo"],
        "calificacion_cliente": [np.nan, 5.0, 5.0],
    })


def crear_logistica() -> pd.DataFrame:
    """Un pedido con 3 eventos + una fila duplicada + nulos a imputar."""
    filas = [
        # evento, pedido, fecha, estado, centro, ciudad, transp, guia, prometida, horas, costo, incid, obs
        (1, "PED1", "2026-01-01 10:00:00", "Pedido recibido", "CEDI Cali", "Cali", None, None, "2026-01-03 10:00:00", None, 8900, None, None),
        (2, "PED1", None, "Despachado", None, None, "TCC", "KMS1", None, 2.0, 8900, None, None),
        (3, "PED1", "2026-01-01 15:00:00", "En tránsito", "CEDI Cali", "Cali", None, "KMS1", "2026-01-03 10:00:00", 3.0, 8900, "Cliente ausente", "Obs"),
        (3, "PED1", "2026-01-01 15:00:00", "En tránsito", "CEDI Cali", "Cali", None, "KMS1", "2026-01-03 10:00:00", 3.0, 8900, "Cliente ausente", "Obs"),
    ]
    columnas = ["evento_id", "pedido_id", "fecha_evento", "estado_evento", "centro_logistico",
                "ciudad_destino", "transportadora", "numero_guia", "fecha_prometida_entrega",
                "tiempo_etapa_horas", "costo_envio", "incidencia", "observacion"]
    return pd.DataFrame(filas, columns=columnas)


def test_estandarizar_texto():
    serie = pd.Series(["  cali ", "CALI", "Cali  Valle"])
    assert estandarizar_texto(serie).tolist() == ["CALI", "CALI", "CALI VALLE"]


def test_ventas_elimina_duplicados_y_convierte_tipos():
    df, _ = limpiar_ventas(crear_ventas())
    assert len(df) == 2
    assert df["valor_neto"].dtype == "float64"
    assert df["ciudad"].tolist() == ["CALI", "BOGOTÁ D.C."]


def test_ventas_id_tienda_no_aplica_en_canal_digital_y_calificacion_se_mantiene_nula():
    df, _ = limpiar_ventas(crear_ventas())
    assert df.loc[0, "id_tienda"] == "NO APLICA"
    assert df.loc[1, "id_tienda"] == "BOG-01"
    assert pd.isna(df.loc[0, "calificacion_cliente"])
    assert not df.loc[0, "tiene_calificacion"]


def test_ventas_no_modifica_el_dataframe_original():
    original = crear_ventas()
    copia = original.copy()
    limpiar_ventas(original)
    pd.testing.assert_frame_equal(original, copia)


def test_logistica_duplicados_y_atributos_del_pedido():
    df, _ = limpiar_logistica(crear_logistica())
    assert len(df) == 3
    assert df["evento_id"].is_unique
    assert (df["centro_logistico"] == "CEDI CALI").all()
    assert (df["ciudad_destino"] == "CALI").all()
    assert df["fecha_prometida_entrega"].notna().all()


def test_logistica_transportadora_segun_etapa():
    df = limpiar_logistica(crear_logistica())[0].set_index("evento_id")
    assert df.loc[1, "transportadora"] == "NO APLICA"   # antes del despacho
    assert pd.isna(df.loc[1, "numero_guia"])              # la guía aún no existe
    assert df.loc[3, "transportadora"] == "TCC"          # recuperada del mismo pedido


def test_logistica_reconstruye_fecha_evento():
    df = limpiar_logistica(crear_logistica())[0].set_index("evento_id")
    # evento 1 (10:00) + 2 horas de la etapa = 12:00
    assert df.loc[2, "fecha_evento"] == pd.Timestamp("2026-01-01 12:00:00")
    assert df.loc[2, "fecha_evento_imputada"]


def test_logistica_nulos_con_significado():
    df = limpiar_logistica(crear_logistica())[0].set_index("evento_id")
    assert pd.isna(df.loc[1, "tiempo_etapa_horas"])       # primera etapa: nulo válido
    assert df.loc[1, "incidencia"] == "SIN INCIDENCIA"
    assert df.loc[3, "tiene_incidencia"]
