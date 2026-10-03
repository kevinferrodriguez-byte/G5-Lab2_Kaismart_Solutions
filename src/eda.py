"""Funciones reutilizables de EDA y perfil de calidad del dato.
"""
import pandas as pd


def resumen_estructura(df: pd.DataFrame) -> pd.DataFrame:
    """Tabla con tipo de dato, no nulos, nulos y valores únicos por variable."""
    return pd.DataFrame({
        "tipo_dato": df.dtypes.astype(str),
        "no_nulos": df.notna().sum(),
        "nulos": df.isna().sum(),
        "valores_unicos": df.nunique(),
    })


def perfil_nulos(df: pd.DataFrame) -> pd.DataFrame:
    """Cantidad y porcentaje de nulos por variable, de mayor a menor porcentaje."""
    perfil = pd.DataFrame({
        "nulos": df.isna().sum(),
        "porcentaje_nulos": (df.isna().mean() * 100).round(2),
    })
    return perfil.sort_values("porcentaje_nulos", ascending=False)


def perfil_cardinalidad(df: pd.DataFrame, umbral_baja: int = 10, umbral_alta: int = 50) -> pd.DataFrame:
    """Clasifica cada variable según su número de valores distintos.

    - Posible identificador: tantos valores distintos como filas no nulas.
    - Alta cardinalidad: más de `umbral_alta` valores distintos.
    - Baja cardinalidad: `umbral_baja` o menos valores distintos.
    - Media: el resto.
    """
    n_unicos = df.nunique()
    no_nulos = df.notna().sum()

    def clasificar(col: str) -> str:
        if n_unicos[col] == no_nulos[col] and no_nulos[col] > 0:
            return "posible identificador (todos distintos)"
        if n_unicos[col] > umbral_alta:
            return "alta cardinalidad"
        if n_unicos[col] <= umbral_baja:
            return "baja cardinalidad"
        return "cardinalidad media"

    perfil = pd.DataFrame({
        "valores_unicos": n_unicos,
        "pct_unicos_sobre_filas": (n_unicos / len(df) * 100).round(2),
        "clasificacion": [clasificar(c) for c in df.columns],
    })
    return perfil.sort_values("valores_unicos", ascending=False)


def resumen_duplicados(df: pd.DataFrame, identificadores: list[str]) -> pd.DataFrame:
    """Filas completamente duplicadas y repeticiones de cada identificador."""
    filas = [{
        "revision": "filas completamente duplicadas",
        "registros_repetidos": int(df.duplicated().sum()),
    }]
    for col in identificadores:
        filas.append({
            "revision": f"valores repetidos en {col}",
            "registros_repetidos": int(df[col].duplicated().sum()),
        })
    return pd.DataFrame(filas)


def frecuencias(df: pd.DataFrame, columna: str, incluir_nulos: bool = True) -> pd.DataFrame:
    """Frecuencia absoluta y porcentual de cada categoría de una columna."""
    conteo = df[columna].value_counts(dropna=not incluir_nulos)
    return pd.DataFrame({
        "frecuencia": conteo,
        "porcentaje": (conteo / conteo.sum() * 100).round(2),
    })


def resumen_categoricas(df: pd.DataFrame, columnas: list[str]) -> pd.DataFrame:
    """Para cada variable categórica: nº de categorías, categoría más frecuente y su frecuencia."""
    filas = []
    for col in columnas:
        conteo = df[col].value_counts()
        filas.append({
            "variable": col,
            "valores_unicos": df[col].nunique(),
            "categoria_mas_frecuente": conteo.index[0],
            "frecuencia_moda": int(conteo.iloc[0]),
            "pct_moda": round(conteo.iloc[0] / df[col].notna().sum() * 100, 2),
        })
    return pd.DataFrame(filas).set_index("variable")


def estadisticos_numericos(serie: pd.Series) -> pd.Series:
    """count, mean, std, min, p25, mediana, p75 y max de una serie.

    Convierte a numérico sobre una COPIA.
    """
    numerica = pd.to_numeric(serie, errors="coerce")
    return numerica.describe().rename({"25%": "p25", "50%": "mediana", "75%": "p75"})


def rango_fechas(serie: pd.Series) -> dict:
    """Fecha mínima, máxima y cantidad de valores que no se pudieron convertir."""
    fechas = pd.to_datetime(serie, errors="coerce")
    return {
        "fecha_minima": fechas.min(),
        "fecha_maxima": fechas.max(),
        "dias_cubiertos": (fechas.max() - fechas.min()).days,
        "valores_no_convertibles": int((fechas.isna() & serie.notna()).sum()),
    }


def outliers_iqr(serie: pd.Series) -> dict:
    """Cuenta valores atípicos con la regla de Tukey (1.5 * rango intercuartílico)."""
    numerica = pd.to_numeric(serie, errors="coerce").dropna()
    q1, q3 = numerica.quantile([0.25, 0.75])
    iqr = q3 - q1
    limite_inf, limite_sup = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    atipicos = numerica[(numerica < limite_inf) | (numerica > limite_sup)]
    return {
        "limite_inferior": round(limite_inf, 2),
        "limite_superior": round(limite_sup, 2),
        "cantidad_atipicos": len(atipicos),
        "pct_atipicos": round(len(atipicos) / len(numerica) * 100, 2),
    }
