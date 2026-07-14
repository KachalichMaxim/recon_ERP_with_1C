from __future__ import annotations

from datetime import date

from recon_erp_1c.domain.entities import AccountingDocument, Counterparty, Delivery, Organization
from recon_erp_1c.domain.value_objects import DateRange, DocumentKind, Money, OneCContractCodes, SourceSystem
from recon_erp_1c.infrastructure.onec_rest.repository import OneCRestReadRepository
from recon_erp_1c.infrastructure.onec_rest.client import OneCRestConfig, snapshot_query_params


class _FakeClient:
    def __init__(self, snapshot: dict[str, object]) -> None:
        self.snapshot = snapshot
        self.requests: list[dict[str, object]] = []

    def get_reconciliation_snapshot(self, request: dict[str, object]) -> dict[str, object]:
        self.requests.append(request)
        return {"ok": True, "snapshot": self.snapshot}


def _delivery() -> Delivery:
    return Delivery(
        erp_spec_id=20334,
        spec_number="1051",
        spec_date=date(2025, 7, 1),
        base_contract_number="660/1",
        organization=Organization(1, "ORG", "", "АО ВЭД Агент"),
        counterparty=Counterparty(221, "CLIENT", "7811451960", "АЭРО-ТРЕЙД"),
        contract_codes=OneCContractCodes("БП-068417", "БП-068418"),
    )


def test_repository_keeps_lines_allocations_and_balances() -> None:
    snapshot = {
        "customer_invoices": [],
        "sales": [],
        "purchases": [
            {
                "source_id": "purchase-guid",
                "number": "00БП-012300",
                "document_type": "purchase",
                "date": "2025-07-22",
                "amount_total": 17715,
                "currency": "RUB",
                "contract_code": "БП-013397",
            }
        ],
        "payments": [
            {
                "source_id": "payment-guid",
                "number": "00БП-010591",
                "document_type": "incoming_payment",
                "date": "2025-08-05",
                "amount_total": 9660.68,
                "currency": "RUB",
                "contract_code": "БП-068412",
                "allocations": [
                    {
                        "amount": 3765.79,
                        "currency": "RUB",
                        "contract_code": "БП-068418",
                        "invoice_number": "ВА-007517",
                    }
                ],
            }
        ],
        "document_lines": [
            {
                "document_id": "purchase-guid",
                "document_number": "00БП-012300",
                "line_id": "3",
                "amount": 6462.89,
                "currency": "RUB",
                "contract_code": "БП-013397",
                "vat_rate": "0%",
            }
        ],
        "balances": [
            {
                "contract_code": "БП-068417",
                "opening_debit": 0,
                "opening_credit": 0,
                "turnover_debit": 100,
                "turnover_credit": 50,
                "closing_debit": 50,
                "closing_credit": 0,
                "currency": "RUB",
            }
        ],
        "warnings": [{"code": "partial", "message": "Часть аналитики недоступна"}],
    }
    client = _FakeClient(snapshot)
    repository = OneCRestReadRepository(client)  # type: ignore[arg-type]

    result = repository.fetch_snapshot(
        delivery=_delivery(),
        period=DateRange(date(2025, 7, 1), date(2025, 8, 31)),
        contracts=[],
        erp_documents=[],
    )

    purchase = next(document for document in result.documents if document.kind.value == "purchase")
    payment = next(document for document in result.documents if document.kind.value == "payment")
    assert purchase.lines[0].line_id == "3"
    assert purchase.lines[0].amount.amount.__str__() == "6462.89"
    assert payment.allocations[0].invoice_number == "ВА-007517"
    assert result.balances[0].signed_closing_balance.amount.__str__() == "-50.00"
    assert result.warnings == ("Часть аналитики недоступна",)
    assert len(client.requests) == 1


def test_onec_url_does_not_duplicate_contract_root() -> None:
    config = OneCRestConfig(base_url="http://1c.local/vedagent_dev/hs/reconciliation/v1", token="token")

    assert config.url("/reconciliation/v1/snapshot") == (
        "http://1c.local/vedagent_dev/hs/reconciliation/v1/snapshot"
    )


def test_delivery_mode_and_business_context_are_sent_in_get_query() -> None:
    params = snapshot_query_params(
        {
            "request_id": "spec-20334",
            "mode": "delivery_reconciliation",
            "period": {"date_from": "2025-07-01", "date_to": "2025-08-31"},
            "delivery": {
                "spec_number": "1051",
                "base_contract": "660/1",
                "buyer_contract_code1c": "БП-068417",
                "committent_contract_code1c": "БП-068418",
            },
            "counterparties": [{"code1c": "000000699", "inn": "7811451960"}],
        },
        include_delivery_context=True,
    )

    assert params["scope"] == "delivery"
    assert params["buyer_contract_code"] == "БП-068417"
    assert params["committent_contract_code"] == "БП-068418"
    assert "counterparty_code" not in params
    assert "counterparty_inn" not in params


def test_delivery_context_is_not_sent_before_onec_support_is_enabled() -> None:
    params = snapshot_query_params(
        {
            "mode": "delivery_reconciliation",
            "period": {"date_from": "2025-07-01", "date_to": "2025-08-31"},
            "delivery": {
                "spec_number": "1051",
                "base_contract": "660/1",
                "buyer_contract_code1c": "БП-068417",
            },
            "counterparties": [{"code1c": "000000699", "inn": "7811451960"}],
        }
    )

    assert params["buyer_contract_code"] == "БП-068417"
    assert "scope" not in params
    assert params["counterparty_code"] == "000000699"
    assert params["counterparty_inn"] == "7811451960"


def test_repository_does_not_repeat_lookup_for_document_already_in_delivery_snapshot() -> None:
    client = _FakeClient(
        {
            "purchases": [
                {
                    "source_id": "purchase-guid",
                    "number": "00БП-012300",
                    "document_type": "purchase",
                    "date": "2025-07-22",
                    "amount_total": 17715,
                    "currency": "RUB",
                    "contract_code": "БП-003834",
                }
            ],
            "document_lines": [],
        }
    )
    repository = OneCRestReadRepository(client)  # type: ignore[arg-type]
    erp_document = AccountingDocument(
        source=SourceSystem.ERP,
        kind=DocumentKind.PURCHASE,
        code1c="00БП-012300",
        number="00БП-012300",
        date=date(2025, 7, 22),
        amount=Money.of("17715.00"),
        contract_code1c="БП-003834",
    )

    repository.fetch_snapshot(
        delivery=_delivery(),
        period=DateRange(date(2025, 7, 1), date(2025, 8, 31)),
        contracts=[],
        erp_documents=[erp_document],
    )

    assert len(client.requests) == 1
