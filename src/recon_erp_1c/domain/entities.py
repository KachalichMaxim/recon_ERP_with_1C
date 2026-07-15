from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from .value_objects import ContractRole, DocumentKind, Money, OneCContractCodes, ReconciliationStatus, SourceSystem


@dataclass(frozen=True, slots=True)
class Organization:
    erp_id: int | None
    code1c: str
    inn: str
    name: str


@dataclass(frozen=True, slots=True)
class Counterparty:
    erp_id: int | None
    code1c: str
    inn: str
    name: str


@dataclass(frozen=True, slots=True)
class Contract:
    source: SourceSystem
    code1c: str
    number: str
    date: date | None
    role: ContractRole
    organization: Organization | None = None
    counterparty: Counterparty | None = None
    base_contract_number: str = ""
    spec_number: str = ""


@dataclass(frozen=True, slots=True)
class Delivery:
    erp_spec_id: int
    spec_number: str
    spec_date: date | None
    base_contract_number: str
    organization: Organization
    counterparty: Counterparty
    contract_codes: OneCContractCodes


@dataclass(frozen=True, slots=True)
class DocumentLine:
    document_id: str
    line_id: str
    amount: Money
    contract_code1c: str = ""
    linked_contract_code1c: str = ""
    line_kind: str = ""
    nomenclature: str = ""
    content: str = ""
    vat_rate: str = ""
    vat_amount: Money | None = None
    settlement_account: str = ""
    cost_account: str = ""


@dataclass(frozen=True, slots=True)
class PaymentAllocation:
    amount: Money
    contract_code1c: str = ""
    linked_contract_code1c: str = ""
    invoice_id: str = ""
    invoice_number: str = ""
    document_line_id: str = ""
    spec_number: str = ""


@dataclass(frozen=True, slots=True)
class RelatedDocument:
    source_id: str
    number: str
    operation_id: int | None = None


@dataclass(frozen=True, slots=True)
class AccountingBalance:
    contract_code1c: str
    opening_debit: Money
    opening_credit: Money
    turnover_debit: Money
    turnover_credit: Money
    closing_debit: Money
    closing_credit: Money
    contract_id: str = ""

    @property
    def signed_closing_balance(self) -> Money:
        # Positive value means client overpayment, negative value means client debt.
        return Money.of(self.closing_credit.amount - self.closing_debit.amount, self.closing_debit.currency)


@dataclass(frozen=True, slots=True)
class AccountingDocument:
    source: SourceSystem
    kind: DocumentKind
    code1c: str
    number: str
    date: date | None
    amount: Money
    contract_code1c: str
    incoming_number: str = ""
    posted: bool = True
    deleted: bool = False
    source_id: str = ""
    source_number: str = ""
    operation_id: int | None = None
    parent_operation_id: int | None = None
    vat_rate: str = ""
    tax_invoice_number: str = ""
    tax_invoice_date: date | None = None
    reimbursement_type: str = ""
    payment_amount: Money | None = None
    linked_contract_codes: tuple[str, ...] = ()
    lines: tuple[DocumentLine, ...] = ()
    allocations: tuple[PaymentAllocation, ...] = ()
    related_documents: tuple[RelatedDocument, ...] = ()


@dataclass(frozen=True, slots=True)
class OneCSnapshot:
    documents: tuple[AccountingDocument, ...]
    balances: tuple[AccountingBalance, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BalanceComparison:
    erp_balance: Money
    onec_balance: Money
    difference: Money
    status: ReconciliationStatus
    contract_codes: tuple[str, ...] = ()
    direct_onec_balance: Money | None = None
    allocated_adjustment: Money | None = None
    comparable: bool = True
    explanation: str = ""


@dataclass(frozen=True, slots=True)
class ReconciliationIssue:
    status: ReconciliationStatus
    message: str
    erp_document: AccountingDocument | None = None
    onec_document: AccountingDocument | None = None
    fields: tuple[str, ...] = ()
    primary_reason: str = ""
    severity: str = "info"
    match_confidence: str = ""
    match_basis: str = ""
    matched_detail_id: str = ""


@dataclass(slots=True)
class ReconciliationRun:
    run_id: str
    delivery: Delivery
    created_at: datetime
    issues: list[ReconciliationIssue] = field(default_factory=list)
    balance_comparison: BalanceComparison | None = None
    source_warnings: tuple[str, ...] = ()
    metrics: dict[str, float | int] = field(default_factory=dict)

    @property
    def matched(self) -> bool:
        documents_matched = all(issue.status == ReconciliationStatus.MATCH for issue in self.issues)
        balance_matched = self.balance_comparison is None or self.balance_comparison.status == ReconciliationStatus.MATCH
        return documents_matched and balance_matched
