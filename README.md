# Achados e Perdidos

Sistema web de achados e perdidos escolar. O aluno consulta os itens encontrados,
filtra por dia ou categoria e abre uma reivindicacao comprovando a propriedade;
a secretaria gerencia o acervo de itens e acompanha os relatorios.

Projeto desenvolvido em **Flask + MySQL**, seguindo a arquitetura
`Tela -> API Flask -> Controller -> Service -> Model/Repository -> Banco de Dados`.

---

## Funcionalidades Implementadas

1. **Cadastrar cliente** - cadastro do aluno com validacao de e-mail, matricula unica e senha com hash.
2. **Listar produtos** - lista todos os itens encontrados cadastrados no sistema.
3. **Atualizar lista de produtos** - edicao dos dados de um item (nome, categoria, cor, marca, local, status, data).
4. **Excluir produto** - remocao de um item, bloqueada quando ele esta reservado para entrega.
5. **Cadastrar produto** - registro de um novo item encontrado, com validacao de categoria e data.
6. **Listar por dia** - itens encontrados em uma data especifica (procedure `sp_listar_produtos_por_dia`).
7. **Buscar produtos por categoria** - filtro por categoria + status (procedure `sp_buscar_produtos_por_categoria`).
8. **Registrar reivindicacao** - solicitacao de devolucao com regras de negocio (datas coerentes, item nao entregue, sem duplicidade pendente).
9. **Consultar historico de reivindicacao** - consulta com JOIN entre reivindicacoes, clientes e produtos, com calculo de compatibilidade (procedure `sp_historico_reivindicacoes`).
10. **Gerar relatorio de reivindicacao** - totais por situacao, por categoria e ranking de locais em um periodo (procedures `sp_relatorio_reivindicacoes`, `sp_relatorio_reivindicacoes_por_categoria`, `sp_ranking_locais_perda`).

> Funcionalidade complementar: **login do cliente** (`AutenticarClienteService`), usado para
> identificar o solicitante nas telas de reivindicacao e historico.

---

## Arquitetura

```
backend/
    app.py                     # cria a aplicacao Flask e registra os blueprints
    config.py                  # le o .env e monta a URI do banco
    extensions.py              # instancia do SQLAlchemy (db)
    errors.py                  # excecoes de regra de negocio
    utils.py                   # validacoes reutilizaveis (data, e-mail, texto)
    controllers/               # classes que recebem as requisicoes HTTP
    services/                  # uma classe por caso de uso, com metodo execute()
    models/                    # entidades do dominio (db.Model) + CRUD via ORM
    repositories/              # consultas complexas encapsulando CALL de procedures
    database/
        schema.sql             # tabelas + stored procedures
        seed.py                # dados de demonstracao

frontend/
    index.html                 # itens encontrados + filtros por dia e categoria
    pages/
        login.html             # login do cliente
        cadastro.html          # cadastro de cliente
        produtos.html          # cadastrar / atualizar / excluir itens
        reivindicar.html       # registrar reivindicacao
        historico.html         # historico de reivindicacoes
        relatorio.html         # relatorio de reivindicacoes
    assets/
        css/style.css
        js/                    # api.js + um script por tela (consomem a API via fetch)
```

**Responsabilidades**

| Camada | Responsabilidade |
| --- | --- |
| Controller | Classe por recurso. Recebe a requisicao, interpreta os dados e chama o `execute()` do Service. Nao contem regra de negocio nem SQL. |
| Service | Uma classe por caso de uso, com um unico metodo `execute()`. Faz as validacoes e coordena Model/Repository. |
| Model | Herda de `db.Model`. Representa a entidade e concentra o CRUD basico via ORM: `salvar()`, `atualizar()`, `deletar()`, `listar_todos()`, `buscar_por_id()`. |
| Repository | Somente acessos especiais ao banco (filtros, JOIN, agregacoes, ranking), sempre chamando Stored Procedures. O `CALL` existe apenas aqui. |

---

## Models

| Model | Tabela | Descricao |
| --- | --- | --- |
| `Cliente` | `clientes` | Aluno que utiliza o sistema. |
| `Produto` | `produtos` | Item encontrado no colegio. |
| `Reivindicacao` | `reivindicacoes` | Solicitacao de devolucao feita por um cliente sobre um item. |

## Repositories

| Repository | Metodo | Procedure chamada |
| --- | --- | --- |
| `ProdutoRepository` | `listar_por_dia` | `sp_listar_produtos_por_dia` |
| `ProdutoRepository` | `buscar_por_categoria` | `sp_buscar_produtos_por_categoria` |
| `ReivindicacaoRepository` | `historico` | `sp_historico_reivindicacoes` |
| `ReivindicacaoRepository` | `relatorio_por_status` | `sp_relatorio_reivindicacoes` |
| `ReivindicacaoRepository` | `relatorio_por_categoria` | `sp_relatorio_reivindicacoes_por_categoria` |
| `ReivindicacaoRepository` | `ranking_locais_perda` | `sp_ranking_locais_perda` |
| `ReivindicacaoRepository` | `existe_pendente` | `sp_reivindicacao_duplicada` |

