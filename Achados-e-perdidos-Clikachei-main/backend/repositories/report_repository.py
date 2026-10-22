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

    @staticmethod
    def itens_para_doacao(conn: Connection, *, dias_limite: int = 90) -> list[dict]:
        """Itens disponíveis que ultrapassaram o limite de dias para doação."""
        return call_procedure(conn, "sp_itens_para_doacao", (dias_limite,))

    @staticmethod
    def buscar_alertas_perda(conn: Connection, *, user_id: int | None = None, status: str | None = None) -> list[dict]:
        """Lista alertas de perda via stored procedure."""
        return call_procedure(conn, "sp_buscar_alertas_perda", (user_id, status))

    @staticmethod
    def buscar_usuarios(conn: Connection, *, busca: str | None = None) -> list[dict]:
        """Lista usuários e indicadores via stored procedure."""
        return call_procedure(conn, "sp_buscar_usuarios", (busca,))

