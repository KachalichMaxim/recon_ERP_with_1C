from __future__ import annotations

from dataclasses import asdict, is_dataclass
import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from recon_erp_1c.domain.entities import AccountingDocument, ReconciliationIssue, ReconciliationRun


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date | datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, list | tuple):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    return value


def document_to_dict(document: AccountingDocument | None) -> dict[str, Any] | None:
    if document is None:
        return None
    payload = to_jsonable(document)
    if document.source.value == "erp":
        payload["erp_url"] = _erp_document_url(document)
        payload["operation_url"] = (
            f"http://erp.vedagent/veda/?pgid=35&invtb=145&obid={document.operation_id}#"
            if document.operation_id
            else ""
        )
        payload["parent_operation_url"] = (
            f"http://erp.vedagent/veda/?pgid=35&invtb=145&obid={document.parent_operation_id}#"
            if document.parent_operation_id
            else ""
        )
        payload["related_erp_links"] = [
            {
                "label": related.number or f"ERP документ {related.source_id}",
                "url": _erp_source_url(document.kind.value, related.source_id),
                "operation_id": related.operation_id,
                "operation_url": (
                    f"http://erp.vedagent/veda/?pgid=35&invtb=145&obid={related.operation_id}#"
                    if related.operation_id
                    else ""
                ),
            }
            for related in document.related_documents
            if related.source_id
        ]
    return payload


def _erp_document_url(document: AccountingDocument) -> str:
    return _erp_source_url(document.kind.value, document.source_id)


def _erp_source_url(kind: str, source_id: str) -> str:
    if not source_id or not source_id.isdigit():
        return ""
    if kind == "customer_invoice":
        return f"http://erp.vedagent/veda/?pgid=17&obid={source_id}#"
    if kind in {"sale", "purchase", "closing_document"}:
        return f"http://erp.vedagent/veda/?pgid=83&obid={source_id}"
    return ""


def reconciliation_issue_key(issue: ReconciliationIssue, ordinal: int = 0) -> str:
    erp = issue.erp_document
    onec = issue.onec_document
    canonical = {
        "ordinal": ordinal,
        "status": issue.status.value,
        "erp": _document_identity(erp),
        "onec": _document_identity(onec),
        "primary_reason": issue.primary_reason,
        "matched_detail_id": issue.matched_detail_id,
    }
    raw = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _document_identity(document: AccountingDocument | None) -> dict[str, Any] | None:
    if document is None:
        return None
    return {
        "source_id": document.source_id,
        "operation_id": document.operation_id,
        "kind": document.kind.value,
        "code1c": document.code1c,
        "number": document.number,
        "date": document.date.isoformat() if document.date else "",
        "amount": str(document.amount.amount),
        "currency": document.amount.currency,
        "contract_code1c": document.contract_code1c,
    }


def issue_to_dict(issue: ReconciliationIssue, ordinal: int = 0) -> dict[str, Any]:
    return {
        "issue_key": reconciliation_issue_key(issue, ordinal),
        "status": issue.status.value,
        "message": issue.message,
        "fields": list(issue.fields),
        "primary_reason": issue.primary_reason,
        "severity": issue.severity,
        "match_confidence": issue.match_confidence,
        "match_basis": issue.match_basis,
        "matched_detail_id": issue.matched_detail_id,
        "erp_document": document_to_dict(issue.erp_document),
        "onec_document": document_to_dict(issue.onec_document),
    }


def run_to_dict(run: ReconciliationRun) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for issue in run.issues:
        counts[issue.status.value] = counts.get(issue.status.value, 0) + 1
    groups = _status_groups(counts)
    return {
        "run_id": run.run_id,
        "created_at": run.created_at.isoformat(),
        "period": to_jsonable(run.period),
        "matched": run.matched,
        "execution_status": run.execution_status,
        "coverage_status": run.coverage_status,
        "result_status": run.result_status,
        "balance_status": run.balance_status,
        "ruleset": {
            "id": run.ruleset_id,
            "version": run.ruleset_version,
            "status": "experimental",
        },
        "application": {
            "version": run.application_version,
            "git_sha": run.git_sha,
        },
        "delivery": to_jsonable(run.delivery),
        "summary": {
            "issues_total": len(run.issues),
            "by_status": counts,
            "by_group": groups,
        },
        "balance_comparison": to_jsonable(run.balance_comparison),
        "coverage": to_jsonable(run.coverage),
        "source_warnings": list(run.source_warnings),
        "metrics": to_jsonable(run.metrics),
        "issues": [issue_to_dict(issue, ordinal) for ordinal, issue in enumerate(run.issues)],
    }


def _status_groups(counts: dict[str, int]) -> dict[str, int]:
    groups = {
        "matched": {"match"},
        "cannot_check": {"missing_erp_invoice", "missing_erp_closing_document", "erp_code1c_missing"},
        "not_found": {"not_found_in_1c", "not_found_in_erp"},
        "link_problem": {"not_linked_to_delivery_in_erp", "contract_context_missing"},
        "attribute_mismatch": {
            "amount_mismatch",
            "date_mismatch",
            "contract_mismatch",
            "number_mismatch",
            "vat_mismatch",
            "duplicate_in_1c",
            "ambiguous_match",
            "aggregation_conflict",
            "not_comparable",
        },
    }
    return {
        group: sum(counts.get(status, 0) for status in statuses)
        for group, statuses in groups.items()
    }
