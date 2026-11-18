"""CARGA: crea la base destino y escribe dimensiones y hechos.

Es una carga completa (full load): el DDL borra y recrea las tablas, y luego se
insertan primero las dimensiones y al final los hechos, para que las llaves
foráneas siempre encuentren su fila en la dimensión.
"""
import re
import time
from pathlib import Path

from etl.conexion import conexion_directa

DDL = Path(__file__).resolve().parent.parent / "sql" / "01_crear_datamart.sql"


def ejecutar_ddl(log=print) -> None:
    lotes = [b.strip() for b in re.split(r"^\s*GO\s*$", DDL.read_text(encoding="utf-8"), flags=re.M | re.I)]
    cn = conexion_directa("master")
    try:
        cur = cn.cursor()
        for lote in filter(None, lotes):
            cur.execute(lote)
    finally:
        cn.close()
    log(f"  Script DDL ejecutado: {DDL.name}")


def cargar(tablas: dict, motor_destino, log=print) -> None:
    """tablas = {nombre: DataFrame} en orden de carga."""
    for nombre, df in tablas.items():
        t0 = time.perf_counter()
        df.to_sql(nombre, motor_destino, schema="dbo", if_exists="append", index=False, chunksize=5000)
        log(f"  {nombre:<24} {len(df):>7,} filas  ({time.perf_counter() - t0:.1f} s)")
