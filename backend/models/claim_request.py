"""Model: claim_requests (trilha de auditoria de toda tentativa)."""

from __future__ import annotations

import json

from pymysql.connections import Connection


class ClaimRequest:
    """CRUD básico da tabela `claim_requests`."""

    @staticmethod
    def create(
        conn: Connection, *, item_id: int, user_id: int, answers: dict, breakdown: list,
        score: float, status: str, pickup_code: str | None, client_ip: str | None,
    ) -> int:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO claim_requests
                    (item_id, user_id, answers, breakdown, score, status,
                     pickup_code, client_ip)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    item_id, user_id,
                    json.dumps(answers, ensure_ascii=False),
                    json.dumps(breakdown, ensure_ascii=False),
                    round(score, 4), status, pickup_code, client_ip,
                ),
            )
            return cursor.lastrowid

    @staticmethod
    def find_by_id(conn: Connection, claim_id: int) -> dict | None:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM claim_requests WHERE id = %s", (claim_id,))
            return cursor.fetchone()

    @staticmethod
    def count_rejected(conn: Connection, item_id: int, user_id: int) -> int:
        """
        Quantas tentativas rejeitadas o usuário já gastou neste item — regra
        de domínio do próprio "claim" (limite anti-fraude), não uma busca de
        negócio, por isso fica no Model.
        """
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) AS total FROM claim_requests
                 WHERE item_id = %s AND user_id = %s AND status = 'rejected'
                """,
                (item_id, user_id),
            )
            return cursor.fetchone()["total"]

    @staticmethod
    def has_pending(conn: Connection, item_id: int, user_id: int) -> bool:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1 FROM claim_requests
                 WHERE item_id = %s AND user_id = %s AND status = 'pending_review'
                 LIMIT 1
                """,
                (item_id, user_id),
            )
            return cursor.fetchone() is not None

    @staticmethod
    def mark_reviewed(conn: Connection, claim_id: int, status: str, pickup_code: str | None, reviewed_by: int) -> None:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE claim_requests
                   SET status = %s, pickup_code = %s, reviewed_by = %s, reviewed_at = NOW()
                 WHERE id = %s
                """,
                (status, pickup_code, reviewed_by, claim_id),
            )

    @staticmethod
    def count_all(conn: Connection) -> int:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM claim_requests")
            return cursor.fetchone()["total"]

    @staticmethod
    def count_by_status(conn: Connection, status: str) -> int:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS total FROM claim_requests WHERE status = %s", (status,)
            )
            return cursor.fetchone()["total"]
