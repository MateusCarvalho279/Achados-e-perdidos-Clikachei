"""
Carga inicial de dados — executada no boot da aplicação.

Idempotente: se o banco já tiver itens, nada é reinserido. Dá ao avaliador um
sistema navegável já no primeiro `python run.py`, com dados suficientes para
exercitar as 5 funcionalidades avançadas (categorias e locais variados,
histórico de reivindicações aprovadas/recusadas/em análise).
"""

from __future__ import annotations

from flask import current_app

from .extensions.db import get_db
from .models import User
from .services.item_admin_service import ItemAdminService

DEMO_ITEMS: list[dict] = [
    {
        "title": "Guarda-chuva", "category": "Acessórios", "icon": "☂️",
        "found_date": "2026-05-04", "found_location": "Bloco A - Corredor principal",
        "internal_notes": "Entregue pela equipe de limpeza.",
        "attributes": [
            {
                "question": "Qual a cor predominante do guarda-chuva?",
                "placeholder": "Ex.: azul, preto, estampado...", "expected_answer": "roxo",
                "alternatives": ["lilas", "violeta", "roxo escuro", "lilás"], "weight": 3,
            },
            {
                "question": "O cabo é reto ou curvo (tipo bengala)?", "field_type": "choice",
                "options": ["Reto", "Curvo (bengala)"], "expected_answer": "Curvo (bengala)",
                "alternatives": ["curvo", "bengala"], "weight": 2,
            },
            {
                "question": "Descreva o mecanismo de abertura e qualquer defeito.",
                "field_type": "textarea", "placeholder": "Ex.: automático, uma vareta entortada...",
                "expected_answer": "automatico com botao, uma vareta solta",
                "alternatives": ["automatico", "botao automatico", "vareta quebrada"], "weight": 2,
            },
        ],
    },
    {
        "title": "Garrafa Térmica", "category": "Utensílios", "icon": "🍶",
        "found_date": "2026-05-03", "found_location": "Refeitório",
        "internal_notes": "Havia líquido dentro; foi higienizada.",
        "attributes": [
            {
                "question": "Qual a marca estampada na garrafa?", "placeholder": "Ex.: Stanley, Termolar...",
                "expected_answer": "stanley", "alternatives": ["stanley termica", "stanlei"], "weight": 3,
            },
            {
                "question": "Qual a capacidade em mililitros?", "field_type": "number",
                "placeholder": "Ex.: 500", "expected_answer": "473", "tolerance": 0.12, "weight": 2,
            },
            {
                "question": "Existe algum adesivo, nome ou marca de uso? Descreva.",
                "field_type": "textarea", "placeholder": "Descreva adesivos, riscos ou amassados.",
                "expected_answer": "adesivo de banda na lateral e amassado no fundo",
                "alternatives": ["adesivo de banda", "sticker de banda", "amassado"], "weight": 2,
            },
        ],
    },
    {
        "title": "Estojo Escolar", "category": "Material Escolar", "icon": "✏️",
        "found_date": "2026-05-02", "found_location": "Sala 204",
        "internal_notes": "Conteúdo conferido e lacrado.",
        "attributes": [
            {
                "question": "Qual a cor e o material do estojo?", "expected_answer": "rosa de tecido",
                "alternatives": ["rosa", "rosa claro tecido", "tecido rosa"], "weight": 2,
            },
            {
                "question": "Cite pelo menos dois itens que estavam dentro do estojo.",
                "field_type": "textarea", "placeholder": "Ex.: calculadora, canetas coloridas...",
                "expected_answer": "calculadora cientifica e canetas coloridas",
                "alternatives": ["calculadora e canetas", "canetas coloridas e calculadora",
                                  "calculadora cientifica"], "weight": 3,
            },
            {
                "question": "O estojo tem o nome do dono escrito em algum lugar? Qual?",
                "expected_answer": "helena", "alternatives": ["helena souza", "nome helena"], "weight": 2,
            },
        ],
    },
    {
        "title": "Smartphone", "category": "Eletrônicos", "icon": "📱",
        "found_date": "2026-05-06", "found_location": "Quadra poliesportiva",
        "internal_notes": "Aparelho desligado, guardado no cofre da secretaria.",
        "attributes": [
            {
                "question": "Qual a marca e o modelo do aparelho?", "placeholder": "Ex.: Samsung Galaxy S21",
                "expected_answer": "motorola moto g54",
                "alternatives": ["moto g54", "motorola g54", "motorola moto g 54"], "weight": 3,
            },
            {
                "question": "Qual a senha/PIN de desbloqueio da tela?", "placeholder": "Somente números",
                "expected_answer": "2019", "weight": 4, "is_critical": True,
            },
            {
                "question": "Descreva a capa e o estado da tela.", "field_type": "textarea",
                "placeholder": "Ex.: capa transparente, trinco no canto superior...",
                "expected_answer": "capa transparente com trinco no canto inferior direito",
                "alternatives": ["capa transparente", "capa incolor trincada"], "weight": 2,
            },
        ],
    },
    {
        "title": "Carteira", "category": "Acessórios", "icon": "👛",
        "found_date": "2026-05-05", "found_location": "Biblioteca",
        "internal_notes": "Documentos retirados e guardados separadamente.",
        "attributes": [
            {
                "question": "Qual a cor e o material da carteira?", "expected_answer": "marrom de couro",
                "alternatives": ["couro marrom", "marrom couro", "marrom"], "weight": 2,
            },
            {
                "question": "Qual o nome completo impresso nos documentos internos?",
                "placeholder": "Nome completo", "expected_answer": "rafael augusto lima",
                "alternatives": ["rafael lima", "rafael augusto"], "weight": 4, "is_critical": True,
            },
            {
                "question": "Quantos cartões havia dentro?", "field_type": "number",
                "placeholder": "Ex.: 3", "expected_answer": "4", "tolerance": 0.25, "weight": 1,
            },
        ],
    },
    {
        "title": "Chaveiro", "category": "Acessórios", "icon": "🔑",
        "found_date": "2026-05-07", "found_location": "Estacionamento",
        "internal_notes": "Molho com chaves residenciais.",
        "attributes": [
            {
                "question": "Quantas chaves estão no molho?", "field_type": "number",
                "placeholder": "Ex.: 3", "expected_answer": "3", "tolerance": 0.0, "weight": 3,
            },
            {
                "question": "Descreva o pingente/enfeite preso ao chaveiro.", "field_type": "textarea",
                "placeholder": "Ex.: pingente de urso de pelúcia azul",
                "expected_answer": "pingente de metal em formato de gato preto",
                "alternatives": ["gato de metal", "pingente de gato", "gatinho preto"], "weight": 3,
            },
        ],
    },
    {
        "title": "Óculos de Sol", "category": "Acessórios", "icon": "🕶️",
        "found_date": "2026-05-08", "found_location": "Quadra poliesportiva",
        "internal_notes": "Uma lente com risco leve.",
        "attributes": [
            {
                "question": "Qual a cor da armação?", "expected_answer": "preto fosco",
                "alternatives": ["preto", "preta fosca"], "weight": 3,
            },
            {
                "question": "Há alguma marca visível na haste?", "expected_answer": "ray ban",
                "alternatives": ["rayban", "ray-ban"], "weight": 2,
            },
        ],
    },
    {
        "title": "Squeeze", "category": "Utensílios", "icon": "🧴",
        "found_date": "2026-05-09", "found_location": "Refeitório",
        "internal_notes": "Higienizado antes do cadastro.",
        "attributes": [
            {
                "question": "Qual a cor predominante do squeeze?", "expected_answer": "verde",
                "alternatives": ["verde limao", "verde claro"], "weight": 2,
            },
            {
                "question": "Tem algum adesivo colado? Descreva.", "field_type": "textarea",
                "expected_answer": "adesivo de dinossauro na tampa",
                "alternatives": ["dinossauro", "adesivo de dino"], "weight": 3,
            },
        ],
    },
]


def _seed_users(conn) -> None:
    accounts = [
        ("Administração COTEMIG", current_app.config["DEFAULT_ADMIN_EMAIL"],
         current_app.config["DEFAULT_ADMIN_PASSWORD"], "admin"),
        ("Aluno Demonstração", "aluno@cotemig.com.br", "aluno123", "user"),
    ]
    from .security import hash_password

    for name, email, password, role in accounts:
        if User.find_by_email(conn, email):
            continue
        User.create(conn, name, email, hash_password(password), role=role)
    conn.commit()


def _seed_items(conn) -> None:
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS total FROM lost_items")
        if cursor.fetchone()["total"] > 0:
            return

    admin = User.find_by_email(conn, current_app.config["DEFAULT_ADMIN_EMAIL"])
    admin_id = admin["id"] if admin else None

    for item in DEMO_ITEMS:
        payload = {**item, "found_date": _to_date(item["found_date"])}
        ItemAdminService.create_item(conn, admin_id=admin_id, payload=payload)


def _to_date(value: str):
    from datetime import date as date_cls
    return date_cls.fromisoformat(value)


def run_seed() -> None:
    conn = get_db()
    _seed_users(conn)
    _seed_items(conn)
