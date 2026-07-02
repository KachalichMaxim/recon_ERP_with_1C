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
        limit = max(1, min(int(limit or 50), 500))
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

    def list_delivery_documents(self, spec_id: int) -> list[AccountingDocument]:
        rows = self._fetch_all(queries.DELIVERY_CUSTOMER_INVOICES, {"spec_id": spec_id})
        rows.extend(self._fetch_all(queries.DELIVERY_OPERATION_DOCUMENTS, {"spec_id": spec_id}))
        return [_row_to_document(row) for row in rows]

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
        code1c=_str(row.get("code1c")),
        number=_str(row.get("document_number")),
        date=_as_date(row.get("document_date")),
        amount=Money.of(row.get("amount_total") or Decimal("0"), _currency(row.get("currency"))),
        contract_code1c=_str(row.get("contract_code1c")),
        posted=True,
        deleted=bool(row.get("deleted")),
        source_id=str(row.get("source_id") or ""),
        operation_id=_int_or_none(row.get("operation_id")),
        vat_rate=_str(row.get("vat_rate")),
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


def _int_or_none(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _meaningful_code(value: object) -> str:
    text = _str(value)
    if text in {"", "_", "-", "0"}:
        return ""
    return text


def _str(value: object) -> str:
    return str(value or "").strip()
