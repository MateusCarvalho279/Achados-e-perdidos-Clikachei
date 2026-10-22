"""
Teste de integração das 5 funcionalidades avançadas exigidas pelo enunciado —
cada uma resolvida por uma stored procedure na camada Repository.

Pré-requisito: servidor rodando com banco recém-criado (`python run.py --reset`).

Rodar:
    python tests/test_advanced_features.py
"""

from __future__ import annotations

import json
import sys
import unicodedata
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api"
_passed = 0
_failed = 0


def check(label: str, condition: bool, extra: str = "") -> None:
    global _passed, _failed
    if condition:
        _passed += 1
        print(f"  [OK]   {label}")
    else:
        _failed += 1
        print(f"  [FALHA] {label} {extra}")


def call(path: str, method: str = "GET", body: dict | None = None, token: str | None = None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(f"{BASE}{path}", data=data, method=method)
    request.add_header("Accept", "application/json")
    if data:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"{}")
    except urllib.error.URLError as error:
        print(f"\nServidor indisponível em {BASE} ({error.reason}). Execute `python run.py`.\n")
        sys.exit(2)


def _sort_key(text: str) -> str:
    """
    Chave de ordenação sem acento, para comparar com o resultado do MySQL.

    A collation `utf8mb4_0900_ai_ci` (accent-insensitive) ordena "Óculos"
    junto dos O's — o correto em português — enquanto `sorted()` puro do
    Python compara pelo code point e jogaria o "Ó" para o final. Removendo
    o acento antes de comparar, as duas ordenações concordam.
    """
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def answers_for(questions, mapping):
    result = {str(q["id"]): "" for q in questions}
    remaining = list(questions)
    for needle, answer in mapping.items():
        for q in remaining:
            if needle.lower() in q["question"].lower():
                result[str(q["id"])] = answer
                remaining.remove(q)
                break
    return result


def main() -> int:
    _, aluno = call("/auth/login", "POST", {"email": "aluno@cotemig.com.br", "password": "aluno123"})
    token = aluno["access_token"]
    _, admin = call("/auth/login", "POST", {"email": "admin@cotemig.com.br", "password": "admin123"})
    admin_token = admin["access_token"]

    # ------------------------------------------------------------------ #
    print("\n=== Funcionalidade 1: Busca avançada de itens (sp_buscar_itens) ===")
    status, todos = call("/items")
    check("Lista sem filtro responde 200", status == 200 and len(todos) > 0)

    status, por_categoria = call("/items?categoria=Acess%C3%B3rios")
    check("Filtro por categoria só devolve a categoria pedida",
          status == 200 and all(i["category"] == "Acessórios" for i in por_categoria)
          and len(por_categoria) < len(todos))

    status, por_texto = call("/items?texto=garrafa")
    check("Filtro por texto encontra pelo título",
          status == 200 and any("Garrafa" in i["title"] for i in por_texto))

    status, sem_resultado = call("/items?texto=objeto-que-nao-existe-em-nenhum-item")
    check("Filtro sem correspondência devolve lista vazia (não erro)",
          status == 200 and sem_resultado == [])

    status, asc = call("/items?ordenacao=titulo_asc")
    titulos_asc = [i["title"] for i in asc]
    check("Ordenação título A-Z realmente ordena",
          status == 200 and titulos_asc == sorted(titulos_asc, key=_sort_key))

    status, desc = call("/items?ordenacao=titulo_desc")
    titulos_desc = [i["title"] for i in desc]
    check("Ordenação título Z-A é o inverso da A-Z", titulos_desc == list(reversed(titulos_asc)))

    status, combinado = call("/items?categoria=Utens%C3%ADlios&ordenacao=antigos")
    datas = [i["found_date"] for i in combinado]
    check("Filtros combinados (categoria + ordenação) funcionam juntos",
          status == 200 and datas == sorted(datas))

    # ------------------------------------------------------------------ #
    print("\n=== Funcionalidade 2: Auditoria de reivindicações com JOIN (sp_listar_reivindicacoes) ===")
    status, form = call("/items/EE-2026-003/questionnaire", token=token)
    respostas = answers_for(form["questions"], {
        "cor e o material": "rosa de tecido",
        "itens que estavam": "calculadora cientifica e canetas coloridas",
        "nome do dono": "helena",
    })
    call("/claims", "POST", {"item_code": "EE-2026-003", "answers": respostas}, token)

    status, claims = call("/admin/claims", token=admin_token)
    check("Listagem traz o JOIN completo (item + usuário)",
          status == 200 and len(claims) >= 1
          and {"item_title", "user_name", "user_email"} <= claims[0].keys())

    status, filtrado = call("/admin/claims?status=approved", token=admin_token)
    check("Filtro por status devolve só o status pedido",
          status == 200 and all(c["status"] == "approved" for c in filtrado))

    status, sem_admin = call("/admin/claims", token=token)
    check("Usuário comum não acessa a auditoria (403)", status == 403)

    # ------------------------------------------------------------------ #
    print("\n=== Funcionalidade 3: Relatório por categoria (sp_relatorio_categorias) ===")
    status, categorias = call("/admin/reports/categories", token=admin_token)
    check("Relatório de categorias responde 200 com dados", status == 200 and len(categorias) > 0)
    check("Cada linha traz as métricas agregadas esperadas",
          all({"category", "total_itens", "total_devolvidos", "taxa_recuperacao_pct"} <= c.keys()
              for c in categorias))
    check("Está ordenado por total de itens decrescente",
          [c["total_itens"] for c in categorias] ==
          sorted((c["total_itens"] for c in categorias), reverse=True))

    # ------------------------------------------------------------------ #
    print("\n=== Funcionalidade 4: Ranking de locais (sp_relatorio_locais) ===")
    status, locais = call("/admin/reports/locations?limite=3", token=admin_token)
    check("Relatório de locais respeita o LIMIT pedido", status == 200 and len(locais) <= 3)
    check("Está ordenado por total de itens decrescente",
          [l["total_itens"] for l in locais] == sorted((l["total_itens"] for l in locais), reverse=True))

    status, negado = call("/admin/reports/locations", token=token)
    check("Usuário comum não acessa relatórios (403)", status == 403)

    # ------------------------------------------------------------------ #
    print("\n=== Funcionalidade 5: Histórico filtrável do usuário (sp_historico_usuario) ===")
    status, historico = call("/claims/mine", token=token)
    check("Histórico do usuário traz a reivindicação feita acima",
          status == 200 and any(c["item_code"] == "EE-2026-003" for c in historico))

    status, so_aprovados = call("/claims/mine?status=approved", token=token)
    check("Filtro por status no histórico funciona",
          status == 200 and all(c["status"] == "approved" for c in so_aprovados))

    status, outro_usuario = call("/claims/mine", token=admin_token)
    check("Histórico é isolado por usuário (admin não vê pedidos do aluno)",
          status == 200 and all(c["item_code"] != "EE-2026-003" for c in outro_usuario))

    print("\n" + "=" * 62)
    print(f"  {_passed} verificações OK · {_failed} falha(s)")
    print("=" * 62 + "\n")
    return 1 if _failed else 0


if __name__ == "__main__":
    sys.exit(main())
