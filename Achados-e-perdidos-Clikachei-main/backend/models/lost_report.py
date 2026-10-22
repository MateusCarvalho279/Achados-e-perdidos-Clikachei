"""Model: lost_reports (alertas de itens perdidos cadastrados pelos alunos)."""

from __future__ import annotations

from datetime import date
from pymysql.connections import Connection


class LostReport:
    """CRUD da tabela lost_reports."""

    @staticmethod
    def create(
        conn: Connection, *, user_id: int, title: str, category: str,
        lost_date: date, lost_location: str | None, description: str,
    ) -> int:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO lost_reports
                    (user_id, title, category, lost_date, lost_location, description, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'open')
                """,
                (user_id, title.strip(), category.strip(), lost_date,
                 lost_location.strip() if lost_location else None, description.strip()),
            )
            return cursor.lastrowid

    @staticmethod
    def find_by_id(conn: Connection, report_id: int) -> dict | None:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT r.*, u.name AS user_name, u.email AS user_email
                  FROM lost_reports r
                  JOIN users u ON u.id = r.user_id
                 WHERE r.id = %s
                """,
                (report_id,),
            )
            return cursor.fetchone()

    @staticmethod
    def find_by_user(conn: Connection, user_id: int) -> list[dict]:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT r.*, i.public_code AS matched_public_code, i.title AS matched_item_title
                  FROM lost_reports r
                  LEFT JOIN lost_items i ON i.id = r.matched_item_id
                 WHERE r.user_id = %s
                 ORDER BY r.created_at DESC
                """,
                (user_id,),
            )
            return cursor.fetchall()

    @staticmethod
    def find_open(conn: Connection) -> list[dict]:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT r.*, u.name AS user_name, u.email AS user_email
                  FROM lost_reports r
                  JOIN users u ON u.id = r.user_id
                 WHERE r.status = 'open'
                 ORDER BY r.created_at DESC
                """
            )
            return cursor.fetchall()

    @staticmethod
    def update_status(conn: Connection, report_id: int, status: str, matched_item_id: int | None = None) -> None:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE lost_reports
                   SET status = %s, matched_item_id = %s
                 WHERE id = %s
                """,
                (status, matched_item_id, report_id),
            )

    @staticmethod
    def cancel(conn: Connection, report_id: int, user_id: int) -> bool:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE lost_reports
                   SET status = 'cancelled'
                 WHERE id = %s AND user_id = %s AND status = 'open'
                """,
                (report_id, user_id),
            )
            return cursor.rowcount == 1
