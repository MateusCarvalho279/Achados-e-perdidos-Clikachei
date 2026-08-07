"""Validação de entrada das Controllers — leve, sem depender de Pydantic."""

from __future__ import annotations

import re
from datetime import date, datetime

from .errors import ApiError

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def require_json(request) -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Corpo da requisição deve ser um JSON válido.", 400)
    return data


def require_fields(data: dict, *fields: str) -> None:
    missing = [f for f in fields if not str(data.get(f, "")).strip()]
    if missing:
        raise ApiError(f"Campo(s) obrigatório(s) ausente(s): {', '.join(missing)}.", 400)


def normalize_email(value: str) -> str:
    value = str(value).strip().lower()
    if not _EMAIL_RE.match(value):
        raise ApiError("E-mail inválido.", 400)
    return value


def require_min_length(value: str, minimum: int, field_name: str) -> str:
    value = str(value)
    if len(value) < minimum:
        raise ApiError(f"{field_name} deve ter pelo menos {minimum} caracteres.", 400)
    return value


def parse_date(value: str, field_name: str = "data") -> date:
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise ApiError(f"{field_name} inválida — use o formato AAAA-MM-DD.", 400) from None
