-- Upgrade an existing reconciliation log schema before switching the service
-- to RECON_STORAGE_DB_*.

ALTER TABLE veda_reconciliation_runs
    ADD COLUMN run_external_id CHAR(36) NULL AFTER id,
    ADD COLUMN period_from DATE NULL AFTER erp_token_hash,
    ADD COLUMN period_to DATE NULL AFTER period_from,
    ADD COLUMN base_contract_number VARCHAR(255) NULL AFTER period_to,
    ADD COLUMN spec_number VARCHAR(255) NULL AFTER base_contract_number,
    ADD COLUMN buyer_contract_code VARCHAR(64) NULL AFTER spec_number,
    ADD COLUMN committent_contract_code VARCHAR(64) NULL AFTER buyer_contract_code,
    ADD COLUMN matched_count INT NOT NULL DEFAULT 0 AFTER erp_docs_count,
    ADD COLUMN unresolved_count INT NOT NULL DEFAULT 0 AFTER matched_count,
    ADD COLUMN balance_status VARCHAR(32) NULL AFTER status,
    ADD COLUMN erp_balance DECIMAL(18,2) NULL AFTER balance_status,
    ADD COLUMN onec_balance DECIMAL(18,2) NULL AFTER erp_balance,
    ADD COLUMN balance_difference DECIMAL(18,2) NULL AFTER onec_balance,
    ADD COLUMN balance_comparable TINYINT(1) NOT NULL DEFAULT 1 AFTER balance_difference,
    ADD COLUMN run_json LONGTEXT NULL AFTER summary_json,
    ADD COLUMN completed_at DATETIME NULL AFTER created_at;

UPDATE veda_reconciliation_runs
SET run_external_id = UUID()
WHERE run_external_id IS NULL OR run_external_id = '';

ALTER TABLE veda_reconciliation_runs
    MODIFY COLUMN run_external_id CHAR(36) NOT NULL,
    ADD UNIQUE KEY uk_vrr_run_external_id (run_external_id);

ALTER TABLE veda_reconciliation_items
    ADD COLUMN issue_key CHAR(64) NULL AFTER erp_doc_id,
    ADD COLUMN erp_source_id VARCHAR(255) NULL AFTER issue_key,
    ADD COLUMN onec_source_id VARCHAR(255) NULL AFTER erp_source_id,
    ADD KEY idx_vri_issue_key (issue_key),
    ADD KEY idx_vri_primary_reason (primary_reason);
