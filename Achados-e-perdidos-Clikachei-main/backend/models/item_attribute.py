"""Model: item_attributes (o gabarito sigiloso de cada item)."""

from __future__ import annotations

import json
from pymysql.connections import Connection
from backend.extensions import db

# Garante herança de db.Model se existir na extensão db, sem quebrar o PyMySQL
BaseModel = getattr(db, "Model", object)


class ItemAttribute(BaseModel):
    """CRUD básico da tabela `item_attributes`."""

    def __init__(
        self,
        id: int | None = None,
        item_id: int = 0,
        question: str = "",
        field_type: str = "text",
        options: list[str] | None = None,
        placeholder: str | None = None,
        expected_answer: str = "",
        alternatives: list[str] | None = None,
        weight: int = 1,
        is_critical: bool = False,
        tolerance: float = 0.0,
        sort_order: int = 0,
    ):
        self.id = id
        self.item_id = item_id
        self.question = question
        self.field_type = field_type
        self.options = options
        self.placeholder = placeholder
        self.expected_answer = expected_answer
        self.alternatives = alternatives or []
        self.weight = weight
        self.is_critical = is_critical
        self.tolerance = tolerance
        self.sort_order = sort_order

    # =========================================================================
    # MÉTODOS OBRIGATÓRIOS DO REQUISITO 4 (Em Português, integrados ao PyMySQL)
    # =========================================================================
    def salvar(self, conn: Connection) -> int:
        self.id = self.create(
            conn,
            item_id=self.item_id,
            question=self.question,
            field_type=self.field_type,
            options=self.options,
            placeholder=self.placeholder,
            expected_answer=self.expected_answer,
            alternatives=self.alternatives,
            weight=self.weight,
            is_critical=self.is_critical,
            tolerance=self.tolerance,
            sort_order=self.sort_order,
        )
        return self.id

    def atualizar(self, conn: Connection) -> None:
        if self.id is None:
            raise ValueError("ID do atributo é obrigatório para atualizar.")
        self.update(
            conn,
            self.id,
            question=self.question,
            field_type=self.field_type,
            options=self.options,
            placeholder=self.placeholder,
            expected_answer=self.expected_answer,
            alternatives=self.alternatives,
            weight=self.weight,
            is_critical=self.is_critical,
            tolerance=self.tolerance,
            sort_order=self.sort_order,
        )

    def deletar(self, conn: Connection) -> bool:
        if self.id is None:
            raise ValueError("ID do atributo é obrigatório para deletar.")
        return self.delete(conn, self.id)

    @staticmethod
    def listar_todos(conn: Connection) -> list[dict]:
        return ItemAttribute.find_all(conn)

    @staticmethod
    def buscar_por_id(conn: Connection, attr_id: int) -> dict | None:
        return ItemAttribute.find_by_id(conn, attr_id)

    # =========================================================================
    # MÉTODOS ORIGINAIS E COMPLEMENTARES DO PROJETO
    # =========================================================================
    @staticmethod
    def create(
        conn: Connection,
        *,
        item_id: int,
        question: str,
        field_type: str,
        options: list[str] | None,
        placeholder: str | None,
        expected_answer: str,
        alternatives: list[str],
        weight: int,
        is_critical: bool,
        tolerance: float,
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
                    item_id,
                    question,
                    field_type,
                    json.dumps(options, ensure_ascii=False) if options else None,
                    placeholder,
                    expected_answer,
                    json.dumps(alternatives, ensure_ascii=False),
                    weight,
                    int(is_critical),
                    tolerance,
                    sort_order,
                ),
            )
            return cursor.lastrowid

    @staticmethod
    def update(
        conn: Connection,
        attr_id: int,
        *,
        question: str,
        field_type: str,
        options: list[str] | None,
        placeholder: str | None,
        expected_answer: str,
        alternatives: list[str],
        weight: int,
        is_critical: bool,
        tolerance: float,
        sort_order: int,
    ) -> None:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE item_attributes
                   SET question = %s, field_type = %s, options = %s, placeholder = %s,
                       expected_answer = %s, alternatives = %s, weight = %s,
                       is_critical = %s, tolerance = %s, sort_order = %s
                 WHERE id = %s
                """,
                (
                    question,
                    field_type,
                    json.dumps(options, ensure_ascii=False) if options else None,
                    placeholder,
                    expected_answer,
                    json.dumps(alternatives, ensure_ascii=False),
                    weight,
                    int(is_critical),
                    tolerance,
                    sort_order,
                    attr_id,
                ),
            )

    @staticmethod
    def delete(conn: Connection, attr_id: int) -> bool:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM item_attributes WHERE id = %s", (attr_id,))
            return cursor.rowcount == 1

    @staticmethod
    def find_by_id(conn: Connection, attr_id: int) -> dict | None:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM item_attributes WHERE id = %s", (attr_id,))
            row = cursor.fetchone()
        if row: