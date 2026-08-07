"""Decoradores de autenticação/autorização usados pelas Controllers."""

from __future__ import annotations

from functools import wraps

from flask import g, jsonify, request

from .extensions.db import get_db
from .models import User
from .security import decode_access_token

_SESSION_ERROR = {"detail": "Sessão inválida ou expirada. Faça login novamente."}


def _extract_bearer() -> str | None:
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


def _authenticate() -> dict | None:
    token = _extract_bearer()
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    return User.find_by_id(get_db(), payload["sub"])


def login_required(fn):
    """Exige um JWT válido; injeta o usuário em `flask.g.current_user`."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = _authenticate()
        if user is None:
            return jsonify(_SESSION_ERROR), 401
        g.current_user = user
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn):
    """Igual a `login_required`, mas exige perfil de administrador (403)."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = _authenticate()
        if user is None:
            return jsonify(_SESSION_ERROR), 401
        if user["role"] != "admin":
            return jsonify({"detail": "Acesso restrito a administradores."}), 403
        g.current_user = user
        return fn(*args, **kwargs)

    return wrapper
