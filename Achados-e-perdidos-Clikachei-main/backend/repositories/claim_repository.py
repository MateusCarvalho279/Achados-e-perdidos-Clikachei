"""
Repository: reivindicações.

Cobre dois casos de uso distintos, cada um com sua própria procedure:
  * `sp_listar_reivindicacoes` — auditoria do admin (JOIN de 3 tabelas).
  * `sp_historico_usuario`     — "Meus Pedidos" do aluno (JOIN + filtro + ordenação).
"""

from __future__ import annotations

from pymysql.connections import Connection

from ..extensions.db import call_procedure


class ClaimRepository:
    @staticmethod
    def listar_reivindicacoes(conn: Connection, *, status: str | None, item_code: str | None) -> list[dict]:
        """Trilha de auditoria completa (painel admin): JOIN claim×item×user."""
        return call_procedure(conn, "sp_listar_reivindicacoes", (status, item_code))

    @staticmethod
    def historico_usuario(conn: Connection, *, user_id: int, status: str | None, ordenacao: str | None) -> list[dict]:
        """Histórico de reivindicações de UM usuário, filtrável e ordenável."""
        return call_procedure(conn, "sp_historico_usuario", (user_id, status, ordenacao))
