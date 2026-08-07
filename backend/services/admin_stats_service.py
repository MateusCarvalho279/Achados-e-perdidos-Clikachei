"""Service — indicadores do painel administrativo (contagens simples de uma tabela)."""

from __future__ import annotations

from pymysql.connections import Connection

from ..models import ClaimRequest, LostItem, User


class AdminStatsService:
    @staticmethod
    def stats(conn: Connection) -> dict:
        return {
            "items_available": LostItem.count_by_status(conn, "available"),
            "items_claimed": LostItem.count_by_status(conn, "claimed"),
            "claims_total": ClaimRequest.count_all(conn),
            "claims_pending": ClaimRequest.count_by_status(conn, "pending_review"),
            "users_total": User.count_by_role(conn, "user"),
        }
