"""TRANSFORMACIÓN de los hechos.

1. staging_lineas_venta: une encabezado + detalle de las órdenes y calcula las
   medidas de cada línea (una sola vez para los dos canales).
2. fact_internet_sales / fact_reseller_sales: separan por OnlineOrderFlag y
   reemplazan los IDs del OLTP por las llaves sustitutas de las dimensiones.
"""
import numpy as np
import pandas as pd


def _llave_fecha(s: pd.Series) -> pd.Series:
    return s.dt.year * 10000 + s.dt.month * 100 + s.dt.day


def staging_lineas_venta(d) -> pd.DataFrame:
    enc = d["SalesOrderHeader"].rename(columns={"TaxAmt": "OrderTaxAmt", "Freight": "OrderFreight"})
    lin = d["SalesOrderDetail"].merge(enc, on="SalesOrderID", how="inner", validate="m:1")

    # Tienda del cliente (para encontrar al revendedor)
    lin = lin.merge(d["Customer"][["CustomerID", "StoreID"]], on="CustomerID", how="left", validate="m:1")

    # Moneda de la orden; sin tasa de cambio = dólares
    tasas = d["CurrencyRate"].rename(columns={"ToCurrencyCode": "CurrencyCode"})
    tasas["CurrencyRateID"] = tasas["CurrencyRateID"].astype("Int64")
    lin["CurrencyRateID"] = lin["CurrencyRateID"].astype("Int64")
    lin = lin.merge(tasas, on="CurrencyRateID", how="left", validate="m:1")
    lin["CurrencyCode"] = lin["CurrencyCode"].str.strip().fillna("USD")

    # Costo estándar vigente en la fecha de la orden (ProductCostHistory);
    # si el producto no tiene historial en esa fecha, se usa el costo actual.
    hist = d["ProductCostHistory"]
    cand = lin[["SalesOrderDetailID", "ProductID", "OrderDate"]].merge(hist, on="ProductID")
    vigente = (cand["StartDate"] <= cand["OrderDate"]) & (cand["EndDate"].isna() | (cand["EndDate"] >= cand["OrderDate"]))
    cand = (cand[vigente].sort_values("StartDate")
            .drop_duplicates("SalesOrderDetailID", keep="last")[["SalesOrderDetailID", "StandardCost"]])
    lin = lin.merge(cand, on="SalesOrderDetailID", how="left", validate="1:1")
    actual = d["Product"].set_index("ProductID")["StandardCost"]
    sin_hist = lin["StandardCost"].isna()
    lin.loc[sin_hist, "StandardCost"] = lin.loc[sin_hist, "ProductID"].map(actual)
    lin = lin.rename(columns={"StandardCost": "ProductStandardCost"})

    # Número de línea dentro de cada orden (1, 2, 3...)
    lin = lin.sort_values(["SalesOrderID", "SalesOrderDetailID"]).reset_index(drop=True)
    lin["SalesOrderLineNumber"] = lin.groupby("SalesOrderID").cumcount() + 1

    # Medidas por línea (redondeadas a 4 decimales, como el tipo money)
    q, p, desc = lin["OrderQty"], lin["UnitPrice"], lin["UnitPriceDiscount"]
    lin["ExtendedAmount"] = (q * p).round(4)
    lin["DiscountAmount"] = (q * p * desc).round(4)
    lin["TotalProductCost"] = (q * lin["ProductStandardCost"]).round(4)
    lin["SalesAmount"] = lin["LineTotal"].round(4)
    peso = np.where(lin["SubTotal"] != 0, lin["LineTotal"] / lin["SubTotal"], 0)   # peso de la línea en la orden
    lin["TaxAmt"] = (lin["OrderTaxAmt"] * peso).round(4)
    lin["Freight"] = (lin["OrderFreight"] * peso).round(4)

    # Fechas sin hora y llaves AAAAMMDD
    for c in ["OrderDate", "DueDate", "ShipDate"]:
        lin[c] = pd.to_datetime(lin[c]).dt.normalize()
    lin["OrderDateKey"] = _llave_fecha(lin["OrderDate"])
    lin["DueDateKey"] = _llave_fecha(lin["DueDate"])
    lin["ShipDateKey"] = _llave_fecha(lin["ShipDate"])

    return lin.rename(columns={"OrderQty": "OrderQuantity", "UnitPriceDiscount": "UnitPriceDiscountPct",
                               "PurchaseOrderNumber": "CustomerPONumber"})


