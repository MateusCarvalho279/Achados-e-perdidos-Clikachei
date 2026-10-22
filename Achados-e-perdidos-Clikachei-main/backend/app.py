"""
Fábrica da aplicação Flask.

Monta a API REST em `/api/*`, serve o frontend estático na raiz e registra o
tratamento uniforme de erros. Um único processo entrega backend e interface —
sem CORS, sem proxy, sem build.
"""

from __future__ import annotations

import pymysql
from flask import Flask, jsonify, send_from_directory
from werkzeug.exceptions import HTTPException

from . import config as cfg
from .controllers import register_blueprints
from .errors import ApiError
from .extensions import db as db_ext
from .seed import run_seed


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.from_object(cfg.Config)

    db_ext.init_app(app)
    register_blueprints(app)
    _register_error_handlers(app)
    _register_frontend_routes(app)

    @app.get("/api/health")
    def health():
        return jsonify({
            "status": "ok",
            "service": "achados-e-perdidos",
            "auto_approve_threshold": app.config["AUTO_APPROVE_THRESHOLD"],
            "max_claim_attempts": app.config["MAX_CLAIM_ATTEMPTS"],
        })

    with app.app_context():
        run_seed()

    return app


def _register_frontend_routes(app: Flask) -> None:
    @app.get("/")
    def index():
        return send_from_directory(cfg.FRONTEND_DIR, "index.html")

    @app.get("/<path:filename>")
    def frontend_files(filename: str):
        # Guarda explícita: a rota curinga nunca deve responder por /api/*,
        # mesmo que a ordenação de rotas do Werkzeug já priorize o blueprint.
        if filename.startswith("api/"):
            from flask import abort
            abort(404)
        return send_from_directory(cfg.FRONTEND_DIR, filename)


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError):
        return jsonify({"detail": error.message}), error.status_code

    @app.errorhandler(pymysql.err.IntegrityError)
    def handle_integrity_error(error: pymysql.err.IntegrityError):
        return jsonify({"detail": "Conflito de dados — verifique se o registro já existe."}), 409

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        return jsonify({"detail": error.description}), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        app.logger.exception("Erro não tratado")
        return jsonify({"detail": "Erro inesperado no servidor."}), 500
