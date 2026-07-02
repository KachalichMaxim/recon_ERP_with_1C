-- Schema for standalone 1C reconciliation module analytics.
-- Apply in the ERP MariaDB database used by reconciliation_api_server.py.

CREATE TABLE IF NOT EXISTS veda_reconciliation_runs (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    scope VARCHAR(32) NOT NULL DEFAULT 'specification',
    scope_id BIGINT NOT NULL DEFAULT 0,
    spec_id BIGINT NOT NULL DEFAULT 0,
    client_id BIGINT NOT NULL DEFAULT 0,
    source_mode VARCHAR(32) NOT NULL DEFAULT 'server-run',
    triggered_by_user VARCHAR(255) NULL,
    triggered_by_name VARCHAR(255) NULL,
    erp_token_hash CHAR(64) NULL,
    onec_docs_count INT NOT NULL DEFAULT 0,
    erp_docs_count INT NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'COMPLETED',
    summary_json LONGTEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_vrr_scope (scope, scope_id),
    KEY idx_vrr_client_id (client_id),
    KEY idx_vrr_spec_id (spec_id),
    KEY idx_vrr_triggered_by_user (triggered_by_user),
    KEY idx_vrr_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS veda_reconciliation_items (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    run_id BIGINT UNSIGNED NOT NULL,
    oper_id BIGINT NOT NULL DEFAULT 0,
    erp_doc_id BIGINT NOT NULL DEFAULT 0,

    erp_code1c VARCHAR(255) NULL,
    erp_number VARCHAR(255) NULL,
    erp_date_iso VARCHAR(10) NULL,
    erp_sum DECIMAL(18,2) NULL,
    erp_type VARCHAR(64) NULL,

    onec_code1c VARCHAR(255) NULL,
    onec_number VARCHAR(255) NULL,
    onec_date_iso VARCHAR(10) NULL,
    onec_sum DECIMAL(18,2) NULL,
    onec_type VARCHAR(64) NULL,

    status VARCHAR(32) NOT NULL,
    primary_reason VARCHAR(64) NULL,
    severity VARCHAR(32) NULL,
    match_confidence VARCHAR(32) NULL,
    mismatch_fields_json LONGTEXT NULL,
    details_json LONGTEXT NULL,
    note VARCHAR(512) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_vri_run_id (run_id),
    KEY idx_vri_status (status),
    KEY idx_vri_oper_id (oper_id),
    KEY idx_vri_erp_code1c (erp_code1c),
    CONSTRAINT fk_vri_run_id FOREIGN KEY (run_id) REFERENCES veda_reconciliation_runs(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS veda_reconciliation_comments (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    comment_key VARCHAR(512) NOT NULL,
    run_external_id VARCHAR(128) NOT NULL DEFAULT '',
    spec_id BIGINT NOT NULL DEFAULT 0,
    status VARCHAR(64) NULL,
    reason_code VARCHAR(64) NULL,
    comment_text TEXT NULL,
    user_login VARCHAR(255) NULL,
    user_name VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_vrc_scope_key (run_external_id, spec_id, comment_key),
    KEY idx_vrc_spec_id (spec_id),
    KEY idx_vrc_status (status),
    KEY idx_vrc_reason_code (reason_code),
    KEY idx_vrc_user_login (user_login)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
