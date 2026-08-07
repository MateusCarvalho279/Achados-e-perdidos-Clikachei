"""
Service — caso de uso avançado #1: Busca de itens com filtros e ordenação.

Alimenta a vitrine pública. Toda a consulta (WHERE combinável + ORDER BY
dinâmico) roda dentro de `sp_buscar_itens`, chamada pela camada Repository.
"""

from __future__ import annotations

from pymysql.connections import Connection

from ..repositories import ItemRepository

ORDENACOES_VALIDAS = {"recentes", "antigos", "titulo_asc", "titulo_desc"}


class ItemSearchService:
    @staticmethod
    def search(
        conn: Connection, *, categoria: str | None = None, texto: str | None = None,
        data_inicio: str | None = None, data_fim: str | None = None,
        ordenacao: str | None = None,
    ) -> list[dict]:
        if ordenacao not in ORDENACOES_VALIDAS:
            ordenacao = "recentes"

        rows = ItemRepository.buscar_itens(
            conn,
            categoria=categoria or None,
            texto=texto or None,
            data_inicio=data_inicio or None,
            data_fim=data_fim or None,
            ordenacao=ordenacao,
        )
        return [_serialize(row) for row in rows]


def _serialize(row: dict) -> dict:
    return {
        "public_code": row["public_code"],
        "title": row["title"],
        "category": row["category"],
        "icon": row["icon"],
        "found_date": str(row["found_date"]),
        "found_location": row["found_location"],
        "status": row["status"],
        "question_count": row["question_count"],
    }
