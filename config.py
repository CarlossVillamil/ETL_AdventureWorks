"""Parámetros del ETL. Cambie SERVIDOR si su instancia no es localhost
(por ejemplo r"localhost\\SQLEXPRESS")."""

SERVIDOR = "localhost"
BD_OLTP = "AdventureWorks2025"        # fuente (base operacional)
BD_DESTINO = "AdventureWorksDM2025"   # destino: los dos data marts
BD_DW_OFICIAL = "AdventureWorksDW2025"  # solo para validar resultados

DRIVER = "ODBC Driver 18 for SQL Server"
