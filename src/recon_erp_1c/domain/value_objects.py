from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum


class SourceSystem(StrEnum):
    ERP = "erp"
    ONE_C = "1c"


class ContractRole(StrEnum):
    BUYER = "buyer"
    COMMITTENT = "committent"
    SUPPLIER = "supplier"
    AGENT = "agent"
    RELATED = "related"
    UNKNOWN = "unknown"


class DocumentKind(StrEnum):
    CUSTOMER_INVOICE = "customer_invoice"
    PAYMENT = "payment"
    SALE = "sale"
    PURCHASE = "purchase"
    CLOSING_DOCUMENT = "closing_document"
    ACCOUNT_MOVEMENT = "account_movement"


class ReconciliationStatus(StrEnum):
    MATCH = "match"
    NOT_FOUND_IN_1C = "not_found_in_1c"
    NOT_FOUND_IN_ERP = "not_found_in_erp"
    AMOUNT_MISMATCH = "amount_mismatch"
    DATE_MISMATCH = "date_mismatch"
    CONTRACT_MISMATCH = "contract_mismatch"
    VAT_MISMATCH = "vat_mismatch"
    NOT_COMPARABLE = "not_comparable"


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str = "RUB"

    @classmethod
    def of(cls, value: Decimal | int | float | str, currency: str = "RUB") -> "Money":
        amount = Decimal(str(value or "0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return cls(amount=amount, currency=currency)

    def same_currency(self, other: "Money") -> bool:
        return self.currency == other.currency


@dataclass(frozen=True, slots=True)
class DateRange:
    date_from: date
    date_to: date

    def contains(self, value: date) -> bool:
        return self.date_from <= value <= self.date_to


@dataclass(frozen=True, slots=True)
class OneCContractCodes:
    buyer_contract_code: str = ""
    committent_contract_code: str = ""

    def all_codes(self) -> tuple[str, ...]:
        return tuple(code for code in (self.buyer_contract_code, self.committent_contract_code) if code)
