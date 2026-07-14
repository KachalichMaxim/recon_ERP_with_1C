from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from recon_erp_1c.domain.entities import AccountingDocument, Contract, Counterparty, Delivery, Organization
from recon_erp_1c.domain.value_objects import ContractRole, DocumentKind, Money, OneCContractCodes, SourceSystem
from recon_erp_1c.infrastructure.erp_mariadb.connection import MariaDbConnectionFactory
from recon_erp_1c.infrastructure.erp_mariadb import queries


class ErpDataNotFound(RuntimeError):
    pass


class MariaDbErpReadRepository:
    def __init__(self, connection_factory: MariaDbConnectionFactory) -> None:
        self.connection_factory = connection_factory

    def list_deliveries(
        self,
        *,
        client_id: int | None = None,
        dog_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, object]]:
        limit = max(1, min(int(limit or 50), 2000))
        offset = max(0, int(offset or 0))
        rows = self._fetch_all(
            queries.LIST_DELIVERIES,
            {
                "client_id": client_id,
                "dog_id": dog_id,
                "date_from": date_from,
                "date_to": date_to,
                "limit": limit,
                "offset": offset,
            },
        )
        return [
            {
                "spec_id": row.get("spec_id"),
                "spec_number": row.get("spec_number"),
                "spec_type_name": row.get("spec_type_name") or "",
                "spec_date": _date_to_iso(row.get("spec_date")),
                "closure_date": _date_to_iso(row.get("closure_date")),
                "spec_status": int(row.get("spec_status") or 0),
                "buyer_contract_code": row.get("buyer_contract_code") or "",
                "committent_contract_code": row.get("committent_contract_code") or "",
                "dog_id": row.get("dog_id"),
                "base_contract_number": row.get("base_contract_number") or "",
                "client_id": row.get("client_id"),
                "client_name": row.get("client_name") or "",
                "client_inn": row.get("client_inn") or "",
            }
            for row in rows
        ]

    def count_deliveries(
        self,
        *,
        client_id: int | None = None,
        dog_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> int:
        row = self._fetch_one(
            queries.COUNT_DELIVERIES,
            {
                "client_id": client_id,
                "dog_id": dog_id,
                "date_from": date_from,
                "date_to": date_to,
            },
        )
        return int(row.get("total_count") or 0) if row else 0

    def matrix_total_summary(
        self,
        *,
        client_id: int | None = None,
        dog_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict[str, object]:
        row = self._fetch_one(
            queries.MATRIX_TOTAL_SUMMARY,
            {
                "client_id": client_id,
                "dog_id": dog_id,
                "date_from": date_from,
                "date_to": date_to,
            },
        )
        if row is None:
            return {
                "deliveries": 0,
                "invoice_sum": "0.00",
                "payment_sum": "0.00",
                "reimbursable_sum": "0.00",
                "non_reimbursable_sum": "0.00",
                "balance": "0.00",
                "debts": 0,
                "overpayments": 0,
            }
        return {
            "deliveries": int(row.get("deliveries") or 0),
            "invoice_sum": _decimal_text(row.get("invoice_sum")),
            "payment_sum": _decimal_text(row.get("payment_sum")),
            "reimbursable_sum": _decimal_text(row.get("reimbursable_sum")),
            "non_reimbursable_sum": _decimal_text(row.get("non_reimbursable_sum")),
            "balance": _decimal_text(row.get("balance")),
            "debts": int(row.get("debts") or 0),
            "overpayments": int(row.get("overpayments") or 0),
        }

    def search_clients(self, query: str, *, limit: int = 12) -> list[dict[str, object]]:
        text = query.strip()
        if len(text) < 3:
            return []
        rows = self._fetch_all(
            queries.SEARCH_CLIENTS,
            {
                "query": text,
                "query_like": f"%{text}%",
                "limit": max(1, min(int(limit or 12), 30)),
            },
        )
        return [
            {
                "client_id": row.get("client_id"),
                "client_name": row.get("client_name") or "",
                "client_inn": row.get("client_inn") or "",
            }
            for row in rows
        ]

    def search_contracts(self, query: str, *, client_id: int | None = None, limit: int = 12) -> list[dict[str, object]]:
        text = query.strip()
        if len(text) < 2:
            return []
        rows = self._fetch_all(
            queries.SEARCH_CONTRACTS,
            {
                "query": text,
                "query_like": f"%{text}%",
                "client_id": client_id,
                "limit": max(1, min(int(limit or 12), 30)),
            },
        )
        return [
            {
                "dog_id": row.get("dog_id"),
                "contract_number": row.get("contract_number") or "",
                "contract_code1c": row.get("contract_code1c") or "",
                "client_id": row.get("client_id"),
                "client_name": row.get("client_name") or "",
                "client_inn": row.get("client_inn") or "",
            }
            for row in rows
        ]

    def get_delivery(self, spec_id: int) -> Delivery:
        row = self._fetch_one(queries.DELIVERY_BY_SPEC_ID, {"spec_id": spec_id})
        if row is None:
            raise ErpDataNotFound(f"ERP delivery not found: spec_id={spec_id}")

        organization = Organization(
            erp_id=_int_or_none(row.get("org_id")),
            code1c=_str(row.get("org_code1c")),
            inn=_str(row.get("org_inn")),
            name=_str(row.get("org_name")),
        )
        counterparty = Counterparty(
            erp_id=_int_or_none(row.get("client_id")),
            code1c=_str(row.get("client_code1c")),
            inn=_str(row.get("client_inn")),
            name=_str(row.get("client_name")),
        )
        return Delivery(
            erp_spec_id=int(row["f_id"]),
            spec_number=_str(row.get("f_num")),
            spec_date=_as_date(row.get("f_dt")),
            base_contract_number=_str(row.get("f_dogname")),
            organization=organization,
            counterparty=counterparty,
            contract_codes=OneCContractCodes(
                buyer_contract_code=_meaningful_code(row.get("f_kod1cb")),
                committent_contract_code=_meaningful_code(row.get("f_kod1cp")),
            ),
        )

    def list_delivery_contracts(self, spec_id: int) -> list[Contract]:
        delivery = self.get_delivery(spec_id)
        contracts: list[Contract] = []
        if delivery.contract_codes.buyer_contract_code:
            contracts.append(
                Contract(
                    source=SourceSystem.ERP,
                    code1c=delivery.contract_codes.buyer_contract_code,
                    number=f"{delivery.base_contract_number}/{delivery.spec_number}",
                    date=delivery.spec_date,
                    role=ContractRole.BUYER,
                    organization=delivery.organization,
                    counterparty=delivery.counterparty,
                    base_contract_number=delivery.base_contract_number,
                    spec_number=delivery.spec_number,
                )
            )
        if delivery.contract_codes.committent_contract_code:
            contracts.append(
                Contract(
                    source=SourceSystem.ERP,
                    code1c=delivery.contract_codes.committent_contract_code,
                    number=f"{delivery.base_contract_number}/{delivery.spec_number}",
                    date=delivery.spec_date,
                    role=ContractRole.COMMITTENT,
                    organization=delivery.organization,
                    counterparty=delivery.counterparty,
                    base_contract_number=delivery.base_contract_number,
                    spec_number=delivery.spec_number,
                )
            )
        return contracts

    def get_delivery_balance(self, spec_id: int) -> Money:
        row = self._fetch_one(queries.DELIVERY_BALANCE_BY_SPEC_ID, {"spec_id": spec_id}) or {}
        return Money.of(row.get("balance") or Decimal("0"), "RUB")

    def document_exists_globally(self, document: AccountingDocument) -> bool:
        if not document.code1c or document.date is None:
            return False
        params = {
            "code1c": document.code1c,
            "document_date": document.date,
            "amount": document.amount.amount,
            "document_kind": document.kind.value,
        }
        if document.kind == DocumentKind.PAYMENT:
            query = queries.GLOBAL_PAYMENT_DOCUMENT_EXISTS
        elif document.kind == DocumentKind.CUSTOMER_INVOICE:
            query = queries.GLOBAL_CUSTOMER_INVOICE_EXISTS
        elif document.kind in {DocumentKind.SALE, DocumentKind.PURCHASE}:
            query = queries.GLOBAL_CLOSING_DOCUMENT_EXISTS
        else:
            return False
        return self._fetch_one(query, params) is not None

    def list_delivery_documents(self, spec_id: int) -> list[AccountingDocument]:
        return self.list_documents_for_deliveries([spec_id]).get(spec_id, [])

    def get_delivery_documents_and_balance(self, spec_id: int) -> tuple[list[AccountingDocument], Money]:
        documents, calculations = self.list_documents_and_calculations_for_deliveries([spec_id])
        calculation = calculations.get(spec_id, {})
        return documents.get(spec_id, []), Money.of(calculation.get("balance") or "0", "RUB")

    def list_documents_for_deliveries(self, spec_ids: list[int]) -> dict[int, list[AccountingDocument]]:
        documents, _calculations = self.list_documents_and_calculations_for_deliveries(spec_ids)
        return documents

    def list_documents_and_calculations_for_deliveries(
        self, spec_ids: list[int]
    ) -> tuple[dict[int, list[AccountingDocument]], dict[int, dict[str, str]]]:
        ids = sorted({int(spec_id) for spec_id in spec_ids if int(spec_id or 0) > 0})
        if not ids:
            return {}, {}
        params = {f"spec_id_{index}": spec_id for index, spec_id in enumerate(ids)}
        filter_sql = ", ".join(f"%(spec_id_{index})s" for index in range(len(ids)))
        rows = self._fetch_all(
            queries.DELIVERY_CUSTOMER_INVOICES_BY_SPEC_IDS.format(spec_id_filter=filter_sql),
            params,
        )
        operation_rows = self._fetch_all(
            queries.DELIVERY_OPERATIONS_BASE_BY_SPEC_IDS.format(spec_id_filter=filter_sql),
            params,
        )
        operation_ids = [int(row.get("operation_id") or 0) for row in operation_rows if int(row.get("operation_id") or 0) > 0]
        amounts_by_operation = {
            int(row.get("operation_id") or 0): row
            for row in self._fetch_operation_rows(queries.OPERATION_AMOUNTS_BY_OPERATION_IDS, operation_ids)
        }
        invoice_linked_operations = {
            int(row.get("operation_id") or 0)
            for row in self._fetch_operation_rows(queries.OPERATION_CUSTOMER_INVOICE_LINKS_BY_OPERATION_IDS, operation_ids)
            if int(row.get("operation_id") or 0) > 0
        }
        closing_by_operation: dict[int, list[dict[str, Any]]] = {}
        for row in self._fetch_operation_rows(queries.OPERATION_CLOSING_DOCS_BY_OPERATION_IDS, operation_ids):
            operation_id = int(row.get("operation_id") or 0)
            if operation_id:
                closing_by_operation.setdefault(operation_id, []).append(row)
        payments_by_operation: dict[int, list[dict[str, Any]]] = {}
        for row in self._fetch_operation_rows(queries.OPERATION_PAYMENT_DOCS_BY_OPERATION_IDS, operation_ids):
            operation_id = int(row.get("operation_id") or 0)
            if operation_id:
                payments_by_operation.setdefault(operation_id, []).append(row)
        calculation_amounts: dict[int, dict[str, Decimal]] = {
            spec_id: {
                "payment_sum": Decimal("0"),
                "reimbursable_sum": Decimal("0"),
                "non_reimbursable_sum": Decimal("0"),
            }
            for spec_id in ids
        }
        calculated_operations: set[tuple[int, int]] = set()
        for operation in operation_rows:
            spec_id = int(operation.get("spec_id") or 0)
            operation_id = int(operation.get("operation_id") or 0)
            if not spec_id or not operation_id:
                continue
            amounts = amounts_by_operation.get(operation_id, {})
            closing_rows = closing_by_operation.get(operation_id, [])
            operation_payments = payments_by_operation.get(operation_id, [])
            reimbursement_id = int(operation.get("reimbursement_id") or 0)
            buyer_code = _str(operation.get("buyer_contract_code"))
            committent_code = _str(operation.get("committent_contract_code"))
            reimbursement_type = (
                "reimbursable" if reimbursement_id == 1 else "non_reimbursable" if reimbursement_id == 2 else "unknown"
            )
            operation_key = (spec_id, operation_id)
            if operation_key not in calculated_operations:
                calculated_operations.add(operation_key)
                calculation = calculation_amounts.setdefault(
                    spec_id,
                    {
                        "payment_sum": Decimal("0"),
                        "reimbursable_sum": Decimal("0"),
                        "non_reimbursable_sum": Decimal("0"),
                    },
                )
                payment_sum = Decimal(str(amounts.get("payment_sum") or "0"))
                sale_sum = Decimal(str(amounts.get("sale_sum") or "0"))
                calculation["payment_sum"] += payment_sum
                if reimbursement_id == 1:
                    calculation["reimbursable_sum"] += sale_sum
                elif reimbursement_id == 2:
                    calculation["non_reimbursable_sum"] += sale_sum
                else:
                    sale_contract_codes = {
                        _str(row.get("dog_code1c"))
                        for row in closing_rows
                        if (_str(row.get("document_kind")) or "sale") == "sale" and _str(row.get("dog_code1c"))
                    }
                    if buyer_code and sale_contract_codes == {buyer_code}:
                        calculation["non_reimbursable_sum"] += sale_sum
                    else:
                        calculation["reimbursable_sum"] += sale_sum
            if closing_rows:
                for closing in closing_rows:
                    document_kind = _str(closing.get("document_kind")) or "sale"
                    dog_code = _str(closing.get("dog_code1c"))
                    if document_kind == "purchase":
                        operation_contract_code = dog_code
                    elif reimbursement_id == 2:
                        operation_contract_code = buyer_code
                    else:
                        operation_contract_code = dog_code or committent_code or buyer_code
                    rows.append(
                        {
                            "spec_id": operation.get("spec_id"),
                            "document_kind": document_kind,
                            "code1c": closing.get("code1c") or "",
                            "document_number": closing.get("document_number") or "",
                            "document_date": closing.get("document_date"),
                            "amount_total": closing.get("amount_total") or Decimal("0"),
                            "currency": closing.get("currency") or "RUB",
                            "contract_code1c": operation_contract_code,
                            "source_id": closing.get("source_id") or 0,
                            "source_number": closing.get("source_number") or "",
                            "operation_id": operation_id,
                            "vat_rate": operation.get("vat_rate") or "",
                            "reimbursement_type": reimbursement_type,
                            "deleted": closing.get("deleted") or 0,
                            "paid_amount": None,
                        }
                    )
            elif Decimal(str(amounts.get("sale_sum") or "0")) != Decimal("0"):
                operation_contract_code = buyer_code if reimbursement_id == 2 else (committent_code or buyer_code)
                rows.append(
                    {
                        "spec_id": operation.get("spec_id"),
                        "document_kind": "sale",
                        "code1c": "",
                        "document_number": "",
                        "document_date": None,
                        "amount_total": amounts.get("sale_sum") or Decimal("0"),
                        "currency": "RUB",
                        "contract_code1c": operation_contract_code,
                        "source_id": 0,
                        "source_number": "",
                        "operation_id": operation_id,
                        "vat_rate": operation.get("vat_rate") or "",
                        "reimbursement_type": reimbursement_type,
                        "deleted": 0,
                        "paid_amount": None,
                    }
                )
            if Decimal(str(amounts.get("sale_sum") or "0")) != Decimal("0") and operation_id not in invoice_linked_operations:
                operation_contract_code = buyer_code if reimbursement_id == 2 else (committent_code or buyer_code)
                rows.append(
                    {
                        "spec_id": operation.get("spec_id"),
                        "document_kind": "customer_invoice",
                        "code1c": "",
                        "document_number": "",
                        "document_date": None,
                        "amount_total": amounts.get("sale_sum") or Decimal("0"),
                        "currency": "RUB",
                        "contract_code1c": operation_contract_code,
                        "source_id": 0,
                        "source_number": "",
                        "operation_id": operation_id,
                        "vat_rate": operation.get("vat_rate") or "",
                        "reimbursement_type": reimbursement_type,
                        "deleted": 0,
                        "paid_amount": None,
                    }
                )
            if Decimal(str(amounts.get("payment_sum") or "0")) != Decimal("0"):
                payment_rows = operation_payments or [
                    {
                        "allocated_amount": amounts.get("payment_sum") or Decimal("0"),
                        "currency": "RUB",
                    }
                ]
                for payment in payment_rows:
                    rows.append(
                        {
                            "spec_id": operation.get("spec_id"),
                            "document_kind": "payment",
                            "code1c": payment.get("code1c") or "",
                            "document_number": payment.get("document_number") or "",
                            "document_date": payment.get("document_date"),
                            "amount_total": payment.get("allocated_amount") or Decimal("0"),
                            "currency": payment.get("currency") or "RUB",
                            "contract_code1c": buyer_code,
                            "source_id": payment.get("source_id") or 0,
                            "source_number": payment.get("document_number") or "",
                            "operation_id": operation_id,
                            "vat_rate": "",
                            "reimbursement_type": "",
                            "deleted": 0,
                            "paid_amount": None,
                        }
                    )
        grouped: dict[int, list[AccountingDocument]] = {spec_id: [] for spec_id in ids}
        for row in rows:
            spec_id = int(row.get("spec_id") or 0)
            if spec_id:
                grouped.setdefault(spec_id, []).append(_row_to_document(row))
        calculations: dict[int, dict[str, str]] = {}
        for spec_id, values in calculation_amounts.items():
            balance = values["payment_sum"] - values["reimbursable_sum"] - values["non_reimbursable_sum"]
            calculations[spec_id] = {
                "payment_sum": _decimal_text(values["payment_sum"]),
                "reimbursable_sum": _decimal_text(values["reimbursable_sum"]),
                "non_reimbursable_sum": _decimal_text(values["non_reimbursable_sum"]),
                "balance": _decimal_text(balance),
            }
        return grouped, calculations

    def _fetch_operation_rows(self, query_template: str, operation_ids: list[int]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for chunk in _chunks(sorted(set(operation_ids)), 500):
            if not chunk:
                continue
            params = {f"operation_id_{index}": operation_id for index, operation_id in enumerate(chunk)}
            filter_sql = ", ".join(f"%(operation_id_{index})s" for index in range(len(chunk)))
            rows.extend(self._fetch_all(query_template.format(operation_id_filter=filter_sql), params))
        return rows

    def authenticate_user(self, login: str, password: str) -> dict[str, object] | None:
        row = self._fetch_one(queries.USER_BY_LOGIN, {"login": login})
        if row is None:
            return None
        if _str(row.get("password")) != password:
            return None
        first_name = _str(row.get("first_name"))
        last_name = _str(row.get("last_name"))
        name = " ".join(part for part in (first_name, last_name) if part).strip() or _str(row.get("login"))
        return {
            "user_id": row.get("user_id"),
            "login": row.get("login"),
            "name": name,
            "auth_type": row.get("auth_type"),
            "structure_code": row.get("structure_code"),
        }

    def _fetch_one(self, sql: str, params: dict[str, object]) -> dict[str, Any] | None:
        with self.connection_factory.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchone()

    def _fetch_all(self, sql: str, params: dict[str, object]) -> list[dict[str, Any]]:
        with self.connection_factory.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                return list(cursor.fetchall())


def _row_to_document(row: dict[str, Any]) -> AccountingDocument:
    return AccountingDocument(
        source=SourceSystem.ERP,
        kind=_document_kind(row.get("document_kind")),
        code1c=_meaningful_code(row.get("code1c")),
        number=_str(row.get("document_number")),
        date=_as_date(row.get("document_date")),
        amount=Money.of(row.get("amount_total") or Decimal("0"), _currency(row.get("currency"))),
        contract_code1c=_str(row.get("contract_code1c")),
        incoming_number=_str(row.get("document_number")),
        posted=True,
        deleted=bool(row.get("deleted")),
        source_id=str(row.get("source_id") or ""),
        source_number=_str(row.get("source_number")),
        operation_id=_int_or_none(row.get("operation_id")),
        vat_rate=_str(row.get("vat_rate")),
        reimbursement_type=_str(row.get("reimbursement_type")),
        payment_amount=Money.of(row.get("paid_amount") or Decimal("0"), "RUB")
        if row.get("paid_amount") is not None
        else None,
    )


def _document_kind(value: object) -> DocumentKind:
    text = _str(value)
    if text == "customer_invoice":
        return DocumentKind.CUSTOMER_INVOICE
    if text == "payment":
        return DocumentKind.PAYMENT
    if text == "sale":
        return DocumentKind.SALE
    if text == "purchase":
        return DocumentKind.PURCHASE
    return DocumentKind.CLOSING_DOCUMENT


def _currency(value: object) -> str:
    text = _str(value).upper()
    text = text.replace(" ", "")
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
    text = _str(value)
    if not text or text.startswith("0000-00-00"):
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt).date()
        except ValueError:
            continue
    return None


def _date_to_iso(value: object) -> str:
    parsed = _as_date(value)
    return parsed.isoformat() if parsed else ""


def _decimal_text(value: object) -> str:
    return str(Decimal(str(value or "0")).quantize(Decimal("0.01")))


def _chunks(values: list[int], size: int) -> list[list[int]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def _int_or_none(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _meaningful_code(value: object) -> str:
    text = _str(value)
    if text.lower() in {"", "_", "-", "0", "б/н", "бн", "без номера"}:
        return ""
    return text


def _str(value: object) -> str:
    return str(value or "").strip()
