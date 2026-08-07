"""
Controller: /api/claims/* — submissão de reivindicação e histórico do usuário.

`GET /api/claims/mine` implementa o caso de uso "Histórico filtrável do
usuário" (aba Meus Pedidos): filtro por status + ordenação, via
`sp_historico_usuario`.
"""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from ..auth_guard import login_required
from ..extensions.db import get_db
from ..services import ClaimSubmissionService, UserHistoryService
from ..validation import require_fields, require_json

claim_bp = Blueprint("claims", __name__, url_prefix="/api/claims")


@claim_bp.post("")
@login_required
def submit_claim():
    data = require_json(request)
    require_fields(data, "item_code")
    answers = data.get("answers") or {}
    if not isinstance(answers, dict):
        answers = {}
    answers = {str(k): ("" if v is None else str(v)) for k, v in answers.items()}

    result = ClaimSubmissionService.submit(
        get_db(), item_code=data["item_code"], user=g.current_user, answers=answers,
        client_ip=request.remote_addr,
    )
    return jsonify(result), 200


@claim_bp.get("/mine")
@login_required
def my_claims():
    args = request.args
    result = UserHistoryService.history(
        get_db(), user_id=g.current_user["id"], status=args.get("status"),
        ordenacao=args.get("ordenacao"),
    )
    return jsonify(result), 200


@claim_bp.get("/limits/<code>")
@login_required
def claim_limits(code: str):
    result = ClaimSubmissionService.limits(get_db(), item_code=code, user_id=g.current_user["id"])
    return jsonify(result), 200
