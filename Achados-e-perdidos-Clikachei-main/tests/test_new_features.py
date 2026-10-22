"""
Testes unitários para as novas funcionalidades:
1. Matching inteligente de alertas de perda contra itens do acervo
2. Exportação de relatórios em formato CSV (UTF-8 com BOM)
3. Formatação e regras de notificação
4. Validações e regras de negócio de cancelamento, doação e entrega
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from backend.services.export_service import ExportService
from backend.services.lost_report_service import LostReportService, _tokenize
from backend.services.pickup_service import PickupService
from backend.services.donation_service import DonationService
from backend.errors import ApiError


class TestNewFeatures(unittest.TestCase):
    def test_tokenize_removes_stopwords(self):
        text = "Garrafa de água Stanley azul no refeitório"
        tokens = _tokenize(text)
        self.assertIn("garrafa", tokens)
        self.assertIn("água", tokens)
        self.assertIn("stanley", tokens)
        self.assertIn("azul", tokens)
        self.assertIn("refeitório", tokens)
        self.assertNotIn("de", tokens)
        self.assertNotIn("no", tokens)

    def test_matching_algorithm(self):
        # Simula itens disponíveis no banco
        conn = MagicMock()
        mock_items = [
            {
                "id": 1,
                "public_code": "GC-2026-001",
                "title": "Guarda-chuva roxo",
                "category": "Acessórios",
                "icon": "☂️",
                "found_date": "2026-05-04",
                "found_location": "Bloco A",
                "status": "available",
            },
            {
                "id": 2,
                "public_code": "GF-2026-002",
                "title": "Garrafa Stanley térmica",
                "category": "Utensílios",
                "icon": "🍶",
                "found_date": "2026-05-03",
                "found_location": "Refeitório",
                "status": "available",
            },
        ]

        with unittest.mock.patch("backend.models.LostItem.find_all", return_value=mock_items):
            matches = LostReportService._compute_matches(
                conn,
                title="Minha garrafa Stanley",
                category="Utensílios",
                description="Perdi minha garrafa térmica Stanley no refeitório",
            )
            self.assertTrue(len(matches) > 0)
            top = matches[0]
            self.assertEqual(top["public_code"], "GF-2026-002")
            self.assertGreaterEqual(top["match_score"], 40)
            self.assertIn("Mesma categoria", top["match_reasons"])

    def test_export_csv_items(self):
        conn = MagicMock()
        mock_items = [
            {
                "public_code": "GC-001",
                "title": "Mochila",
                "category": "Acessórios",
                "found_date": "2026-05-01",
                "found_location": "Pátio",
                "status": "available",
                "pickup_code": None,
            }
        ]
        with unittest.mock.patch("backend.models.LostItem.find_all", return_value=mock_items):
            csv_text, filename = ExportService.export_csv(conn, "items")
            self.assertTrue(csv_text.startswith("\ufeff"))  # UTF-8 BOM
            self.assertIn("relatorio_itens", filename)
            self.assertIn("GC-001", csv_text)
            self.assertIn("Mochila", csv_text)

    def test_export_csv_invalid_type(self):
        conn = MagicMock()
        with self.assertRaises(ApiError):
            ExportService.export_csv(conn, "invalid_report_type")

    def test_pickup_validation_not_found(self):
        conn = MagicMock()
        with unittest.mock.patch("backend.models.LostItem.find_by_pickup_code", return_value=None):
            with self.assertRaises(ApiError) as ctx:
                PickupService.validate(conn, "REC-INVALIDO")
            self.assertEqual(ctx.exception.status_code, 404)

    def test_pickup_validation_already_delivered(self):
        conn = MagicMock()
        item = {
            "public_code": "GC-001",
            "title": "Celular",
            "status": "delivered",
            "delivered_to_name": "João",
            "delivered_at": "2026-05-10",
        }
        with unittest.mock.patch("backend.models.LostItem.find_by_pickup_code", return_value=item):
            with self.assertRaises(ApiError) as ctx:
                PickupService.validate(conn, "REC-1234-XYZ")
            self.assertEqual(ctx.exception.status_code, 409)

    def test_donation_requires_entity(self):
        conn = MagicMock()
        with self.assertRaises(ApiError) as ctx:
            DonationService.donate_batch(conn, item_ids=[1, 2], entity_name="", admin_id=1)
        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
