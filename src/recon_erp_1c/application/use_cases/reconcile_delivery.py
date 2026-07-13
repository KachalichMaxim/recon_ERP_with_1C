from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from time import perf_counter
from uuid import uuid4

from recon_erp_1c.application.ports.repositories import ErpReadRepository, OneCReadRepository, ReconciliationLogRepository
from recon_erp_1c.domain.entities import (
    AccountingBalance,
    AccountingDocument,
    BalanceComparison,
    Delivery,
    DocumentLine,
    PaymentAllocation,
    ReconciliationIssue,
    ReconciliationRun,
)
from recon_erp_1c.domain.services import compare_documents, normalize_document_number
from recon_erp_1c.domain.value_objects import DateRange, Money, ReconciliationStatus


@dataclass(frozen=True, slots=True)
class ReconcileDeliveryCommand:
    spec_id: int
    period: DateRange
    persist_log: bool = True


class ReconcileDeliveryUseCase:
    def __init__(
        self,
        erp_repository: ErpReadRepository,
        onec_repository: OneCReadRepository,
        log_repository: ReconciliationLogRepository | None = None,
    ) -> None:
        self.erp_repository = erp_repository
        self.onec_repository = onec_repository
        self.log_repository = log_repository

    def execute(self, command: ReconcileDeliveryCommand) -> ReconciliationRun:
        total_started = perf_counter()
        erp_started = perf_counter()
        delivery = self.erp_repository.get_delivery(command.spec_id)
        contracts = self.erp_repository.list_delivery_contracts(command.spec_id)
        erp_documents = self.erp_repository.list_delivery_documents(command.spec_id)
        erp_balance = self.erp_repository.get_delivery_balance(command.spec_id)
        erp_ms = (perf_counter() - erp_started) * 1000
        onec_started = perf_counter()
        onec_snapshot = self.onec_repository.fetch_snapshot(
            delivery=delivery,
            period=command.period,
            contracts=contracts,
            erp_documents=erp_documents,
        )
        onec_ms = (perf_counter() - onec_started) * 1000
        match_started = perf_counter()
        issues = match_documents(
            aggregate_documents(erp_documents),
            aggregate_documents(list(onec_snapshot.documents)),
        )
        global_lookup_started = perf_counter()
        issues = _classify_global_erp_presence(issues, self.erp_repository)
        global_lookup_ms = (perf_counter() - global_lookup_started) * 1000
        balance_comparison = compare_balances(
            erp_balance,
            list(onec_snapshot.balances),
            delivery.contract_codes.all_codes(),
            issues,
        )
        match_ms = (perf_counter() - match_started) * 1000
        run = ReconciliationRun(
            run_id=str(uuid4()),
            delivery=delivery,
            created_at=datetime.now(),
            issues=issues,
            balance_comparison=balance_comparison,
            source_warnings=onec_snapshot.warnings,
            metrics={
                "erp_read_ms": round(erp_ms, 2),
                "onec_rest_ms": round(onec_ms, 2),
                "matching_ms": round(match_ms, 2),
                "erp_global_lookup_ms": round(global_lookup_ms, 2),
                "total_ms": round((perf_counter() - total_started) * 1000, 2),
                "erp_documents": len(erp_documents),
                "onec_documents": len(onec_snapshot.documents),
                "onec_balances": len(onec_snapshot.balances),
            },
        )
        if command.persist_log and self.log_repository is not None:
            self.log_repository.save_run(run)
        return run


def _classify_global_erp_presence(
    issues: list[ReconciliationIssue], erp_repository: ErpReadRepository
) -> list[ReconciliationIssue]:
    checker = getattr(erp_repository, "document_exists_globally", None)
    if not callable(checker):
        return issues
    result: list[ReconciliationIssue] = []
    for issue in issues:
        if issue.status != ReconciliationStatus.NOT_LINKED_TO_DELIVERY_IN_ERP or issue.onec_document is None:
            result.append(issue)
            continue
        if issue.onec_document.amount.amount == Decimal("0.00"):
            result.append(
                replace(
                    issue,
                    status=ReconciliationStatus.NOT_COMPARABLE,
                    message="Документ 1С имеет нулевую сумму и не участвует в документной сверке",
                    primary_reason="zero_amount_onec_document",
                    severity="warning",
                )
            )
            continue
        if checker(issue.onec_document):
            result.append(issue)
            continue
        result.append(
            replace(
                issue,
                status=ReconciliationStatus.NOT_FOUND_IN_ERP,
                message="Документ 1С не найден в исходных таблицах ERP",
                primary_reason="not_found_in_erp",
            )
        )
    return result


