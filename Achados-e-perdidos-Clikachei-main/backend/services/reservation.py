"""
Reserva de item — compartilhada entre `ClaimSubmissionService` (aprovação
automática) e `ClaimReviewService` (aprovação manual do admin), já que as duas
trilhas terminam no mesmo efeito: gerar o código e marcar o item como retirado.
"""

from __future__ import annotations

import pymysql
from pymysql.connections import Connection

from ..errors import ApiError
from ..models import LostItem
from ..security import generate_pickup_code


def reserve_item(conn: Connection, item_id: int, user_id: int) -> str | None:
    """
    Gera um código de retirada único e marca o item como reivindicado.

    Devolve `None` se o item já não estava mais disponível (corrida perdida).
    A colisão de código é praticamente impossível, mas a coluna é UNIQUE —
    o laço tenta de novo com outro código por garantia.
    """
    for _ in range(10):
        code = generate_pickup_code()
        try:
            updated = LostItem.mark_claimed(conn, item_id, user_id, code)
        except pymysql.err.IntegrityError:
            continue
        return code if updated else None

    raise ApiError("Não foi possível gerar um código de retirada. Tente novamente.", 500)
