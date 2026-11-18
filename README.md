# Punto 4 – ETL en Python

Versión en Python del ETL del punto 4. Toma la base operacional **AdventureWorks2025**, construye los data marts **Internet Sales** y **Reseller Sales** y los carga en una base nueva de SQL Server, **AdventureWorksDM2025**. Es el mismo modelo que la versión de Power BI (carpeta `Punto 4`): 11 dimensiones, 2 tablas de hechos y los mismos totales.

## Cómo ejecutarlo

Requisitos: SQL Server con `AdventureWorks2025` (y `AdventureWorksDW2025` para la validación), Python 3.12 y el *ODBC Driver 18 for SQL Server*.

```powershell
cd "Punto 4 Python"
py -3.12 -m venv .venv                      # solo la primera vez
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python main.py
```

Si su servidor no es `localhost`, cambie `SERVIDOR` en `config.py` (por ejemplo `r"localhost\SQLEXPRESS"`).

La carga completa tarda unos 25 segundos. Cada ejecución borra y vuelve a crear las tablas de `AdventureWorksDM2025`, así que se puede correr las veces que haga falta.

## Estructura

| Archivo | Fase | Qué hace |
|---|---|---|
| `config.py` | – | Servidor y nombres de las bases |
| `sql/01_crear_datamart.sql` | Carga | DDL: crea la base destino y las 13 tablas con llaves primarias y foráneas |
| `etl/conexion.py` | – | Conexiones a SQL Server (autenticación de Windows) |
| `etl/extraccion.py` | Extracción | Un `SELECT` por cada una de las 26 tablas y vistas del OLTP que se usan |
| `etl/dimensiones.py` | Transformación | Construye las 11 dimensiones: combina tablas, limpia y crea la llave sustituta |
| `etl/hechos.py` | Transformación | Staging de líneas de venta, separación por canal y búsqueda de llaves |
| `etl/carga.py` | Carga | Ejecuta el DDL y escribe dimensiones y luego hechos |
| `etl/validacion.py` | Validación | Conteos y totales contra el OLTP y la bodega oficial |
| `main.py` | – | Ejecuta las 4 fases en orden |
| `salida/` | – | `etl_log.txt`, `validacion_filas.csv`, `validacion_totales.csv` |

## Qué hace cada fase

1. **Extracción.** Lee del OLTP solo las columnas necesarias con `pandas.read_sql`. No hace uniones en SQL: toda la lógica queda en Python.
2. **Transformación.**
   - *Dimensiones:* cada una combina sus tablas con `merge`, limpia los datos y se ordena por la llave natural para numerarla desde 1 (llave sustituta). Las reglas de limpieza son: quitar espacios de relleno, cambiar nulos por "NA", traducir códigos a texto y quitar la hora de las fechas. Todos los `merge` usan `validate="m:1"`, así que el ETL falla si una dimensión tiene duplicados que multiplicarían filas.
   - *Staging (`staging_lineas_venta`):* une encabezado y detalle de las órdenes, trae la moneda (USD si no hay tasa de cambio), busca el costo vigente en la fecha de la orden en `ProductCostHistory`, numera las líneas de cada orden y calcula las medidas. El impuesto y el flete de la orden se reparten entre sus líneas según el peso de cada una.
   - *Hechos:* filtran el staging por `OnlineOrderFlag` (1 = Internet, 0 = Revendedores) y cambian los IDs del OLTP por las llaves sustitutas. Si alguna llave queda sin resolver, el ETL se detiene con un error.
3. **Carga.** Ejecuta el DDL (borra y recrea las tablas) e inserta primero las dimensiones y al final los hechos, para respetar las llaves foráneas.
4. **Validación.** Cuenta las filas de cada tabla y compara los totales por canal contra el OLTP y contra AdventureWorksDW2025.

## Resultados de la última ejecución

| Canal | Fuente | Líneas | Ventas | Costo | Impuestos |
|---|---|---|---|---|---|
| Internet | ETL Python | 60.398 | 29.358.677,22 | 17.277.793,58 | 2.348.694,23 |
| Internet | AdventureWorksDW2025 | 60.398 | 29.358.677,22 | 17.277.793,58 | 2.348.694,23 |
| Revendedores | ETL Python | 60.919 | 80.487.704,19 | 80.010.807,23 | 7.838.280,23 |
| Revendedores | OLTP | 60.919 | 80.487.704,18 | – | – |
| Revendedores | AdventureWorksDW2025 | 60.855 | 80.450.596,98 | 79.980.114,38 | 6.436.047,61 |

- **Internet:** coincide al centavo con la bodega oficial.
- **Revendedores:** coincide con el OLTP, que es la fuente que pide el enunciado. La bodega oficial tiene 64 líneas menos, probablemente porque se generó desde otra copia de la base. Su impuesto es menor porque en la bodega es un 8 % fijo de la venta, mientras que aquí se reparte el impuesto real de cada orden.

## Power BI frente a Python

| | Power BI (Power Query) | Python (pandas) |
|---|---|---|
| Dónde quedan los datos | Dentro del archivo `.pbix` | En una base de SQL Server (`AdventureWorksDM2025`) |
| Modelo físico | Relaciones del modelo de Power BI | DDL con llaves primarias y foráneas |
| Tiempo de carga | Unos 8 minutos | Unos 25 segundos |
| Transformaciones | Pasos visuales (código M) | Código Python versionable |
| Resultado | Mismas tablas, filas y totales | Mismas tablas, filas y totales |

Las respuestas a las tres preguntas del enunciado (dimensiones, granularidad y medidas) son las mismas que en el documento del punto 4, porque el modelo es idéntico.
