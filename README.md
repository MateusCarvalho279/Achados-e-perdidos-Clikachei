# Achados e Perdidos · Colégio COTEMIG

Sistema web de achados e perdidos escolar. O aluno consulta os itens encontrados, reivindica
o que é seu respondendo a um questionário sigiloso (validado automaticamente contra o gabarito
cadastrado pela secretaria) e registra alertas do que perdeu. A secretaria gerencia o acervo,
decide os pedidos duvidosos, registra a entrega presencial, destina itens antigos à doação e
acompanha relatórios.

**Stack:** Flask 3 + Flask-SQLAlchemy + MySQL 8 (Stored Procedures) · frontend em HTML/CSS/JS puro
consumindo a API REST via `fetch`.

Arquitetura: `Tela → API Flask → Controller → Service → Model/Repository → Banco de Dados`

📐 **Diagrama de classes:** [`docs/diagrama-de-classes.md`](docs/diagrama-de-classes.md)
(imagem: [`docs/diagrama-de-classes.png`](docs/diagrama-de-classes.png))

---

## Funcionalidades Implementadas

São 34 funcionalidades (0 a 33). Cada uma funciona de ponta a ponta: tela → rota da API → Controller →
Service → Model/Repository → MySQL.

### Área do aluno

> O site inteiro exige login. A porta de entrada é a **tela inicial** (`/` → `inicio.html`), que
> exibe uma **conta de teste** para conhecer o sistema sem precisar se cadastrar.

| # | Funcionalidade | Tela | Rota da API | Controller → Service | Model / Repository |
|---|---|---|---|---|---|
| 0 | **Tela inicial com conta de teste** (login obrigatório, entrada em um clique) | `inicio.html` | `GET /api/auth/test-account` · `POST /api/auth/login` | `AuthController.conta_teste` → `ObterContaTesteService` | `User.buscar_por_email()` |
| 1 | **Cadastrar aluno** | `login.html` (aba Cadastro) | `POST /api/auth/register` | `AuthController.cadastrar` → `CadastrarUsuarioService` | `User.salvar()` |
| 2 | **Fazer login** | `login.html` | `POST /api/auth/login` | `AuthController.autenticar` → `AutenticarUsuarioService` | `User.buscar_por_email()` |
| 3 | **Buscar itens com filtros e ordenação** (texto, categoria, período) | `index.html` | `GET /api/items` | `ItemController.buscar` → `BuscarItensService` | `ItemRepository.buscar_itens` → `CALL sp_buscar_itens` |
| 4 | **Listar categorias** (filtro e formulários) | `index.html`, `meus-alertas.html`, `admin.html` | `GET /api/items/categories` | `ItemController.listar_categorias` → `ListarCategoriasService` | `ItemRepository.listar_categorias` |
| 5 | **Reivindicar item por questionário** (motor de validação, limite de 3 tentativas, código de retirada) | `reivindicar.html` | `GET /api/items/<code>/questionnaire` · `POST /api/claims` | `ItemController.questionario` → `ObterQuestionarioService` · `ClaimController.enviar` → `EnviarReivindicacaoService` | `ClaimRequest.salvar()`, `ClaimRepository`, `ItemRepository.reservar_se_disponivel` |
| 6 | **Consultar histórico de pedidos** (filtro por situação + ordenação) | `meus-pedidos.html` | `GET /api/claims/mine` | `ClaimController.historico` → `ConsultarHistoricoService` | `ClaimRepository.historico_usuario` → `CALL sp_historico_usuario` |
| 7 | **Cancelar reivindicação** (libera o item se já estava reservado) | `meus-pedidos.html` | `POST /api/claims/<id>/cancel` | `ClaimController.cancelar` → `CancelarReivindicacaoService` | `ClaimRequest.atualizar()`, `LostItem.atualizar()` |
| 8 | **Registrar alerta de perda** (sugere itens compatíveis e notifica) | `meus-alertas.html` | `POST /api/lost-reports` | `LostReportController.registrar` → `RegistrarAlertaService` | `LostReport.salvar()`, `Notification.salvar()` |
| 9 | **Listar meus alertas de perda** | `meus-alertas.html` | `GET /api/lost-reports/mine` | `LostReportController.listar_meus` → `ListarMeusAlertasService` | `LostReportRepository.listar_do_usuario` |
| 10 | **Ver itens compatíveis com um alerta** | `meus-alertas.html` | `GET /api/lost-reports/<id>/matches` | `LostReportController.correspondencias` → `BuscarCorrespondenciasService` | `LostReport.buscar_por_id()`, `ItemRepository.listar_disponiveis` |
| 11 | **Cancelar alerta de perda** | `meus-alertas.html` | `POST /api/lost-reports/<id>/cancel` | `LostReportController.cancelar` → `CancelarAlertaService` | `LostReport.atualizar()` |
| 12 | **Consultar notificações** (contador no cabeçalho) | `notificacoes.html` + sino no menu | `GET /api/notifications` | `NotificationController.listar` → `ListarNotificacoesService` | `NotificationRepository` |
| 13 | **Marcar notificação como lida** | `notificacoes.html` | `POST /api/notifications/<id>/read` | `NotificationController.marcar_lida` → `MarcarNotificacaoLidaService` | `Notification.atualizar()` |
| 14 | **Marcar todas as notificações como lidas** | `notificacoes.html` | `POST /api/notifications/read-all` | `NotificationController.marcar_todas` → `MarcarTodasLidasService` | `NotificationRepository.marcar_todas_como_lidas` |

