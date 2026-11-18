"""EXTRACCIÓN: lee de AdventureWorks2025 solo las columnas que usa el ETL.

Cada consulta es un SELECT simple sobre una tabla o vista del OLTP; todas las
uniones, limpiezas y cálculos se hacen después en pandas (transformación).
"""
import time

import pandas as pd

CONSULTAS = {
    # --- Ventas
    "SalesOrderHeader": """SELECT SalesOrderID, RevisionNumber, OrderDate, DueDate, ShipDate,
        OnlineOrderFlag, SalesOrderNumber, PurchaseOrderNumber, CustomerID, SalesPersonID,
        TerritoryID, CurrencyRateID, SubTotal, TaxAmt, Freight FROM Sales.SalesOrderHeader""",
    "SalesOrderDetail": """SELECT SalesOrderID, SalesOrderDetailID, CarrierTrackingNumber, OrderQty,
        ProductID, SpecialOfferID, UnitPrice, UnitPriceDiscount, LineTotal FROM Sales.SalesOrderDetail""",
    "Customer": "SELECT CustomerID, PersonID, StoreID, AccountNumber FROM Sales.Customer",
    "CurrencyRate": "SELECT CurrencyRateID, ToCurrencyCode FROM Sales.CurrencyRate",
    "Currency": "SELECT CurrencyCode, Name FROM Sales.Currency",
    "SpecialOffer": """SELECT SpecialOfferID, Description, DiscountPct, Type, Category, StartDate,
        EndDate, MinQty, MaxQty FROM Sales.SpecialOffer""",
    "SalesTerritory": 'SELECT TerritoryID, Name, CountryRegionCode, [Group] FROM Sales.SalesTerritory',
    "SalesPerson": "SELECT BusinessEntityID, TerritoryID, SalesQuota, Bonus, CommissionPct FROM Sales.SalesPerson",
    "vPersonDemographics": """SELECT BusinessEntityID, BirthDate, MaritalStatus, Gender, YearlyIncome,
        TotalChildren, NumberChildrenAtHome, Education, Occupation, HomeOwnerFlag, NumberCarsOwned,
        DateFirstPurchase FROM Sales.vPersonDemographics""",
    "vStoreWithDemographics": """SELECT BusinessEntityID, Name, AnnualSales, AnnualRevenue, BankName,
        BusinessType, YearOpened, Specialty, SquareFeet, Brands, NumberEmployees
        FROM Sales.vStoreWithDemographics""",
    # --- Producción
    "Product": """SELECT ProductID, ProductNumber, Name, Color, Size, SizeUnitMeasureCode, Weight,
        WeightUnitMeasureCode, StandardCost, ListPrice, ProductLine, Class, Style, DaysToManufacture,
        FinishedGoodsFlag, ProductSubcategoryID, ProductModelID, SellStartDate, SellEndDate
        FROM Production.Product""",
    "ProductSubcategory": "SELECT ProductSubcategoryID, ProductCategoryID, Name FROM Production.ProductSubcategory",
    "ProductCategory": "SELECT ProductCategoryID, Name FROM Production.ProductCategory",
    "ProductModel": "SELECT ProductModelID, Name FROM Production.ProductModel",
    "ProductCostHistory": "SELECT ProductID, StartDate, EndDate, StandardCost FROM Production.ProductCostHistory",
    # --- Personas y direcciones
    "Person": """SELECT BusinessEntityID, Title, FirstName, MiddleName, LastName, Suffix, EmailPromotion
        FROM Person.Person""",
    "EmailAddress": "SELECT BusinessEntityID, EmailAddress FROM Person.EmailAddress",
    "PersonPhone": "SELECT BusinessEntityID, PhoneNumber FROM Person.PersonPhone",
    "BusinessEntityAddress": "SELECT BusinessEntityID, AddressID, AddressTypeID FROM Person.BusinessEntityAddress",
    "AddressType": "SELECT AddressTypeID, Name FROM Person.AddressType",
    "Address": "SELECT AddressID, AddressLine1, AddressLine2, City, StateProvinceID, PostalCode FROM Person.Address",
    "StateProvince": """SELECT StateProvinceID, StateProvinceCode, Name, CountryRegionCode, TerritoryID
        FROM Person.StateProvince""",
    "CountryRegion": "SELECT CountryRegionCode, Name FROM Person.CountryRegion",
    # --- Recursos humanos
    "Employee": """SELECT BusinessEntityID, NationalIDNumber, LoginID, JobTitle, BirthDate, MaritalStatus,
        Gender, HireDate, SalariedFlag, CurrentFlag FROM HumanResources.Employee""",
    "EmployeeDepartmentHistory": """SELECT BusinessEntityID, DepartmentID, EndDate
        FROM HumanResources.EmployeeDepartmentHistory""",
    "Department": "SELECT DepartmentID, Name FROM HumanResources.Department",
}


def extraer_todo(motor_oltp, log=print) -> dict[str, pd.DataFrame]:
    """Ejecuta todas las consultas y devuelve {nombre: DataFrame}."""
    datos = {}
    with motor_oltp.connect() as cn:
        for nombre, sql in CONSULTAS.items():
            t0 = time.perf_counter()
            datos[nombre] = pd.read_sql(sql, cn)  # coerce_float convierte money/decimal a float
            log(f"  {nombre:<28} {len(datos[nombre]):>7,} filas  ({time.perf_counter() - t0:.1f} s)")
    return datos
