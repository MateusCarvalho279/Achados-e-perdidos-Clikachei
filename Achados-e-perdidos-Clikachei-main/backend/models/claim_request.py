"""Model: claim_requests (trilha de auditoria de toda tentativa)."""

from __future__ import annotations

import json
from pymysql.connections import Connection
from backend.extensions import db

# Garante herança de db.Model se existir na extensão db, sem quebrar o PyMySQL
BaseModel = getattr(db, "Model", object)


class ClaimRequest(BaseModel):
    """CRUD básico da tabela `claim_requests`."""

    def __init__(
        self,
        id: int | None = None,
        item_id: int = 0,
        user_id: int = 0,
        answers: dict | None = None,
        breakdown: list | None = None,
        score: float = 0.0,
        status: str = "pending_review",
        pickup_code: str | None = None,
        client_ip: str | None = None,
        reviewed_by: int | None = None,
    ):
        self.id = id
        self.item_id = item_id
        self.user_id = user_id
        self.answers = answers or {}
        self.breakdown = breakdown or []
        self.score = score
        self.status = status
        self.pickup_code = pickup_code
        self.client_ip = client_ip
        self.reviewed_by = reviewed_by

    # =========================================================================
    # MÉTODOS OBRIGATÓRIOS DO REQUISITO 4 (Em Português, integrados ao PyMySQL)
    # =========================================================================
    def salvar(self, conn: Connection) -> int:
        self.id = self.create(
            conn,
            item_id=self.item_id,
            user_id=self.user_id,
            answers=self.answers,
            breakdown=self.breakdown,
            score=self.score,
            status=self.status,
            pickup_code=self.pickup_code,
            client_ip=self.client_ip,
        )
        return self.id

    def atualizar(self, conn: Connection) -> None:
        if self.id is None:
            raise ValueError("ID da reivindicação é obrigatório para atualizar.")
        self.mark_reviewed(
            conn,
            claim_id=self.id,
            status=self.status,
            pickup_code=self.pickup_code,
            reviewed_by=self.reviewed_by or self.user_id,
        )

    def deletar(self, conn: Connection) -> bool:
        if self.id is None:
            raise ValueError("ID da reivindicação é obrigatório para deletar.")
        return self.delete(conn, self.id)

    @staticmethod
    def listar_todos(conn: Connection) -> list[dict]:
        return ClaimRequest.find_all(conn)

    @staticmethod
    def buscar_por_id(conn: Connection, claim_id: int) -> dict | None:
        return ClaimRequest.find_by_id(conn, claim_id)

    # =========================================================================
    # MÉTODOS ORIGINAIS DO PROJETO (Mantidos para não quebrar os Services)
    # =========================================================================
    @staticmethod
    def create(
        conn: Connection,
        *,
        item_id: int,
        user_id: int,
        answers: dict,
        breakdown: list,
        score: float,
        status: str,
        pickup_code: str | None,
        client_ip: str | None,
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
                    item_id,
                    user_id,
                    json.dumps(answers, ensure_ascii=False),
                    json.dumps(breakdown, ensure_ascii=False),
                    round(score, 4),
                    status,
                    pickup_code,
                    client_ip,
                ),
            )
            return cursor.lastrowid

    @staticmethod
    def find_by_id(conn: Connection, claim_id: int) -> dict | None:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM claim_requests WHERE id = %s", (claim_id,))
            return cursor.fetchone()

    @staticmethod
    def find_all(conn: Connection) -> list[dict]:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM claim_requests ORDER BY id DESC")
            return cursor.fetchall()

    @staticmethod
    def delete(conn: Connection, claim_id: int) -> bool:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM claim_requests WHERE id = %s", (claim_id,))
            return cursor.rowcount == 1

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
    def mark_reviewed(
        conn: Connection,
        claim_id: int,
        status: str,
        pickup_code: str | None,
        reviewed_by: int,
    ) -> None:
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
    def cancel(conn: Connection, claim_id: int, user_id: int) -> bool:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE claim_requests
                   SET status = 'cancelled'
                 WHERE id = %s AND user_id = %s AND status IN ('pending_review', 'approved')
                """,
                (claim_id, user_id),
            )
            return cursor.rowcount == 1

    @staticmethod
    def count_all(conn: Connection) -> int:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM claim_requests")
            return cursor.fetchone()["total"]

    @staticmethod
    def count_by_status(conn: Connection, status: str) -> int:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS total FROM claim_requests WHERE status = %s",
                (status,),
            )
            return cursor.fetchone()["total"]