"""SILVER - Limpieza de df_logistica (fuente Excel) -> df_logisitica_transformado.
"""
import logging

import pandas as pd

from src.transform.utils_limpieza import Bitacora, estandarizar_texto

logger = logging.getLogger(__name__)

# Orden lógico del proceso logístico (ya estandarizado en mayúsculas)
ETAPAS = [
    "PEDIDO RECIBIDO", "PAGO APROBADO", "ORDEN ENVIADA A LOGÍSTICA", "EN ALISTAMIENTO",
    "EMPACADO", "LISTO PARA DESPACHO", "DESPACHADO", "EN TRÁNSITO",
    "EN RUTA DE ENTREGA", "ENTREGADO",
]
# A partir del despacho el pedido ya tiene transportadora y número de guía
ETAPAS_CON_TRANSPORTADORA = ETAPAS[ETAPAS.index("DESPACHADO"):]

COLUMNAS_TEXTO = ["pedido_id", "estado_evento", "centro_logistico", "ciudad_destino",
                  "transportadora", "numero_guia", "incidencia"]
COLUMNAS_FECHA = ["fecha_evento", "fecha_prometida_entrega"]
FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"
# Atributos que pertenecen al pedido: son iguales en todos sus eventos
ATRIBUTOS_PEDIDO = ["centro_logistico", "ciudad_destino", "fecha_prometida_entrega"]


def eliminar_duplicados(df: pd.DataFrame, bitacora: Bitacora) -> pd.DataFrame:
    """1) Filas idénticas. 2) evento_id repetido: se conserva la versión más completa."""
    antes = len(df)
    df = df.drop_duplicates()
    bitacora.registrar("Duplicados", "Eliminar filas completamente duplicadas", antes - len(df))

    # Si un evento_id aparece con datos distintos, se queda la fila con MENOS
    # nulos (la más completa) en lugar de la primera que aparezca.
    antes = len(df)
    df = (
        df.assign(_nulos=df.isna().sum(axis=1))
          .sort_values(["evento_id", "_nulos"])
          .drop_duplicates(subset="evento_id", keep="first")
          .drop(columns="_nulos")
    )
    bitacora.registrar("Duplicados", "evento_id repetido: conservar la fila más completa", antes - len(df))
    return df


def convertir_tipos(df: pd.DataFrame, bitacora: Bitacora) -> pd.DataFrame:
    """Fechas de texto a datetime; métricas a numérico."""
    for col in COLUMNAS_FECHA:
        texto_original = df[col]
        df[col] = pd.to_datetime(df[col], format=FORMATO_FECHA, errors="coerce")
        invalidas = (df[col].isna() & texto_original.notna()).sum()
        bitacora.registrar("Tipos de datos", f"{col}: texto -> datetime (valores con formato inválido: {invalidas})", len(df))

    df["tiempo_etapa_horas"] = pd.to_numeric(df["tiempo_etapa_horas"], errors="coerce")
    df["costo_envio"] = pd.to_numeric(df["costo_envio"], errors="coerce").astype("Int64")
    return df


def estandarizar_categorias(df: pd.DataFrame, bitacora: Bitacora) -> pd.DataFrame:
    for col in COLUMNAS_TEXTO:
        df[col] = estandarizar_texto(df[col])
    df["observacion"] = df["observacion"].str.strip()  # texto libre: solo espacios

    desconocidas = ~df["estado_evento"].isin(ETAPAS)
    bitacora.registrar("Estandarización", f"Texto en MAYÚSCULAS en {COLUMNAS_TEXTO}", len(df))
    bitacora.registrar("Validación", "Eventos con estado fuera del catálogo de 10 etapas", desconocidas.sum())

    # Orden lógico de la etapa (1 = Pedido recibido ... 10 = Entregado)
    df["orden_etapa"] = df["estado_evento"].map({etapa: i for i, etapa in enumerate(ETAPAS, start=1)}).astype("Int64")
    return df.sort_values(["pedido_id", "evento_id"]).reset_index(drop=True)


