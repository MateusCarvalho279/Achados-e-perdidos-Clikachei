"""
Teste de integração ponta a ponta contra o servidor em execução.

Pré-requisito: servidor rodando com o banco recém-criado, pois o teste consome
reivindicações e tentativas (que são de uso único por design):

    python run.py --reset

Rodar:
    python tests/test_api_flow.py
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "http://127.0.0.1:8000/api"

_passed = 0
_failed = 0


def check(label: str, condition: bool, extra: str = "") -> None:
    """Registra uma asserção com saída legível."""
    global _passed, _failed
    if condition:
        _passed += 1
        print(f"  [OK]   {label}")
    else:
        _failed += 1
        print(f"  [FALHA] {label} {extra}")


def call(path: str, method: str = "GET", body: dict | None = None,
         token: str | None = None) -> tuple[int, dict]:
    """Chamada HTTP que devolve (status, payload) sem lançar em erro 4xx/5xx."""
    data = json.dumps(body).encode() if body is not None else None
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
        print(f"\nServidor indisponível em {BASE} ({error.reason}).")
        print("Execute `python run.py` antes deste teste.\n")
        sys.exit(2)


def answers_for(questions: list[dict], mapping: dict[str, str]) -> dict[str, str]:
    """
    Casa respostas por trecho da pergunta, já que os ids variam por banco.

    Cada pergunta é consumida ao ser casada — sem isso um trecho genérico como
    "marca" casaria com duas perguntas distintas e a segunda ficaria sem
    resposta, produzindo um falso negativo no teste.
    """
    result = {str(question["id"]): "" for question in questions}
    remaining = list(questions)

    for needle, answer in mapping.items():
        for question in remaining:
            if needle.lower() in question["question"].lower():
                result[str(question["id"])] = answer
                remaining.remove(question)
                break
        else:
            raise AssertionError(f"Nenhuma pergunta corresponde a {needle!r}")

    return result


def main() -> int:
    print("\n=== 1. Infraestrutura e vitrine pública ===")
    status, health = call("/health")
    check("GET /health responde 200", status == 200)

    status, items = call("/items")
    check("GET /items responde 200", status == 200)
    check("Vitrine tem itens disponíveis", len(items) > 0, f"({len(items)})")

    serialized = json.dumps(items)
    check("Vitrine NÃO vaza gabarito",
          "expected_answer" not in serialized and "alternatives" not in serialized)
    check("Vitrine NÃO vaza notas internas", "internal_notes" not in serialized)
    check("Todos os itens listados estão disponíveis",
          all(item["status"] == "available" for item in items))
    initial_count = len(items)

    print("\n=== 2. Proteção do questionário ===")
    status, _ = call("/items/GT-2026-002/questionnaire")
    check("Questionário exige autenticação (401)", status == 401, f"(veio {status})")

    print("\n=== 3. Autenticação ===")
    status, auth = call("/auth/login", "POST",
                        {"email": "aluno@cotemig.com.br", "password": "aluno123"})
    check("Login do aluno responde 200", status == 200, str(auth)[:90])
    token = auth.get("access_token", "")
    check("Token JWT emitido", bool(token))

    status, _ = call("/auth/login", "POST",
                     {"email": "aluno@cotemig.com.br", "password": "senha-errada"})
    check("Senha incorreta é rejeitada (401)", status == 401)

    print("\n=== 4. Questionário autenticado ===")
    status, form = call("/items/GT-2026-002/questionnaire", token=token)
    check("Questionário carrega para usuário logado", status == 200, str(form)[:90])
    questions = form.get("questions", [])
    check("Perguntas retornadas", len(questions) == 3, f"({len(questions)})")
    check("Perguntas NÃO carregam a resposta esperada",
          "expected_answer" not in json.dumps(form))

    print("\n=== 5. Reivindicação correta -> código de retirada ===")
    correct = answers_for(questions, {
        "marca estampada": "Stanley",
        "capacidade": "473",
        "adesivo": "adesivo de banda na lateral e amassado no fundo",
    })
    status, result = call("/claims", "POST",
                          {"item_code": "GT-2026-002", "answers": correct}, token)
    check("Reivindicação aceita (200)", status == 200, str(result)[:90])
    check("Status = approved", result.get("status") == "approved", str(result)[:120])
    code = result.get("pickup_code") or ""
    check("Código de retirada emitido no formato REC-9999-AAA",
          code.startswith("REC-") and len(code) == 12, code)

    print("\n=== 6. Remoção imediata da vitrine (post-claim) ===")
    status, items_after = call("/items")
    codes = [item["public_code"] for item in items_after]
    check("Item reivindicado sumiu da vitrine", "GT-2026-002" not in codes)
    check("Contagem caiu em exatamente 1",
          len(items_after) == initial_count - 1, f"({initial_count} -> {len(items_after)})")

    status, _ = call("/items/GT-2026-002/questionnaire", token=token)
    check("Novo questionário do item bloqueado (409)", status == 409, f"(veio {status})")

    status, retry = call("/claims", "POST",
                         {"item_code": "GT-2026-002", "answers": correct}, token)
    check("Nova reivindicação do mesmo item bloqueada (409)", status == 409)

    print("\n=== 7. Reivindicação incorreta ===")
    status, form = call("/items/CH-2026-006/questionnaire", token=token)
    wrong = answers_for(form["questions"], {
        "quantas": "9",
        "pingente": "pingente de urso de pelucia azul",
    })
    status, result = call("/claims", "POST",
                          {"item_code": "CH-2026-006", "answers": wrong}, token)
    check("Resposta errada é recusada", result.get("status") == "rejected", str(result)[:120])
    check("Nenhum código emitido em recusa", result.get("pickup_code") is None)
    check("Tentativas restantes decrementadas",
          result.get("attempts_left") == 2, str(result.get("attempts_left")))
    check("Mensagem NÃO revela qual resposta errou",
          "pingente" not in result.get("message", "").lower())

    status, items_now = call("/items")
    check("Item permanece na vitrine após recusa",
          "CH-2026-006" in [i["public_code"] for i in items_now])

    print("\n=== 8. Veto de característica crítica ===")
    status, form = call("/items/CA-2026-005/questionnaire", token=token)
    critical = answers_for(form["questions"], {
        "cor e o material": "marrom de couro",   # correto
        "nome completo": "joao pedro silva",     # CRÍTICA errada
        "quantos cartões": "4",                  # correto
    })
    status, result = call("/claims", "POST",
                          {"item_code": "CA-2026-005", "answers": critical}, token)
    check("Errar característica crítica reprova mesmo com o resto correto",
          result.get("status") == "rejected", str(result)[:120])

    print("\n=== 9. Limite anti-fraude (3 tentativas) ===")
    # A 1ª tentativa já foi gasta na seção 7; gastamos as duas restantes.
    for _ in range(2):
        call("/claims", "POST", {"item_code": "CH-2026-006", "answers": {}}, token)
    status, _ = call("/claims", "POST",
                     {"item_code": "CH-2026-006", "answers": wrong}, token)
    check("4ª tentativa bloqueada (429)", status == 429, f"(veio {status})")

    status, _ = call("/items/CH-2026-006/questionnaire", token=token)
    check("Questionário também fica bloqueado após o limite (429)",
          status == 429, f"(veio {status})")

    print("\n=== 10. Área administrativa ===")
    status, denied = call("/admin/stats", token=token)
    check("Aluno não acessa rota de admin (403)", status == 403, f"(veio {status})")

    status, admin_auth = call("/auth/login", "POST",
                              {"email": "admin@cotemig.com.br", "password": "admin123"})
    admin_token = admin_auth.get("access_token", "")
    check("Login do administrador", status == 200 and bool(admin_token))

    status, stats = call("/admin/stats", token=admin_token)
    check("Estatísticas acessíveis ao admin", status == 200, str(stats)[:90])
    check("Contabiliza o item devolvido", stats.get("items_claimed", 0) >= 1, str(stats))

    status, claims = call("/admin/claims", token=admin_token)
    check("Trilha de auditoria registrou as tentativas",
          status == 200 and len(claims) >= 4, f"({len(claims)} registros)")
    check("Auditoria traz o detalhamento por pergunta",
          bool(claims and claims[0].get("breakdown")))

    status, created = call("/admin/items", "POST", {
        "title": "Fone de Ouvido",
        "category": "Eletrônicos",
        "icon": "🎧",
        "found_date": "2026-05-08",
        "found_location": "Laboratório 3",
        "attributes": [{
            "question": "Qual a marca e a cor do fone?",
            "expected_answer": "jbl preto",
            "alternatives": ["jbl", "preto jbl"],
            "weight": 3,
        }],
    }, admin_token)
    check("Admin cadastra item novo (201)", status == 201, str(created)[:110])
    new_code = created.get("public_code", "")
    check("Código público derivado das iniciais (FO-2026-###)",
          new_code.startswith("FO-2026-"), new_code)

    status, items_final = call("/items")
    check("Item novo aparece na vitrine pública",
          new_code in [item["public_code"] for item in items_final])

    call(f"/admin/items/{new_code}", "DELETE", token=admin_token)
    status, items_archived = call("/items")
    check("Item arquivado sai da vitrine",
          new_code not in [item["public_code"] for item in items_archived])

    print("\n=== 11. Requisições concorrentes ===")
    # O painel administrativo dispara várias chamadas em paralelo, e o servidor
    # de desenvolvimento do Flask atende com `threaded=True`. Cada requisição
    # abre e fecha sua própria conexão PyMySQL — este teste garante que isso
    # continue seguro sob concorrência real.
    endpoints = [("/items", None), ("/admin/stats", admin_token),
                 ("/admin/items", admin_token), ("/admin/claims", admin_token),
                 ("/health", None), ("/claims/mine", token)]
    tasks = endpoints * 5

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(lambda job: call(job[0], token=job[1])[0], tasks))

    falhas = [
        f"{path} -> {status}"
        for (path, _), status in zip(tasks, results) if status != 200
    ]
    check(f"{len(tasks)} requisições paralelas sem erro 5xx",
          not falhas, " | ".join(falhas[:4]))

    print("\n" + "=" * 62)
    print(f"  {_passed} verificações OK · {_failed} falha(s)")
    print("=" * 62 + "\n")
    return 1 if _failed else 0


if __name__ == "__main__":
    sys.exit(main())
