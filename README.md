# Laboratorio práctico de ETL — Kaismart Solutions S.A.S.

Proceso ETL con **arquitectura Medallion** (Bronze → Silver → Gold) que integra:

| Fuente | Origen | DataFrame crudo | DataFrame limpio |
|---|---|---|---|
| Sistema comercial | MySQL `clientes.ventas` (5.000 registros) | `df_ventas` | `df_ventas_transformado` |
| Sistema logístico | `kaismart_eventos_logisticos.xlsx` (50.000 registros) | `df_logistica` | `df_logisitica_transformado` |

Las fuentes se integran por `pedido_id`. Autores: ver [`config/config.yaml`](config/config.yaml).

## Estructura del proyecto

```
Lab2 ETL/
├── main.py                        # Punto de entrada: ejecución única u orquestador
├── config/config.yaml             # Autores, rutas, fuentes y frecuencia del orquestador
├── .env                           # Credenciales MySQL (no se escriben en el código)
├── data/
│   ├── kaismart_eventos_logisticos.xlsx   # Fuente 2 (Excel)
│   ├── bronze/                    # Datos crudos, sin modificar
│   ├── silver/                    # Datos limpios + bitacora_limpieza.csv
│   └── gold/                      # gold_pedidos + KPIs (CSV) y kaismart_gold.db (SQLite)
├── notebooks/lab2_etl_kaismart.ipynb      # DOCUMENTO PRINCIPAL: Partes 1 a 8 + conclusiones
├── src/
│   ├── config.py                  # Lectura de config.yaml
│   ├── logger.py                  # Log en consola y logs/etl.log
│   ├── eda.py                     # Funciones de EDA/perfil de calidad
│   ├── pipeline.py                # Extracción → Bronze → Silver → Gold
│   ├── extract/
│   │   ├── extract_database.py    # MySQL → df_ventas
│   │   └── extract_excel.py       # Excel → df_logistica
│   ├── transform/
│   │   ├── utils_limpieza.py      # Estandarización de texto + bitácora de decisiones
│   │   ├── clean_database.py      # Silver: limpieza de ventas
│   │   ├── clean_excel.py         # Silver: limpieza de logística
│   │   └── gold_transformations.py# Gold: integración 1:1 por pedido + KPIs
│   └── load/
│       ├── load_files.py          # Guardar cada capa en CSV
│       └── load_database.py       # Cargar Gold en SQLite
├── tests/                         # Pruebas con pytest (extracción, reglas de limpieza, calidad)
└── logs/etl.log
```

## Para ejecutar

```bash
# 1. Crear y activar el entorno virtual
python -m venv venv
venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar el pipeline una vez
python main.py

# 4. Ejecutar con el orquestador, cada N minutos según config.yaml
python main.py --programar

# 5. Pruebas
python -m pytest -v
```
## Resumen de decisiones de limpieza (Silver)

| Variable | Tipo de nulo | Decisión |
|---|---|---|
| `id_tienda` | Estructural (ventas web/app) | `"NO APLICA"` (la moda inventaría una tienda) |
| `calificacion_cliente` | Válido (no calificó) | Se **mantiene nulo** + bandera `tiene_calificacion` |
| `centro_logistico`, `ciudad_destino`, `fecha_prometida_entrega` | Problema | Se copian de otro evento del **mismo pedido** (son constantes por pedido) |
| `transportadora` antes del despacho | Normal | `"NO APLICA"` |
| `transportadora` / `numero_guia` desde el despacho | Problema | Se copian del mismo pedido |
| `numero_guia` antes del despacho | Normal | Se **mantiene nulo** (la guía aún no existe) |
| `fecha_evento` | Problema | Se reconstruye: fecha anterior + `tiempo_etapa_horas` (bandera `fecha_evento_imputada`) |
| `tiempo_etapa_horas` en "Pedido recibido" | Normal (no hay etapa previa) | Se **mantiene nulo** |
| `incidencia` / `observacion` | Normal (sin novedad) | `"SIN INCIDENCIA"` / `"Sin observación"` |

Duplicados: se eliminan 99 filas idénticas de logística y, para el `evento_id` repetido con datos distintos, se conserva la fila más completa.