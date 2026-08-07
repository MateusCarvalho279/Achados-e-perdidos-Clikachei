"""
Camada Model — entidades de domínio e CRUD básico.

Cada classe aqui representa UMA tabela e só faz operações de granularidade de
registro único: inserir, buscar por chave (primária ou única) e atualizar/
remover por chave. Nenhuma classe deste pacote faz JOIN entre tabelas nem
aceita critérios de busca combináveis — isso é responsabilidade da camada
Repository, via stored procedure (veja `backend/repositories/`).

Duas exceções deliberadas, documentadas em cada método: pequenas contagens de
uma única tabela com uma única condição (ex.: "quantas tentativas rejeitadas
este usuário já fez neste item") que são regra de domínio da própria entidade,
não uma funcionalidade de busca/relatório para o usuário final.
"""

from .claim_request import ClaimRequest
from .item_attribute import ItemAttribute
from .lost_item import LostItem
from .user import User

__all__ = ["ClaimRequest", "ItemAttribute", "LostItem", "User"]
