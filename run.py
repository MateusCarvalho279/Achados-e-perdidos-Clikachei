"""
Inicializador do servidor Flask.

Uso:
    python run.py            # sobe em http://127.0.0.1:8000
    python run.py --reload   # modo desenvolvimento com hot reload
    python run.py --reset    # recria o schema + procedures no MySQL antes de subir
"""

from __future__ import annotations

import sys

import pymysql

from backend import config
from backend.app import create_app


def _reset_database() -> None:
    """Reexecuta `database/01_schema.sql` e `02_procedures.sql` no MySQL."""
    print("Reiniciando o banco de dados (schema + procedures)...")
    conn = pymysql.connect(
        host=config.Config.DB_HOST, port=config.Config.DB_PORT,
        user=config.Config.DB_USER, password=config.Config.DB_PASSWORD,
        charset="utf8mb4", autocommit=True,
    )
    try:
        for filename in ("01_schema.sql", "02_procedures.sql"):
            script = (config.DATABASE_DIR / filename).read_text(encoding="utf-8")
            with conn.cursor() as cursor:
                for statement in _split_statements(script):
                    cursor.execute(statement)
    finally:
        conn.close()
    print("Banco de dados reiniciado.")


def _split_statements(script: str) -> list[str]:
    """
    Divide o script em instruções executáveis, respeitando os blocos
    `DELIMITER $$ ... $$` usados pelas stored procedures — o PyMySQL executa
    uma instrução por vez e não entende `DELIMITER` (é um comando do cliente
    `mysql`, não do servidor).

    Comentários de linha inteira (`-- ...`) e linhas em branco são descartados
    ANTES de entrar no buffer: se entrassem, um bloco de comentário na frente
    de um CREATE TABLE faria a instrução inteira começar com "--" e ser
    perdida por engano.
    """
    statements: list[str] = []
    buffer: list[str] = []
    delimiter = ";"

    for raw_line in script.splitlines():
        stripped = raw_line.strip()

        if stripped.upper().startswith("DELIMITER"):
            pending = "".join(buffer).strip()
            if pending:
                statements.append(pending)
            buffer = []
            delimiter = stripped.split()[1]
            continue

        if not stripped or stripped.startswith("--"):
            continue

        buffer.append(raw_line + "\n")
        joined = "".join(buffer).rstrip()
        if joined.endswith(delimiter):
            statement = joined[: -len(delimiter)].strip()
            if statement:
                statements.append(statement)
            buffer = []

    tail = "".join(buffer).strip()
    if tail:
        statements.append(tail.rstrip(";"))

    return statements


def main() -> None:
    if "--reset" in sys.argv:
        _reset_database()

    reload_enabled = "--reload" in sys.argv

    app = create_app()

    print("=" * 68)
    print("  ACHADOS E PERDIDOS - Colégio COTEMIG (Flask + MySQL)")
    print("=" * 68)
    print(f"  Aplicação .......: http://{config.Config.HOST}:{config.Config.PORT}")
    print(f"  Painel admin ....: http://{config.Config.HOST}:{config.Config.PORT}/admin.html")
    print(f"  Banco MySQL .....: {config.Config.DB_USER}@{config.Config.DB_HOST}:{config.Config.DB_PORT}/{config.Config.DB_NAME}")
    print("-" * 68)
    print("  Contas de demonstração")
    print(f"    admin : {config.Config.DEFAULT_ADMIN_EMAIL} / {config.Config.DEFAULT_ADMIN_PASSWORD}")
    print("    aluno : aluno@cotemig.com.br / aluno123")
    print("=" * 68)

    app.run(
        host=config.Config.HOST, port=config.Config.PORT,
        debug=reload_enabled, use_reloader=reload_enabled, threaded=True,
    )


if __name__ == "__main__":
    main()
