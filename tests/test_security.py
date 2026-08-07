"""
Testes das primitivas de segurança: hashing de senha, JWT e geração de códigos.

`hash_password`/`create_access_token`/`decode_access_token` leem configuração
de `flask.current_app` — por isso os testes rodam dentro de um contexto de
aplicação Flask mínimo, sem precisar subir o servidor nem conectar ao MySQL.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask  # noqa: E402

from backend.security import (  # noqa: E402
    create_access_token, decode_access_token, generate_pickup_code,
    generate_public_code, hash_password, verify_password,
)


def _test_app() -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY="chave-de-teste-nao-usar-em-producao",
        JWT_ALGORITHM="HS256", JWT_EXPIRATION_HOURS=12, PBKDF2_ITERATIONS=1_000,
    )
    return app


class SecurityTestCase(unittest.TestCase):
    """Empurra um app-context antes de cada teste — igual a uma requisição real."""

    def setUp(self):
        self.app = _test_app()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()


class TestSenhas(SecurityTestCase):
    def test_senha_correta_valida(self):
        stored = hash_password("aluno123")
        self.assertTrue(verify_password("aluno123", stored))

    def test_senha_incorreta_reprova(self):
        stored = hash_password("aluno123")
        self.assertFalse(verify_password("aluno124", stored))
        self.assertFalse(verify_password("", stored))

    def test_salt_torna_hashes_distintos(self):
        self.assertNotEqual(hash_password("mesma"), hash_password("mesma"))

    def test_hash_nao_contem_a_senha(self):
        self.assertNotIn("aluno123", hash_password("aluno123"))

    def test_hash_corrompido_nao_derruba(self):
        self.assertFalse(verify_password("x", "formato-invalido"))


class TestToken(SecurityTestCase):
    def test_ida_e_volta(self):
        token = create_access_token({"sub": 7, "role": "admin"})
        payload = decode_access_token(token)
        self.assertEqual(payload["sub"], 7)
        self.assertEqual(payload["role"], "admin")

    def test_assinatura_adulterada_e_rejeitada(self):
        token = create_access_token({"sub": 1, "role": "user"})
        header, body, signature = token.split(".")
        forged = f"{header}.{body[:-4]}AAAA.{signature}"
        self.assertIsNone(decode_access_token(forged))

    def test_token_malformado_e_rejeitado(self):
        for invalid in ("", "abc", "a.b", None):
            self.assertIsNone(decode_access_token(invalid))


class TestCodigos(unittest.TestCase):
    """Não dependem de config — não precisam de app-context."""

    def test_formato_do_codigo_de_retirada(self):
        code = generate_pickup_code()
        prefix, digits, letters = code.split("-")
        self.assertEqual(prefix, "REC")
        self.assertTrue(digits.isdigit() and len(digits) == 4)
        self.assertTrue(letters.isalpha() and len(letters) == 3)

    def test_codigo_de_retirada_sem_caracteres_ambiguos(self):
        for _ in range(200):
            code = generate_pickup_code()
            self.assertNotIn("O", code[4:])
            self.assertNotIn("I", code)
            self.assertNotIn("0", code)
            self.assertNotIn("1", code)

    def test_codigos_de_retirada_sao_unicos(self):
        codes = {generate_pickup_code() for _ in range(500)}
        self.assertGreater(len(codes), 495)

    def test_codigo_publico_usa_iniciais(self):
        self.assertEqual(generate_public_code("Guarda-chuva", 2026, 1), "GC-2026-001")
        self.assertEqual(generate_public_code("Garrafa Térmica", 2026, 2), "GT-2026-002")

    def test_codigo_publico_ignora_conectivos(self):
        self.assertEqual(generate_public_code("Fone de Ouvido", 2026, 7), "FO-2026-007")
        self.assertEqual(generate_public_code("Caderno de Matemática", 2026, 8), "CM-2026-008")

    def test_codigo_publico_com_palavra_unica(self):
        # Uma palavra só usa suas DUAS primeiras letras — uma só colidiria fácil.
        self.assertEqual(generate_public_code("Carteira", 2026, 5), "CA-2026-005")
        self.assertEqual(generate_public_code("Smartphone", 2026, 4), "SM-2026-004")

    def test_codigo_publico_com_titulo_degenerado(self):
        self.assertTrue(generate_public_code("的 的", 2026, 1).endswith("-2026-001"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
