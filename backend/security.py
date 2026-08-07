"""
Primitivas de segurança implementadas com a stdlib.

Evita dependências externas (passlib / PyJWT) sem abrir mão de práticas
corretas: PBKDF2-HMAC-SHA256 com salt aleatório por usuário e comparação em
tempo constante para senhas; JWT HS256 assinado para as sessões.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import string
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any

from flask import current_app

# --------------------------------------------------------------------------- #
# Senhas
# --------------------------------------------------------------------------- #


def hash_password(password: str) -> str:
    """Deriva o hash no formato `pbkdf2_sha256$<iter>$<salt>$<hash>`."""
    iterations = current_app.config["PBKDF2_ITERATIONS"]
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
    )
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Confere a senha contra o hash salvo, em tempo constante."""
    try:
        algorithm, iterations, salt, expected = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations)
        )
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(digest.hex(), expected)


# --------------------------------------------------------------------------- #
# JWT (HS256)
# --------------------------------------------------------------------------- #


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(message: str) -> str:
    secret = current_app.config["SECRET_KEY"]
    signature = hmac.new(secret.encode("utf-8"), message.encode("ascii"), hashlib.sha256).digest()
    return _b64url_encode(signature)


def create_access_token(payload: dict[str, Any]) -> str:
    """Emite um JWT HS256 com expiração de `JWT_EXPIRATION_HOURS`."""
    hours = current_app.config["JWT_EXPIRATION_HOURS"]
    now = datetime.now(timezone.utc)
    body = {
        **payload,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=hours)).timestamp()),
    }
    header = {"alg": current_app.config["JWT_ALGORITHM"], "typ": "JWT"}

    segments = [
        _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8")),
        _b64url_encode(json.dumps(body, separators=(",", ":")).encode("utf-8")),
    ]
    signing_input = ".".join(segments)
    return f"{signing_input}.{_sign(signing_input)}"


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Valida assinatura e expiração; devolve o payload ou `None`."""
    try:
        header_b64, payload_b64, signature = token.split(".")
    except (ValueError, AttributeError):
        return None

    signing_input = f"{header_b64}.{payload_b64}"
    if not hmac.compare_digest(_sign(signing_input), signature):
        return None

    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except (ValueError, json.JSONDecodeError):
        return None

    if payload.get("exp", 0) < datetime.now(timezone.utc).timestamp():
        return None
    return payload


# --------------------------------------------------------------------------- #
# Códigos
# --------------------------------------------------------------------------- #

_CODE_LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ"  # sem I/O para não confundir com 1/0
_CODE_DIGITS = "23456789"                   # sem 0/1 pelo mesmo motivo
_CONNECTIVES = {"de", "da", "do", "das", "dos", "e", "a", "o", "em", "com", "para"}


def generate_pickup_code() -> str:
    """Gera um código de retirada no formato `REC-9842-XYZ` (CSPRNG)."""
    digits = "".join(secrets.choice(_CODE_DIGITS) for _ in range(4))
    letters = "".join(secrets.choice(_CODE_LETTERS) for _ in range(3))
    return f"REC-{digits}-{letters}"


def _base_letters(word: str) -> str:
    """Letras do alfabeto de uma palavra, sem acento (NFKD descarta a marca combinante)."""
    decomposed = unicodedata.normalize("NFKD", word)
    return "".join(c for c in decomposed if c.isalpha())


def generate_public_code(title: str, year: int, sequence: int) -> str:
    """
    Deriva o código público a partir das iniciais do título, ignorando
    conectivos ("Fone de Ouvido" -> "FO", não "FD").

    Título com duas ou mais palavras: uma letra de cada uma das duas
    primeiras ("Garrafa Térmica" -> "GT"). Título de uma palavra só: as duas
    primeiras letras dela ("Carteira" -> "CA", "Smartphone" -> "SM") — do
    contrário sobraria uma única letra, fácil de colidir com outro item.
    """
    words = [
        word for word in title.replace("-", " ").split()
        if word and word.lower() not in _CONNECTIVES
    ]
    if not words:
        words = title.replace("-", " ").split()

    if len(words) == 1:
        initials = _base_letters(words[0])[:2].upper()
    else:
        initials = "".join(_base_letters(word)[:1] for word in words[:2]).upper()

    initials = "".join(c for c in initials if c in string.ascii_uppercase)
    return f"{initials or 'IT'}-{year}-{sequence:03d}"