def match_documents(erp_documents: list[AccountingDocument], onec_documents: list[AccountingDocument]) -> list[ReconciliationIssue]:
    issues: list[ReconciliationIssue] = []
    onec_index = _build_match_index(onec_documents)
    matched_onec_indexes: set[int] = set()
    used_detail_resources: set[tuple[int, str, str]] = set()

    for erp_doc in erp_documents:
        precondition_issue = _erp_document_precondition_issue(erp_doc)
        if precondition_issue is not None:
            issues.append(precondition_issue)
            continue
        match = _find_onec_match(erp_doc, onec_index, onec_documents, matched_onec_indexes)
        if match is None:
            fallback = _find_unlinked_detail_match(erp_doc, onec_documents, used_detail_resources)
            if fallback is not None:
                onec_index_value, detail_match = fallback
                if detail_match.ambiguous:
                    issues.append(
                        ReconciliationIssue(
                            status=ReconciliationStatus.AMBIGUOUS_MATCH,
                            message="Найдено несколько строк 1С с одинаковой датой, суммой и договором",
                            erp_document=erp_doc,
                            fields=("amount", "date", "contract_code1c"),
                            primary_reason="ambiguous_unlinked_document_line",
                            severity="critical",
                            match_confidence="ambiguous",
                            match_basis=detail_match.basis,
                        )
                    )
                    continue
                matched_onec_indexes.add(onec_index_value)
                used_detail_resources.add((onec_index_value, detail_match.basis, detail_match.detail_id))
                comparable_erp = replace(
                    erp_doc,
                    code1c=detail_match.document.code1c,
                    number=detail_match.document.number,
                    incoming_number=detail_match.document.incoming_number,
                )
                issue = _compare_matched_detail(comparable_erp, detail_match)
                issues.append(
                    replace(
                        issue,
                        erp_document=erp_doc,
                        match_confidence="detail",
                        match_basis=detail_match.basis,
                        matched_detail_id=detail_match.detail_id,
                    )
                )
                continue
            issues.append(
                ReconciliationIssue(
                    status=ReconciliationStatus.NOT_FOUND_IN_1C,
                    message="Документ ERP не найден в 1С по типу, коду/номеру и дате",
                    erp_document=erp_doc,
                    fields=(),
                    primary_reason="not_found_in_1c",
                    severity="critical",
                )
            )
            continue
        candidate_indexes, confidence = match
        if len(candidate_indexes) > 1:
            matched_onec_indexes.update(candidate_indexes)
            status = ReconciliationStatus.DUPLICATE_IN_1C if confidence in {"exact", "strong"} else ReconciliationStatus.AMBIGUOUS_MATCH
            issues.append(
                ReconciliationIssue(
                    status=status,
                    message="Найдено несколько кандидатов 1С для одного документа ERP",
                    erp_document=erp_doc,
                    onec_document=onec_documents[candidate_indexes[0]],
                    fields=("code1c", "date", "contract_code1c"),
                    primary_reason=status.value,
                    severity="critical",
                    match_confidence=confidence,
                )
            )
            continue

        onec_index_value = candidate_indexes[0]
        matched_onec_indexes.add(onec_index_value)
        onec_doc = onec_documents[onec_index_value]
        detail_match = _project_matching_detail(erp_doc, onec_doc)
        if detail_match.ambiguous:
            issues.append(
                ReconciliationIssue(
                    status=ReconciliationStatus.AMBIGUOUS_MATCH,
                    message="В документе 1С найдено несколько строк/распределений с одинаковой суммой",
                    erp_document=erp_doc,
                    onec_document=onec_doc,
                    fields=("amount", "document_detail"),
                    primary_reason="ambiguous_document_detail",
                    severity="critical",
                    match_confidence="ambiguous",
                    match_basis=detail_match.basis,
                )
            )
            continue
        if detail_match.detail_id:
            used_detail_resources.add((onec_index_value, detail_match.basis, detail_match.detail_id))
        elif detail_match.basis == "document_header":
            for line in onec_doc.lines:
                used_detail_resources.add((onec_index_value, "document_line", line.line_id))
        issue = _compare_matched_detail(erp_doc, detail_match)
        issues.append(
            replace(
                issue,
                match_confidence=confidence,
                match_basis=detail_match.basis,
                matched_detail_id=detail_match.detail_id,
            )
        )

    for index, onec_doc in enumerate(onec_documents):
        if index not in matched_onec_indexes:
            issues.append(
                ReconciliationIssue(
                    status=ReconciliationStatus.NOT_LINKED_TO_DELIVERY_IN_ERP,
                    message="Документ 1С не связан с выбранной поставкой ERP",
                    onec_document=onec_doc,
                    fields=(),
                    primary_reason="not_linked_to_delivery_in_erp",
                    severity="critical",
                )
            )

    return issues