MEDIDAS = ["SalesOrderNumber", "SalesOrderLineNumber", "RevisionNumber", "OrderQuantity", "UnitPrice",
           "ExtendedAmount", "UnitPriceDiscountPct", "DiscountAmount", "ProductStandardCost", "TotalProductCost",
           "SalesAmount", "TaxAmt", "Freight", "CarrierTrackingNumber", "CustomerPONumber",
           "OrderDate", "DueDate", "ShipDate"]


def _buscar(df, dim, col_hecho, col_dim, llave):
    """Lookup: trae la llave sustituta de la dimensión cruzando por la llave natural."""
    m = dim[[col_dim, llave]].rename(columns={col_dim: col_hecho})
    if m[col_hecho].dtype.kind in "iuf":
        m[col_hecho] = m[col_hecho].astype("Int64")
        df[col_hecho] = df[col_hecho].astype("Int64")
    return df.merge(m, on=col_hecho, how="left", validate="m:1")


def _verificar_llaves(df, llaves, nombre):
    faltan = {k: int(df[k].isna().sum()) for k in llaves if df[k].isna().any()}
    if faltan:
        raise ValueError(f"{nombre}: llaves sin resolver {faltan}")


def _comunes(df, dims):
    df = _buscar(df, dims["DimProduct"], "ProductID", "ProductID", "ProductKey")
    df = _buscar(df, dims["DimPromotion"], "SpecialOfferID", "SpecialOfferID", "PromotionKey")
    df = _buscar(df, dims["DimCurrency"], "CurrencyCode", "CurrencyCode", "CurrencyKey")
    df = _buscar(df, dims["DimSalesTerritory"], "TerritoryID", "TerritoryID", "SalesTerritoryKey")
    return df


def fact_internet_sales(stg, dims) -> pd.DataFrame:
    df = stg[stg["OnlineOrderFlag"] == True].copy()                       # canal Internet
    df = _comunes(df, dims)
    df = _buscar(df, dims["DimCustomer"], "CustomerID", "CustomerID", "CustomerKey")
    llaves = ["ProductKey", "OrderDateKey", "DueDateKey", "ShipDateKey", "CustomerKey", "PromotionKey",
              "CurrencyKey", "SalesTerritoryKey"]
    _verificar_llaves(df, llaves, "FactInternetSales")
    return df[llaves + MEDIDAS].sort_values(["SalesOrderNumber", "SalesOrderLineNumber"]).reset_index(drop=True)


def fact_reseller_sales(stg, dims) -> pd.DataFrame:
    df = stg[stg["OnlineOrderFlag"] == False].copy()                      # canal revendedores
    df = _comunes(df, dims)
    df = _buscar(df, dims["DimReseller"], "StoreID", "StoreID", "ResellerKey")
    df = _buscar(df, dims["DimEmployee"], "SalesPersonID", "BusinessEntityID", "EmployeeKey")
    llaves = ["ProductKey", "OrderDateKey", "DueDateKey", "ShipDateKey", "ResellerKey", "EmployeeKey",
              "PromotionKey", "CurrencyKey", "SalesTerritoryKey"]
    _verificar_llaves(df, llaves, "FactResellerSales")
    return df[llaves + MEDIDAS].sort_values(["SalesOrderNumber", "SalesOrderLineNumber"]).reset_index(drop=True)
