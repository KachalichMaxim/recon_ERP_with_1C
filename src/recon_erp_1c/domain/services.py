from __future__ import annotations

from .entities import AccountingDocument, ReconciliationIssue
from .value_objects import ReconciliationStatus


def compare_documents(erp_doc: AccountingDocument, onec_doc: AccountingDocument) -> ReconciliationIssue:
    mismatch_fields: list[str] = []

    if erp_doc.code1c and onec_doc.code1c and erp_doc.code1c != onec_doc.code1c:
        mismatch_fields.append("code1c")
    if erp_doc.date and onec_doc.date and erp_doc.date != onec_doc.date:
        mismatch_fields.append("date")
    if not erp_doc.amount.same_currency(onec_doc.amount):
        mismatch_fields.append("currency")
    elif erp_doc.amount.amount != onec_doc.amount.amount:
        mismatch_fields.append("amount")
    if erp_doc.contract_code1c and onec_doc.contract_code1c and erp_doc.contract_code1c != onec_doc.contract_code1c:
        mismatch_fields.append("contract_code1c")
    if erp_doc.vat_rate and onec_doc.vat_rate and erp_doc.vat_rate != onec_doc.vat_rate:
        mismatch_fields.append("vat_rate")

    if not mismatch_fields:
        return ReconciliationIssue(
            status=ReconciliationStatus.MATCH,
            message="Документ совпал по ключевым полям",
            erp_document=erp_doc,
            onec_document=onec_doc,
        )

    status = (
        ReconciliationStatus.AMOUNT_MISMATCH
        if "amount" in mismatch_fields or "currency" in mismatch_fields
        else ReconciliationStatus.CONTRACT_MISMATCH
    )
    if "date" in mismatch_fields:
        status = ReconciliationStatus.DATE_MISMATCH
    if "vat_rate" in mismatch_fields:
        status = ReconciliationStatus.VAT_MISMATCH

    return ReconciliationIssue(
        status=status,
        message="Есть расхождения по документу",
        erp_document=erp_doc,
        onec_document=onec_doc,
        fields=tuple(mismatch_fields),
    )
