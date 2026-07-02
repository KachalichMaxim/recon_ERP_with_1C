from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from recon_erp_1c.application.ports.repositories import ErpReadRepository, OneCReadRepository, ReconciliationLogRepository
from recon_erp_1c.domain.entities import AccountingDocument, Delivery, ReconciliationIssue, ReconciliationRun
from recon_erp_1c.domain.services import compare_documents
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
    onec_by_code = {doc.code1c: doc for doc in onec_documents if doc.code1c}
    matched_onec_codes: set[str] = set()

    for erp_doc in erp_documents:
        onec_doc = onec_by_code.get(erp_doc.code1c)
        if onec_doc is None:
            issues.append(
                ReconciliationIssue(
                    status=ReconciliationStatus.NOT_FOUND_IN_1C,
                    message="Документ ERP не найден в 1С по коду 1С",
                    erp_document=erp_doc,
                    fields=("code1c",),
                )
            )
            continue
        matched_onec_codes.add(onec_doc.code1c)
        issues.append(compare_documents(erp_doc, onec_doc))

    for onec_doc in onec_documents:
        if onec_doc.code1c and onec_doc.code1c not in matched_onec_codes:
            issues.append(
                ReconciliationIssue(
                    status=ReconciliationStatus.NOT_FOUND_IN_ERP,
                    message="Документ 1С не найден в ERP по коду 1С",
                    onec_document=onec_doc,
                    fields=("code1c",),
                )
            )

    return issues


def aggregate_documents(documents: list[AccountingDocument]) -> list[AccountingDocument]:
    grouped: dict[tuple[str, str, str], list[AccountingDocument]] = {}
    passthrough: list[AccountingDocument] = []
    for document in documents:
        if not document.code1c:
            passthrough.append(document)
            continue
        grouped.setdefault((document.kind.value, document.code1c, document.amount.currency), []).append(document)

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
