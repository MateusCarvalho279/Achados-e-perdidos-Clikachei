"""Controller: /api/lost-reports/* — alertas de itens perdidos pelos alunos."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from ..auth_guard import login_required
from ..extensions.db import get_db
from ..services import LostReportService
from ..validation import parse_date, require_fields, require_json

lost_report_bp = Blueprint("lost_reports", __name__, url_prefix="/api/lost-reports")


@lost_report_bp.post("")
@login_required
def create_report():
    data = require_json(request)
    require_fields(data, "title", "category", "lost_date", "description")

    payload = {
        "title": data["title"],
        "category": data["category"],
        "lost_date": parse_date(data["lost_date"], "Data em que foi perdido"),
        "lost_location": data.get("lost_location"),
        "description": data["description"],
    }

    result = LostReportService.create(get_db(), user_id=g.current_user["id"], payload=payload)
    return jsonify(result), 201


@lost_report_bp.get("/mine")
@login_required
def my_reports():
    rows = LostReportService.list_mine(get_db(), user_id=g.current_user["id"])
    return jsonify(rows), 200


@lost_report_bp.get("/<int:report_id>/matches")
@login_required
def get_matches(report_id: int):
    matches = LostReportService.find_matches_for_report(get_db(), report_id=report_id, user_id=g.current_user["id"])
    return jsonify(matches), 200


@lost_report_bp.post("/<int:report_id>/cancel")
@login_required
def cancel_report(report_id: int):
    result = LostReportService.cancel(get_db(), report_id=report_id, user_id=g.current_user["id"])
    return jsonify(result), 200
