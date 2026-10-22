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
    def update(
        conn: Connection, item_id: int, *, title: str, category: str, icon: str,
        found_date: date, found_location: str | None, internal_notes: str | None,
        status: str,
    ) -> None:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE lost_items
                   SET title = %s, category = %s, icon = %s, found_date = %s,
                       found_location = %s, internal_notes = %s, status = %s
                 WHERE id = %s
                """,
                (title, category, icon, found_date, found_location, internal_notes, status, item_id),
            )

    @staticmethod
    def find_by_pickup_code(conn: Connection, pickup_code: str) -> dict | None:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT i.*, u.name AS claimer_name, u.email AS claimer_email
                  FROM lost_items i
                  LEFT JOIN users u ON u.id = i.claimed_by_user_id
                 WHERE i.pickup_code = %s
                """,
                (pickup_code.strip(),),
            )
            return cursor.fetchone()

    @staticmethod
    def mark_delivered(
        conn: Connection, item_id: int, *, delivered_to_name: str,
        delivered_to_doc: str, delivered_notes: str | None,
    ) -> bool:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE lost_items
                   SET status = 'delivered', delivered_to_name = %s,
                       delivered_to_doc = %s, delivered_notes = %s, delivered_at = NOW()
                 WHERE id = %s AND status = 'claimed'
                """,
                (delivered_to_name, delivered_to_doc, delivered_notes, item_id),
            )
            return cursor.rowcount == 1

    @staticmethod
    def release_to_available(conn: Connection, item_id: int) -> None:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE lost_items
                   SET status = 'available', claimed_by_user_id = NULL,
                       claimed_at = NULL, pickup_code = NULL
                 WHERE id = %s
                """,
                (item_id,),
            )

    @staticmethod
    def mark_donated_batch(conn: Connection, item_ids: list[int], entity: str) -> int:
        if not item_ids:
            return 0
        format_strings = ",".join(["%s"] * len(item_ids))
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE lost_items
                   SET status = 'donated', donation_entity = %s, donated_at = NOW()
                 WHERE id IN ({format_strings}) AND status = 'available'
                """,
                [entity, *item_ids],
            )
            return cursor.rowcount

    @staticmethod
    def find_for_donation(conn: Connection, days_limit: int = 90) -> list[dict]:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, public_code, title, category, icon, found_date,
                       found_location, status,
                       DATEDIFF(CURDATE(), found_date) AS dias_guardado
                  FROM lost_items
                 WHERE status = 'available'
                   AND found_date <= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                 ORDER BY found_date ASC
                """,
                (days_limit,),
            )
            return cursor.fetchall()

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

