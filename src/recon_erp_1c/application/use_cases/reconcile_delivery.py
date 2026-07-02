from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from recon_erp_1c.application.ports.repositories import ErpReadRepository, OneCReadRepository, ReconciliationLogRepository
from recon_erp_1c.domain.entities import AccountingDocument, Delivery, ReconciliationIssue, ReconciliationRun
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
        delivery = self.erp_repository.get_delivery(command.spec_id)
        contracts = self.erp_repository.list_delivery_contracts(command.spec_id)
        erp_documents = self.erp_repository.list_delivery_documents(command.spec_id)
        onec_documents = self.onec_repository.fetch_snapshot(
            delivery=delivery,
            period=command.period,
            contracts=contracts,
            erp_documents=erp_documents,
        )

        issues = match_documents(aggregate_documents(erp_documents), aggregate_documents(onec_documents))
        run = ReconciliationRun(
            run_id=str(uuid4()),
            delivery=delivery,
            created_at=datetime.now(),
            issues=issues,
        )
        if command.persist_log and self.log_repository is not None:
            self.log_repository.save_run(run)
        return run


def match_documents(erp_documents: list[AccountingDocument], onec_documents: list[AccountingDocument]) -> list[ReconciliationIssue]:
    issues: list[ReconciliationIssue] = []
    onec_index = _build_match_index(onec_documents)
    matched_onec_indexes: set[int] = set()

    for erp_doc in erp_documents:
        match = _find_onec_match(erp_doc, onec_index, matched_onec_indexes)
        if match is None:
            issues.append(
                ReconciliationIssue(
                    status=ReconciliationStatus.NOT_FOUND_IN_1C,
                    message="Документ ERP не найден в 1С по коду, дате, номеру и договору",
                    erp_document=erp_doc,
                    fields=("code1c", "date", "number", "contract_code1c"),
                    primary_reason="not_found_in_1c",
                    severity="critical",
                )
            )
            continue
        candidate_indexes, confidence = match
        if len(candidate_indexes) > 1:
            matched_onec_indexes.update(candidate_indexes)
            status = ReconciliationStatus.DUPLICATE_IN_1C if confidence in {"exact", "strong_code_date"} else ReconciliationStatus.AMBIGUOUS_MATCH
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
        issue = compare_documents(erp_doc, onec_documents[onec_index_value])
        issues.append(replace(issue, match_confidence=confidence))

    for index, onec_doc in enumerate(onec_documents):
        if index not in matched_onec_indexes:
            issues.append(
                ReconciliationIssue(
                    status=ReconciliationStatus.NOT_FOUND_IN_ERP,
                    message="Документ 1С не найден в ERP по коду, дате, номеру и договору",
                    onec_document=onec_doc,
                    fields=("code1c", "date", "number", "contract_code1c"),
                    primary_reason="not_found_in_erp",
                    severity="critical",
                )
            )

    return issues


def _build_match_index(documents: list[AccountingDocument]) -> dict[tuple[str, ...], list[int]]:
    index: dict[tuple[str, ...], list[int]] = {}
    for doc_index, document in enumerate(documents):
        for key, _confidence in _match_keys(document):
            index.setdefault(key, []).append(doc_index)
    return index


def _find_onec_match(
    erp_doc: AccountingDocument,
    onec_index: dict[tuple[str, ...], list[int]],
    matched_onec_indexes: set[int],
) -> tuple[list[int], str] | None:
    for key, confidence in _match_keys(erp_doc):
        candidates = [idx for idx in onec_index.get(key, []) if idx not in matched_onec_indexes]
        if candidates:
            return candidates, confidence
    return None


def _match_keys(document: AccountingDocument) -> list[tuple[tuple[str, ...], str]]:
    keys: list[tuple[tuple[str, ...], str]] = []
    kind = document.kind.value
    code = document.code1c.strip()
    doc_date = document.date.isoformat() if document.date else ""
    contract = document.contract_code1c.strip()
    number = normalize_document_number(document.number)
    amount = str(document.amount.amount)
    currency = document.amount.currency

    if code and doc_date and contract:
        keys.append((("exact", kind, code, doc_date, contract), "exact"))
    if code and doc_date:
        keys.append((("code_date", kind, code, doc_date), "strong_code_date"))
    if number and doc_date and contract:
        keys.append((("strong", kind, number, doc_date, amount, currency, contract), "strong"))
    if number:
        keys.append((("weak", kind, number, amount, currency), "weak"))
    return keys


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
                posted=all(row.posted for row in rows),
                deleted=all(row.deleted for row in rows),
                source_id=",".join(row.source_id for row in rows if row.source_id),
                operation_id=None,
                vat_rate=first.vat_rate if same_vat else "",
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
        return (*common, date_value)
    if document.kind.value == "sale":
        return (*common, date_value, document.vat_rate.strip())
    if document.kind.value == "customer_invoice":
        return (*common, date_value, normalize_document_number(document.number))
    return (*common, date_value, document.vat_rate.strip())
