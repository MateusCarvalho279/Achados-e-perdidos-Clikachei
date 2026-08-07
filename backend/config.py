"""
Configuração central da aplicação Flask.

Parâmetros de conexão com o MySQL, segurança e limiares do motor de
validação. Tudo pode ser sobrescrito por variável de ambiente.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
DATABASE_DIR = BASE_DIR / "database"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


def _load_or_create_secret() -> str:
    """Chave de assinatura dos JWT — gerada uma vez e persistida em disco."""
    env_secret = os.getenv("LOSTFOUND_SECRET")
    if env_secret:
        return env_secret

    key_file = DATA_DIR / ".secret_key"
    if key_file.exists():
        return key_file.read_text(encoding="utf-8").strip()

    generated = secrets.token_hex(32)
    key_file.write_text(generated, encoding="utf-8")
    return generated


class Config:
    # --- MySQL -------------------------------------------------------------
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "achados_perdidos")

    # --- Segurança -----------------------------------------------------------
    SECRET_KEY = _load_or_create_secret()
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_HOURS = 12
    PBKDF2_ITERATIONS = 260_000

    DEFAULT_ADMIN_EMAIL = os.getenv("LOSTFOUND_ADMIN_EMAIL", "admin@cotemig.com.br")
    DEFAULT_ADMIN_PASSWORD = os.getenv("LOSTFOUND_ADMIN_PASSWORD", "admin123")

    # --- Motor de validação ---------------------------------------------------
    AUTO_APPROVE_THRESHOLD = 0.75
    MANUAL_REVIEW_THRESHOLD = 0.55
    CRITICAL_FIELD_THRESHOLD = 0.85
    MAX_CLAIM_ATTEMPTS = 3

    # --- Servidor ------------------------------------------------------------
    HOST = os.getenv("LOSTFOUND_HOST", "127.0.0.1")
    PORT = int(os.getenv("LOSTFOUND_PORT", "8000"))
