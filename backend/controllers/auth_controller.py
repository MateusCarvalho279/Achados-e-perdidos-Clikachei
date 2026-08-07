"""Controller: /api/auth/* — cadastro, login e perfil."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from ..auth_guard import login_required
from ..extensions.db import get_db
from ..services import AuthService
from ..validation import normalize_email, require_fields, require_json, require_min_length

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/register")
def register():
    data = require_json(request)
    require_fields(data, "name", "email", "password")
    email = normalize_email(data["email"])
    password = require_min_length(data["password"], 6, "Senha")
    name = " ".join(str(data["name"]).split())
    require_min_length(name, 3, "Nome")

    result = AuthService.register(get_db(), name=name, email=email, password=password)
    return jsonify(result), 201


@auth_bp.post("/login")
def login():
    data = require_json(request)
    require_fields(data, "email", "password")
    result = AuthService.login(get_db(), email=data["email"], password=data["password"])
    return jsonify(result), 200


@auth_bp.get("/me")
@login_required
def me():
    return jsonify(AuthService.profile(g.current_user)), 200
