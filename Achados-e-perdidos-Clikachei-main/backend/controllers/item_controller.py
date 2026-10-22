"""
Controller: /api/items/* — vitrine pública e questionário de reivindicação.

`GET /api/items` implementa o caso de uso "Busca avançada de itens": todos os
filtros são opcionais via query string, a listagem sempre passa pela procedure
`sp_buscar_itens` na camada Repository (nunca SQL solto).
"""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from ..auth_guard import login_required
from ..extensions.db import get_db
from ..services import ItemAdminService, ItemSearchService

item_bp = Blueprint("items", __name__, url_prefix="/api/items")


@item_bp.get("")
def search_items():
    args = request.args
    result = ItemSearchService.search(
        get_db(),
        categoria=args.get("categoria"),
        texto=args.get("texto"),
        data_inicio=args.get("data_inicio"),
        data_fim=args.get("data_fim"),
        ordenacao=args.get("ordenacao"),
    )
    return jsonify(result), 200


@item_bp.get("/<code>")
def get_item(code: str):
    return jsonify(ItemAdminService.get_public_item(get_db(), code)), 200


@item_bp.get("/<code>/questionnaire")
@login_required
def get_questionnaire(code: str):
    return jsonify(ItemAdminService.get_questionnaire(get_db(), code, g.current_user)), 200
