"""
Controller: /api/admin/* — cadastro de itens (CRUD básico) e auditoria de
reivindicações (caso de uso avançado #2, via `sp_listar_reivindicacoes`).

Todas as rotas exigem perfil de administrador (`@admin_required` → 403 para
usuário comum).
"""

from __future__ import annotations

from flask import Blueprint, Response, g, jsonify, request

from ..auth_guard import admin_required
from ..errors import ApiError
from ..extensions.db import get_db
from ..services import (
    AdminStatsService,
    ClaimReviewService,
    DonationService,
    ExportService,
    ItemAdminService,
    PickupService,
    UserAdminService,
)
from ..validation import parse_date, require_fields, require_json

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


# --------------------------------------------------------------------------- #
# Itens (CRUD básico e edição)
# --------------------------------------------------------------------------- #


@admin_bp.post("/items")
@admin_required
def create_item():
    data = require_json(request)
    require_fields(data, "title", "category", "found_date")

    attributes_raw = data.get("attributes") or []
    if not isinstance(attributes_raw, list) or not attributes_raw:
        raise ApiError("O item precisa de pelo menos uma característica.", 400)

    attributes = []
    for entry in attributes_raw:
        require_fields(entry, "question", "expected_answer")
        attributes.append({
            "question": str(entry["question"]).strip(),
            "expected_answer": str(entry["expected_answer"]).strip(),
            "field_type": entry.get("field_type") or "text",
            "options": entry.get("options") or None,
            "placeholder": entry.get("placeholder"),
            "alternatives": entry.get("alternatives") or [],
            "weight": int(entry.get("weight") or 1),
            "is_critical": bool(entry.get("is_critical", False)),
            "tolerance": float(entry.get("tolerance") or 0.1),
        })

    payload = {
        "title": str(data["title"]).strip(),
        "category": str(data["category"]).strip(),
        "icon": data.get("icon") or "📦",
        "found_date": parse_date(data["found_date"], "Data em que foi encontrado"),
        "found_location": data.get("found_location"),
        "internal_notes": data.get("internal_notes"),
        "attributes": attributes,
    }

    result = ItemAdminService.create_item(get_db(), admin_id=g.current_user["id"], payload=payload)
    return jsonify(result), 201


@admin_bp.put("/items/<code>")
@admin_required
def update_item(code: str):
    data = require_json(request)
    require_fields(data, "title", "category", "found_date")

    payload = {
        "title": str(data["title"]).strip(),
        "category": str(data["category"]).strip(),
        "icon": data.get("icon") or "📦",
        "found_date": parse_date(data["found_date"], "Data em que foi encontrado"),
        "found_location": data.get("found_location"),
        "internal_notes": data.get("internal_notes"),
        "status": data.get("status"),
    }

    result = ItemAdminService.update_item(get_db(), code, payload)
    return jsonify(result), 200


@admin_bp.get("/items/<code>/label")
@admin_required
def item_label(code: str):
    return jsonify(ItemAdminService.get_print_label(get_db(), code)), 200


@admin_bp.get("/items")
@admin_required
def list_items():
    rows = ItemAdminService.list_all(get_db())
    return jsonify([_serialize_admin_item(row) for row in rows]), 200


@admin_bp.get("/items/<code>/attributes")
@admin_required
def item_attributes(code: str):
    return jsonify(ItemAdminService.get_attributes(get_db(), code)), 200


@admin_bp.delete("/items/<code>")
@admin_required
def archive_item(code: str):
    archived_code = ItemAdminService.archive_item(get_db(), code)
    return jsonify({"message": f"Item {archived_code} arquivado."}), 200


# --------------------------------------------------------------------------- #
# Baixa e Retirada Presencial (Check-out na Secretaria)
# --------------------------------------------------------------------------- #


@admin_bp.get("/pickup/validate")
@admin_required
def validate_pickup():
    code = request.args.get("code")
    if not code:
        raise ApiError("Código de retirada não informado.", 400)
    result = PickupService.validate(get_db(), code)
    return jsonify(result), 200


