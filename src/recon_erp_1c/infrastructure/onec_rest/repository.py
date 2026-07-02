from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from recon_erp_1c.domain.entities import AccountingDocument, Contract, Delivery
from recon_erp_1c.domain.value_objects import DateRange, DocumentKind, Money, SourceSystem
from recon_erp_1c.infrastructure.onec_rest.client import OneCRestClient


class OneCRestReadRepository:
    def __init__(self, client: OneCRestClient) -> None:
        self.client = client

    def fetch_snapshot(
        self,
        *,
        delivery: Delivery,
        period: DateRange,
        contracts: list[Contract],
        erp_documents: list[AccountingDocument],
    ) -> list[AccountingDocument]:
        response = self.client.get_reconciliation_snapshot(
            _snapshot_request(
                delivery=delivery,
                period=period,
                contracts=contracts,
                erp_documents=erp_documents,
            )
        )
        snapshot = response.get("snapshot") if isinstance(response.get("snapshot"), dict) else {}
        return _documents_from_snapshot(snapshot)


def _snapshot_request(
    *,
    delivery: Delivery,
    period: DateRange,
    contracts: list[Contract],
    erp_documents: list[AccountingDocument],
) -> dict[str, Any]:
    return {
        "request_id": f"spec-{delivery.erp_spec_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "mode": "delivery_reconciliation",
        "contract_version": "reconciliation.v1",
        "period": {
            "date_from": period.date_from.isoformat(),
            "date_to": period.date_to.isoformat(),
        },
        "delivery": {
            "spec_number": delivery.spec_number,
            "base_contract": delivery.base_contract_number,
            "buyer_contract_code1c": delivery.contract_codes.buyer_contract_code,
            "committent_contract_code1c": delivery.contract_codes.committent_contract_code,
        },
        "organizations": [
            {
                "code1c": delivery.organization.code1c,
                "inn": delivery.organization.inn,
                "name": delivery.organization.name,
            }
        ],
        "counterparties": [
            {
                "code1c": delivery.counterparty.code1c,
                "inn": delivery.counterparty.inn,
                "name": delivery.counterparty.name,
            }
        ],
        "contracts": [
            {
                "code1c": contract.code1c,
                "number": contract.number,
                "role": contract.role.value,
            }
            for contract in contracts
            if contract.code1c
        ],
        "documents": [
            {
                "code1c": document.code1c,
                "number": document.number,
                "kind": document.kind.value,
            }
            for document in erp_documents
            if document.code1c or document.number
        ],
        "include": {
            "contracts": True,
            "customer_invoices": True,
            "payments": True,
            "sales": True,
            "purchases": True,
            "account_movements": True,
        },
    }


def _documents_from_snapshot(snapshot: dict[str, Any]) -> list[AccountingDocument]:
    documents: list[AccountingDocument] = []
    for block_name in ("customer_invoices", "payments", "sales", "purchases", "account_movements"):
        rows = snapshot.get(block_name)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict):
                documents.append(_document_from_1c_row(row, block_name))
    return documents


def _document_from_1c_row(row: dict[str, Any], block_name: str) -> AccountingDocument:
    return AccountingDocument(
        source=SourceSystem.ONE_C,
        kind=_kind(row, block_name),
        code1c=_first_text(row, "code1c", "code", "source_ref", "number"),
        number=_first_text(row, "number", "source_ref"),
        date=_as_date(row.get("date")),
        amount=Money.of(row.get("amount_total") or row.get("amount") or Decimal("0"), _currency(_first_text(row, "currency"))),
        contract_code1c=_first_text(row, "contract_code", "contract_code1c"),
        posted=bool(row.get("posted", True)),
        deleted=bool(row.get("deleted", False)),
        source_id=_first_text(row, "source_id"),
        operation_id=None,
        vat_rate=_first_text(row, "vat_rate", "vat"),
    )


def _kind(row: dict[str, Any], block_name: str) -> DocumentKind:
    document_type = _first_text(row, "document_type")
    if block_name == "customer_invoices" or document_type == "customer_invoice":
        return DocumentKind.CUSTOMER_INVOICE
    if block_name == "payments" or document_type in {"incoming_payment", "outgoing_payment", "payment"}:
        return DocumentKind.PAYMENT
    if block_name == "sales" or document_type.startswith("sale_"):
        return DocumentKind.SALE
    if block_name == "purchases" or document_type.startswith("purchase_"):
        return DocumentKind.PURCHASE
    if block_name == "account_movements":
        return DocumentKind.ACCOUNT_MOVEMENT
    return DocumentKind.CLOSING_DOCUMENT


def _first_text(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _currency(value: object) -> str:
    text = str(value or "").strip().upper().replace(" ", "")
    if text in {"", "643", "РУБ", "РУБ.", "RUR", "RUB"}:
        return "RUB"
    if text in {"840", "USD", "$", "ДОЛЛ.", "ДОЛЛАР"}:
        return "USD"
    if text in {"978", "EUR", "€", "ЕВРО"}:
        return "EUR"
    if text in {"156", "CNY", "ЮАНЬ", "ЮАНИ"}:
        return "CNY"
    return text


def _as_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d.%m.%Y"):
        try:
            return datetime.strptime(text[:19], fmt).date()
        except ValueError:
            continue
    return None
