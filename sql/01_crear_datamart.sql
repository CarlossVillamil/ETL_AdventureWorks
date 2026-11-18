/* =====================================================================
   Proyecto AdventureWorks - Punto 4 (versión Python)
   Base de datos destino de los Data Marts Internet Sales y Reseller Sales.
   El ETL (main.py) ejecuta este script al inicio de cada carga completa:
   borra las tablas y las vuelve a crear vacías.
   ===================================================================== */

IF DB_ID('AdventureWorksDM2025') IS NULL
    CREATE DATABASE AdventureWorksDM2025;
GO
USE AdventureWorksDM2025;
GO

/* ---- Borrado en orden inverso a las llaves foráneas: hechos primero ---- */
DROP TABLE IF EXISTS dbo.FactInternetSales;
DROP TABLE IF EXISTS dbo.FactResellerSales;
DROP TABLE IF EXISTS dbo.DimCustomer;
DROP TABLE IF EXISTS dbo.DimReseller;
DROP TABLE IF EXISTS dbo.DimEmployee;
DROP TABLE IF EXISTS dbo.DimGeography;
DROP TABLE IF EXISTS dbo.DimProduct;
DROP TABLE IF EXISTS dbo.DimProductSubcategory;
DROP TABLE IF EXISTS dbo.DimProductCategory;
DROP TABLE IF EXISTS dbo.DimPromotion;
DROP TABLE IF EXISTS dbo.DimCurrency;
DROP TABLE IF EXISTS dbo.DimSalesTerritory;
DROP TABLE IF EXISTS dbo.DimDate;
GO

/* =========================== DIMENSIONES =========================== */

CREATE TABLE dbo.DimDate (
    DateKey            INT          NOT NULL PRIMARY KEY,   -- AAAAMMDD
    FullDate           DATE         NOT NULL UNIQUE,
    DayNumberOfWeek    TINYINT      NOT NULL,               -- 1 = domingo
    DayNameOfWeek      NVARCHAR(10) NOT NULL,
    DayNumberOfMonth   TINYINT      NOT NULL,
    DayNumberOfYear    SMALLINT     NOT NULL,
    WeekNumberOfYear   TINYINT      NOT NULL,
    MonthNumberOfYear  TINYINT      NOT NULL,
    MonthName          NVARCHAR(10) NOT NULL,
    CalendarQuarter    TINYINT      NOT NULL,
    CalendarSemester   TINYINT      NOT NULL,
    CalendarYear       SMALLINT     NOT NULL,
    YearMonth          CHAR(7)      NOT NULL,               -- AAAA-MM
    FiscalYear         SMALLINT     NOT NULL,               -- inicia en julio
    FiscalQuarter      TINYINT      NOT NULL,
    FiscalSemester     TINYINT      NOT NULL,
    IsWeekend          BIT          NOT NULL
);

CREATE TABLE dbo.DimProductCategory (
    ProductCategoryKey   INT          NOT NULL PRIMARY KEY,
    ProductCategoryID    INT          NOT NULL,             -- llave natural OLTP
    ProductCategoryName  NVARCHAR(50) NOT NULL
);

CREATE TABLE dbo.DimProductSubcategory (
    ProductSubcategoryKey   INT          NOT NULL PRIMARY KEY,
    ProductSubcategoryID    INT          NOT NULL,
    ProductSubcategoryName  NVARCHAR(50) NOT NULL,
    ProductCategoryKey      INT          NOT NULL REFERENCES dbo.DimProductCategory(ProductCategoryKey)
);

