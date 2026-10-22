"""Service — gerenciamento de usuários pelo administrador."""

from __future__ import annotations

from pymysql.connections import Connection

from ..errors import ApiError
from ..models import User
from ..repositories import ReportRepository


class UserAdminService:
    @staticmethod
    def list_users(conn: Connection, search: str | None = None) -> list[dict]:
        try:
            rows = ReportRepository.buscar_usuarios(conn, busca=search)
        except Exception:
            # Fallback caso a procedure sp_buscar_usuarios não esteja carregada
            with conn.cursor() as cursor:
                query = "SELECT id, name, email, role, created_at FROM users"
                params = []
                if search:
                    query += " WHERE name LIKE %s OR email LIKE %s"
                    params.extend([f"%{search}%", f"%{search}%"])
                query += " ORDER BY name ASC"
                cursor.execute(query, params)
                rows = cursor.fetchall()
                for r in rows:
                    r["total_reivindicacoes"] = 0
                    r["total_alertas"] = 0

        for r in rows:
            r["created_at"] = str(r["created_at"])
        return rows

    @staticmethod
    def toggle_role(conn: Connection, target_user_id: int, current_admin_id: int) -> dict:
        if target_user_id == current_admin_id:
            raise ApiError("Você não pode alterar seu próprio nível de permissão.", 400)

        user = User.find_by_id(conn, target_user_id)
        if user is None:
            raise ApiError("Usuário não encontrado.", 404)

        new_role = "admin" if user["role"] == "user" else "user"
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, target_user_id))
        conn.commit()

        return {
            "id": target_user_id,
            "new_role": new_role,
            "message": f"Permissão do usuário {user['name']} alterada para '{new_role}'.",
        }
