"""Pruebas de extracción. Ejecutar desde la raíz: python -m pytest -v"""
import pytest

from src.config import cargar_config, ruta_absoluta
from src.extract.extract_excel import extraer_excel

COLUMNAS_LOGISTICA = [
    "evento_id", "pedido_id", "fecha_evento", "estado_evento", "centro_logistico",
    "ciudad_destino", "transportadora", "numero_guia", "fecha_prometida_entrega",
    "tiempo_etapa_horas", "costo_envio", "incidencia", "observacion",
]


def test_excel_tiene_50000_registros_y_columnas_esperadas():
    config = cargar_config()
    ruta = ruta_absoluta(config["fuentes"]["excel"]["ruta"])
    if not ruta.exists():
        pytest.skip("No está el archivo Excel en data/")
    df = extraer_excel(ruta, config["fuentes"]["excel"]["hoja"])
    assert df.shape == (50000, 13)
    assert list(df.columns) == COLUMNAS_LOGISTICA


def test_excel_inexistente_lanza_error():
    with pytest.raises(FileNotFoundError):
        extraer_excel("data/no_existe.xlsx")


@pytest.mark.red
def test_mysql_ventas_tiene_5000_registros():
    """Requiere conexión a internet / acceso a la BD del laboratorio."""
    from src.extract.extract_database import extraer_tabla
    try:
        df = extraer_tabla("ventas")
    except Exception as error:  # sin red o BD caída
        pytest.skip(f"BD no disponible: {error}")
    assert len(df) == 5000
    assert {"id_venta", "pedido_id", "valor_neto"}.issubset(df.columns)
