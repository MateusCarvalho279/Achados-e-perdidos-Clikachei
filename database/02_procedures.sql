-- =============================================================================
--  Stored Procedures — camada Repository
-- =============================================================================
--  Toda consulta que envolve filtros combináveis, ordenação dinâmica, JOIN
--  entre tabelas ou agregação (relatório) vive aqui, não no código Python.
--  A camada Repository apenas executa `CALL sp_x(...)` e mapeia o result set.
--
--  Truque de ordenação dinâmica: em vez de SQL dinâmico (PREPARE/EXECUTE),
--  usamos múltiplas colunas CASE no ORDER BY — cada uma só "acende" (deixa de
--  ser NULL) quando o parâmetro pedido bate. Linhas com todas as colunas
--  CASE = NULL empatam entre si e caem para a próxima coluna de desempate.
--  Isso evita concatenar texto do usuário em SQL dinâmico (risco de injeção)
--  mantendo a ordenação configurável pelo caller.
-- =============================================================================

USE achados_perdidos;

-- -----------------------------------------------------------------------------
-- 1) sp_buscar_itens
--    Caso de uso: "Busca avançada de itens" (dashboard público).
--    Filtros combináveis (todos opcionais, NULL = sem filtro) + ordenação.
--    Sempre restrita a status='available' — a mesma regra de segurança da
--    vitrine pública (item reivindicado nunca aparece).
-- -----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_buscar_itens;

DELIMITER $$
CREATE PROCEDURE sp_buscar_itens(
    IN p_categoria   VARCHAR(80),
    IN p_texto       VARCHAR(120),
    IN p_data_inicio DATE,
    IN p_data_fim    DATE,
    IN p_ordenacao   VARCHAR(20)   -- 'recentes' | 'antigos' | 'titulo_asc' | 'titulo_desc'
)
BEGIN
    SELECT
        i.public_code,
        i.title,
        i.category,
        i.icon,
        i.found_date,
        i.found_location,
        i.status,
        (SELECT COUNT(*) FROM item_attributes a WHERE a.item_id = i.id) AS question_count
    FROM lost_items i
    WHERE i.status = 'available'
      AND (p_categoria   IS NULL OR i.category = p_categoria)
      AND (p_texto       IS NULL OR i.title LIKE CONCAT('%', p_texto, '%')
                                  OR i.found_location LIKE CONCAT('%', p_texto, '%'))
      AND (p_data_inicio IS NULL OR i.found_date >= p_data_inicio)
      AND (p_data_fim    IS NULL OR i.found_date <= p_data_fim)
    ORDER BY
        CASE WHEN p_ordenacao = 'antigos'     THEN i.found_date END ASC,
        CASE WHEN p_ordenacao = 'titulo_asc'  THEN i.title      END ASC,
        CASE WHEN p_ordenacao = 'titulo_desc' THEN i.title      END DESC,
        CASE WHEN p_ordenacao IS NULL
               OR p_ordenacao NOT IN ('antigos', 'titulo_asc', 'titulo_desc')
             THEN i.found_date END DESC,
        i.id DESC;
END $$
DELIMITER ;

-- -----------------------------------------------------------------------------
-- 2) sp_listar_reivindicacoes
--    Caso de uso: "Auditoria de reivindicações" (painel admin).
--    JOIN de 3 tabelas (claim_requests + lost_items + users) com filtro
--    opcional por status e por item.
-- -----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_listar_reivindicacoes;

DELIMITER $$
CREATE PROCEDURE sp_listar_reivindicacoes(
    IN p_status    VARCHAR(20),   -- 'approved' | 'rejected' | 'pending_review' | NULL
    IN p_item_code VARCHAR(20)    -- filtra por item específico, ou NULL = todos
)
BEGIN
    SELECT
        c.id,
        i.public_code AS item_code,
        i.title       AS item_title,
        i.icon,
        u.name        AS user_name,
        u.email       AS user_email,
        c.score,
        c.status,
        c.pickup_code,
        c.breakdown,
        c.created_at
    FROM claim_requests c
    JOIN lost_items i ON i.id = c.item_id
    JOIN users u      ON u.id = c.user_id
    WHERE (p_status    IS NULL OR c.status = p_status)
      AND (p_item_code IS NULL OR i.public_code = p_item_code)
    ORDER BY c.created_at DESC, c.id DESC;
