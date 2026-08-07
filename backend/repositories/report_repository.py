"""Repository: relatórios gerenciais do painel administrativo."""

from __future__ import annotations

from pymysql.connections import Connection

from ..extensions.db import call_procedure


class ReportRepository:
    @staticmethod
    def relatorio_categorias(conn: Connection) -> list[dict]:
        """
        Itens x reivindicações agrupados por categoria: total encontrado,
        total devolvido, taxa de recuperação e score médio das aprovações.
        """
        return call_procedure(conn, "sp_relatorio_categorias", ())

    @staticmethod
    def relatorio_locais(conn: Connection, *, limite: int = 10) -> list[dict]:
        """Ranking dos locais onde mais itens são encontrados."""
        return call_procedure(conn, "sp_relatorio_locais", (limite,))
