"""Repository: busca avançada de itens (procedure `sp_buscar_itens`)."""

from __future__ import annotations

from datetime import date

from pymysql.connections import Connection

from ..extensions.db import call_procedure


class ItemRepository:
    @staticmethod
    def buscar_itens(
        conn: Connection, *, categoria: str | None, texto: str | None,
        data_inicio: date | None, data_fim: date | None, ordenacao: str | None,
    ) -> list[dict]:
        """
        Vitrine pública com filtros combináveis e ordenação dinâmica.

        Implementa o caso de uso "Busca avançada de itens": qualquer
        combinação de categoria/texto/intervalo de datas, com 4 modos de
        ordenação. Sempre restrito a itens `available` — a mesma regra de
        segurança da vitrine (item reivindicado nunca reaparece).
        """
        return call_procedure(
            conn, "sp_buscar_itens", (categoria, texto, data_inicio, data_fim, ordenacao)
        )
