"""Exceção de negócio usada pelas Services para sinalizar erros de API."""

from __future__ import annotations


class ApiError(Exception):
    """Erro esperado de regra de negócio — a Controller converte em resposta HTTP."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
