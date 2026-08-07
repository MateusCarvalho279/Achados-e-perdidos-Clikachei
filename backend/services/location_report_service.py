"""
Service — caso de uso avançado #5: ranking dos locais com mais achados
(painel admin) — `sp_relatorio_locais`.
"""

from __future__ import annotations

from pymysql.connections import Connection

from ..repositories import ReportRepository


class LocationReportService:
    @staticmethod
    def report(conn: Connection, *, limite: int = 10) -> list[dict]:
        limite = max(1, min(int(limite or 10), 50))
        rows = ReportRepository.relatorio_locais(conn, limite=limite)
        for row in rows:
            row["taxa_recuperacao_pct"] = float(row["taxa_recuperacao_pct"] or 0)
        return rows
