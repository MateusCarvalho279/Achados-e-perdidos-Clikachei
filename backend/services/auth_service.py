"""Service — caso de uso: cadastro, login e perfil (CRUD básico de usuário)."""

from __future__ import annotations

from pymysql.connections import Connection

from ..errors import ApiError
from ..models import User
from ..security import create_access_token, hash_password, verify_password


class AuthService:
    @staticmethod
    def register(conn: Connection, *, name: str, email: str, password: str) -> dict:
        email = email.strip().lower()
        if User.find_by_email(conn, email):
            raise ApiError("Este e-mail já está cadastrado.", 409)

        user_id = User.create(conn, name.strip(), email, hash_password(password), role="user")
        conn.commit()

        return _issue_token(User.find_by_id(conn, user_id))

    @staticmethod
    def login(conn: Connection, *, email: str, password: str) -> dict:
        email = email.strip().lower()
        user = User.find_by_email(conn, email)
        # Mensagem genérica de propósito: não revela se o e-mail existe.
        if user is None or not verify_password(password, user["password_hash"]):
            raise ApiError("E-mail ou senha incorretos.", 401)
        return _issue_token(user)

    @staticmethod
    def profile(user: dict) -> dict:
        return _public_user(user)


def _issue_token(user: dict) -> dict:
    token = create_access_token({"sub": user["id"], "email": user["email"], "role": user["role"]})
    return {"access_token": token, "token_type": "bearer", "user": _public_user(user)}


def _public_user(user: dict) -> dict:
    return {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]}
