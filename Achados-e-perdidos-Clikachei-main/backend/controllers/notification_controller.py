"""Controller: /api/notifications/* — central de notificações do usuário."""

from __future__ import annotations

from flask import Blueprint, g, jsonify

from ..auth_guard import login_required
from ..extensions.db import get_db
from ..services import NotificationService

notification_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


@notification_bp.get("")
@login_required
def list_notifications():
    result = NotificationService.list_user_notifications(get_db(), user_id=g.current_user["id"])
    return jsonify(result), 200


@notification_bp.post("/<int:notification_id>/read")
@login_required
def mark_read(notification_id: int):
    result = NotificationService.mark_read(get_db(), notification_id=notification_id, user_id=g.current_user["id"])
    return jsonify(result), 200


@notification_bp.post("/read-all")
@login_required
def mark_all_read():
    result = NotificationService.mark_all_read(get_db(), user_id=g.current_user["id"])
    return jsonify(result), 200
