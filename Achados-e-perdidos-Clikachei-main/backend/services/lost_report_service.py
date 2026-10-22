"""Service — gestão de alertas de itens perdidos e matching automático."""

from __future__ import annotations

import re
from datetime import date
from pymysql.connections import Connection

from ..errors import ApiError
from ..models import LostItem, LostReport, Notification


class LostReportService:
    @staticmethod
    def create(conn: Connection, *, user_id: int, payload: dict) -> dict:
        title = str(payload.get("title", "")).strip()
        category = str(payload.get("category", "")).strip()
        description = str(payload.get("description", "")).strip()
        lost_location = payload.get("lost_location")
        lost_date: date = payload["lost_date"]

        if not title:
            raise ApiError("Informe o título do item perdido.", 400)
        if not category:
            raise ApiError("Informe a categoria.", 400)
        if not description or len(description) < 5:
            raise ApiError("Forneça uma descrição de ao menos 5 caracteres.", 400)

        report_id = LostReport.create(
            conn, user_id=user_id, title=title, category=category,
            lost_date=lost_date, lost_location=lost_location, description=description,
        )

        matches = LostReportService._compute_matches(conn, title, category, description)
        if matches:
            top = matches[0]
            Notification.create(
                conn, user_id=user_id,
                title="🔍 Possível item encontrado!",
                message=f"Encontramos um item ({top['title']}) que pode corresponder ao seu alerta de perda.",
                link=f"reivindicar.html?code={top['public_code']}",
            )

        conn.commit()
        return {
            "id": report_id,
            "message": "Alerta de perda registrado com sucesso. Você será avisado caso um item compatível dê entrada.",
            "match_count": len(matches),
            "top_matches": matches[:3],
        }

    @staticmethod
    def list_mine(conn: Connection, user_id: int) -> list[dict]:
        rows = LostReport.find_by_user(conn, user_id)
        for r in rows:
            r["lost_date"] = str(r["lost_date"])
            r["created_at"] = str(r["created_at"])
        return rows

    @staticmethod
    def find_matches_for_report(conn: Connection, report_id: int, user_id: int) -> list[dict]:
        report = LostReport.find_by_id(conn, report_id)
        if report is None or report["user_id"] != user_id:
            raise ApiError("Alerta de perda não encontrado.", 404)
        return LostReportService._compute_matches(
            conn, report["title"], report["category"], report["description"]
        )

    @staticmethod
    def cancel(conn: Connection, report_id: int, user_id: int) -> dict:
        success = LostReport.cancel(conn, report_id, user_id)
        if not success:
            raise ApiError("Alerta de perda não encontrado ou já encerrado.", 400)
        conn.commit()
        return {"message": "Alerta de perda cancelado."}

    @staticmethod
    def _compute_matches(conn: Connection, title: str, category: str, description: str) -> list[dict]:
        """Calcula similaridade com itens disponíveis no acervo."""
        items = LostItem.find_all(conn)
        available_items = [i for i in items if i["status"] == "available"]

        tokens_report = set(_tokenize(f"{title} {category} {description}"))

        results = []
        for item in available_items:
            score = 0.0
            reasons = []

            if item["category"].strip().lower() == category.strip().lower():
                score += 0.40
                reasons.append("Mesma categoria")

            tokens_item = set(_tokenize(f"{item['title']} {item.get('found_location', '')}"))
            overlap = tokens_report.intersection(tokens_item)
            if overlap:
                score += min(len(overlap) * 0.20, 0.50)
                reasons.append(f"Palavras em comum: {', '.join(list(overlap)[:3])}")

            if score >= 0.35:
                results.append({
                    "public_code": item["public_code"],
                    "title": item["title"],
                    "category": item["category"],
                    "icon": item["icon"],
                    "found_date": str(item["found_date"]),
                    "found_location": item["found_location"],
                    "match_score": round(min(score, 1.0) * 100),
                    "match_reasons": reasons,
                })

        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results


def _tokenize(text: str) -> list[str]:
    stopwords = {"de", "a", "o", "da", "do", "em", "um", "uma", "para", "com", "no", "na", "que", "e"}
    words = re.findall(r"\b[a-zA-Z0-9áéíóúâêîôûãõç]{3,}\b", text.lower())
    return [w for w in words if w not in stopwords]