def imputar_atributos_pedido(df: pd.DataFrame, bitacora: Bitacora) -> pd.DataFrame:
    """centro_logistico, ciudad_destino y fecha_prometida_entrega son datos del PEDIDO.

    En el EDA se verificó que cada pedido tiene un único valor para cada uno de
    ellos. Por eso el faltante se copia de los otros eventos del mismo pedido
    """
    for col in ATRIBUTOS_PEDIDO:
        faltantes = df[col].isna()
        df[col] = df[col].fillna(df.groupby("pedido_id")[col].transform("first"))
        bitacora.registrar(f"Nulos {col}", "Recuperado desde otros eventos del mismo pedido",
                           (faltantes & df[col].notna()).sum())

    # Si un pedido tuviera TODOS sus eventos sin el dato, no hay de dónde copiarlo.
    for col in ["centro_logistico", "ciudad_destino"]:
        restantes = df[col].isna()
        df.loc[restantes, col] = "NO INFORMADO"
        bitacora.registrar(f"Nulos {col}", "Sin información en todo el pedido -> 'NO INFORMADO'", restantes.sum())
    return df


def imputar_transportadora_y_guia(df: pd.DataFrame, bitacora: Bitacora) -> pd.DataFrame:
    """Nulos normales vs. nulos problemáticos según la etapa del evento.

    - Antes de DESPACHADO: el pedido aún no se entrega a una transportadora, por
      eso el nulo es NORMAL -> transportadora = 'NO APLICA' y numero_guia se
      MANTIENE nulo (la guía todavía no existe; inventar un código no tiene sentido).
    - Desde DESPACHADO: el dato debería existir -> se recupera de los otros eventos
      post-despacho del mismo pedido (cada pedido tiene una sola transportadora/guía).
    """
    post_despacho = df["estado_evento"].isin(ETAPAS_CON_TRANSPORTADORA)

    for col in ["transportadora", "numero_guia"]:
        valor_del_pedido = df[col].where(post_despacho).groupby(df["pedido_id"]).transform("first")
        faltantes = post_despacho & df[col].isna()
        df.loc[faltantes, col] = valor_del_pedido[faltantes]
        bitacora.registrar(f"Nulos {col}", "Post-despacho: recuperado desde otros eventos del mismo pedido",
                           (faltantes & df[col].notna()).sum())

    pre_despacho_sin_dato = ~post_despacho & df["transportadora"].isna()
    df.loc[pre_despacho_sin_dato, "transportadora"] = "NO APLICA"
    bitacora.registrar("Nulos transportadora", "Pre-despacho (nulo normal) -> 'NO APLICA'", pre_despacho_sin_dato.sum())

    restantes = post_despacho & df["transportadora"].isna()
    df.loc[restantes, "transportadora"] = "NO INFORMADO"
    bitacora.registrar("Nulos transportadora", "Post-despacho sin dato en todo el pedido -> 'NO INFORMADO'", restantes.sum())

    bitacora.registrar("Nulos numero_guia", "Pre-despacho: se MANTIENE nulo (la guía aún no existe)",
                       (~post_despacho & df["numero_guia"].isna()).sum())
    return df


def reconstruir_fecha_evento(df: pd.DataFrame, bitacora: Bitacora) -> pd.DataFrame:
    """Reconstruye fecha_evento faltante usando tiempo_etapa_horas.

    En el EDA se verificó que tiempo_etapa_horas = horas transcurridas desde el
    evento anterior del mismo pedido. Entonces:
        hacia adelante:  fecha = fecha_evento_anterior + tiempo_etapa_horas (propio)
        hacia atrás:     fecha = fecha_evento_siguiente - tiempo_etapa_horas (del siguiente)
    Es una reconstrucción determinística. Se marca con la
    bandera 'fecha_evento_imputada' para que el análisis pueda excluirla.
    """
    por_pedido = df.groupby("pedido_id")
    horas_propias = pd.to_timedelta(df["tiempo_etapa_horas"], unit="h")
    horas_siguiente = pd.to_timedelta(por_pedido["tiempo_etapa_horas"].shift(-1), unit="h")

    hacia_adelante = por_pedido["fecha_evento"].shift(1) + horas_propias
    hacia_atras = por_pedido["fecha_evento"].shift(-1) - horas_siguiente

    faltantes = df["fecha_evento"].isna()
    df.loc[faltantes, "fecha_evento"] = hacia_adelante.fillna(hacia_atras)[faltantes].dt.round("s")
    df["fecha_evento_imputada"] = faltantes & df["fecha_evento"].notna()

    bitacora.registrar("Nulos fecha_evento", "Reconstruida con evento vecino +/- tiempo_etapa_horas",
                       df["fecha_evento_imputada"].sum())
    bitacora.registrar("Nulos fecha_evento", "Sin evento vecino con fecha: se mantiene nulo",
                       df["fecha_evento"].isna().sum())
    return df


