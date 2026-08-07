-- =============================================================================
--  Sistema de Achados e Perdidos — Colégio COTEMIG
--  Schema MySQL (InnoDB, utf8mb4)
-- =============================================================================
--  Mesmo princípio de segurança da etapa anterior: dados PÚBLICOS de um item
--  (lost_items) e dados SIGILOSOS (item_attributes) ficam em tabelas
--  separadas. A API pública nunca faz JOIN entre elas.
-- =============================================================================

CREATE DATABASE IF NOT EXISTS achados_perdidos
    CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

USE achados_perdidos;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS claim_requests;
DROP TABLE IF EXISTS item_attributes;
DROP TABLE IF EXISTS lost_items;
DROP TABLE IF EXISTS users;
SET FOREIGN_KEY_CHECKS = 1;

-- -----------------------------------------------------------------------------
-- USERS — donos dos itens e administradores
-- -----------------------------------------------------------------------------
CREATE TABLE users (
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(120)  NOT NULL,
    email         VARCHAR(190)  NOT NULL UNIQUE,
    password_hash VARCHAR(255)  NOT NULL,       -- pbkdf2_sha256$iter$salt$hash
    role          ENUM('user', 'admin') NOT NULL DEFAULT 'user',
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE = InnoDB;

-- -----------------------------------------------------------------------------
-- LOST_ITEMS — vitrine pública (informações genéricas apenas)
-- -----------------------------------------------------------------------------
CREATE TABLE lost_items (
    id                 INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    public_code        VARCHAR(20)   NOT NULL UNIQUE,   -- ex.: GC-2026-001
    title              VARCHAR(120)  NOT NULL,          -- ex.: "Guarda-chuva"
    category           VARCHAR(80)   NOT NULL,
    icon               VARCHAR(8)    NOT NULL DEFAULT '📦',
    found_date         DATE          NOT NULL,
    found_location     VARCHAR(120),
    internal_notes     TEXT,                            -- SIGILOSO (somente admin)
    status             ENUM('available', 'reserved', 'claimed', 'archived')
                       NOT NULL DEFAULT 'available',
    claimed_by_user_id INT UNSIGNED REFERENCES users (id),
    claimed_at         DATETIME,
    pickup_code        VARCHAR(20) UNIQUE,               -- ex.: REC-9842-XYZ
    created_by         INT UNSIGNED REFERENCES users (id),
    created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_items_claimer FOREIGN KEY (claimed_by_user_id)
        REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT fk_items_creator FOREIGN KEY (created_by)
        REFERENCES users (id) ON DELETE SET NULL,

    INDEX idx_items_status (status),
    INDEX idx_items_category (category),
    INDEX idx_items_location (found_location),
    FULLTEXT INDEX ftx_items_title (title)
) ENGINE = InnoDB;

-- -----------------------------------------------------------------------------
-- ITEM_ATTRIBUTES — o "gabarito" sigiloso de cada item
-- -----------------------------------------------------------------------------
CREATE TABLE item_attributes (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    item_id         INT UNSIGNED NOT NULL,
    question        VARCHAR(250) NOT NULL,
    field_type      ENUM('text', 'textarea', 'choice', 'number')
                    NOT NULL DEFAULT 'text',
    options         JSON,                        -- lista de opções (field_type=choice)
    placeholder     VARCHAR(200),
    expected_answer VARCHAR(250) NOT NULL,        -- SIGILOSO
    alternatives    JSON,                         -- lista de sinônimos aceitos
    weight          TINYINT UNSIGNED NOT NULL DEFAULT 1,
    is_critical     TINYINT(1) NOT NULL DEFAULT 0,
    tolerance       DECIMAL(4, 3) NOT NULL DEFAULT 0.100,
    sort_order      SMALLINT UNSIGNED NOT NULL DEFAULT 0,

    CONSTRAINT fk_attributes_item FOREIGN KEY (item_id)
        REFERENCES lost_items (id) ON DELETE CASCADE,
    INDEX idx_attributes_item (item_id)
) ENGINE = InnoDB;

-- -----------------------------------------------------------------------------
-- CLAIM_REQUESTS — auditoria de toda tentativa de reivindicação
-- -----------------------------------------------------------------------------
CREATE TABLE claim_requests (
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    item_id       INT UNSIGNED NOT NULL,
    user_id       INT UNSIGNED NOT NULL,
    answers       JSON NOT NULL,                 -- {attribute_id: resposta}
    breakdown     JSON NOT NULL,                 -- score por atributo
    score         DECIMAL(5, 4) NOT NULL,        -- 0.0000 .. 1.0000
    status        ENUM('approved', 'rejected', 'pending_review') NOT NULL,
    pickup_code   VARCHAR(20),
    reviewed_by   INT UNSIGNED REFERENCES users (id),
    reviewed_at   DATETIME,
    client_ip     VARCHAR(45),
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_claims_item FOREIGN KEY (item_id)
        REFERENCES lost_items (id) ON DELETE CASCADE,
    CONSTRAINT fk_claims_user FOREIGN KEY (user_id)
        REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_claims_reviewer FOREIGN KEY (reviewed_by)
        REFERENCES users (id) ON DELETE SET NULL,

    INDEX idx_claims_item (item_id),
    INDEX idx_claims_user (user_id),
    INDEX idx_claims_status (status)
) ENGINE = InnoDB;
