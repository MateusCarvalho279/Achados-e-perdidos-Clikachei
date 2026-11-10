"""
Inicializador do servidor Flask.

Uso:
    python run.py            # sobe em http://127.0.0.1:8000
    python run.py --reload   # modo desenvolvimento com hot reload
    python run.py --reset    # APAGA e recria o schema + procedures antes de subir

Na primeira execução as tabelas e procedures são criadas automaticamente.
"""

from __future__ import annotations

import sys

import pymysql

from backend.app import create_app
from backend.config import Config
from backend.database_setup import preparar_banco


def main() -> None:
    try:
        if "--reset" in sys.argv:
            print("Recriando o banco de dados (schema + procedures)...")
            preparar_banco(resetar=True)
        app = create_app()
    except pymysql.err.OperationalError as erro:
        print("\n[ERRO] Não foi possível conectar ao MySQL "
              f"em {Config.DB_USER}@{Config.DB_HOST}:{Config.DB_PORT}.")
        print(f"       Detalhe: {erro}")
        print("       Verifique se o MySQL está rodando e se o arquivo .env está correto.\n")
        sys.exit(1)

    reload_enabled = "--reload" in sys.argv or Config.DEBUG

    print("=" * 68)
    print("  ACHADOS E PERDIDOS - Colégio COTEMIG (Flask + MySQL)")
    print("=" * 68)
    print(f"  Aplicação .......: http://{Config.HOST}:{Config.PORT}")
    print(f"  Painel admin ....: http://{Config.HOST}:{Config.PORT}/admin.html")
    print(f"  Banco MySQL .....: {Config.DB_USER}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}")
    print("-" * 68)
    print("  Contas de demonstração")
    print(f"    admin : {Config.DEFAULT_ADMIN_EMAIL} / {Config.DEFAULT_ADMIN_PASSWORD}")
    print("    aluno : aluno@cotemig.com.br / aluno123")
    print("=" * 68)

    app.run(
        host=Config.HOST, port=Config.PORT,
        debug=reload_enabled, use_reloader=reload_enabled, threaded=True,
    )


if __name__ == "__main__":
    main()
