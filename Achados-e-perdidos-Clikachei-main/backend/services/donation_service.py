"""Service — gestão de itens vencidos (+90 dias) e doação em lote."""

from __future__ import annotations

from pymysql.connections import Connection

from ..errors import ApiError
from ..models import LostItem
from ..repositories import ReportRepository


class DonationService:
    @staticmethod
    def list_eligible(conn: Connection, days_limit: int = 90) -> list[dict]:
        try:
            rows = ReportRepository.itens_para_doacao(conn, dias_limite=days_limit)
        except Exception:
            # Fallback para o Model caso a procedure não esteja carregada
            rows = LostItem.find_for_donation(conn, days_limit=days_limit)

        for r in rows:
            r["found_date"] = str(r["found_date"])
        return rows

    @staticmethod
    def donate_batch(conn: Connection, *, item_ids: list[int], entity_name: str, admin_id: int) -> dict:
        entity = str(entity_name).strip()
        if not entity:
            raise ApiError("Informe o nome da instituição beneficente receptora.", 400)
        if not item_ids:
            raise ApiError("Selecione ao menos um item para doar.", 400)

        updated_count = LostItem.mark_donated_batch(conn, item_ids, entity)
        conn.commit()
        return {
            "donated_count": updated_count,
            "entity": entity,
            "message": f"{updated_count} item(ns) destinado(s) à doação para '{entity}' com sucesso.",
        }