CREATE TABLE dbo.DimProduct (
    ProductKey             INT           NOT NULL PRIMARY KEY,
    ProductID              INT           NOT NULL,
    ProductNumber          NVARCHAR(25)  NOT NULL,
    ProductName            NVARCHAR(50)  NOT NULL,
    ProductSubcategoryKey  INT           NULL REFERENCES dbo.DimProductSubcategory(ProductSubcategoryKey),
    ModelName              NVARCHAR(50)  NOT NULL,
    Color                  NVARCHAR(15)  NOT NULL,
    Size                   NVARCHAR(5)   NOT NULL,
    SizeUnitMeasureCode    NVARCHAR(3)   NULL,
    Weight                 DECIMAL(8,2)  NULL,
    WeightUnitMeasureCode  NVARCHAR(3)   NULL,
    StandardCost           DECIMAL(19,4) NOT NULL,
    ListPrice              DECIMAL(19,4) NOT NULL,
    ProductLine            NVARCHAR(2)   NOT NULL,
    ProductLineName        NVARCHAR(20)  NOT NULL,
    Class                  NVARCHAR(2)   NOT NULL,
    Style                  NVARCHAR(2)   NOT NULL,
    DaysToManufacture      INT           NOT NULL,
    FinishedGoodsFlag      BIT           NOT NULL,
    SellStartDate          DATE          NOT NULL,
    SellEndDate            DATE          NULL,
    Status                 NVARCHAR(15)  NOT NULL
);

CREATE TABLE dbo.DimPromotion (
    PromotionKey       INT           NOT NULL PRIMARY KEY,
    SpecialOfferID     INT           NOT NULL,
    PromotionName      NVARCHAR(255) NOT NULL,
    DiscountPct        DECIMAL(10,4) NOT NULL,
    PromotionType      NVARCHAR(50)  NOT NULL,
    PromotionCategory  NVARCHAR(50)  NOT NULL,
    StartDate          DATE          NOT NULL,
    EndDate            DATE          NOT NULL,
    MinQty             INT           NOT NULL,
    MaxQty             INT           NULL
);

CREATE TABLE dbo.DimCurrency (
    CurrencyKey   INT          NOT NULL PRIMARY KEY,
    CurrencyCode  NCHAR(3)     NOT NULL,
    CurrencyName  NVARCHAR(50) NOT NULL
);

CREATE TABLE dbo.DimSalesTerritory (
    SalesTerritoryKey      INT          NOT NULL PRIMARY KEY,
    TerritoryID            INT          NOT NULL,
    SalesTerritoryRegion   NVARCHAR(50) NOT NULL,
    CountryRegionCode      NVARCHAR(3)  NOT NULL,
    SalesTerritoryCountry  NVARCHAR(50) NOT NULL,
    SalesTerritoryGroup    NVARCHAR(50) NOT NULL
);

CREATE TABLE dbo.DimGeography (
    GeographyKey       INT          NOT NULL PRIMARY KEY,
    City               NVARCHAR(30) NOT NULL,
    StateProvinceID    INT          NOT NULL,
    StateProvinceCode  NVARCHAR(3)  NOT NULL,
    StateProvinceName  NVARCHAR(50) NOT NULL,
    CountryRegionCode  NVARCHAR(3)  NOT NULL,
    CountryRegionName  NVARCHAR(50) NOT NULL,
    PostalCode         NVARCHAR(15) NOT NULL,
    SalesTerritoryKey  INT          NOT NULL REFERENCES dbo.DimSalesTerritory(SalesTerritoryKey)
);

