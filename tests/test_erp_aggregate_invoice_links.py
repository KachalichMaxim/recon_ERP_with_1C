from __future__ import annotations

from datetime import date
from decimal import Decimal

from recon_erp_1c.application.serializers import document_to_dict
from recon_erp_1c.infrastructure.erp_mariadb.repository import _row_to_document


def test_aggregate_invoice_serializes_every_child_invoice_and_operation_link() -> None:
    document = _row_to_document(
        {
            "document_kind": "customer_invoice",
            "code1c": "ВА-012197",
            "document_number": "ВА-012197",
            "document_date": date(2024, 10, 10),
            "amount_total": Decimal("276020.00"),
            "currency": "RUB",
            "contract_code1c": "БП-078980",
            "source_id": 169959,
            "operation_id": 0,
            "related_source_ids": "169957||169958",
            "related_document_numbers": "ВА-021228/0||ВА-021229/1",
            "related_operation_ids": "256960||256961",
            "vat_rate": "",
            "reimbursement_type": "",
            "deleted": 0,
            "paid_amount": None,
        }
    )

    payload = document_to_dict(document)

    assert payload is not None
    assert payload["erp_url"].endswith("pgid=17&obid=169959#")
    assert payload["related_erp_links"] == [
        {
            "label": "ВА-021228/0",
            "url": "http://erp.vedagent/veda/?pgid=17&obid=169957#",
            "operation_id": 256960,
            "operation_url": "http://erp.vedagent/veda/?pgid=35&invtb=145&obid=256960#",
        },
        {
            "label": "ВА-021229/1",
            "url": "http://erp.vedagent/veda/?pgid=17&obid=169958#",
            "operation_id": 256961,
            "operation_url": "http://erp.vedagent/veda/?pgid=35&invtb=145&obid=256961#",
        },
    ]