def _erp_document_precondition_issue(document: AccountingDocument) -> ReconciliationIssue | None:
    missing_document = (
        bool(document.operation_id)
        and not document.source_id
        and not document.code1c
        and not document.number
        and document.amount.amount != Decimal("0.00")
    )
    if not missing_document:
        return None
    if document.kind.value == "customer_invoice":
        return ReconciliationIssue(
            status=ReconciliationStatus.MISSING_ERP_INVOICE,
            message="По операции ERP не выставлен или не привязан счет покупателю",
            erp_document=document,
            fields=("erp_invoice_link",),
            primary_reason="missing_erp_invoice",
            severity="critical",
        )
    if document.kind.value == "sale":
        return ReconciliationIssue(
            status=ReconciliationStatus.MISSING_ERP_CLOSING_DOCUMENT,
            message="По операции ERP отсутствует связь с закрывающим документом",
            erp_document=document,
            fields=("erp_closing_document_link",),
            primary_reason="missing_erp_closing_document",
            severity="critical",
        )
    return None


def _build_match_index(documents: list[AccountingDocument]) -> dict[tuple[str, ...], list[int]]:
    index: dict[tuple[str, ...], list[int]] = {}
    for doc_index, document in enumerate(documents):
        for key, _confidence in _pairing_keys(document):
            index.setdefault(key, []).append(doc_index)
    return index


def _find_onec_match(
    erp_doc: AccountingDocument,
    onec_index: dict[tuple[str, ...], list[int]],
    onec_documents: list[AccountingDocument],
    matched_onec_indexes: set[int],
) -> tuple[list[int], str] | None:
    for key, confidence in _pairing_keys(erp_doc):
        candidates = [idx for idx in onec_index.get(key, []) if idx not in matched_onec_indexes]
        if candidates:
            return _select_candidates_by_contract(erp_doc, candidates, onec_documents, confidence)
    return None


def _pairing_keys(document: AccountingDocument) -> list[tuple[tuple[str, ...], str]]:
    keys: list[tuple[tuple[str, ...], str]] = []
    kind = document.kind.value
    code = document.code1c.strip()
    doc_date = document.date.isoformat() if document.date else ""
    number = normalize_document_number(document.number)
    amount = str(document.amount.amount)
    currency = document.amount.currency

    if code and doc_date:
        keys.append((("code_date", kind, code, doc_date), "code_date"))
    if number and doc_date:
        keys.append((("number_date_amount", kind, number, doc_date, amount, currency), "strong"))
    return keys


def _select_candidates_by_contract(
    erp_doc: AccountingDocument,
    candidate_indexes: list[int],
    onec_documents: list[AccountingDocument],
    confidence: str,
) -> tuple[list[int], str]:
    if len(candidate_indexes) <= 1:
        return candidate_indexes, confidence

    contract = erp_doc.contract_code1c.strip()
    if contract:
        same_contract = [
            idx for idx in candidate_indexes if onec_documents[idx].contract_code1c.strip() == contract
        ]
        if same_contract:
            return same_contract, "exact" if confidence == "code_date" else "strong"
    return candidate_indexes, "ambiguous"


def aggregate_documents(documents: list[AccountingDocument]) -> list[AccountingDocument]:
    grouped: dict[tuple[str, ...], list[AccountingDocument]] = {}
    passthrough: list[AccountingDocument] = []
    for document in documents:
        key = _aggregation_key(document)
        if key is None:
            passthrough.append(document)
            continue
        grouped.setdefault(key, []).append(document)

    result = list(passthrough)
    for rows in grouped.values():
        if len(rows) == 1:
            result.append(rows[0])
            continue
        first = rows[0]
        total = sum((row.amount.amount for row in rows), Decimal("0"))
        same_date = all(row.date == first.date for row in rows)
        same_contract = all(row.contract_code1c == first.contract_code1c for row in rows)
        same_vat = all(row.vat_rate == first.vat_rate for row in rows)
        result.append(
            AccountingDocument(
                source=first.source,
                kind=first.kind,
                code1c=first.code1c,
                number=first.number,
                date=first.date if same_date else None,
                amount=Money.of(total, first.amount.currency),
                contract_code1c=first.contract_code1c if same_contract else "",
                incoming_number=first.incoming_number,
                posted=all(row.posted for row in rows),
                deleted=all(row.deleted for row in rows),
                source_id=",".join(row.source_id for row in rows if row.source_id),
                source_number=first.source_number,
                operation_id=None,
                vat_rate=first.vat_rate if same_vat else "",
                reimbursement_type=first.reimbursement_type,
                linked_contract_codes=tuple(dict.fromkeys(code for row in rows for code in row.linked_contract_codes)),
                lines=tuple(line for row in rows for line in row.lines),
                allocations=tuple(allocation for row in rows for allocation in row.allocations),
            )
        )
    return result


