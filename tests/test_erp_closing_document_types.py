from recon_erp_1c.infrastructure.erp_mariadb import queries
from recon_erp_1c.application.serializers import document_to_dict
from recon_erp_1c.infrastructure.erp_mariadb.repository import _row_to_document


def test_foreign_supplier_documents_are_classified_as_purchases() -> None:
    sql = queries.OPERATION_CLOSING_DOCS_BY_OPERATION_IDS

    assert sql.count("IN (7, 23, 24, 25) THEN 'purchase'") == 2


def test_global_closing_document_lookup_uses_same_purchase_types() -> None:
    sql = queries.GLOBAL_CLOSING_DOCUMENT_EXISTS

    assert "document.f_type IN (7, 23, 24, 25)" in sql
    assert "document.f_type, 0) NOT IN (7, 23, 24, 25)" in sql


def test_supplier_operation_exposes_parent_customer_operation_link() -> None:
    document = _row_to_document(
        {
            "document_kind": "purchase",
            "code1c": "0ЛБП-003165",
            "document_number": "б/н",
            "document_date": "2026-06-06",
            "amount_total": "2026.31",
            "currency": "USD",
            "contract_code1c": "БП-053039",
            "source_id": 234469,
            "operation_id": 493958,
            "parent_operation_id": 487320,
        }
    )

    payload = document_to_dict(document)

    assert payload is not None
    assert payload["operation_url"].endswith("obid=493958#")
    assert payload["parent_operation_url"].endswith("obid=487320#")
