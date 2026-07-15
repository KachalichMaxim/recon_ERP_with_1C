from __future__ import annotations

from dataclasses import asdict, is_dataclass
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


def issue_to_dict(issue: ReconciliationIssue) -> dict[str, Any]:
    return {
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
    return {
        "run_id": run.run_id,
        "created_at": run.created_at.isoformat(),
        "matched": run.matched,
        "delivery": to_jsonable(run.delivery),
        "summary": {
            "issues_total": len(run.issues),
            "by_status": counts,
        },
        "balance_comparison": to_jsonable(run.balance_comparison),
        "source_warnings": list(run.source_warnings),
        "metrics": to_jsonable(run.metrics),
        "issues": [issue_to_dict(issue) for issue in run.issues],
    }