END $$
DELIMITER ;

-- -----------------------------------------------------------------------------
-- 3) sp_relatorio_categorias
--    Caso de uso: "Relatório gerencial por categoria" (painel admin).
--    Agregação (COUNT/AVG/GROUP BY) cruzando itens e reivindicações: quantos
--    itens por categoria, quantos devolvidos, taxa de recuperação e o score
--    médio das reivindicações aprovadas.
-- -----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_relatorio_categorias;

DELIMITER $$
CREATE PROCEDURE sp_relatorio_categorias()
BEGIN
    SELECT
        i.category,
        COUNT(DISTINCT i.id) AS total_itens,
        COUNT(DISTINCT CASE WHEN i.status = 'claimed' THEN i.id END) AS total_devolvidos,
        ROUND(
            COUNT(DISTINCT CASE WHEN i.status = 'claimed' THEN i.id END) * 100.0
            / NULLIF(COUNT(DISTINCT i.id), 0)
        , 1) AS taxa_recuperacao_pct,
        COUNT(c.id) AS total_tentativas,
        ROUND(AVG(CASE WHEN c.status = 'approved' THEN c.score END) * 100, 1)
            AS score_medio_aprovados_pct
    FROM lost_items i
    LEFT JOIN claim_requests c ON c.item_id = i.id
    GROUP BY i.category
    ORDER BY total_itens DESC, i.category ASC;
END $$
DELIMITER ;

-- -----------------------------------------------------------------------------
-- 4) sp_relatorio_locais
--    Caso de uso: "Ranking de locais com mais achados" (painel admin) — ajuda
--    a decidir onde reforçar a supervisão. GROUP BY + LIMIT parametrizado.
-- -----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_relatorio_locais;

DELIMITER $$
CREATE PROCEDURE sp_relatorio_locais(
    IN p_limite INT
)
BEGIN
    -- MySQL não aceita LIMIT NULL; se o caller não informar, usa 10.
    SET p_limite = IFNULL(p_limite, 10);

    SELECT
        COALESCE(i.found_location, 'Não informado') AS local,
        COUNT(*) AS total_itens,
        COUNT(CASE WHEN i.status = 'claimed' THEN 1 END) AS total_devolvidos,
        ROUND(COUNT(CASE WHEN i.status = 'claimed' THEN 1 END) * 100.0 / COUNT(*), 1)
            AS taxa_recuperacao_pct
    FROM lost_items i
    GROUP BY COALESCE(i.found_location, 'Não informado')
    ORDER BY total_itens DESC
    LIMIT p_limite;
END $$
DELIMITER ;

-- -----------------------------------------------------------------------------
-- 5) sp_historico_usuario
--    Caso de uso: "Meus Pedidos" filtrável (área do aluno). JOIN + filtro
--    opcional por status + ordenação dinâmica, restrito ao próprio usuário.
-- -----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_historico_usuario;

DELIMITER $$
CREATE PROCEDURE sp_historico_usuario(
    IN p_user_id   INT UNSIGNED,
    IN p_status    VARCHAR(20),   -- NULL = todos os status
    IN p_ordenacao VARCHAR(20)    -- 'recentes' (padrão) | 'antigos'
)
BEGIN
    SELECT
        c.id,
        i.public_code AS item_code,
        i.title       AS item_title,
        i.icon,
        c.status,
        c.pickup_code,
        c.score,
        c.created_at
    FROM claim_requests c
    JOIN lost_items i ON i.id = c.item_id
    WHERE c.user_id = p_user_id
      AND (p_status IS NULL OR c.status = p_status)
    ORDER BY
        CASE WHEN p_ordenacao = 'antigos' THEN c.created_at END ASC,
        CASE WHEN p_ordenacao IS NULL OR p_ordenacao <> 'antigos'
             THEN c.created_at END DESC,
        c.id DESC;
END $$
DELIMITER ;