CREATE TABLE dbo.DimCustomer (
    CustomerKey           INT           NOT NULL PRIMARY KEY,
    CustomerID            INT           NOT NULL,
    AccountNumber         NVARCHAR(10)  NOT NULL,
    GeographyKey          INT           NOT NULL REFERENCES dbo.DimGeography(GeographyKey),
    Title                 NVARCHAR(8)   NULL,
    FirstName             NVARCHAR(50)  NOT NULL,
    MiddleName            NVARCHAR(50)  NULL,
    LastName              NVARCHAR(50)  NOT NULL,
    FullName              NVARCHAR(160) NOT NULL,
    Suffix                NVARCHAR(10)  NULL,
    BirthDate             DATE          NULL,
    MaritalStatus         NVARCHAR(1)   NULL,
    MaritalStatusName     NVARCHAR(15)  NOT NULL,
    Gender                NVARCHAR(1)   NULL,
    GenderName            NVARCHAR(15)  NOT NULL,
    EmailAddress          NVARCHAR(50)  NULL,
    Phone                 NVARCHAR(25)  NULL,
    YearlyIncome          NVARCHAR(30)  NULL,
    TotalChildren         INT           NULL,
    NumberChildrenAtHome  INT           NULL,
    Education             NVARCHAR(40)  NULL,
    Occupation            NVARCHAR(100) NULL,
    HomeOwnerFlag         BIT           NULL,
    NumberCarsOwned       INT           NULL,
    EmailPromotion        INT           NOT NULL,
    AddressLine1          NVARCHAR(60)  NOT NULL,
    AddressLine2          NVARCHAR(60)  NULL,
    DateFirstPurchase     DATE          NULL
);

CREATE TABLE dbo.DimReseller (
    ResellerKey       INT           NOT NULL PRIMARY KEY,
    StoreID           INT           NOT NULL,
    AccountNumber     NVARCHAR(10)  NOT NULL,
    ResellerName      NVARCHAR(50)  NOT NULL,
    GeographyKey      INT           NOT NULL REFERENCES dbo.DimGeography(GeographyKey),
    BusinessType      NVARCHAR(5)   NULL,
    BusinessTypeName  NVARCHAR(40)  NOT NULL,
    Specialty         NVARCHAR(50)  NULL,
    YearOpened        INT           NULL,
    NumberEmployees   INT           NULL,
    SquareFeet        INT           NULL,
    Brands            NVARCHAR(30)  NULL,
    BankName          NVARCHAR(50)  NULL,
    AnnualSales       DECIMAL(19,4) NULL,
    AnnualRevenue     DECIMAL(19,4) NULL,
    AddressLine1      NVARCHAR(60)  NOT NULL,
    AddressLine2      NVARCHAR(60)  NULL
);

CREATE TABLE dbo.DimEmployee (
    EmployeeKey           INT           NOT NULL PRIMARY KEY,
    BusinessEntityID      INT           NOT NULL,
    NationalIDNumber      NVARCHAR(15)  NOT NULL,
    FirstName             NVARCHAR(50)  NOT NULL,
    MiddleName            NVARCHAR(50)  NULL,
    LastName              NVARCHAR(50)  NOT NULL,
    FullName              NVARCHAR(160) NOT NULL,
    JobTitle              NVARCHAR(50)  NOT NULL,
    DepartmentName        NVARCHAR(50)  NULL,
    LoginID               NVARCHAR(256) NOT NULL,
    HireDate              DATE          NOT NULL,
    BirthDate             DATE          NOT NULL,
    Gender                NCHAR(1)      NOT NULL,
    MaritalStatus         NCHAR(1)      NOT NULL,
    SalariedFlag          BIT           NOT NULL,
    CurrentFlag           BIT           NOT NULL,
    SalesPersonFlag       BIT           NOT NULL,
    SalesTerritoryRegion  NVARCHAR(50)  NULL,
    SalesQuota            DECIMAL(19,4) NULL,
    Bonus                 DECIMAL(19,4) NULL,
    CommissionPct         DECIMAL(10,4) NULL
);
GO

/* ============================ HECHOS ============================ */

