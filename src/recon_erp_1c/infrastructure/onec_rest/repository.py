from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from decimal import Decimal
import os
from typing import Any

from recon_erp_1c.domain.entities import (
    AccountingBalance,
    AccountingDocument,
    Contract,
    Delivery,
    DocumentLine,
    OneCSnapshot,
    PaymentAllocation,
)
from recon_erp_1c.domain.value_objects import DateRange, DocumentKind, Money, SourceSystem
from recon_erp_1c.infrastructure.onec_rest.client import OneCRestClient


class OneCRestReadRepository:
    def __init__(self, client: OneCRestClient) -> None:
        self.client = client
        self.lookup_workers = max(1, min(8, int(os.environ.get("RECON_ONEC_LOOKUP_WORKERS", "6") or "6")))
        self.last_metrics: dict[str, int | float] = {}

    def fetch_snapshot(
        self,
        *,
        delivery: Delivery,
        period: DateRange,
        contracts: list[Contract],
        erp_documents: list[AccountingDocument],
    ) -> OneCSnapshot:
        reset_metrics = getattr(self.client, "reset_metrics", None)
        if callable(reset_metrics):
            reset_metrics()
        snapshot = _empty_snapshot()
        base_request = _snapshot_request(
            delivery=delivery,
            period=period,
            contracts=contracts,
            erp_documents=erp_documents,
        )
        response = self.client.get_reconciliation_snapshot(base_request)
        base_snapshot = response.get("snapshot") if isinstance(response.get("snapshot"), dict) else {}
        _merge_full_snapshot(snapshot, base_snapshot)
        _merge_known_document_lookups(
            self.client,
            snapshot,
            delivery=delivery,
            period=period,
            erp_documents=erp_documents,
            lookup_workers=self.lookup_workers,
        )
        warnings = tuple(
            dict.fromkeys(_warning_text(item) for item in snapshot.get("warnings", []) if _warning_text(item))
        )
        result = OneCSnapshot(
            documents=tuple(_documents_from_snapshot(snapshot)),
            balances=tuple(_balances_from_snapshot(snapshot)),
            warnings=warnings,
        )
        metrics_snapshot = getattr(self.client, "metrics_snapshot", None)
        self.last_metrics = metrics_snapshot() if callable(metrics_snapshot) else {}
        return result


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
            "customer_invoices": True,
            "payments": True,
            "sales": True,
            "purchases": True,
            "document_lines": True,
            "balances": True,
        },
    }


def _empty_snapshot() -> dict[str, Any]:
    return {
        "metadata": {},
        "customer_invoices": [],
        "payments": [],
        "sales": [],
        "purchases": [],
        "document_lines": [],
        "balances": [],
        "warnings": [],
    }


def _merge_snapshot_block(target: dict[str, Any], source: dict[str, Any], block_name: str) -> None:
    metadata = source.get("metadata")
    if isinstance(metadata, dict):
        target["metadata"] = metadata
    rows = source.get(block_name)
    if isinstance(rows, list):
        for row in rows:
            _append_unique_row(target[block_name], row)
    warnings = source.get("warnings")
    if isinstance(warnings, list):
        target["warnings"].extend(warnings)


def _merge_full_snapshot(target: dict[str, Any], source: dict[str, Any]) -> None:
    for block_name in ("customer_invoices", "payments", "sales", "purchases", "document_lines", "balances"):
        _merge_snapshot_block(target, source, block_name)


def _merge_known_document_lookups(
    client: OneCRestClient,
    snapshot: dict[str, Any],
    *,
    delivery: Delivery,
    period: DateRange,
    erp_documents: list[AccountingDocument],
    lookup_workers: int,
) -> None:
    lookups: list[tuple[str, str, AccountingDocument, dict[str, Any]]] = []
    seen: set[tuple[str, str, str]] = set()
    existing_codes = {
        block_name: {
            str(row.get("code1c") or row.get("number") or "").strip()
            for row in snapshot.get(block_name, [])
            if isinstance(row, dict)
        }
        for block_name in ("customer_invoices", "payments", "sales", "purchases")
    }
    for document in erp_documents:
        code = document.code1c.strip()
        if not code:
            continue
        block_name = _block_for_kind(document.kind.value)
        if not block_name:
            continue
        if code in existing_codes.get(block_name, set()):
            continue
        key = (block_name, code, document.date.isoformat() if document.date else "")
        if key in seen:
            continue
        seen.add(key)
        lookups.append(
            (
                block_name,
                code,
                document,
                {
                    "request_id": f"doc-{delivery.erp_spec_id}-{code}",
                    "period": {
                        "date_from": period.date_from.isoformat(),
                        "date_to": period.date_to.isoformat(),
                    },
                    "documents": [
                        {
                            "code1c": code,
                            "kind": document.kind.value,
                        }
                    ],
                    "include": {block_name: True, "document_lines": block_name in {"sales", "purchases"}},
                },
            )
        )

    if not lookups:
        return
    workers = min(lookup_workers, len(lookups))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(client.get_reconciliation_snapshot, request): (block_name, code, document)
            for block_name, code, document, request in lookups
        }
        completed: list[tuple[str, str, AccountingDocument, dict[str, Any]]] = []
        for future in as_completed(futures):
            block_name, code, document = futures[future]
            completed.append((block_name, code, document, future.result()))
    for block_name, _code, document, response in sorted(completed, key=lambda item: (item[0], item[1])):
        block_snapshot = response.get("snapshot") if isinstance(response.get("snapshot"), dict) else {}
        block_snapshot = _filter_document_lookup_snapshot(block_snapshot, block_name, document)
        _merge_snapshot_block(snapshot, block_snapshot, block_name)
        if block_name in {"sales", "purchases"}:
            _merge_snapshot_block(snapshot, block_snapshot, "document_lines")


