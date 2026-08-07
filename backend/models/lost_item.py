"""Model: lost_items."""

from __future__ import annotations

from datetime import date

from pymysql.connections import Connection


class LostItem:
    """CRUD básico da tabela `lost_items` (sem filtros de negócio nem JOIN)."""

    @staticmethod
    def create(
        conn: Connection, *, public_code: str, title: str, category: str, icon: str,
        found_date: date, found_location: str | None, internal_notes: str | None,
        created_by: int,
    ) -> int:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO lost_items
                    (public_code, title, category, icon, found_date, found_location,
                     internal_notes, status, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'available', %s)
                """,
                (public_code, title, category, icon, found_date, found_location,
                 internal_notes, created_by),
            )
            return cursor.lastrowid

    @staticmethod
    def find_by_id(conn: Connection, item_id: int) -> dict | None:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM lost_items WHERE id = %s", (item_id,))
            return cursor.fetchone()

    @staticmethod
    def find_by_code(conn: Connection, public_code: str) -> dict | None:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM lost_items WHERE public_code = %s", (public_code.strip(),))
            return cursor.fetchone()

    @staticmethod
    def find_all(conn: Connection) -> list[dict]:
        """
        Todos os itens, sem filtro — visão bruta de tabela usada apenas pelo
        painel administrativo. Ordenação por `id DESC` é o padrão trivial de
        "mais recente primeiro" (não é uma ordenação escolhida pelo usuário —
        para isso existe `sp_buscar_itens` na camada Repository).
        """
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM lost_items ORDER BY id DESC")
            return cursor.fetchall()

    @staticmethod
    def count_public_code_prefix(conn: Connection, year: int) -> int:
        """Sequência auxiliar para gerar o próximo código público do ano."""
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS total FROM lost_items WHERE public_code LIKE %s",
                (f"%-{year}-%",),
            )
            return cursor.fetchone()["total"]

    @staticmethod
    def mark_claimed(conn: Connection, item_id: int, user_id: int, pickup_code: str) -> bool:
        """
        UPDATE condicionado a `status = 'available'` — é o ponto de
        serialização que impede dois usuários de serem aprovados no mesmo
        item. Devolve False se o item já tinha sido levado.
        """
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE lost_items
                   SET status = 'claimed', claimed_by_user_id = %s,
                       claimed_at = NOW(), pickup_code = %s
                 WHERE id = %s AND status = 'available'
                """,
                (user_id, pickup_code, item_id),
            )
            return cursor.rowcount == 1

    @staticmethod
    def archive(conn: Connection, item_id: int) -> None:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE lost_items SET status = 'archived' WHERE id = %s", (item_id,))

    @staticmethod
    def count_by_status(conn: Connection, status: str) -> int:
        """Contagem de uma única tabela/condição — usada no card de indicadores do admin."""
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS total FROM lost_items WHERE status = %s", (status,)
            )
            return cursor.fetchone()["total"]