### Painel administrativo (`admin.html`)

| # | Funcionalidade | Aba | Rota da API | Controller → Service | Model / Repository |
|---|---|---|---|---|---|
| 15 | **Cadastrar item com gabarito sigiloso** (avisa alunos com alertas compatíveis) | Cadastrar item | `POST /api/admin/items` | `ItemController.cadastrar` → `CadastrarItemService` | `LostItem.salvar()` + `ItemAttribute` (composição) |
| 16 | **Listar itens do acervo** (todas as situações) | Itens registrados | `GET /api/admin/items` | `ItemController.listar_admin` → `ListarItensAdminService` | `LostItem.listar_todos()`, `ItemRepository.contar_perguntas_por_item` |
| 17 | **Editar item** (com visualização do gabarito) | Itens → Editar | `PUT /api/admin/items/<code>` · `GET /api/admin/items/<code>/attributes` | `ItemController.atualizar` → `AtualizarItemService` · `ConsultarGabaritoService` | `LostItem.atualizar()` |
| 18 | **Arquivar item** (sai da vitrine, mantém histórico) | Itens → Arquivar | `POST /api/admin/items/<code>/archive` | `ItemController.arquivar` → `ArquivarItemService` | `LostItem.atualizar()` |
| 19 | **Excluir item** (somente sem reivindicações) | Itens → Excluir | `DELETE /api/admin/items/<code>` | `ItemController.excluir` → `ExcluirItemService` | `LostItem.deletar()`, `ClaimRepository.existe_para_item` |
| 20 | **Imprimir etiqueta do item** | Itens → Etiqueta | `GET /api/admin/items/<code>/label` | `ItemController.etiqueta` → `GerarEtiquetaService` | `LostItem.buscar_por_codigo()` |
| 21 | **Auditar reivindicações** (JOIN item × aluno, filtros) | Reivindicações | `GET /api/admin/claims` | `ClaimController.listar_admin` → `ListarReivindicacoesService` | `ClaimRepository.listar_reivindicacoes` → `CALL sp_listar_reivindicacoes` |
| 22 | **Aprovar ou recusar reivindicação em análise** | Reivindicações | `POST /api/admin/claims/<id>/review` | `ClaimController.avaliar` → `AvaliarReivindicacaoService` | `ClaimRequest.atualizar()`, `ItemRepository.reservar_se_disponivel` |
| 23 | **Conferir código de retirada** | Retirada | `GET /api/admin/pickup/validate?code=` | `PickupController.validar` → `ValidarRetiradaService` | `LostItem.buscar_por_codigo_retirada()` |
| 24 | **Registrar entrega presencial** | Retirada | `POST /api/admin/pickup/deliver` | `PickupController.entregar` → `RegistrarEntregaService` | `LostItem.atualizar()`, `Notification.salvar()` |
| 25 | **Listar itens aptos à doação** (+N dias guardados) | Doações | `GET /api/admin/donations/eligible?days=` | `DonationController.listar_aptos` → `ListarItensDoacaoService` | `ItemRepository.itens_para_doacao` → `CALL sp_itens_para_doacao` |
| 26 | **Doar itens em lote** | Doações | `POST /api/admin/donations/batch` | `DonationController.doar` → `DoarItensService` | `ItemRepository.doar_em_lote` |
| 27 | **Consultar alertas de perda dos alunos** | Alertas de perda | `GET /api/admin/lost-reports?status=` | `LostReportController.listar_admin` → `ListarAlertasAdminService` | `LostReportRepository.buscar_alertas` → `CALL sp_buscar_alertas_perda` |
| 28 | **Buscar usuários com indicadores** | Usuários | `GET /api/admin/users?search=` | `UserController.listar` → `ListarUsuariosService` | `UserRepository.buscar_usuarios` → `CALL sp_buscar_usuarios` |
| 29 | **Alterar perfil do usuário** (aluno ↔ admin) | Usuários | `POST /api/admin/users/<id>/toggle-role` | `UserController.alterar_papel` → `AlterarPapelUsuarioService` | `User.atualizar()` |
| 30 | **Indicadores do painel** | Topo do painel | `GET /api/admin/stats` | `ReportController.indicadores` → `ObterIndicadoresService` | `ItemRepository`, `ClaimRepository`, `UserRepository` (contagens) |
| 31 | **Relatório por categoria** (itens × devolvidos × taxa de recuperação) | Relatórios | `GET /api/admin/reports/categories` | `ReportController.por_categoria` → `GerarRelatorioCategoriasService` | `ReportRepository.relatorio_categorias` → `CALL sp_relatorio_categorias` |
| 32 | **Ranking de locais com mais achados** | Relatórios | `GET /api/admin/reports/locations` | `ReportController.ranking_locais` → `GerarRankingLocaisService` | `ReportRepository.ranking_locais` → `CALL sp_relatorio_locais` |
| 33 | **Exportar relatórios em CSV** (acervo, reivindicações, categorias) | Relatórios | `GET /api/admin/reports/export?type=` | `ReportController.exportar_csv` → `ExportarRelatorioCsvService` | `LostItem.listar_todos()`, `ClaimRepository`, `ReportRepository` |

