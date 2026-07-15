from recon_erp_1c.bootstrap.config import AppConfig


def test_storage_database_uses_independent_environment(monkeypatch):
    monkeypatch.setenv("RECON_ERP_DB_HOST", "erp-db")
    monkeypatch.setenv("RECON_ERP_DB_NAME", "erp")
    monkeypatch.setenv("RECON_ERP_DB_USER", "erp-reader")
    monkeypatch.setenv("RECON_ERP_DB_PASSWORD", "erp-secret")
    monkeypatch.setenv("RECON_STORAGE_DB_HOST", "audit-db")
    monkeypatch.setenv("RECON_STORAGE_DB_NAME", "reconciliation")
    monkeypatch.setenv("RECON_STORAGE_DB_USER", "audit-writer")
    monkeypatch.setenv("RECON_STORAGE_DB_PASSWORD", "audit-secret")

    config = AppConfig.from_env()

    assert config.erp_db.host == "erp-db"
    assert config.storage_db.host == "audit-db"
    assert config.storage_db.database == "reconciliation"
    assert config.storage_db.configured


def test_storage_database_reports_storage_variable_names(monkeypatch):
    for name in (
        "RECON_STORAGE_DB_HOST",
        "RECON_STORAGE_DB_NAME",
        "RECON_STORAGE_DB_USER",
        "RECON_STORAGE_DB_PASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)

    config = AppConfig.from_env()

    assert config.storage_db.missing_fields() == [
        "RECON_STORAGE_DB_HOST",
        "RECON_STORAGE_DB_NAME",
        "RECON_STORAGE_DB_USER",
        "RECON_STORAGE_DB_PASSWORD",
    ]