@admin_bp.post("/pickup/deliver")
@admin_required
def deliver_pickup():
    data = require_json(request)
    require_fields(data, "pickup_code", "delivered_to_name", "delivered_to_doc")
    result = PickupService.deliver(
        get_db(),
        pickup_code=data["pickup_code"],
        delivered_to_name=data["delivered_to_name"],
        delivered_to_doc=data["delivered_to_doc"],
        notes=data.get("notes"),
        admin_id=g.current_user["id"],
    )
    return jsonify(result), 200


# --------------------------------------------------------------------------- #
# Gestão de Doações (+90 dias)
# --------------------------------------------------------------------------- #


@admin_bp.get("/donations/eligible")
@admin_required
def eligible_donations():
    days = request.args.get("days", default=90, type=int)
    rows = DonationService.list_eligible(get_db(), days_limit=days)
    return jsonify(rows), 200


@admin_bp.post("/donations/batch")
@admin_required
def donate_batch():
    data = require_json(request)
    require_fields(data, "item_ids", "entity_name")
    result = DonationService.donate_batch(
        get_db(),
        item_ids=data["item_ids"],
        entity_name=data["entity_name"],
        admin_id=g.current_user["id"],
    )
    return jsonify(result), 200


# --------------------------------------------------------------------------- #
# Exportação de Relatórios em CSV
# --------------------------------------------------------------------------- #


@admin_bp.get("/reports/export")
@admin_required
def export_reports():
    rtype = request.args.get("type", "items")
    csv_content, filename = ExportService.export_csv(get_db(), rtype)
    return Response(
        csv_content,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# --------------------------------------------------------------------------- #
# Gestão de Usuários
# --------------------------------------------------------------------------- #


@admin_bp.get("/users")
@admin_required
def list_users():
    search = request.args.get("search")
    rows = UserAdminService.list_users(get_db(), search=search)
    return jsonify(rows), 200


@admin_bp.post("/users/<int:user_id>/toggle-role")
@admin_required
def toggle_user_role(user_id: int):
    result = UserAdminService.toggle_role(get_db(), target_user_id=user_id, current_admin_id=g.current_user["id"])
    return jsonify(result), 200


# --------------------------------------------------------------------------- #
# Indicadores
# --------------------------------------------------------------------------- #


@admin_bp.get("/stats")
@admin_required
def stats():
    return jsonify(AdminStatsService.stats(get_db())), 200


# --------------------------------------------------------------------------- #
# Reivindicações
# --------------------------------------------------------------------------- #


@admin_bp.get("/claims")
@admin_required
def list_claims():
    args = request.args
    only_pending = args.get("only_pending", "false").lower() == "true"
    status = "pending_review" if only_pending else args.get("status")
    result = ClaimReviewService.list_claims(get_db(), status=status, item_code=args.get("item_code"))
    return jsonify(result), 200


@admin_bp.post("/claims/<int:claim_id>/review")
@admin_required
def review_claim(claim_id: int):
    data = require_json(request)
    approve = bool(data.get("approve", False))
    result = ClaimReviewService.review(get_db(), claim_id=claim_id, approve=approve, admin_id=g.current_user["id"])
    return jsonify(result), 200


def _serialize_admin_item(row: dict) -> dict:
    return {
        "id": row["id"], "public_code": row["public_code"], "title": row["title"],
        "category": row["category"], "icon": row["icon"], "found_date": str(row["found_date"]),
        "found_location": row["found_location"], "internal_notes": row["internal_notes"],
        "status": row["status"], "pickup_code": row["pickup_code"],
        "claimed_at": str(row["claimed_at"]) if row["claimed_at"] else None,
        "question_count": row.get("question_count", 0),
        "delivered_to_name": row.get("delivered_to_name"),
        "delivered_at": str(row["delivered_at"]) if row.get("delivered_at") else None,
        "donation_entity": row.get("donation_entity"),
        "donated_at": str(row["donated_at"]) if row.get("donated_at") else None,
    }

