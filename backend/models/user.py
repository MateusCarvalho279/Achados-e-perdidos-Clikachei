"""Model: users."""

from __future__ import annotations

from pymysql.connections import Connection


class User:
    """CRUD básico da tabela `users`."""

    @staticmethod
    def create(conn: Connection, name: str, email: str, password_hash: str, role: str = "user") -> int:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s)",
                (name, email, password_hash, role),
            )
            return cursor.lastrowid

    @staticmethod
    def find_by_id(conn: Connection, user_id: int) -> dict | None:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, name, email, role, created_at FROM users WHERE id = %s", (user_id,)
            )
            return cursor.fetchone()

    @staticmethod
    def find_by_email(conn: Connection, email: str) -> dict | None:
        """Inclui `password_hash` — uso exclusivo do fluxo de login."""
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            return cursor.fetchone()

    @staticmethod
    def count_by_role(conn: Connection, role: str) -> int:
        """Contagem de uma única tabela/condição — usada no card de indicadores do admin."""
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM users WHERE role = %s", (role,))
            return cursor.fetchone()["total"]