**Regras automáticas que atravessam funcionalidades:**

- Ao cadastrar um item, os alunos com alertas compatíveis recebem notificação (`NotificarCorrespondenciasService`).
- Quando uma reivindicação é aprovada, os alertas compatíveis do aluno são marcados como resolvidos (`ResolverAlertasService`).
- A reserva do item usa um `UPDATE ... WHERE status = 'available'` atômico. Duas aprovações simultâneas nunca reservam o mesmo item (`ReservarItemService`).

---

## Arquitetura e organização

```
backend/
├── app.py                  # fábrica Flask: registra controllers, erros e serve o frontend
├── config.py               # lê o .env (python-dotenv) e monta a URI do MySQL
├── extensions.py           # instância db = SQLAlchemy()
├── database_setup.py       # cria tabelas/procedures automaticamente na subida
├── seed.py                 # dados de demonstração (via Models e Services)
├── controllers/            # 1 classe por recurso (herdam de BaseController)
│   ├── base_controller.py
│   ├── auth_controller.py, user_controller.py, item_controller.py,
│   ├── claim_controller.py, lost_report_controller.py, notification_controller.py,
│   └── pickup_controller.py, donation_controller.py, report_controller.py
├── services/               # 1 classe = 1 caso de uso, método único executar()
│   ├── auth/  users/  items/  claims/  lost_reports/
│   └── notifications/  pickup/  donations/  reports/
├── models/                 # entidades (herdam de BaseModel → db.Model)
│   ├── base_model.py       # salvar, atualizar, deletar, listar_todos, buscar_por_id
│   └── user.py, lost_item.py, item_attribute.py, claim_request.py,
│       lost_report.py, notification.py
├── repositories/           # SÓ consultas especiais: CALL de procedures, filtros, contagens
│   ├── base_repository.py  # _chamar_procedure(): único ponto que executa CALL
│   └── item_, claim_, report_, user_, lost_report_, notification_repository.py
└── utils/                  # erros, validação, segurança (PBKDF2/JWT), motor de validação

frontend/
├── inicio.html (tela inicial)  index.html  login.html  reivindicar.html  meus-pedidos.html
├── meus-alertas.html  notificacoes.html  admin.html
├── css/styles.css
└── js/  api.js (único ponto de acesso à API) + um script por tela

database/
├── 01_schema.sql           # tabelas
└── 02_procedures.sql       # 8 stored procedures

docs/
└── diagrama-de-classes.md / .png
```

