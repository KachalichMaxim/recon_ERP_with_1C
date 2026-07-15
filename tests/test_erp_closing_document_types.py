from recon_erp_1c.infrastructure.erp_mariadb import queries


def test_foreign_supplier_documents_are_classified_as_purchases() -> None:
    sql = queries.OPERATION_CLOSING_DOCS_BY_OPERATION_IDS

    assert sql.count("IN (7, 23, 24, 25) THEN 'purchase'") == 2


def test_global_closing_document_lookup_uses_same_purchase_types() -> None:
    sql = queries.GLOBAL_CLOSING_DOCUMENT_EXISTS

    assert "document.f_type IN (7, 23, 24, 25)" in sql
    assert "document.f_type, 0) NOT IN (7, 23, 24, 25)" in sql
