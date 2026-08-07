"""Model: item_attributes (o gabarito sigiloso de cada item)."""

from __future__ import annotations

import json

from pymysql.connections import Connection


class ItemAttribute:
    """CRUD básico da tabela `item_attributes`."""

    @staticmethod
    def create(
        conn: Connection, *, item_id: int, question: str, field_type: str,
        options: list[str] | None, placeholder: str | None, expected_answer: str,
        alternatives: list[str], weight: int, is_critical: bool, tolerance: float,
        sort_order: int,
    ) -> int:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO item_attributes
                    (item_id, question, field_type, options, placeholder,
                     expected_answer, alternatives, weight, is_critical,
                     tolerance, sort_order)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    item_id, question, field_type,
                    json.dumps(options, ensure_ascii=False) if options else None,
                    placeholder, expected_answer,
                    json.dumps(alternatives, ensure_ascii=False),
                    weight, int(is_critical), tolerance, sort_order,
                ),
            )
            return cursor.lastrowid

    @staticmethod
    def find_by_item_id(conn: Connection, item_id: int) -> list[dict]:
        """
        Gabarito completo de um item, na ordem de apresentação fixa
        (`sort_order`) — essa ordenação é intrínseca à entidade (a mesma
        pergunta sempre aparece na mesma posição), não uma escolha do usuário
        final, por isso continua no Model em vez de virar uma procedure.
        """
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM item_attributes WHERE item_id = %s ORDER BY sort_order, id",
                (item_id,),
            )
            rows = cursor.fetchall()

        for row in rows:
            row["options"] = _load_json_list(row["options"])
            row["alternatives"] = _load_json_list(row["alternatives"])
        return rows

    @staticmethod
    def count_by_item_id(conn: Connection, item_id: int) -> int:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS total FROM item_attributes WHERE item_id = %s", (item_id,)
            )
            return cursor.fetchone()["total"]


def _load_json_list(raw) -> list[str]:
    """MySQL/PyMySQL já desserializa colunas JSON automaticamente."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(v) for v in raw]
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return [str(v) for v in value] if isinstance(value, list) else []
