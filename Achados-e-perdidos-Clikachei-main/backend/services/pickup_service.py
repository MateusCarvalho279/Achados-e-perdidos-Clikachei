"""Service — validação e baixa de retirada presencial na secretaria."""

from __future__ import annotations

from pymysql.connections import Connection

from ..errors import ApiError
from ..models import LostItem, Notification


class PickupService:
    @staticmethod
    def validate(conn: Connection, pickup_code: str) -> dict:
        code = str(pickup_code).strip().upper()
        item = LostItem.find_by_pickup_code(conn, code)
        if item is None:
            raise ApiError("Código de retirada não encontrado.", 404)

        if item["status"] == "delivered":
            raise ApiError(
                f"Este item já foi entregue a {item.get('delivered_to_name')} em {item.get('delivered_at')}.", 409
            )
        if item["status"] != "claimed":
            raise ApiError(f"O item associado a este código está com situação '{item['status']}'.", 400)

        return {
            "public_code": item["public_code"],
            "title": item["title"],
            "category": item["category"],
            "icon": item["icon"],
            "found_date": str(item["found_date"]),
            "found_location": item["found_location"],
            "pickup_code": item["pickup_code"],
            "status": item["status"],
            "claimed_at": str(item["claimed_at"]) if item.get("claimed_at") else None,
            "claimer_name": item.get("claimer_name") or "Não identificado",
            "claimer_email": item.get("claimer_email") or "—",
        }

    @staticmethod
    def deliver(
        conn: Connection, *, pickup_code: str, delivered_to_name: str,
        delivered_to_doc: str, notes: str | None, admin_id: int,
    ) -> dict:
        code = str(pickup_code).strip().upper()
        item = LostItem.find_by_pickup_code(conn, code)
        if item is None:
            raise ApiError("Código de retirada não encontrado.", 404)
        if item["status"] != "claimed":
            raise ApiError(f"O item não está pronto para entrega (situação atual: {item['status']}).", 409)

        name = str(delivered_to_name).strip()
        doc = str(delivered_to_doc).strip()
        if not name:
            raise ApiError("Informe o nome completo de quem está retirando o item.", 400)
        if not doc:
            raise ApiError("Informe o documento / matrícula do aluno.", 400)

        success = LostItem.mark_delivered(
            conn, item["id"], delivered_to_name=name, delivered_to_doc=doc, delivered_notes=notes,
        )
        if not success:
            raise ApiError("Não foi possível registrar a entrega.", 500)

        if item.get("claimed_by_user_id"):
            Notification.create(
                conn, user_id=item["claimed_by_user_id"],
                title="✅ Devolução Concluída!",
                message=f"A entrega do item '{item['title']}' foi confirmada na secretaria para {name}.",
                link="meus-pedidos.html",
            )

        conn.commit()
        return {
            "message": f"Entrega do item '{item['title']}' registrada com sucesso para {name} (Doc: {doc}).",
            "public_code": item["public_code"],
            "delivered_at": "Agora",
        }