def _filter_document_lookup_snapshot(
    snapshot: dict[str, Any],
    block_name: str,
    expected: AccountingDocument,
) -> dict[str, Any]:
    """Remove documents that only reuse the same 1C code in another period."""
    rows = [
        row
        for row in _dict_list(snapshot.get(block_name))
        if _first_text(row, "code1c", "code", "number", "source_ref") == expected.code1c
    ]
    exact_date = [row for row in rows if expected.date and _as_date(row.get("date")) == expected.date]
    if exact_date:
        selected = exact_date
    else:
        selected = [
            row
            for row in rows
            if Money.of(
                row.get("amount_total") or row.get("amount") or Decimal("0"),
                _currency(_first_text(row, "currency")),
            )
            == expected.amount
        ]

    selected_ids = {_first_text(row, "source_id") for row in selected if _first_text(row, "source_id")}
    selected_numbers = {
        _first_text(row, "number", "source_ref")
        for row in selected
        if _first_text(row, "number", "source_ref")
    }
    filtered = dict(snapshot)
    filtered[block_name] = selected
    if block_name in {"sales", "purchases"}:
        if selected_ids:
            filtered["document_lines"] = [
                row
                for row in _dict_list(snapshot.get("document_lines"))
                if _first_text(row, "document_id") in selected_ids
            ]
        else:
            filtered["document_lines"] = [
                row
                for row in _dict_list(snapshot.get("document_lines"))
                if _first_text(row, "document_number") in selected_numbers
            ]
    return filtered


def _block_for_kind(kind: str) -> str:
    if kind == "customer_invoice":
        return "customer_invoices"
    if kind == "payment":
        return "payments"
    if kind == "sale":
        return "sales"
    if kind == "purchase":
        return "purchases"
    return ""


def _append_unique_row(rows: list[Any], row: Any) -> None:
    if not isinstance(row, dict):
        rows.append(row)
        return
    key = _row_identity(row)
    for existing in rows:
        if isinstance(existing, dict) and _row_identity(existing) == key:
            return
    rows.append(row)


def _row_identity(row: dict[str, Any]) -> tuple[str, ...]:
    if row.get("line_id") not in (None, ""):
        return (
            "line",
            _first_text(row, "document_id"),
            _first_text(row, "document_number"),
            _first_text(row, "line_id"),
            _first_text(row, "amount"),
        )
    return (
        _first_text(row, "document_type"),
        _first_text(row, "source_id"),
        _first_text(row, "number", "source_ref"),
        _first_text(row, "date"),
        _first_text(row, "amount_total", "amount"),
        _first_text(row, "contract_code", "contract_code1c"),
    )


def _documents_from_snapshot(snapshot: dict[str, Any]) -> list[AccountingDocument]:
    lines_by_document = _lines_by_document(snapshot.get("document_lines"))
    documents: list[AccountingDocument] = []
    for block_name in ("customer_invoices", "payments", "sales", "purchases", "account_movements"):
        rows = snapshot.get(block_name)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict):
                documents.append(_document_from_1c_row(row, block_name, lines_by_document))
    return documents


def _document_from_1c_row(
    row: dict[str, Any],
    block_name: str,
    lines_by_document: dict[str, tuple[DocumentLine, ...]],
) -> AccountingDocument:
    source_id = _first_text(row, "source_id")
    source_number = _first_text(row, "number", "source_ref")
    incoming_number = _first_text(row, "incoming_number")
    number = source_number
    lines = _lookup_document_lines(lines_by_document, source_id, source_number)
    line_vat_rates = {line.vat_rate for line in lines if line.vat_rate}
    vat_rate = _first_text(row, "vat_rate", "vat")
    if not vat_rate and len(line_vat_rates) == 1:
        vat_rate = next(iter(line_vat_rates))
    return AccountingDocument(
        source=SourceSystem.ONE_C,
        kind=_kind(row, block_name),
        code1c=_first_text(row, "code1c", "code", "number", "source_ref"),
        number=number,
        date=_as_date(row.get("date")),
        amount=Money.of(row.get("amount_total") or row.get("amount") or Decimal("0"), _currency(_first_text(row, "currency"))),
        contract_code1c=_first_text(row, "contract_code", "contract_code1c"),
        incoming_number=incoming_number,
        posted=bool(row.get("posted", True)),
        deleted=bool(row.get("deleted", False)),
        source_id=source_id,
        operation_id=None,
        vat_rate=vat_rate,
        tax_invoice_number=_first_text(row, "tax_invoice_number", "invoice_number"),
        tax_invoice_date=_as_date(row.get("tax_invoice_date") or row.get("invoice_date")),
        linked_contract_codes=tuple(_text_list(row.get("linked_contract_codes"))),
        lines=lines,
        allocations=tuple(_allocation_from_row(item, row) for item in _dict_list(row.get("allocations"))),
    )


