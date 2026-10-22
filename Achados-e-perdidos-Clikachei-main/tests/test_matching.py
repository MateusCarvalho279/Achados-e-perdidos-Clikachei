"""
Testes unitários do Motor de Validação.

Rodar (sem dependências extras, sem precisar do MySQL):
    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.matching import normalize, score_attribute, validate_claim  # noqa: E402

THRESHOLDS = dict(
    auto_approve_threshold=0.75, manual_review_threshold=0.55, critical_field_threshold=0.85,
)


def attribute(**overrides) -> dict:
    """Constrói um atributo de teste com padrões sensatos."""
    base = {
        "id": 1, "question": "Qual a cor?", "field_type": "text",
        "expected_answer": "azul marinho", "alternatives": [], "weight": 1,
        "is_critical": 0, "tolerance": 0.1,
    }
    return {**base, **overrides}


def validate(attributes, answers):
    return validate_claim(attributes, answers, **THRESHOLDS)


class TestNormalization(unittest.TestCase):
    def test_remove_acentos_e_caixa(self):
        self.assertEqual(normalize("Azul-Marinho!!"), "azul marinho")
        self.assertEqual(normalize("CALCULADORA Científica"), "calculadora cientifica")

    def test_texto_vazio(self):
        self.assertEqual(normalize(""), "")
        self.assertEqual(normalize(None), "")


class TestScoreTexto(unittest.TestCase):
    def test_igualdade_apos_normalizacao(self):
        self.assertEqual(score_attribute(attribute(), "AZUL MARINHO"), 1.0)
        self.assertEqual(score_attribute(attribute(), "azul-marinho"), 1.0)

    def test_sinonimo_cadastrado(self):
        attr = attribute(alternatives=["azul escuro", "marinho"])
        self.assertEqual(score_attribute(attr, "Azul Escuro"), 1.0)

    def test_erro_de_digitacao_ainda_passa(self):
        self.assertGreaterEqual(score_attribute(attribute(), "azul marinhoo"), 0.75)

    def test_resposta_generica_reprova(self):
        self.assertLess(score_attribute(attribute(), "sei la"), 0.4)
        self.assertLess(score_attribute(attribute(), "verde"), 0.4)

    def test_resposta_vazia_zera(self):
        self.assertEqual(score_attribute(attribute(), ""), 0.0)

    def test_descricao_mais_detalhada_conta(self):
        score = score_attribute(attribute(), "a cor dele e azul marinho bem escuro")
        self.assertGreaterEqual(score, 0.9)


class TestScoreNumero(unittest.TestCase):
    def test_valor_exato(self):
        attr = attribute(field_type="number", expected_answer="473")
        self.assertEqual(score_attribute(attr, "473"), 1.0)

    def test_dentro_da_tolerancia(self):
        attr = attribute(field_type="number", expected_answer="473", tolerance=0.12)
        self.assertEqual(score_attribute(attr, "500"), 1.0)

    def test_fora_da_tolerancia(self):
        attr = attribute(field_type="number", expected_answer="473", tolerance=0.05)
        self.assertEqual(score_attribute(attr, "1000"), 0.0)

    def test_ignora_unidade(self):
        attr = attribute(field_type="number", expected_answer="128")
        self.assertEqual(score_attribute(attr, "128 GB"), 1.0)


class TestScoreEscolha(unittest.TestCase):
    def test_multipla_escolha_e_binaria(self):
        attr = attribute(field_type="choice", expected_answer="Curvo (bengala)")
        self.assertEqual(score_attribute(attr, "curvo (bengala)"), 1.0)
        self.assertEqual(score_attribute(attr, "Reto"), 0.0)


class TestValidacaoCompleta(unittest.TestCase):
    def setUp(self):
        self.attributes = [
            attribute(id=1, question="Cor?", expected_answer="roxo", weight=3),
            attribute(id=2, question="Marca?", expected_answer="stanley", weight=2),
            attribute(id=3, question="Detalhe?", expected_answer="adesivo azul", weight=1),
        ]

    def test_todas_corretas_aprova(self):
        result = validate(self.attributes, {"1": "roxo", "2": "Stanley", "3": "adesivo azul"})
        self.assertEqual(result.status, "approved")
        self.assertAlmostEqual(result.score, 1.0)

    def test_todas_erradas_reprova(self):
        result = validate(self.attributes, {"1": "verde", "2": "nike", "3": "nada"})
        self.assertEqual(result.status, "rejected")

    def test_faixa_intermediaria_vai_para_analise(self):
        result = validate(self.attributes, {"1": "roxo", "2": "termolar", "3": "adesivo azul"})
        self.assertEqual(result.status, "pending_review")
        self.assertTrue(0.55 <= result.score < 0.75, result.score)

    def test_um_acerto_isolado_nao_chega_a_analise(self):
        result = validate(self.attributes, {"1": "roxo", "2": "", "3": ""})
        self.assertEqual(result.status, "rejected")

    def test_peso_influencia_o_score(self):
        so_o_pesado = validate(self.attributes, {"1": "roxo", "2": "", "3": ""})
        so_o_leve = validate(self.attributes, {"1": "", "2": "", "3": "adesivo azul"})
        self.assertGreater(so_o_pesado.score, so_o_leve.score)

    def test_caracteristica_critica_veta_mesmo_com_score_alto(self):
        attributes = [
            attribute(id=1, question="Cor?", expected_answer="roxo", weight=1),
            attribute(id=2, question="Marca?", expected_answer="stanley", weight=1),
            attribute(id=3, question="Senha?", expected_answer="2019", weight=1, is_critical=1),
        ]
        result = validate(attributes, {"1": "roxo", "2": "stanley", "3": "1234"})
        self.assertTrue(result.critical_failure)
        self.assertEqual(result.status, "rejected")
        self.assertGreater(result.score, 0.6)

    def test_item_sem_gabarito_nunca_aprova(self):
        self.assertEqual(validate([], {"1": "qualquer coisa"}).status, "rejected")


if __name__ == "__main__":
    unittest.main(verbosity=2)
