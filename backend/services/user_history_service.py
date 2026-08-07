"""
Service — caso de uso avançado #3: histórico de reivindicações de UM usuário
("Meus Pedidos"), com filtro por status e ordenação — `sp_historico_usuario`.
"""

from __future__ import annotations

from pymysql.connections import Connection

from ..repositories import ClaimRepository

STATUS_VALIDOS = {"approved", "rejected", "pending_review"}
ORDENACOES_VALIDAS = {"recentes", "antigos"}


class UserHistoryService:
    @staticmethod
    def history(conn: Connection, *, user_id: int, status: str | None = None, ordenacao: str | None = None) -> list[dict]:
        if status not in STATUS_VALIDOS:
            status = None
        if ordenacao not in ORDENACOES_VALIDAS:
            ordenacao = "recentes"

        rows = ClaimRepository.historico_usuario(conn, user_id=user_id, status=status, ordenacao=ordenacao)
        for row in rows:
            row["created_at"] = str(row["created_at"])
        return rows
