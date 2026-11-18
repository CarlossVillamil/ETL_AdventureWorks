"""ETL AdventureWorks2025 -> Data Marts Internet Sales y Reseller Sales (Python).

Uso:  .venv\\Scripts\\python main.py

Fases:
  1. Extracción   : lee las tablas necesarias del OLTP (AdventureWorks2025).
  2. Transformación: construye 11 dimensiones, el staging de líneas de venta y 2 hechos.
  3. Carga        : recrea la base AdventureWorksDM2025 y carga dimensiones, luego hechos.
  4. Validación   : conteo de filas y totales contra el OLTP y la bodega oficial.
"""
import time
from pathlib import Path

import pandas as pd

import config
from etl import dimensiones as D
from etl import hechos as H
from etl.carga import cargar, ejecutar_ddl
from etl.conexion import motor
from etl.extraccion import extraer_todo
from etl.validacion import comparar_totales, conteo_filas

SALIDA = Path(__file__).resolve().parent / "salida"
SALIDA.mkdir(exist_ok=True)
_log_lineas = []


def log(msg: str = "") -> None:
    print(msg, flush=True)
    _log_lineas.append(msg)


def main() -> None:
    t_total = time.perf_counter()
    log(f"ETL AdventureWorks -> {config.BD_DESTINO}  (servidor: {config.SERVIDOR})")

    # 1. EXTRACCIÓN ------------------------------------------------------------
    log("\n[1/4] Extracción desde " + config.BD_OLTP)
    d = extraer_todo(motor(config.BD_OLTP), log)

    # 2. TRANSFORMACIÓN --------------------------------------------------------
    log("\n[2/4] Transformación")
    t0 = time.perf_counter()
    dims = {}
    dims["DimDate"] = D.dim_date(d)
    dims["DimProductCategory"] = D.dim_product_category(d)
    dims["DimProductSubcategory"] = D.dim_product_subcategory(d, dims["DimProductCategory"])
    dims["DimProduct"] = D.dim_product(d, dims["DimProductSubcategory"])
    dims["DimPromotion"] = D.dim_promotion(d)
    dims["DimCurrency"] = D.dim_currency(d)
    dims["DimSalesTerritory"] = D.dim_sales_territory(d)
    dims["DimGeography"] = D.dim_geography(d, dims["DimSalesTerritory"])
    dims["DimCustomer"] = D.dim_customer(d, dims["DimGeography"])
    dims["DimReseller"] = D.dim_reseller(d, dims["DimGeography"])
    dims["DimEmployee"] = D.dim_employee(d, dims["DimSalesTerritory"])
    stg = H.staging_lineas_venta(d)
    hechos = {"FactInternetSales": H.fact_internet_sales(stg, dims),
              "FactResellerSales": H.fact_reseller_sales(stg, dims)}
    log(f"  stg_LineasVenta: {len(stg):,} líneas de venta")
    log(f"  11 dimensiones y 2 hechos construidos ({time.perf_counter() - t0:.1f} s)")

    # 3. CARGA -----------------------------------------------------------------
    log("\n[3/4] Carga en " + config.BD_DESTINO)
    ejecutar_ddl(log)
    destino = motor(config.BD_DESTINO)
    cargar({**dims, **hechos}, destino, log)          # dimensiones primero, hechos al final

    # 4. VALIDACIÓN ------------------------------------------------------------
    log("\n[4/4] Validación")
    filas = conteo_filas(destino)
    totales = comparar_totales(destino)
    filas.to_csv(SALIDA / "validacion_filas.csv", index=False, encoding="utf-8-sig")
    totales.to_csv(SALIDA / "validacion_totales.csv", index=False, encoding="utf-8-sig")
    with pd.option_context("display.width", 200, "display.max_columns", 20,
                           "display.float_format", "{:,.2f}".format):
        log(filas.to_string(index=False))
        log("")
        log(totales.to_string(index=False))

    log(f"\nETL terminado en {time.perf_counter() - t_total:.1f} s")
    (SALIDA / "etl_log.txt").write_text("\n".join(_log_lineas), encoding="utf-8")


if __name__ == "__main__":
    main()
