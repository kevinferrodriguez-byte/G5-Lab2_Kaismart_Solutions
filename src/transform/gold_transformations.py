"""GOLD - Integración de ventas + logística y tablas listas para análisis.

Granularidad:
  - df_ventas_transformado: 1 fila = 1 venta (= 1 pedido).
  - df_logisitica_transformado: 1 fila = 1 evento de un pedido (~10 por pedido).
Para integrar sin duplicar ventas, primero se RESUME la logística a 1 fila por
pedido y luego se une con ventas por pedido_id mediante una relación uno a uno.
"""
import pandas as pd

from src.transform.clean_excel import ETAPAS, ETAPAS_CON_TRANSPORTADORA

HORA = pd.Timedelta(hours=1)


def resumir_logistica_por_pedido(df_log: pd.DataFrame) -> pd.DataFrame:
    """Convierte los eventos logísticos en una fila por pedido con sus métricas."""
    por_pedido = df_log.groupby("pedido_id")

    resumen = por_pedido.agg(
        centro_logistico=("centro_logistico", "first"),
        ciudad_destino=("ciudad_destino", "first"),
        fecha_prometida_entrega=("fecha_prometida_entrega", "first"),
        costo_envio=("costo_envio", "first"),
        eventos_registrados=("evento_id", "count"),
        etapas_registradas=("estado_evento", "nunique"),
        incidencias=("tiene_incidencia", "sum"),
        ultima_etapa=("orden_etapa", "max"),
    )
    resumen["estado_actual"] = resumen["ultima_etapa"].map(lambda n: ETAPAS[n - 1])
    resumen["pedido_completo"] = resumen["etapas_registradas"] == len(ETAPAS)

    # Transportadora y guía solo existen desde el despacho
    despachos = df_log[df_log["estado_evento"].isin(ETAPAS_CON_TRANSPORTADORA)]
    transporte = despachos.groupby("pedido_id").agg(
        transportadora=("transportadora", "first"),
        numero_guia=("numero_guia", "first"),
    )

    # Tipo de incidencia del pedido (si tuvo varias, se listan separadas por " | ")
    con_incidencia = df_log[df_log["tiene_incidencia"]]
    tipo_incidencia = con_incidencia.groupby("pedido_id")["incidencia"].agg(lambda s: " | ".join(s.unique()))

    # Fechas de los hitos clave del proceso
    hitos = {"PEDIDO RECIBIDO": "fecha_recibido", "DESPACHADO": "fecha_despacho", "ENTREGADO": "fecha_entrega"}
    fechas = (
        df_log[df_log["estado_evento"].isin(hitos)]
        .groupby(["pedido_id", "estado_evento"])["fecha_evento"].min()
        .unstack()
        .rename(columns=hitos)
        .reindex(columns=list(hitos.values()))
    )

    resumen = resumen.join(transporte).join(fechas)
    resumen["tipo_incidencia"] = tipo_incidencia.reindex(resumen.index).fillna("SIN INCIDENCIA")
    resumen["transportadora"] = resumen["transportadora"].fillna("SIN DESPACHO")

    # Métricas de desempeño logístico
    resumen["horas_hasta_despacho"] = ((resumen["fecha_despacho"] - resumen["fecha_recibido"]) / HORA).round(2)
    resumen["horas_totales_entrega"] = ((resumen["fecha_entrega"] - resumen["fecha_recibido"]) / HORA).round(2)
    # Positivo = llegó después de lo prometido (retraso); negativo = llegó antes
    resumen["horas_vs_promesa"] = ((resumen["fecha_entrega"] - resumen["fecha_prometida_entrega"]) / HORA).round(2)
    resumen["entregado"] = resumen["fecha_entrega"].notna()
    # Solo se evalúa si hubo entrega; si no, queda <NA> (no se puede saber aún)
    resumen["entrega_a_tiempo"] = (resumen["horas_vs_promesa"] <= 0).astype("boolean")
    resumen.loc[resumen["horas_vs_promesa"].isna(), "entrega_a_tiempo"] = pd.NA

    return resumen.drop(columns="ultima_etapa").reset_index()


def construir_gold_pedidos(df_ventas_t: pd.DataFrame, df_log_t: pd.DataFrame) -> pd.DataFrame:
    """Tabla integrada: 1 fila por pedido con la venta y su desempeño logístico."""
    resumen_log = resumir_logistica_por_pedido(df_log_t)
    gold = df_ventas_t.merge(resumen_log, on="pedido_id", how="left",
                             validate="one_to_one", indicator="origen_union")
    gold["tiene_logistica"] = gold["origen_union"] == "both"
    gold["ciudad_consistente"] = gold["ciudad"] == gold["ciudad_destino"]
    gold["valor_neto_mas_envio"] = gold["valor_neto"] + gold["costo_envio"].astype(float)
    return gold.drop(columns="origen_union")


def _kpis(gold: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """KPIs comerciales y logísticos agregados por una dimensión."""
    tabla = gold.groupby(dimension).agg(
        pedidos=("pedido_id", "count"),
        ventas_netas=("valor_neto", "sum"),
        ticket_promedio=("valor_neto", "mean"),
        costo_envio_promedio=("costo_envio", "mean"),
        horas_promedio_entrega=("horas_totales_entrega", "mean"),
        pct_entrega_a_tiempo=("entrega_a_tiempo", "mean"),
        incidencias=("incidencias", "sum"),
        calificacion_promedio=("calificacion_cliente", "mean"),
    )
    tabla["pct_entrega_a_tiempo"] = tabla["pct_entrega_a_tiempo"] * 100
    tabla["incidencias_por_100_pedidos"] = tabla["incidencias"] / tabla["pedidos"] * 100
    return tabla.round(2).sort_values("pedidos", ascending=False).reset_index()


def construir_gold(df_ventas_transformado: pd.DataFrame, df_logisitica_transformado: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Genera todas las tablas de la capa Gold."""
    gold_pedidos = construir_gold_pedidos(df_ventas_transformado, df_logisitica_transformado)
    return {
        "gold_pedidos": gold_pedidos,
        "gold_kpi_ciudad": _kpis(gold_pedidos, "ciudad"),
        "gold_kpi_transportadora": _kpis(gold_pedidos, "transportadora"),
        "gold_kpi_categoria": _kpis(gold_pedidos, "categoria"),
    }
