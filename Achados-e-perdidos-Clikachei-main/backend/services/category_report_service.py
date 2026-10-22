"""
Service — caso de uso avançado #4: relatório gerencial por categoria
(painel admin) — `sp_relatorio_categorias`.
"""

from __future__ import annotations

from pymysql.connections import Connection

from ..repositories import ReportRepository


class CategoryReportService:
    @staticmethod
    def report(conn: Connection) -> list[dict]:
        rows = ReportRepository.relatorio_categorias(conn)
        for row in rows:
            row["taxa_recuperacao_pct"] = float(row["taxa_recuperacao_pct"] or 0)
            row["score_medio_aprovados_pct"] = (
                float(row["score_medio_aprovados_pct"])
                if row["score_medio_aprovados_pct"] is not None else None
            )
        return rows
