from __future__ import annotations

import re

from .entities import AccountingDocument, ReconciliationIssue
from .value_objects import ReconciliationStatus


STATUS_PRIORITY = (
    ("amount", ReconciliationStatus.AMOUNT_MISMATCH, "critical"),
    ("currency", ReconciliationStatus.AMOUNT_MISMATCH, "critical"),
    ("contract_code1c", ReconciliationStatus.CONTRACT_MISMATCH, "critical"),
    ("contract_context", ReconciliationStatus.CONTRACT_CONTEXT_MISSING, "critical"),
    ("date", ReconciliationStatus.DATE_MISMATCH, "warning"),
    ("code1c", ReconciliationStatus.NUMBER_MISMATCH, "warning"),
    ("number", ReconciliationStatus.NUMBER_MISMATCH, "warning"),
    ("vat_rate", ReconciliationStatus.VAT_MISMATCH, "warning"),
)


def compare_documents(erp_doc: AccountingDocument, onec_doc: AccountingDocument) -> ReconciliationIssue:
    mismatch_fields: list[str] = []

    if erp_doc.code1c and onec_doc.code1c and erp_doc.code1c != onec_doc.code1c:
        mismatch_fields.append("code1c")
    if (
        erp_doc.number
        and onec_doc.number
        and normalize_document_number(erp_doc.number) != normalize_document_number(onec_doc.number)
    ):
        mismatch_fields.append("number")
    if erp_doc.date and onec_doc.date and erp_doc.date != onec_doc.date:
        mismatch_fields.append("date")
    if not erp_doc.amount.same_currency(onec_doc.amount):
        mismatch_fields.append("currency")
    elif erp_doc.amount.amount != onec_doc.amount.amount:
        mismatch_fields.append("amount")
    if erp_doc.contract_code1c and onec_doc.contract_code1c:
        if erp_doc.contract_code1c != onec_doc.contract_code1c:
            mismatch_fields.append("contract_code1c")
    elif erp_doc.contract_code1c or onec_doc.contract_code1c:
        mismatch_fields.append("contract_context")
    if erp_doc.vat_rate and onec_doc.vat_rate and erp_doc.vat_rate != onec_doc.vat_rate:
        mismatch_fields.append("vat_rate")

    if not mismatch_fields:
        return ReconciliationIssue(
            status=ReconciliationStatus.MATCH,
            message="Документ совпал по ключевым полям",
            erp_document=erp_doc,
            onec_document=onec_doc,
            match_confidence="exact",
        )

    primary_reason = mismatch_fields[0]
    status = ReconciliationStatus.NOT_COMPARABLE
    severity = "warning"
    for field, candidate_status, candidate_severity in STATUS_PRIORITY:
        if field in mismatch_fields:
            primary_reason = field
            status = candidate_status
            severity = candidate_severity
            break

    return ReconciliationIssue(
        status=status,
        message="Есть расхождения по документу",
        erp_document=erp_doc,
        onec_document=onec_doc,
        fields=tuple(mismatch_fields),
        primary_reason=primary_reason,
        severity=severity,
        match_confidence="exact",
    )


def normalize_document_number(value: str) -> str:
    text = str(value or "").strip().upper()
    text = text.replace("№", "")
    text = re.sub(r"^(N|NO)\.?\s*", "", text)
    text = text.replace("СЧЁТ", "СЧЕТ")
    text = re.sub(r"[\s_]+", "", text)
    text = re.sub(r"[‐‑‒–—−]+", "-", text)
    parts = text.split("-")
    normalized_parts = [part.lstrip("0") or "0" if part.isdigit() else part for part in parts]
    return "-".join(normalized_parts)
