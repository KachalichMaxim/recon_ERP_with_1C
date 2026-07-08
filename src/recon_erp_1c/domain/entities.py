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
class AccountingDocument:
    source: SourceSystem
    kind: DocumentKind
    code1c: str
    number: str
    date: date | None
    amount: Money
    contract_code1c: str
    posted: bool = True
    deleted: bool = False
    source_id: str = ""
    operation_id: int | None = None
    vat_rate: str = ""
    reimbursement_type: str = ""
    payment_amount: Money | None = None


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


@dataclass(slots=True)
class ReconciliationRun:
    run_id: str
    delivery: Delivery
    created_at: datetime
    issues: list[ReconciliationIssue] = field(default_factory=list)

    @property
    def matched(self) -> bool:
        return all(issue.status == ReconciliationStatus.MATCH for issue in self.issues)
