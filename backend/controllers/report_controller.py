"""
Controller: /api/admin/reports/* — relatórios gerenciais (casos de uso
avançados #3 e #4), cada um sobre sua própria stored procedure.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..auth_guard import admin_required
from ..extensions.db import get_db
from ..services import CategoryReportService, LocationReportService

report_bp = Blueprint("reports", __name__, url_prefix="/api/admin/reports")


@report_bp.get("/categories")
@admin_required
def categories_report():
    return jsonify(CategoryReportService.report(get_db())), 200


@report_bp.get("/locations")
@admin_required
def locations_report():
    limite = request.args.get("limite", default=10, type=int)
    return jsonify(LocationReportService.report(get_db(), limite=limite)), 200
