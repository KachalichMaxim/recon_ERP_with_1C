-- Add observable MVP scope and rule provenance to existing audit storage.

ALTER TABLE veda_reconciliation_runs
    ADD COLUMN execution_status VARCHAR(32) NOT NULL DEFAULT 'completed' AFTER status,
    ADD COLUMN coverage_status VARCHAR(64) NOT NULL DEFAULT 'unknown' AFTER execution_status,
    ADD COLUMN result_status VARCHAR(64) NOT NULL DEFAULT 'issues_found' AFTER coverage_status,
    ADD COLUMN ruleset_id VARCHAR(128) NULL AFTER result_status,
    ADD COLUMN ruleset_version VARCHAR(32) NULL AFTER ruleset_id,
    ADD COLUMN application_version VARCHAR(32) NULL AFTER ruleset_version,
    ADD COLUMN git_sha VARCHAR(40) NULL AFTER application_version,
    ADD COLUMN coverage_json LONGTEXT NULL AFTER git_sha,
    ADD KEY idx_vrr_result_status (result_status),
    ADD KEY idx_vrr_ruleset (ruleset_id, ruleset_version);
