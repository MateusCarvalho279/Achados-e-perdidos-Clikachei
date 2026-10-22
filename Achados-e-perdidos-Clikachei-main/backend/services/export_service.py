"""Service — exportação de relatórios em CSV para prestação de contas."""

from __future__ import annotations

import csv
import io
from pymysql.connections import Connection

from ..errors import ApiError
from ..models import LostItem
from ..repositories import ClaimRepository, ReportRepository


class ExportService:
    @staticmethod
    def export_csv(conn: Connection, report_type: str) -> tuple[str, str]:
        rtype = str(report_type).lower().strip()
        output = io.StringIO()
        # UTF-8 BOM para o Excel abrir direto com acentuação correta
        output.write("\ufeff")
        writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)

        if rtype == "items":
            filename = "relatorio_itens_achados_e_perdidos.csv"
            writer.writerow(["Código", "Título", "Categoria", "Data Encontrado", "Local", "Situação", "Código Retirada"])
            rows = LostItem.find_all(conn)
            for r in rows:
                writer.writerow([
                    r.get("public_code", ""),
                    r.get("title", ""),
                    r.get("category", ""),
                    str(r.get("found_date", "")),
                    r.get("found_location", "") or "Não informado",
                    r.get("status", ""),
                    r.get("pickup_code", "") or "—",
                ])

        elif rtype == "claims":
            filename = "relatorio_reivindicacoes.csv"
            writer.writerow(["ID", "Código Item", "Título Item", "Solicitante", "E-mail", "Score (%)", "Situação", "Código Retirada", "Data"])
            rows = ClaimRepository.listar_reivindicacoes(conn)
            for r in rows:
                score_pct = f"{round(float(r['score']) * 100, 1)}%" if r.get("score") is not None else "—"
                writer.writerow([
                    r.get("id", ""),
                    r.get("item_code", ""),
                    r.get("item_title", ""),
                    r.get("user_name", ""),
                    r.get("user_email", ""),
                    score_pct,
                    r.get("status", ""),
                    r.get("pickup_code", "") or "—",
                    str(r.get("created_at", "")),
                ])

        elif rtype == "categories":
            filename = "relatorio_estatisticas_categorias.csv"
            writer.writerow(["Categoria", "Total Itens", "Devolvidos", "Taxa Recuperação (%)", "Tentativas", "Score Médio Aprovados (%)"])
            rows = ReportRepository.relatorio_categorias(conn)
            for r in rows:
                writer.writerow([
                    r.get("category", ""),
                    r.get("total_itens", 0),
                    r.get("total_devolvidos", 0),
                    f"{r.get('taxa_recuperacao_pct', 0)}%",
                    r.get("total_tentativas", 0),
                    f"{r.get('score_medio_aprovados_pct', 0)}%",
                ])

        else:
            raise ApiError(f"Tipo de exportação '{report_type}' inválido. Use 'items', 'claims' ou 'categories'.", 400)

        return output.getvalue(), filename
