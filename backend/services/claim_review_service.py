"""
Service — caso de uso avançado #2: auditoria e revisão manual de
reivindicações (painel admin). Lista via `sp_listar_reivindicacoes` (JOIN de
3 tabelas) e decide os pedidos que caíram na faixa intermediária de score.
"""

from __future__ import annotations

import json

from pymysql.connections import Connection

from ..errors import ApiError
from ..models import ClaimRequest
from ..repositories import ClaimRepository
from .reservation import reserve_item

STATUS_VALIDOS = {"approved", "rejected", "pending_review"}


class ClaimReviewService:
    @staticmethod
    def list_claims(conn: Connection, *, status: str | None = None, item_code: str | None = None) -> list[dict]:
        if status not in STATUS_VALIDOS:
            status = None
        rows = ClaimRepository.listar_reivindicacoes(conn, status=status, item_code=item_code)
        for row in rows:
            row["breakdown"] = _load_breakdown(row["breakdown"])
            row["created_at"] = str(row["created_at"])
        return rows

    @staticmethod
    def review(conn: Connection, *, claim_id: int, approve: bool, admin_id: int) -> dict:
        claim = ClaimRequest.find_by_id(conn, claim_id)
        if claim is None:
            raise ApiError("Reivindicação não encontrada.", 404)
        if claim["status"] != "pending_review":
            raise ApiError("Esta reivindicação já foi decidida.", 409)

        pickup_code = None
        if approve:
            pickup_code = reserve_item(conn, claim["item_id"], claim["user_id"])
            if pickup_code is None:
                raise ApiError("O item não está mais disponível para reivindicação.", 409)

        ClaimRequest.mark_reviewed(
            conn, claim_id, "approved" if approve else "rejected", pickup_code, admin_id
        )
        conn.commit()

        return {
            "status": "approved" if approve else "rejected",
            "pickup_code": pickup_code,
            "message": (
                f"Reivindicação aprovada. Código de retirada: {pickup_code}"
                if approve else "Reivindicação recusada."
            ),
        }


def _load_breakdown(raw) -> list[dict]:
    if isinstance(raw, list):
        return raw
    try:
        return json.loads(raw) if raw else []
    except (TypeError, ValueError):
        return []
