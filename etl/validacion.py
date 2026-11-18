"""VALIDACIÓN: compara lo cargado en el data mart contra el OLTP y contra la
bodega oficial AdventureWorksDW2025."""
import pandas as pd

import config

TABLAS = ["DimDate", "DimProductCategory", "DimProductSubcategory", "DimProduct", "DimPromotion",
          "DimCurrency", "DimSalesTerritory", "DimGeography", "DimCustomer", "DimReseller", "DimEmployee",
          "FactInternetSales", "FactResellerSales"]

TOTALES_DM = """SELECT '{canal}' AS Canal, COUNT(*) AS Lineas, COUNT(DISTINCT SalesOrderNumber) AS Ordenes,
    SUM(OrderQuantity) AS Unidades, SUM(SalesAmount) AS Ventas, SUM(TotalProductCost) AS Costo,
    SUM(TaxAmt) AS Impuestos, SUM(Freight) AS Flete FROM {bd}.dbo.{tabla}"""

TOTALES_OLTP = """SELECT CASE h.OnlineOrderFlag WHEN 1 THEN 'Internet' ELSE 'Revendedores' END AS Canal,
    COUNT(*) AS Lineas, COUNT(DISTINCT h.SalesOrderID) AS Ordenes, SUM(d.OrderQty) AS Unidades,
    SUM(d.LineTotal) AS Ventas FROM {bd}.Sales.SalesOrderDetail d
    JOIN {bd}.Sales.SalesOrderHeader h ON h.SalesOrderID = d.SalesOrderID GROUP BY h.OnlineOrderFlag"""


def conteo_filas(motor_destino) -> pd.DataFrame:
    sql = " UNION ALL ".join(f"SELECT '{t}' AS Tabla, COUNT(*) AS Filas FROM dbo.{t}" for t in TABLAS)
    with motor_destino.connect() as cn:
        return pd.read_sql(sql, cn)


def comparar_totales(motor_destino) -> pd.DataFrame:
    dm = config.BD_DESTINO
    dw = config.BD_DW_OFICIAL
    with motor_destino.connect() as cn:
        etl = pd.concat([
            pd.read_sql(TOTALES_DM.format(canal="Internet", bd=dm, tabla="FactInternetSales"), cn),
            pd.read_sql(TOTALES_DM.format(canal="Revendedores", bd=dm, tabla="FactResellerSales"), cn)])
        oficial = pd.concat([
            pd.read_sql(TOTALES_DM.format(canal="Internet", bd=dw, tabla="FactInternetSales"), cn),
            pd.read_sql(TOTALES_DM.format(canal="Revendedores", bd=dw, tabla="FactResellerSales"), cn)])
        oltp = pd.read_sql(TOTALES_OLTP.format(bd=config.BD_OLTP), cn)
    etl.insert(0, "Fuente", "ETL Python")
    oficial.insert(0, "Fuente", "AdventureWorksDW2025")
    oltp.insert(0, "Fuente", "OLTP (SQL directo)")
    return (pd.concat([etl, oltp, oficial], ignore_index=True)
            .sort_values(["Canal", "Fuente"]).reset_index(drop=True))
