"""
Camada de conexão com o MySQL.

Cada requisição recebe sua própria conexão (guardada em `flask.g`), fechada
automaticamente ao final via `teardown_appcontext`. `call_procedure` é o único
ponto de acesso usado pela camada Repository para chamar as stored procedures.
"""

from __future__ import annotations

import pymysql
import pymysql.cursors
from flask import current_app, g


def _connect() -> pymysql.connections.Connection:
    cfg = current_app.config
    return pymysql.connect(
        host=cfg["DB_HOST"],
        port=cfg["DB_PORT"],
        user=cfg["DB_USER"],
        password=cfg["DB_PASSWORD"],
        database=cfg["DB_NAME"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def get_db() -> pymysql.connections.Connection:
    """Devolve a conexão desta requisição, abrindo uma na primeira chamada."""
    if "db" not in g:
        g.db = _connect()
    return g.db


def close_db(_exception=None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_app(app) -> None:
    app.teardown_appcontext(close_db)


def call_procedure(conn: pymysql.connections.Connection, name: str, params: tuple = ()) -> list[dict]:
    """
    Executa `CALL nome(params)` e devolve todas as linhas do primeiro result
    set como uma lista de dicts.

    Único ponto por onde a camada Repository fala com o banco — nenhum SQL
    solto de filtro/JOIN/relatório deve existir fora de uma stored procedure.
    """
    with conn.cursor() as cursor:
        cursor.callproc(name, params)
        rows = cursor.fetchall()
    return rows