def tratar_tiempo_etapa(df: pd.DataFrame, bitacora: Bitacora) -> pd.DataFrame:
    """PEDIDO RECIBIDO no tiene etapa previa -> su nulo es válido y se MANTIENE.

    No se imputa con 0 ni con la media: 0 bajaría los promedios y la media
    inventaría una duración que no existe. En otras etapas, si faltara el dato,
    se recalcula con la diferencia entre fechas de eventos consecutivos.
    """
    es_primera_etapa = df["estado_evento"] == ETAPAS[0]
    bitacora.registrar("Nulos tiempo_etapa_horas", "PEDIDO RECIBIDO: se mantiene nulo (no hay etapa previa)",
                       (es_primera_etapa & df["tiempo_etapa_horas"].isna()).sum())

    diferencia = df.groupby("pedido_id")["fecha_evento"].diff().dt.total_seconds() / 3600
    faltantes = ~es_primera_etapa & df["tiempo_etapa_horas"].isna()
    df.loc[faltantes, "tiempo_etapa_horas"] = diferencia[faltantes].round(2)
    bitacora.registrar("Nulos tiempo_etapa_horas", "Otras etapas: recalculado con diferencia de fechas",
                       (faltantes & df["tiempo_etapa_horas"].notna()).sum())
    return df


def tratar_incidencias(df: pd.DataFrame, bitacora: Bitacora) -> pd.DataFrame:
    """incidencia/observacion nulas significan 'no hubo novedad' (no es dato perdido)."""
    faltantes = df["incidencia"].isna()
    df["incidencia"] = df["incidencia"].fillna("SIN INCIDENCIA")
    df["tiene_incidencia"] = ~faltantes
    bitacora.registrar("Nulos incidencia", "Nulo = no hubo incidencia -> 'SIN INCIDENCIA'", faltantes.sum())

    faltantes = df["observacion"].isna()
    df["observacion"] = df["observacion"].fillna("Sin observación")
    bitacora.registrar("Nulos observacion", "Nulo = no se registró comentario -> 'Sin observación'", faltantes.sum())
    return df


def validar_consistencia(df: pd.DataFrame, bitacora: Bitacora) -> pd.DataFrame:
    """Validaciones que se DOCUMENTAN pero no se corrigen (no se inventan eventos)."""
    etapas_por_pedido = df.groupby("pedido_id")["estado_evento"].nunique()
    bitacora.registrar("Validación", "Pedidos con menos de 10 etapas registradas (no se crean eventos)",
                       (etapas_por_pedido < len(ETAPAS)).sum())

    costos_por_pedido = df.groupby("pedido_id")["costo_envio"].nunique()
    bitacora.registrar("Validación", "Pedidos con más de un costo_envio distinto", (costos_por_pedido > 1).sum())
    return df


def limpiar_logistica(df_logistica: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aplica todos los pasos de limpieza. Devuelve (df_logisitica_transformado, bitácora).

    Trabaja sobre una copia: df_logistica (Bronze) queda intacto.
    El orden importa: primero duplicados y tipos, luego estandarizar (para poder
    comparar etapas), y al final las imputaciones que dependen del orden de eventos.
    """
    bitacora = Bitacora("logistica")
    df = df_logistica.copy()

    df = eliminar_duplicados(df, bitacora)
    df = convertir_tipos(df, bitacora)
    df = estandarizar_categorias(df, bitacora)
    df = imputar_atributos_pedido(df, bitacora)
    df = imputar_transportadora_y_guia(df, bitacora)
    df = reconstruir_fecha_evento(df, bitacora)
    df = tratar_tiempo_etapa(df, bitacora)
    df = tratar_incidencias(df, bitacora)
    df = validar_consistencia(df, bitacora)

    return df.reset_index(drop=True), bitacora.como_dataframe()