def _aggregation_key(document: AccountingDocument) -> tuple[str, ...] | None:
    document_id = document.code1c.strip() or normalize_document_number(document.number)
    if not document_id:
        return None
    date_value = document.date.isoformat() if document.date else ""
    source_id = document.source_id.strip()
    common = (document.kind.value, document_id, source_id, document.contract_code1c.strip(), document.amount.currency)
    if document.kind.value == "payment":
        # One bank document may be allocated to several ERP operations and
        # contracts. It remains one physical payment for reconciliation.
        return (document.kind.value, document_id, source_id, document.amount.currency, date_value)
    if document.kind.value == "sale":
        return (*common, date_value, document.vat_rate.strip())
    if document.kind.value == "customer_invoice":
        return (*common, date_value, normalize_document_number(document.number))
    return (*common, date_value, document.vat_rate.strip())


@dataclass(frozen=True, slots=True)
class _DetailMatch:
    document: AccountingDocument
    basis: str = "document_header"
    detail_id: str = ""
    ambiguous: bool = False


def _compare_matched_detail(erp_doc: AccountingDocument, detail_match: _DetailMatch) -> ReconciliationIssue:
    onec_doc = detail_match.document
    # A contract is candidate-selection context, not a reconciliation error:
    # one delivery legitimately contains documents posted on related contracts.
    comparable_onec = (
        replace(onec_doc, contract_code1c=erp_doc.contract_code1c)
        if erp_doc.contract_code1c and onec_doc.contract_code1c
        else onec_doc
    )
    issue = compare_documents(erp_doc, comparable_onec)
    return replace(
        issue,
        onec_document=onec_doc,
        message=(
            "Документ совпал; договор документа 1С показан справочно"
            if issue.status == ReconciliationStatus.MATCH
            else issue.message
        ),
    )


def _project_matching_detail(erp_doc: AccountingDocument, onec_doc: AccountingDocument) -> _DetailMatch:
    if erp_doc.amount == onec_doc.amount:
        if onec_doc.kind.value == "payment" and onec_doc.allocations and erp_doc.contract_code1c:
            allocation_contracts = {
                allocation.linked_contract_code1c or allocation.contract_code1c
                for allocation in onec_doc.allocations
                if allocation.linked_contract_code1c or allocation.contract_code1c
            }
            if erp_doc.contract_code1c in allocation_contracts:
                return _DetailMatch(
                    document=replace(onec_doc, contract_code1c=erp_doc.contract_code1c),
                    basis="payment_header_allocations",
                )
        return _DetailMatch(document=onec_doc)

    details: list[tuple[Money, str, str, str]] = []
    for allocation in onec_doc.allocations:
        details.append(
            (
                allocation.amount,
                allocation.linked_contract_code1c or allocation.contract_code1c,
                allocation.document_line_id or allocation.invoice_id or allocation.invoice_number,
                "payment_allocation" if onec_doc.kind.value == "payment" else "document_allocation",
            )
        )
    for line in onec_doc.lines:
        details.append(
            (
                line.amount,
                line.linked_contract_code1c or line.contract_code1c,
                line.line_id,
                "document_line",
            )
        )
    exact_amount = [item for item in details if item[0] == erp_doc.amount]
    if not exact_amount:
        return _DetailMatch(document=onec_doc)

    contract = erp_doc.contract_code1c.strip()
    same_contract = [item for item in exact_amount if contract and item[1] == contract]
    candidates = same_contract or exact_amount
    if len(candidates) != 1:
        return _DetailMatch(document=onec_doc, basis=candidates[0][3] if candidates else "document_detail", ambiguous=True)

    amount, detail_contract, detail_id, basis = candidates[0]
    projected = replace(
        onec_doc,
        amount=amount,
        contract_code1c=detail_contract or onec_doc.contract_code1c,
        vat_rate=_detail_vat_rate(onec_doc, detail_id) or onec_doc.vat_rate,
    )
    return _DetailMatch(document=projected, basis=basis, detail_id=detail_id)