## Procedures criadas

| Procedure | O que faz |
| --- | --- |
| `sp_listar_produtos_por_dia(p_data)` | `WHERE` por data + `LEFT JOIN` com reivindicacoes, `GROUP BY` e `ORDER BY`. |
| `sp_buscar_produtos_por_categoria(p_categoria, p_status)` | Filtro por categoria com status opcional, contando reivindicacoes. |
| `sp_historico_reivindicacoes(p_cliente_id, p_status)` | `INNER JOIN` das 3 tabelas, `DATEDIFF` e `CASE` calculando a compatibilidade da reivindicacao. |
| `sp_relatorio_reivindicacoes(p_data_inicio, p_data_fim)` | Agregacao por situacao no periodo (`COUNT`, `AVG`, `MIN`, `MAX`). |
| `sp_relatorio_reivindicacoes_por_categoria(p_data_inicio, p_data_fim)` | Agregacao por categoria do item com `SUM(CASE ...)`. |
| `sp_ranking_locais_perda(p_limite)` | Ranking dos locais com mais perdas (`GROUP BY` + `ORDER BY` + `LIMIT`). |
| `sp_reivindicacao_duplicada(p_produto_id, p_cliente_id)` | Verifica se ja existe reivindicacao pendente do mesmo cliente para o item. |

---

## Rotas da API

| Metodo | Rota | Funcionalidade | Controller -> Service |
| --- | --- | --- | --- |
| POST | `/api/clientes` | 1. Cadastrar cliente | `ClienteController.cadastrar` -> `CadastrarClienteService` |
| GET | `/api/clientes` | Listar clientes (apoio) | `ClienteController.listar` -> `ListarClientesService` |
| POST | `/api/clientes/login` | Login do cliente | `ClienteController.autenticar` -> `AutenticarClienteService` |
| GET | `/api/produtos` | 2. Listar produtos | `ProdutoController.listar` -> `ListarProdutosService` |
| PUT | `/api/produtos/<id>` | 3. Atualizar produto | `ProdutoController.atualizar` -> `AtualizarProdutoService` |
| DELETE | `/api/produtos/<id>` | 4. Excluir produto | `ProdutoController.excluir` -> `ExcluirProdutoService` |
| POST | `/api/produtos` | 5. Cadastrar produto | `ProdutoController.cadastrar` -> `CadastrarProdutoService` |
| GET | `/api/produtos/por-dia?data=` | 6. Listar por dia | `ProdutoController.listar_por_dia` -> `ListarProdutosPorDiaService` |
| GET | `/api/produtos/categoria?categoria=&status=` | 7. Buscar por categoria | `ProdutoController.buscar_por_categoria` -> `BuscarProdutosPorCategoriaService` |
| GET | `/api/produtos/<id>` | Detalhar item (apoio) | `ProdutoController.buscar` -> `BuscarProdutoService` |
| GET | `/api/produtos/categorias` | Categorias aceitas (apoio) | `ProdutoController.listar_categorias` |
| POST | `/api/reivindicacoes` | 8. Registrar reivindicacao | `ReivindicacaoController.registrar` -> `RegistrarReivindicacaoService` |
| GET | `/api/reivindicacoes/historico?cliente_id=&status=` | 9. Consultar historico | `ReivindicacaoController.historico` -> `ConsultarHistoricoReivindicacaoService` |
| GET | `/api/reivindicacoes/relatorio?data_inicio=&data_fim=` | 10. Gerar relatorio | `ReivindicacaoController.relatorio` -> `GerarRelatorioReivindicacaoService` |

---

## Como executar

**Pre-requisitos:** Python 3.10+ e MySQL 8 (o WampServer/XAMPP ja atende).

```bash
# 1. Ambiente virtual e dependencias
python -m venv .venv
.venv\Scripts\activate          # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt

# 2. Variaveis de ambiente
copy .env.example .env          # Linux/Mac: cp .env.example .env
# edite o .env com o usuario e a senha do seu MySQL

# 3. Banco de dados (cria tabelas e procedures)
mysql -u root -p < backend/database/schema.sql

# 4. Dados de demonstracao (opcional)
cd backend
python database/seed.py

# 5. Subir a aplicacao
python app.py
```

Acesse **http://localhost:5000**.

Usuario de teste criado pelo seed: `ana@cotemig.br` / `123456`.

> As credenciais do banco ficam no arquivo `.env`, que esta no `.gitignore` e
> nao e enviado para o repositorio. Use o `.env.example` como modelo.

---

## Regras de negocio implementadas nos Services

- E-mail e matricula do cliente nao podem se repetir; a senha e gravada com hash.
- A categoria do item precisa estar na lista aceita e a data do encontro nao pode ser futura.
- Um item com status `Reservado` nao pode ser excluido.
- A data da perda deve ser anterior a data em que o item foi encontrado.
- Um item ja `Entregue` nao aceita novas reivindicacoes.
- O mesmo cliente nao pode abrir duas reivindicacoes pendentes para o mesmo item.
- Ao registrar uma reivindicacao, o item passa automaticamente para `Reservado`.
