"""Model: notifications (central de avisos do usuário)."""

from __future__ import annotations

from pymysql.connections import Connection


class Notification:
    """CRUD da tabela notifications."""

    @staticmethod
    def create(
        conn: Connection, *, user_id: int, title: str, message: str, link: str | None = None,
    ) -> int:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO notifications (user_id, title, message, link, is_read)
                VALUES (%s, %s, %s, %s, 0)
                """,
                (user_id, title.strip(), message.strip(), link.strip() if link else None),
            )
            return cursor.lastrowid

    @staticmethod
    def find_by_user(conn: Connection, user_id: int, limit: int = 20) -> list[dict]:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, title, message, link, is_read, created_at
                  FROM notifications
                 WHERE user_id = %s
                 ORDER BY created_at DESC, id DESC
                 LIMIT %s
                """,
                (user_id, limit),
            )
            return cursor.fetchall()

    @staticmethod
    def mark_as_read(conn: Connection, notification_id: int, user_id: int) -> bool:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE notifications
                   SET is_read = 1
                 WHERE id = %s AND user_id = %s
                """,
                (notification_id, user_id),
            )
            return cursor.rowcount == 1

    @staticmethod
    def mark_all_as_read(conn: Connection, user_id: int) -> int:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE notifications
                   SET is_read = 1
                 WHERE user_id = %s AND is_read = 0
                """,
                (user_id,),
            )
            return cursor.rowcount

    @staticmethod
    def count_unread(conn: Connection, user_id: int) -> int:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                  FROM notifications
                 WHERE user_id = %s AND is_read = 0
                """,
                (user_id,),
            )
            row = cursor.fetchone()
            return row["total"] if row else 0
