"""Conexiones a SQL Server con autenticación de Windows."""
from urllib.parse import quote_plus

import pyodbc
from sqlalchemy import create_engine

import config


def cadena_odbc(base: str) -> str:
    return (
        f"DRIVER={{{config.DRIVER}}};SERVER={config.SERVIDOR};DATABASE={base};"
        "Trusted_Connection=yes;TrustServerCertificate=yes;"
    )


def motor(base: str):
    """Motor SQLAlchemy; fast_executemany acelera los INSERT masivos."""
    url = "mssql+pyodbc:///?odbc_connect=" + quote_plus(cadena_odbc(base))
    return create_engine(url, fast_executemany=True)


def conexion_directa(base: str = "master") -> pyodbc.Connection:
    """Conexión pyodbc en autocommit, necesaria para CREATE DATABASE."""
    return pyodbc.connect(cadena_odbc(base), autocommit=True)
