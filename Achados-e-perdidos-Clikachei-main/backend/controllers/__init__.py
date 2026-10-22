"""Camada Controller — Blueprints Flask que recebem as requisições da API."""

from flask import Flask

from .admin_controller import admin_bp
from .auth_controller import auth_bp
from .claim_controller import claim_bp
from .item_controller import item_bp
from .lost_report_controller import lost_report_bp
from .notification_controller import notification_bp
from .report_controller import report_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(auth_bp)
    app.register_blueprint(item_bp)
    app.register_blueprint(claim_bp)
    app.register_blueprint(lost_report_bp)
    app.register_blueprint(notification_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(report_bp)