CREATE TABLE dbo.FactInternetSales (
    ProductKey             INT           NOT NULL REFERENCES dbo.DimProduct(ProductKey),
    OrderDateKey           INT           NOT NULL REFERENCES dbo.DimDate(DateKey),
    DueDateKey             INT           NOT NULL REFERENCES dbo.DimDate(DateKey),
    ShipDateKey            INT           NOT NULL REFERENCES dbo.DimDate(DateKey),
    CustomerKey            INT           NOT NULL REFERENCES dbo.DimCustomer(CustomerKey),
    PromotionKey           INT           NOT NULL REFERENCES dbo.DimPromotion(PromotionKey),
    CurrencyKey            INT           NOT NULL REFERENCES dbo.DimCurrency(CurrencyKey),
    SalesTerritoryKey      INT           NOT NULL REFERENCES dbo.DimSalesTerritory(SalesTerritoryKey),
    SalesOrderNumber       NVARCHAR(25)  NOT NULL,   -- dimensión degenerada
    SalesOrderLineNumber   SMALLINT      NOT NULL,   -- dimensión degenerada
    RevisionNumber         TINYINT       NOT NULL,
    OrderQuantity          SMALLINT      NOT NULL,
    UnitPrice              DECIMAL(19,4) NOT NULL,
    ExtendedAmount         DECIMAL(19,4) NOT NULL,
    UnitPriceDiscountPct   DECIMAL(10,4) NOT NULL,
    DiscountAmount         DECIMAL(19,4) NOT NULL,
    ProductStandardCost    DECIMAL(19,4) NOT NULL,
    TotalProductCost       DECIMAL(19,4) NOT NULL,
    SalesAmount            DECIMAL(19,4) NOT NULL,
    TaxAmt                 DECIMAL(19,4) NOT NULL,
    Freight                DECIMAL(19,4) NOT NULL,
    CarrierTrackingNumber  NVARCHAR(25)  NULL,
    CustomerPONumber       NVARCHAR(25)  NULL,
    OrderDate              DATE          NOT NULL,
    DueDate                DATE          NOT NULL,
    ShipDate               DATE          NOT NULL,
    CONSTRAINT PK_FactInternetSales PRIMARY KEY (SalesOrderNumber, SalesOrderLineNumber)
);

CREATE TABLE dbo.FactResellerSales (
    ProductKey             INT           NOT NULL REFERENCES dbo.DimProduct(ProductKey),
    OrderDateKey           INT           NOT NULL REFERENCES dbo.DimDate(DateKey),
    DueDateKey             INT           NOT NULL REFERENCES dbo.DimDate(DateKey),
    ShipDateKey            INT           NOT NULL REFERENCES dbo.DimDate(DateKey),
    ResellerKey            INT           NOT NULL REFERENCES dbo.DimReseller(ResellerKey),
    EmployeeKey            INT           NOT NULL REFERENCES dbo.DimEmployee(EmployeeKey),
    PromotionKey           INT           NOT NULL REFERENCES dbo.DimPromotion(PromotionKey),
    CurrencyKey            INT           NOT NULL REFERENCES dbo.DimCurrency(CurrencyKey),
    SalesTerritoryKey      INT           NOT NULL REFERENCES dbo.DimSalesTerritory(SalesTerritoryKey),
    SalesOrderNumber       NVARCHAR(25)  NOT NULL,
    SalesOrderLineNumber   SMALLINT      NOT NULL,
    RevisionNumber         TINYINT       NOT NULL,
    OrderQuantity          SMALLINT      NOT NULL,
    UnitPrice              DECIMAL(19,4) NOT NULL,
    ExtendedAmount         DECIMAL(19,4) NOT NULL,
    UnitPriceDiscountPct   DECIMAL(10,4) NOT NULL,
    DiscountAmount         DECIMAL(19,4) NOT NULL,
    ProductStandardCost    DECIMAL(19,4) NOT NULL,
    TotalProductCost       DECIMAL(19,4) NOT NULL,
    SalesAmount            DECIMAL(19,4) NOT NULL,
    TaxAmt                 DECIMAL(19,4) NOT NULL,
    Freight                DECIMAL(19,4) NOT NULL,
    CarrierTrackingNumber  NVARCHAR(25)  NULL,
    CustomerPONumber       NVARCHAR(25)  NULL,
    OrderDate              DATE          NOT NULL,
    DueDate                DATE          NOT NULL,
    ShipDate               DATE          NOT NULL,
    CONSTRAINT PK_FactResellerSales PRIMARY KEY (SalesOrderNumber, SalesOrderLineNumber)
);
GO
