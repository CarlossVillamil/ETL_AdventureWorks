"""TRANSFORMACIÓN de las dimensiones.

Cada función recibe el diccionario de tablas extraídas y devuelve un DataFrame
con las columnas finales de la dimensión. Patrón común (igual que en Power Query):
  1. combinar (merge) las tablas del OLTP que forman la dimensión,
  2. limpiar: espacios de relleno, nulos, códigos a texto, fechas sin hora,
  3. ordenar por la llave natural y numerar desde 1 = llave sustituta.
Los merge usan validate="m:1" para detectar duplicados que multiplicarían filas.
"""
import numpy as np
import pandas as pd

DIAS = np.array(["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
MESES = np.array(["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
                  "Septiembre", "Octubre", "Noviembre", "Diciembre"])


# ------------------------------------------------------------------ utilidades
def llave_sustituta(df: pd.DataFrame, orden, nombre: str) -> pd.DataFrame:
    """Ordena por la llave natural y agrega una llave entera consecutiva desde 1."""
    df = df.sort_values(orden, kind="stable").reset_index(drop=True)
    df.insert(0, nombre, np.arange(1, len(df) + 1, dtype="int64"))
    return df


def recortar(s: pd.Series) -> pd.Series:
    """Quita los espacios de relleno de columnas nchar ('R ' -> 'R')."""
    return s.str.strip()


def sin_hora(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s).dt.normalize()


def direccion_y_geografia(df, col_entidad, tipo, d, dim_geo):
    """Agrega la dirección de un tipo dado (Home / Main Office) y su GeographyKey."""
    tipos = d["AddressType"].loc[d["AddressType"]["Name"] == tipo, ["AddressTypeID"]]
    bea = d["BusinessEntityAddress"].merge(tipos, on="AddressTypeID")[["BusinessEntityID", "AddressID"]]
    bea = bea.rename(columns={"BusinessEntityID": col_entidad})
    df = df.merge(bea, on=col_entidad, how="left", validate="m:1")
    df = df.merge(d["Address"], on="AddressID", how="left", validate="m:1")
    claves = ["City", "StateProvinceID", "PostalCode"]
    df = df.merge(dim_geo[claves + ["GeographyKey"]], on=claves, how="left", validate="m:1")
    return df


# ------------------------------------------------------------------ DimDate
def dim_date(d) -> pd.DataFrame:
    """Calendario generado (no viene del OLTP): del 1 de enero del año de la primera
    orden al 31 de diciembre del año del último vencimiento."""
    h = d["SalesOrderHeader"]
    f = pd.date_range(pd.Timestamp(h["OrderDate"].min().year, 1, 1),
                      pd.Timestamp(h["DueDate"].max().year, 12, 31), freq="D")
    dom = (f.dayofweek + 1) % 7                       # 0 = domingo
    ene1 = pd.to_datetime(pd.DataFrame({"year": f.year, "month": 1, "day": 1}))
    ene1_dom = (ene1.dt.dayofweek.to_numpy() + 1) % 7
    trim_fiscal = (f.quarter + 1) % 4 + 1             # julio-septiembre = trimestre fiscal 1
    return pd.DataFrame({
        "DateKey": f.year * 10000 + f.month * 100 + f.day,   # llave inteligente AAAAMMDD
        "FullDate": f,
        "DayNumberOfWeek": dom + 1,
        "DayNameOfWeek": DIAS[dom],
        "DayNumberOfMonth": f.day,
        "DayNumberOfYear": f.dayofyear,
        "WeekNumberOfYear": (f.dayofyear - 1 + ene1_dom) // 7 + 1,
        "MonthNumberOfYear": f.month,
        "MonthName": MESES[f.month - 1],
        "CalendarQuarter": f.quarter,
        "CalendarSemester": np.where(f.month <= 6, 1, 2),
        "CalendarYear": f.year,
        "YearMonth": f.strftime("%Y-%m"),
        "FiscalYear": f.year + (f.month >= 7),
        "FiscalQuarter": trim_fiscal,
        "FiscalSemester": np.where(trim_fiscal <= 2, 1, 2),
        "IsWeekend": f.dayofweek >= 5,
    })


# ------------------------------------------------------------------ Producto (copo de nieve)
def dim_product_category(d) -> pd.DataFrame:
    df = d["ProductCategory"].rename(columns={"Name": "ProductCategoryName"})
    return llave_sustituta(df, "ProductCategoryID", "ProductCategoryKey")


def dim_product_subcategory(d, dim_cat) -> pd.DataFrame:
    df = d["ProductSubcategory"].rename(columns={"Name": "ProductSubcategoryName"})
    df = df.merge(dim_cat[["ProductCategoryID", "ProductCategoryKey"]], on="ProductCategoryID",
                  how="left", validate="m:1")
    df = llave_sustituta(df, "ProductSubcategoryID", "ProductSubcategoryKey")
    return df[["ProductSubcategoryKey", "ProductSubcategoryID", "ProductSubcategoryName", "ProductCategoryKey"]]


LINEAS = {"R": "Ruta", "M": "Montaña", "T": "Turismo", "S": "Estándar"}


def dim_product(d, dim_sub) -> pd.DataFrame:
    df = d["Product"].rename(columns={"Name": "ProductName"})
    modelos = d["ProductModel"].rename(columns={"Name": "ModelName"})
    df = df.merge(modelos, on="ProductModelID", how="left", validate="m:1")
    df = df.merge(dim_sub[["ProductSubcategoryID", "ProductSubcategoryKey"]], on="ProductSubcategoryID",
                  how="left", validate="m:1")
    for c in ["ProductLine", "Class", "Style", "SizeUnitMeasureCode", "WeightUnitMeasureCode"]:
        df[c] = recortar(df[c])
    for c in ["Color", "Size", "ProductLine", "Class", "Style", "ModelName"]:
        df[c] = df[c].fillna("NA")                       # mismo criterio que AdventureWorksDW
    df["ProductLineName"] = df["ProductLine"].map(LINEAS).fillna("No aplica")
    df["Status"] = np.where(df["SellEndDate"].isna(), "Vigente", "Descontinuado")
    df["SellStartDate"] = sin_hora(df["SellStartDate"])
    df["SellEndDate"] = sin_hora(df["SellEndDate"])
    df["ProductSubcategoryKey"] = df["ProductSubcategoryKey"].astype("Int64")  # 209 componentes sin subcategoría
    df = llave_sustituta(df, "ProductID", "ProductKey")
    return df[["ProductKey", "ProductID", "ProductNumber", "ProductName", "ProductSubcategoryKey", "ModelName",
               "Color", "Size", "SizeUnitMeasureCode", "Weight", "WeightUnitMeasureCode", "StandardCost",
               "ListPrice", "ProductLine", "ProductLineName", "Class", "Style", "DaysToManufacture",
               "FinishedGoodsFlag", "SellStartDate", "SellEndDate", "Status"]]


# ------------------------------------------------------------------ Promoción, moneda, territorio
def dim_promotion(d) -> pd.DataFrame:
    df = d["SpecialOffer"].rename(columns={"Description": "PromotionName", "Type": "PromotionType",
                                           "Category": "PromotionCategory"})
    df["StartDate"] = sin_hora(df["StartDate"])
    df["EndDate"] = sin_hora(df["EndDate"])
    df["MaxQty"] = df["MaxQty"].astype("Int64")
    df = llave_sustituta(df, "SpecialOfferID", "PromotionKey")
    return df[["PromotionKey", "SpecialOfferID", "PromotionName", "DiscountPct", "PromotionType",
               "PromotionCategory", "StartDate", "EndDate", "MinQty", "MaxQty"]]


def dim_currency(d) -> pd.DataFrame:
    df = d["Currency"].rename(columns={"Name": "CurrencyName"})
    df["CurrencyCode"] = recortar(df["CurrencyCode"])
    return llave_sustituta(df, "CurrencyCode", "CurrencyKey")[["CurrencyKey", "CurrencyCode", "CurrencyName"]]


def dim_sales_territory(d) -> pd.DataFrame:
    df = d["SalesTerritory"].rename(columns={"Name": "SalesTerritoryRegion", "Group": "SalesTerritoryGroup"})
    paises = d["CountryRegion"].rename(columns={"Name": "SalesTerritoryCountry"})
    df = df.merge(paises, on="CountryRegionCode", how="left", validate="m:1")
    df = llave_sustituta(df, "TerritoryID", "SalesTerritoryKey")
    return df[["SalesTerritoryKey", "TerritoryID", "SalesTerritoryRegion", "CountryRegionCode",
               "SalesTerritoryCountry", "SalesTerritoryGroup"]]


# ------------------------------------------------------------------ Geografía
def dim_geography(d, dim_ter) -> pd.DataFrame:
    df = d["Address"][["City", "StateProvinceID", "PostalCode"]].drop_duplicates()
    prov = d["StateProvince"].rename(columns={"Name": "StateProvinceName"})
    df = df.merge(prov, on="StateProvinceID", how="inner", validate="m:1")
    paises = d["CountryRegion"].rename(columns={"Name": "CountryRegionName"})
    df = df.merge(paises, on="CountryRegionCode", how="left", validate="m:1")
    df = df.merge(dim_ter[["TerritoryID", "SalesTerritoryKey"]], on="TerritoryID", how="left", validate="m:1")
    df["StateProvinceCode"] = recortar(df["StateProvinceCode"])
    df = llave_sustituta(df, ["CountryRegionCode", "StateProvinceCode", "City", "PostalCode"], "GeographyKey")
    return df[["GeographyKey", "City", "StateProvinceID", "StateProvinceCode", "StateProvinceName",
               "CountryRegionCode", "CountryRegionName", "PostalCode", "SalesTerritoryKey"]]


# ------------------------------------------------------------------ Cliente (solo Internet)
def dim_customer(d, dim_geo) -> pd.DataFrame:
    c = d["Customer"]
    df = c[c["PersonID"].notna() & c["StoreID"].isna()].copy()          # solo personas
    df["PersonID"] = df["PersonID"].astype("int64")
    df = df.merge(d["Person"], left_on="PersonID", right_on="BusinessEntityID", how="inner",
                  validate="1:1").drop(columns="BusinessEntityID")
    df = df.merge(d["vPersonDemographics"], left_on="PersonID", right_on="BusinessEntityID", how="left",
                  validate="1:1").drop(columns="BusinessEntityID")
    df = df.merge(d["EmailAddress"], left_on="PersonID", right_on="BusinessEntityID", how="left",
                  validate="1:1").drop(columns="BusinessEntityID")
    tel = d["PersonPhone"].rename(columns={"PhoneNumber": "Phone"})
    df = df.merge(tel, left_on="PersonID", right_on="BusinessEntityID", how="left",
                  validate="1:1").drop(columns="BusinessEntityID")
    df = direccion_y_geografia(df, "PersonID", "Home", d, dim_geo)
    df["FullName"] = df[["FirstName", "MiddleName", "LastName"]].apply(
        lambda r: " ".join(x for x in r if isinstance(x, str) and x), axis=1)
    df["MaritalStatusName"] = df["MaritalStatus"].map({"M": "Casado(a)", "S": "Soltero(a)"}).fillna("Desconocido")
    df["GenderName"] = df["Gender"].map({"M": "Masculino", "F": "Femenino"}).fillna("Desconocido")
    df["BirthDate"] = sin_hora(df["BirthDate"])
    df["DateFirstPurchase"] = sin_hora(df["DateFirstPurchase"])
    df = llave_sustituta(df, "CustomerID", "CustomerKey")
    return df[["CustomerKey", "CustomerID", "AccountNumber", "GeographyKey", "Title", "FirstName", "MiddleName",
               "LastName", "FullName", "Suffix", "BirthDate", "MaritalStatus", "MaritalStatusName", "Gender",
               "GenderName", "EmailAddress", "Phone", "YearlyIncome", "TotalChildren", "NumberChildrenAtHome",
               "Education", "Occupation", "HomeOwnerFlag", "NumberCarsOwned", "EmailPromotion",
               "AddressLine1", "AddressLine2", "DateFirstPurchase"]]


# ------------------------------------------------------------------ Revendedor (solo Reseller)
TIPOS_NEGOCIO = {"BM": "Distribuidor de valor agregado", "BS": "Tienda especializada en bicicletas",
                 "OS": "Almacén"}


def dim_reseller(d, dim_geo) -> pd.DataFrame:
    df = d["vStoreWithDemographics"].rename(columns={"BusinessEntityID": "StoreID", "Name": "ResellerName"})
    c = d["Customer"]
    cuentas = c[c["StoreID"].notna() & c["PersonID"].isna()][["StoreID", "AccountNumber"]].copy()
    cuentas["StoreID"] = cuentas["StoreID"].astype("int64")
    df = df.merge(cuentas, on="StoreID", how="left", validate="1:1")
    df = direccion_y_geografia(df, "StoreID", "Main Office", d, dim_geo)
    df["BusinessTypeName"] = df["BusinessType"].map(TIPOS_NEGOCIO).fillna("Desconocido")
    df = llave_sustituta(df, "StoreID", "ResellerKey")
    return df[["ResellerKey", "StoreID", "AccountNumber", "ResellerName", "GeographyKey", "BusinessType",
               "BusinessTypeName", "Specialty", "YearOpened", "NumberEmployees", "SquareFeet", "Brands",
               "BankName", "AnnualSales", "AnnualRevenue", "AddressLine1", "AddressLine2"]]


# ------------------------------------------------------------------ Empleado (solo Reseller)
def dim_employee(d, dim_ter) -> pd.DataFrame:
    df = d["Employee"].merge(d["Person"][["BusinessEntityID", "FirstName", "MiddleName", "LastName"]],
                             on="BusinessEntityID", how="inner", validate="1:1")
    vend = d["SalesPerson"].assign(SalesPersonFlag=True)
    df = df.merge(vend, on="BusinessEntityID", how="left", validate="1:1")
    df["SalesPersonFlag"] = df["SalesPersonFlag"].fillna(False).astype(bool)   # no vendedores
    df["TerritoryID"] = df["TerritoryID"].astype("Int64")
    ter = dim_ter[["TerritoryID", "SalesTerritoryRegion"]].astype({"TerritoryID": "Int64"})
    df = df.merge(ter, on="TerritoryID", how="left", validate="m:1")
    edh = d["EmployeeDepartmentHistory"]
    depto = edh[edh["EndDate"].isna()].merge(d["Department"].rename(columns={"Name": "DepartmentName"}),
                                             on="DepartmentID")[["BusinessEntityID", "DepartmentName"]]
    df = df.merge(depto, on="BusinessEntityID", how="left", validate="1:1")
    df["FullName"] = df[["FirstName", "MiddleName", "LastName"]].apply(
        lambda r: " ".join(x for x in r if isinstance(x, str) and x), axis=1)
    df["HireDate"] = sin_hora(df["HireDate"])
    df["BirthDate"] = sin_hora(df["BirthDate"])
    df = llave_sustituta(df, "BusinessEntityID", "EmployeeKey")
    return df[["EmployeeKey", "BusinessEntityID", "NationalIDNumber", "FirstName", "MiddleName", "LastName",
               "FullName", "JobTitle", "DepartmentName", "LoginID", "HireDate", "BirthDate", "Gender",
               "MaritalStatus", "SalariedFlag", "CurrentFlag", "SalesPersonFlag", "SalesTerritoryRegion",
               "SalesQuota", "Bonus", "CommissionPct"]]
