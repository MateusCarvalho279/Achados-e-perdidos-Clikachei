"""
Camada Repository — encapsula TODO acesso ao banco que envolva filtros
combináveis, ordenação dinâmica, JOIN entre tabelas ou agregação/relatório.

Cada método aqui faz exatamente uma coisa: montar os parâmetros e chamar
`CALL sp_xxx(...)` via `backend.extensions.db.call_procedure`. Nenhuma
instrução SQL solta (SELECT/WHERE/JOIN escrita à mão) existe neste pacote —
toda a lógica de consulta vive nas stored procedures em
`database/02_procedures.sql`.
"""

from .claim_repository import ClaimRepository
from .item_repository import ItemRepository
from .report_repository import ReportRepository

__all__ = ["ClaimRepository", "ItemRepository", "ReportRepository"]
