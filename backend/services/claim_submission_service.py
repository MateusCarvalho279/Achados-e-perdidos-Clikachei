"""Service — submissão de uma reivindicação (fluxo central do sistema)."""

from __future__ import annotations

from flask import current_app
from pymysql.connections import Connection

from ..errors import ApiError
from ..matching import validate_claim
from ..models import ClaimRequest, ItemAttribute, LostItem
from .reservation import reserve_item


class ClaimSubmissionService:
    @staticmethod
    def limits(conn: Connection, *, item_code: str, user_id: int) -> dict:
        """Consulta rápida de tentativas restantes (usada pelo frontend)."""
        item = LostItem.find_by_code(conn, item_code)
        if item is None:
            raise ApiError("Item não encontrado.", 404)

        max_attempts = current_app.config["MAX_CLAIM_ATTEMPTS"]
        used = ClaimRequest.count_rejected(conn, item["id"], user_id)
        return {
            "max_attempts": max_attempts,
            "attempts_left": max(max_attempts - used, 0),
            "status": item["status"],
        }

    @staticmethod
    def submit(
        conn: Connection, *, item_code: str, user: dict, answers: dict, client_ip: str | None,
    ) -> dict:
        item = LostItem.find_by_code(conn, item_code)
        if item is None:
            raise ApiError("Item não encontrado.", 404)
        if item["status"] != "available":
            raise ApiError("Este item já foi reivindicado por outra pessoa.", 409)
        if ClaimRequest.has_pending(conn, item["id"], user["id"]):
            raise ApiError(
                "Você já tem um pedido em análise para este item. Aguarde o retorno.", 409
            )

        max_attempts = current_app.config["MAX_CLAIM_ATTEMPTS"]
        used_before = ClaimRequest.count_rejected(conn, item["id"], user["id"])
        if max_attempts - used_before <= 0:
            raise ApiError(
                "Limite de tentativas atingido para este item. "
                "Procure a secretaria presencialmente.", 429,
            )

        attributes = ItemAttribute.find_by_item_id(conn, item["id"])
        result = validate_claim(
            attributes, answers,
            auto_approve_threshold=current_app.config["AUTO_APPROVE_THRESHOLD"],
            manual_review_threshold=current_app.config["MANUAL_REVIEW_THRESHOLD"],
            critical_field_threshold=current_app.config["CRITICAL_FIELD_THRESHOLD"],
        )

        pickup_code = None
        if result.status == "approved":
            pickup_code = reserve_item(conn, item["id"], user["id"])
            if pickup_code is None:
                raise ApiError("Este item acabou de ser reivindicado por outra pessoa.", 409)

        ClaimRequest.create(
            conn, item_id=item["id"], user_id=user["id"], answers=answers,
            breakdown=result.breakdown_as_dicts(), score=result.score, status=result.status,
            pickup_code=pickup_code, client_ip=client_ip,
        )
        conn.commit()

        used_after = ClaimRequest.count_rejected(conn, item["id"], user["id"])
        remaining_after = max(max_attempts - used_after, 0)

        return {
            "status": result.status,
            "message": _build_message(result.status, remaining_after),
            "pickup_code": pickup_code,
            "item_title": item["title"],
            "attempts_left": remaining_after,
        }


def _build_message(status: str, remaining_after: int) -> str:
    # Mensagens deliberadamente vagas quanto ao motivo: dizer "você errou a
    # cor" entregaria o gabarito por eliminação.
    if status == "approved":
        return (
            "Identificação confirmada! Apresente o código abaixo na secretaria, "
            "junto de um documento com foto, para retirar seu item."
        )
    if status == "pending_review":
        return (
            "Sua descrição foi parcialmente compatível. O pedido foi encaminhado "
            "para análise manual — você será avisado pelo e-mail cadastrado."
        )
    if remaining_after > 0:
        return (
            "As características informadas não conferem com o item registrado. "
            f"Você ainda tem {remaining_after} tentativa(s)."
        )
    return (
        "As características não conferem e suas tentativas se esgotaram. "
        "Procure a secretaria presencialmente."
    )
