# Achados e Perdidos — Colégio COTEMIG

Sistema web de gerenciamento de achados e perdidos com **validação automatizada
de propriedade**: a vitrine pública mostra apenas dados genéricos de cada
item, e o reivindicante só recebe um **código de retirada** depois de
descrever corretamente características que só o dono legítimo saberia.

Este README documenta a **segunda etapa** do projeto: as funcionalidades além
do CRUD básico (busca com filtros, relatórios agregados, JOINs) implementadas
via **stored procedures no MySQL**, na arquitetura em camadas
**Model → Repository → Service → Controller**.

---

## Sumário

- [Stack e arquitetura](#stack-e-arquitetura)
- [Funcionalidades implementadas nesta etapa](#funcionalidades-implementadas-nesta-etapa)
- [Stored procedures criadas](#stored-procedures-criadas)
- [Onde fica a fronteira CRUD × avançado](#onde-fica-a-fronteira-crud--avançado)
- [Models e Repositories](#models-e-repositories)
- [Rotas da API](#rotas-da-api)
- [Modelagem do banco de dados](#modelagem-do-banco-de-dados)
- [Como executar](#como-executar)
- [Segurança](#segurança)

---

## Stack e arquitetura

| Camada | Tecnologia |
|---|---|
| Controller | **Flask** (Blueprints) — recebe a requisição HTTP, valida entrada, devolve JSON |
| Service | **Python puro**, um módulo por caso de uso — regra de negócio, transações |
| Repository | **PyMySQL** — só chama `CALL sp_xxx(...)`, nunca escreve SQL solto |
| Model | **PyMySQL** — CRUD de um registro por vez (insert/find/update por chave) |
| Banco | **MySQL 8** — schema + 5 stored procedures |
| Frontend | HTML + CSS + JavaScript (ES Modules), sem framework/build |

```
Requisição HTTP
      │
      ▼
┌─────────────┐   valida entrada, extrai parâmetros
│  Controller │   (backend/controllers/*.py — Blueprints Flask)
└──────┬──────┘
       │ chama
       ▼
┌─────────────┐   regra de negócio, decide o que é CRUD e o que é
│   Service   │   consulta avançada, orquestra Model + Repository,
│             │   único lugar que faz commit()
└──┬───────┬──┘   (backend/services/*.py — um arquivo por caso de uso)
   │       │
   ▼       ▼
┌──────┐ ┌────────────┐
│ Model│ │ Repository │  CALL sp_xxx(...) — filtros, JOIN, relatório
└──┬───┘ └─────┬──────┘  (backend/repositories/*.py)
   │ INSERT/SELECT-por-PK/UPDATE-por-PK
   ▼           ▼
┌───────────────────┐
│   MySQL 8          │
│  tabelas + 5 SPs   │
└───────────────────┘
```

Regra de dependência: **Controller nunca importa Model nem Repository
diretamente** — sempre passa por um Service. Isso é o que garante que toda
consulta com filtro/ordenação/JOIN passe por uma procedure, e não vaze como
SQL solto em algum controller apressado.

---

## Funcionalidades implementadas nesta etapa

As 5 funcionalidades abaixo vão além de criar/ler/atualizar/remover um
registro de uma tabela — cada uma envolve filtros combináveis, ordenação
dinâmica, JOIN entre tabelas ou agregação (relatório), e cada uma tem sua
própria stored procedure, Repository, Service e Controller/rota.

| # | Funcionalidade | Onde aparece na interface | Procedure |
|---|---|---|---|
| 1 | **Busca avançada de itens** — filtro por categoria, texto (título/local), intervalo de datas, e 4 modos de ordenação | Dashboard público (`index.html`), barra de busca acima da vitrine | `sp_buscar_itens` |
| 2 | **Auditoria de reivindicações** — JOIN de 3 tabelas (reivindicação × item × usuário), com filtro por situação | Painel admin → aba **Reivindicações** | `sp_listar_reivindicacoes` |
| 3 | **Relatório gerencial por categoria** — itens encontrados × devolvidos × taxa de recuperação × score médio, agrupado (`GROUP BY`) | Painel admin → aba **Relatórios** (primeira tabela) | `sp_relatorio_categorias` |
| 4 | **Ranking de locais** — locais com mais itens encontrados, com `LIMIT` configurável | Painel admin → aba **Relatórios** (segunda tabela) | `sp_relatorio_locais` |
| 5 | **Histórico filtrável do usuário** — JOIN reivindicação × item, filtro por situação e ordenação | `meus-pedidos.html`, filtro acima da tabela | `sp_historico_usuario` |

---

## Stored procedures criadas

Definidas em [`database/02_procedures.sql`](database/02_procedures.sql).

### 1. `sp_buscar_itens(p_categoria, p_texto, p_data_inicio, p_data_fim, p_ordenacao)`

Todos os parâmetros são opcionais (`NULL` = sem aquele filtro). `p_texto` busca
em título **e** local com `LIKE '%...%'`. `p_ordenacao` aceita `'recentes'`
(padrão), `'antigos'`, `'titulo_asc'`, `'titulo_desc'`. Sempre restrita a
`status = 'available'` — a mesma regra de segurança da vitrine pública.

A ordenação dinâmica é resolvida com múltiplas colunas `CASE` no `ORDER BY`
em vez de SQL dinâmico (`PREPARE`/`EXECUTE`): cada `CASE` só deixa de ser
`NULL` quando o parâmetro pedido bate, e linhas empatadas caem para a próxima
coluna de desempate. Isso evita concatenar texto do usuário em SQL dinâmico.

### 2. `sp_listar_reivindicacoes(p_status, p_item_code)`

`JOIN` de `claim_requests` + `lost_items` + `users`. Ambos os parâmetros são
opcionais. Usada na auditoria do painel admin.

### 3. `sp_relatorio_categorias()`

`LEFT JOIN` de `lost_items` com `claim_requests`, `GROUP BY category`.
Devolve, por categoria: total de itens, total devolvido, taxa de recuperação
(`%`) e o score médio das reivindicações aprovadas (`AVG` condicional).

### 4. `sp_relatorio_locais(p_limite)`

`GROUP BY found_location`, `ORDER BY total_itens DESC`, `LIMIT p_limite`
(usa `IFNULL(p_limite, 10)` internamente — MySQL aceita um parâmetro de
procedure diretamente no `LIMIT` desde a versão 5.5).

### 5. `sp_historico_usuario(p_user_id, p_status, p_ordenacao)`

`JOIN` de `claim_requests` + `lost_items`, restrito a `user_id = p_user_id`
(cada aluno só vê o próprio histórico). `p_status` filtra por situação;
`p_ordenacao` aceita `'recentes'` (padrão) ou `'antigos'`.

---

## Onde fica a fronteira CRUD × avançado

O enunciado pede que "consultas com filtros, buscas, ordenações, relatórios,
JOIN... " fiquem no Repository via procedure, enquanto o Model cobre "CRUD
básico". Levado ao pé da letra, isso incluiria até um `WHERE email = ?` de
login. A regra que seguimos, documentada aqui para deixar o critério
explícito:

- **Fica no Model** (SQL direto, sem procedure): busca por chave primária ou
  única (`find_by_id`, `find_by_code`, `find_by_email`), inserção/atualização
  de um registro, e pequenas contagens de uma única tabela com uma única
  condição que são regra de domínio da própria entidade — por exemplo,
  "quantas tentativas rejeitadas este usuário já fez neste item" (limite
  anti-fraude) ou "quantos itens estão com status X" (card de indicador). Isso
  não é uma busca de negócio para o usuário final, é o próprio "claim"
  verificando sua regra de limite.
- **Vai para o Repository + procedure**: qualquer consulta com **filtros
  combináveis escolhidos pelo usuário**, **ordenação escolhida pelo
  usuário**, **JOIN entre tabelas** para exibição, ou **agregação/relatório**
  (`GROUP BY`, `AVG`, ranking). As 5 funcionalidades da tabela acima.

---

## Models e Repositories

### Models (`backend/models/`)

| Classe | Tabela | Métodos |
|---|---|---|
| `User` | `users` | `create`, `find_by_id`, `find_by_email`, `count_by_role` |
| `LostItem` | `lost_items` | `create`, `find_by_id`, `find_by_code`, `find_all`, `count_public_code_prefix`, `mark_claimed`, `archive`, `count_by_status` |
| `ItemAttribute` | `item_attributes` | `create`, `find_by_item_id`, `count_by_item_id` |
| `ClaimRequest` | `claim_requests` | `create`, `find_by_id`, `count_rejected`, `has_pending`, `mark_reviewed`, `count_all`, `count_by_status` |

### Repositories (`backend/repositories/`)

| Classe | Método | Procedure chamada |
|---|---|---|
| `ItemRepository` | `buscar_itens(...)` | `sp_buscar_itens` |
| `ClaimRepository` | `listar_reivindicacoes(...)` | `sp_listar_reivindicacoes` |
| `ClaimRepository` | `historico_usuario(...)` | `sp_historico_usuario` |
| `ReportRepository` | `relatorio_categorias(...)` | `sp_relatorio_categorias` |
| `ReportRepository` | `relatorio_locais(...)` | `sp_relatorio_locais` |

### Services (`backend/services/`) — um por caso de uso

`AuthService` · `ItemAdminService` (CRUD de itens + questionário) ·
`ItemSearchService` (busca avançada) · `ClaimSubmissionService` (submissão +
motor de validação) · `ClaimReviewService` (auditoria + revisão manual) ·
`UserHistoryService` (histórico do usuário) · `CategoryReportService` ·
`LocationReportService` · `AdminStatsService` (indicadores do painel).

---

## Rotas da API

### Públicas

| Método | Rota | Camada avançada envolvida |
|---|---|---|
| `GET` | `/api/items?categoria=&texto=&data_inicio=&data_fim=&ordenacao=` | **Repository** → `sp_buscar_itens` |
| `GET` | `/api/items/{code}` | Model |
| `GET` | `/api/health` | — |
| `POST` | `/api/auth/register` | Model |
| `POST` | `/api/auth/login` | Model |

### Autenticadas (aluno)

| Método | Rota | Camada avançada envolvida |
|---|---|---|
| `GET` | `/api/auth/me` | Model |
| `GET` | `/api/items/{code}/questionnaire` | Model |
| `POST` | `/api/claims` | Service (motor de validação) |
| `GET` | `/api/claims/mine?status=&ordenacao=` | **Repository** → `sp_historico_usuario` |
| `GET` | `/api/claims/limits/{code}` | Model |

### Administrador

| Método | Rota | Camada avançada envolvida |
|---|---|---|
| `POST` | `/api/admin/items` | Model (transação: item + atributos) |
| `GET` | `/api/admin/items` | Model |
| `GET` | `/api/admin/items/{code}/attributes` | Model |
| `DELETE` | `/api/admin/items/{code}` | Model |
| `GET` | `/api/admin/stats` | Model (contagens) |
| `GET` | `/api/admin/claims?status=&item_code=` | **Repository** → `sp_listar_reivindicacoes` |
| `POST` | `/api/admin/claims/{id}/review` | Model |
| `GET` | `/api/admin/reports/categories` | **Repository** → `sp_relatorio_categorias` |
| `GET` | `/api/admin/reports/locations?limite=` | **Repository** → `sp_relatorio_locais` |

---

## Modelagem do banco de dados

```
users ──┬──< lost_items >──┬──< item_attributes   (gabarito sigiloso)
        │   (vitrine        │
        │    pública)       └──< claim_requests >── users
        └────────────────────────────< claim_requests
```

- **`users`** — `id, name, email UNIQUE, password_hash, role ENUM, created_at`
- **`lost_items`** — dados públicos (`title, category, found_date...`) +
  campos sigilosos/operacionais (`internal_notes, pickup_code`) na mesma
  tabela, mas a API pública nunca lê `internal_notes`.
- **`item_attributes`** — o gabarito: `question, field_type, expected_answer
  (sigiloso), alternatives (sigiloso), weight, is_critical, tolerance`.
- **`claim_requests`** — trilha de auditoria de toda tentativa: `answers,
  breakdown, score, status, pickup_code, reviewed_by`.

Script completo em [`database/01_schema.sql`](database/01_schema.sql).

---

## Como executar

### Pré-requisitos

- Python 3.10+
- MySQL 8 rodando localmente (ou acessível), com um usuário que possa criar
  bancos e procedures

### Passos

```bash
# 1. Instalar as dependências
pip install -r requirements.txt

# 2. Configurar a conexão (opcional — os padrões abaixo já funcionam para
#    um MySQL local com root sem senha)
set DB_HOST=localhost
set DB_PORT=3306
set DB_USER=root
set DB_PASSWORD=

# 3. Criar o schema + procedures e subir o servidor
python run.py --reset
```

| Endereço | O quê |
|---|---|
| <http://127.0.0.1:8000> | Vitrine pública com busca avançada |
| <http://127.0.0.1:8000/login.html> | Portal do aluno |
| <http://127.0.0.1:8000/admin.html> | Painel administrativo (itens, reivindicações, relatórios) |

Flags do `run.py`:

```bash
python run.py            # sobe o servidor (não mexe no banco)
python run.py --reload   # + hot reload (desenvolvimento)
python run.py --reset    # recria o schema e as procedures no MySQL antes de subir
```

### Contas de demonstração

| Perfil | E-mail | Senha |
|---|---|---|
| Administrador | `admin@cotemig.com.br` | `admin123` |
| Aluno | `aluno@cotemig.com.br` | `aluno123` |

---

## Segurança

Mesmas proteções da etapa anterior, agora sustentadas pelo desenho do banco:
tabelas separadas para dados públicos (`lost_items`) e sigilosos
(`item_attributes`), nenhuma procedure pública devolve `expected_answer`,
limite de 3 tentativas por item/usuário, características críticas vetam a
reivindicação, senhas em PBKDF2-SHA256 (260 mil iterações), sessão via JWT
HS256, e todo texto vindo do backend passa por `escapeHtml()` no frontend
antes de virar HTML.