def _lines_by_document(value: object) -> dict[str, tuple[DocumentLine, ...]]:
    grouped: dict[str, list[DocumentLine]] = {}
    for row in _dict_list(value):
        line = _line_from_row(row)
        for key in {_first_text(row, "document_id"), _first_text(row, "document_number")}:
            if key:
                grouped.setdefault(key, []).append(line)
    return {key: tuple(rows) for key, rows in grouped.items()}


def _lookup_document_lines(
    lines_by_document: dict[str, tuple[DocumentLine, ...]], source_id: str, number: str
) -> tuple[DocumentLine, ...]:
    rows: list[DocumentLine] = []
    seen: set[tuple[str, str]] = set()
    for key in (source_id, number):
        for line in lines_by_document.get(key, ()):
            identity = (line.document_id, line.line_id)
            if identity not in seen:
                rows.append(line)
                seen.add(identity)
    return tuple(rows)


def _line_from_row(row: dict[str, Any]) -> DocumentLine:
    currency = _currency(_first_text(row, "currency"))
    vat_amount = row.get("vat_amount")
    return DocumentLine(
        document_id=_first_text(row, "document_id", "source_id"),
        line_id=_first_text(row, "line_id", "row_number"),
        amount=Money.of(row.get("amount") or Decimal("0"), currency),
        contract_code1c=_first_text(row, "contract_code", "commissioner_contract_code"),
        linked_contract_code1c=_first_text(row, "linked_contract_code"),
        line_kind=_first_text(row, "line_kind"),
        nomenclature=_first_text(row, "nomenclature"),
        content=_first_text(row, "content"),
        vat_rate=_first_text(row, "vat_rate", "vat"),
        vat_amount=Money.of(vat_amount, currency) if vat_amount not in (None, "") else None,
        settlement_account=_first_text(row, "settlement_account"),
        cost_account=_first_text(row, "cost_account"),
    )


def _allocation_from_row(row: dict[str, Any], parent: dict[str, Any]) -> PaymentAllocation:
    return PaymentAllocation(
        amount=Money.of(row.get("amount") or Decimal("0"), _currency(_first_text(row, "currency") or parent.get("currency"))),
        contract_code1c=_first_text(row, "contract_code", "contract_code1c"),
        linked_contract_code1c=_first_text(row, "linked_contract_code"),
        invoice_id=_first_text(row, "invoice_id"),
        invoice_number=_first_text(row, "invoice_number"),
        document_line_id=_first_text(row, "document_line_id"),
        spec_number=_first_text(row, "spec_number"),
    )


def _balances_from_snapshot(snapshot: dict[str, Any]) -> list[AccountingBalance]:
    balances: list[AccountingBalance] = []
    for row in _dict_list(snapshot.get("balances")):
        currency = _currency(_first_text(row, "currency"))
        balances.append(
            AccountingBalance(
                contract_code1c=_first_text(row, "contract_code", "contract_code1c"),
                contract_id=_first_text(row, "contract_id"),
                opening_debit=Money.of(row.get("opening_debit") or Decimal("0"), currency),
                opening_credit=Money.of(row.get("opening_credit") or Decimal("0"), currency),
                turnover_debit=Money.of(row.get("turnover_debit") or Decimal("0"), currency),
                turnover_credit=Money.of(row.get("turnover_credit") or Decimal("0"), currency),
                closing_debit=Money.of(row.get("closing_debit") or Decimal("0"), currency),
                closing_credit=Money.of(row.get("closing_credit") or Decimal("0"), currency),
            )
        )
    return balances


def _dict_list(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _text_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _warning_text(value: object) -> str:
    if isinstance(value, dict):
        return _first_text(value, "message", "code")
    return str(value or "").strip()


def _kind(row: dict[str, Any], block_name: str) -> DocumentKind:
    document_type = _first_text(row, "document_type")
    if block_name == "customer_invoices" or document_type == "customer_invoice":
        return DocumentKind.CUSTOMER_INVOICE
    if block_name == "payments" or document_type in {"incoming_payment", "outgoing_payment", "payment"}:
        return DocumentKind.PAYMENT
    if block_name == "sales" or document_type == "sale" or document_type.startswith("sale_"):
        return DocumentKind.SALE
    if block_name == "purchases" or document_type == "purchase" or document_type.startswith("purchase_"):
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
