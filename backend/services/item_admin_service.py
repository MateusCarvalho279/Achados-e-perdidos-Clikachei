"""
Service — CRUD básico de itens (cadastro pelo admin, listagem, arquivamento)
e o questionário público de reivindicação.
"""

from __future__ import annotations

from datetime import date

from flask import current_app
from pymysql.connections import Connection

from ..errors import ApiError
from ..models import ClaimRequest, ItemAttribute, LostItem
from ..security import generate_public_code


class ItemAdminService:
    @staticmethod
    def create_item(conn: Connection, *, admin_id: int, payload: dict) -> dict:
        """Cadastra um item e seu gabarito sigiloso na mesma transação."""
        found_date: date = payload["found_date"]
        code = _next_public_code(conn, payload["title"], found_date.year)

        item_id = LostItem.create(
            conn, public_code=code, title=payload["title"], category=payload["category"],
            icon=payload.get("icon") or "📦", found_date=found_date,
            found_location=payload.get("found_location"),
            internal_notes=payload.get("internal_notes"), created_by=admin_id,
        )

        for order, attribute in enumerate(payload["attributes"]):
            ItemAttribute.create(
                conn, item_id=item_id, question=attribute["question"],
                field_type=attribute.get("field_type", "text"),
                options=attribute.get("options"), placeholder=attribute.get("placeholder"),
                expected_answer=attribute["expected_answer"],
                alternatives=attribute.get("alternatives", []),
                weight=attribute.get("weight", 1), is_critical=attribute.get("is_critical", False),
                tolerance=attribute.get("tolerance", 0.1), sort_order=order,
            )

        conn.commit()
        return {
            "id": item_id, "public_code": code, "questions": len(payload["attributes"]),
            "message": f"Item cadastrado com o código público {code}.",
        }

    @staticmethod
    def list_all(conn: Connection) -> list[dict]:
        """Visão administrativa bruta (todos os status, sem JOIN)."""
        rows = LostItem.find_all(conn)
        for row in rows:
            row["question_count"] = ItemAttribute.count_by_item_id(conn, row["id"])
        return rows

    @staticmethod
    def archive_item(conn: Connection, public_code: str) -> str:
        item = LostItem.find_by_code(conn, public_code)
        if item is None:
            raise ApiError("Item não encontrado.", 404)
        LostItem.archive(conn, item["id"])
        conn.commit()
        return item["public_code"]

    @staticmethod
    def get_attributes(conn: Connection, public_code: str) -> list[dict]:
        item = LostItem.find_by_code(conn, public_code)
        if item is None:
            raise ApiError("Item não encontrado.", 404)
        return ItemAttribute.find_by_item_id(conn, item["id"])

    @staticmethod
    def get_public_item(conn: Connection, public_code: str) -> dict:
        item = LostItem.find_by_code(conn, public_code)
        if item is None or item["status"] != "available":
            raise ApiError("Item não encontrado ou já reivindicado.", 404)
        return {
            "public_code": item["public_code"], "title": item["title"], "category": item["category"],
            "icon": item["icon"], "found_date": str(item["found_date"]),
            "found_location": item["found_location"], "status": item["status"],
            "question_count": ItemAttribute.count_by_item_id(conn, item["id"]),
        }

    @staticmethod
    def get_questionnaire(conn: Connection, public_code: str, user: dict) -> dict:
        item = LostItem.find_by_code(conn, public_code)
        if item is None:
            raise ApiError("Item não encontrado.", 404)
        if item["status"] != "available":
            raise ApiError("Este item já foi reivindicado e não está mais disponível.", 409)

        max_attempts = current_app.config["MAX_CLAIM_ATTEMPTS"]
        used = ClaimRequest.count_rejected(conn, item["id"], user["id"])
        remaining = max(max_attempts - used, 0)
        if remaining <= 0:
            raise ApiError(
                "Você atingiu o limite de tentativas para este item. "
                "Procure a secretaria presencialmente.", 429,
            )

        attributes = ItemAttribute.find_by_item_id(conn, item["id"])
        questions = [
            {
                "id": attribute["id"], "question": attribute["question"],
                "field_type": attribute["field_type"], "options": attribute["options"] or None,
                "placeholder": attribute["placeholder"], "is_critical": bool(attribute["is_critical"]),
            }
            for attribute in attributes
        ]

        return {
            "item": {
                "public_code": item["public_code"], "title": item["title"], "category": item["category"],
                "icon": item["icon"], "found_date": str(item["found_date"]),
                "found_location": item["found_location"], "status": item["status"],
                "question_count": len(questions),
            },
            "questions": questions, "attempts_used": used, "attempts_left": remaining,
        }


def _next_public_code(conn: Connection, title: str, year: int) -> str:
    used = LostItem.count_public_code_prefix(conn, year)
    for offset in range(1, 1000):
        candidate = generate_public_code(title, year, used + offset)
        if LostItem.find_by_code(conn, candidate) is None:
            return candidate
    raise ApiError("Não foi possível gerar um código público para o item.", 500)