def _detail_vat_rate(document: AccountingDocument, detail_id: str) -> str:
    for line in document.lines:
        if line.line_id == detail_id:
            return line.vat_rate
    return ""


def _find_unlinked_detail_match(
    erp_doc: AccountingDocument,
    onec_documents: list[AccountingDocument],
    used_detail_resources: set[tuple[int, str, str]],
) -> tuple[int, _DetailMatch] | None:
    if erp_doc.kind.value not in {"sale", "purchase"}:
        return None
    candidates: list[tuple[int, _DetailMatch]] = []
    for index, document in enumerate(onec_documents):
        if document.kind != erp_doc.kind or document.date != erp_doc.date:
            continue
        if erp_doc.code1c and document.code1c != erp_doc.code1c:
            continue
        for line in document.lines:
            resource = (index, "document_line", line.line_id)
            if resource in used_detail_resources or line.amount != erp_doc.amount:
                continue
            line_contract = line.linked_contract_code1c or line.contract_code1c or document.contract_code1c
            candidates.append(
                (
                    index,
                    _DetailMatch(
                        document=replace(
                            document,
                            amount=line.amount,
                            contract_code1c=line_contract,
                            vat_rate=line.vat_rate or document.vat_rate,
                        ),
                        basis="document_line",
                        detail_id=line.line_id,
                    ),
                )
            )
    if not candidates:
        return None
    contract = erp_doc.contract_code1c.strip()
    same_contract = [
        candidate for candidate in candidates if contract and candidate[1].document.contract_code1c == contract
    ]
    candidates = same_contract or candidates
    if len(candidates) > 1:
        first_index, first = candidates[0]
        return first_index, replace(first, ambiguous=True)
    return candidates[0]


def compare_balances(
    erp_balance: Money,
    onec_balances: list[AccountingBalance],
    contract_codes: tuple[str, ...],
    issues: list[ReconciliationIssue] | None = None,
) -> BalanceComparison | None:
    codes = tuple(code for code in contract_codes if code)
    relevant = [balance for balance in onec_balances if not codes or balance.contract_code1c in codes]
    if not relevant:
        return None
    currency = erp_balance.currency
    onec_amount = sum(
        (balance.signed_closing_balance.amount for balance in relevant if balance.closing_debit.currency == currency),
        Decimal("0"),
    )
    direct_onec_balance = Money.of(onec_amount, currency)
    allocated_adjustment = Money.of(_allocated_external_adjustment(issues or [], codes, currency), currency)
    onec_balance = Money.of(direct_onec_balance.amount + allocated_adjustment.amount, currency)
    difference = Money.of(erp_balance.amount - onec_balance.amount, currency)
    status = ReconciliationStatus.MATCH if difference.amount == Decimal("0.00") else ReconciliationStatus.AMOUNT_MISMATCH
    return BalanceComparison(
        erp_balance=erp_balance,
        onec_balance=onec_balance,
        difference=difference,
        status=status,
        contract_codes=codes,
        direct_onec_balance=direct_onec_balance,
        allocated_adjustment=allocated_adjustment,
    )


def _allocated_external_adjustment(
    issues: list[ReconciliationIssue], contract_codes: tuple[str, ...], currency: str
) -> Decimal:
    adjustment = Decimal("0")
    comparable_statuses = {
        ReconciliationStatus.MATCH,
        ReconciliationStatus.CONTRACT_MISMATCH,
        ReconciliationStatus.DATE_MISMATCH,
        ReconciliationStatus.NUMBER_MISMATCH,
        ReconciliationStatus.VAT_MISMATCH,
    }
    for issue in issues:
        erp_doc = issue.erp_document
        onec_doc = issue.onec_document
        if not erp_doc or not onec_doc or not erp_doc.operation_id:
            continue
        if issue.status not in comparable_statuses:
            continue
        if issue.match_basis not in {"document_line", "payment_allocation"}:
            continue
        if onec_doc.contract_code1c in contract_codes or onec_doc.amount.currency != currency:
            continue
        if erp_doc.kind.value == "payment":
            adjustment += onec_doc.amount.amount
        elif erp_doc.kind.value == "sale":
            adjustment -= onec_doc.amount.amount
    return adjustment