| Camada | Responsabilidade |
|---|---|
| **Controller** | Classe por recurso. Registra as próprias rotas, lê o corpo/parâmetros da requisição HTTP, chama `Service().executar(...)` e devolve o JSON. Não tem regra de negócio nem SQL. |
| **Service** | Uma classe por caso de uso, com um único método público `executar()`. Valida as entradas, aplica as regras de negócio, coordena Models e Repositories e controla a transação (`commit`). |
| **Model** | Entidade do domínio. Herda de `BaseModel`, que herda de `db.Model` e fornece `salvar()`, `atualizar()`, `deletar()`, `listar_todos()` e `buscar_por_id()`. |
| **Repository** | Só acessos especiais: filtros específicos, contagens, atualizações condicionais, relatórios e Stored Procedures. O `CALL` existe apenas em `BaseRepository._chamar_procedure`. |

### Stored Procedures (chamadas apenas pela camada Repository)

| Procedure | Repository | Uso |
|---|---|---|
| `sp_buscar_itens` | `ItemRepository.buscar_itens` | Vitrine com filtros combináveis e ordenação dinâmica |
| `sp_itens_para_doacao` | `ItemRepository.itens_para_doacao` | Itens disponíveis há mais de N dias |
| `sp_listar_reivindicacoes` | `ClaimRepository.listar_reivindicacoes` | Auditoria (JOIN reivindicação × item × usuário) |
| `sp_historico_usuario` | `ClaimRepository.historico_usuario` | Histórico do aluno com filtro e ordenação |
| `sp_relatorio_categorias` | `ReportRepository.relatorio_categorias` | Agregação por categoria |
| `sp_relatorio_locais` | `ReportRepository.ranking_locais` | Ranking com `GROUP BY` + `LIMIT` |
| `sp_buscar_alertas_perda` | `LostReportRepository.buscar_alertas` | Alertas com dados do aluno (JOIN) |
| `sp_buscar_usuarios` | `UserRepository.buscar_usuarios` | Usuários com totais de pedidos e alertas |

---

## Como executar

**Pré-requisitos:** Python 3.10+ e MySQL 8 (o MySQL do WampServer/XAMPP atende).

```bash
# 1. Ambiente virtual e dependências
python -m venv .venv
.venv\Scripts\activate            # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt

# 2. Variáveis de ambiente
copy .env.example .env            # Linux/Mac: cp .env.example .env
# edite o .env com o usuário e a senha do seu MySQL

# 3. Subir a aplicação (cria o banco, as tabelas, as procedures e os dados de demonstração)
python run.py
```

Acesse **http://127.0.0.1:8000**. A tela inicial pede login e mostra a conta de teste.

| Perfil | E-mail | Senha |
|---|---|---|
| **Conta de teste** (exibida na tela inicial) | `teste@cotemig.com.br` | `teste123` |
| Aluno | `aluno@cotemig.com.br` | `aluno123` |
| Administrador | `admin@cotemig.com.br` | `admin123` |

Opções: `python run.py --reload` (recarrega ao salvar) · `python run.py --reset` (**apaga** e recria o banco).

### Variáveis de ambiente (`.env`)

O arquivo `.env` **não vai para o repositório** (está no `.gitignore`). Use o `.env.example` como modelo.

| Variável | Descrição |
|---|---|
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | Conexão com o MySQL |
| `SECRET_KEY` | Chave de assinatura dos tokens. Se ficar vazia, é gerada uma vez em `data/.secret_key` (também ignorada pelo git). |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Conta de administrador criada na primeira execução |
| `TEST_ACCOUNT_NAME`, `TEST_ACCOUNT_EMAIL`, `TEST_ACCOUNT_PASSWORD` | Conta de teste (perfil aluno) exibida na tela inicial |
| `FLASK_DEBUG` | `1` liga o modo de desenvolvimento |

---

## Testes

Com o servidor rodando (`python run.py`):

```bash
python -m unittest tests.test_matching tests.test_security   # unitários (motor de validação e segurança)
python tests/test_new_features.py                            # ponta a ponta: alertas, notificações, retirada, doações, CSV, usuários...
python tests/test_advanced_features.py                       # ponta a ponta: procedures de busca, auditoria e relatórios
python tests/test_api_flow.py                                # fluxo completo (requer banco recém-criado)
```
#   A c h a d o s - e - p e r d i d o s - d e f i n i t i v o - c l i k a c h e i  
 #   A c h a d o s - e - p e r d i d o s - d e f i n i t i v o - c l i k a c h e i  
 