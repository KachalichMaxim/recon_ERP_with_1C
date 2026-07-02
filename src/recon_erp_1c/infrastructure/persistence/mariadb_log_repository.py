from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from recon_erp_1c.application.serializers import run_to_dict
from recon_erp_1c.domain.entities import AccountingDocument, ReconciliationRun
from recon_erp_1c.infrastructure.erp_mariadb.connection import MariaDbConnectionFactory


class MariaDbReconciliationLogRepository:
    def __init__(self, connection_factory: MariaDbConnectionFactory) -> None:
        self.connection_factory = connection_factory

    def save_run(self, run: ReconciliationRun) -> None:
        payload = run_to_dict(run)
        erp_docs_count = sum(1 for issue in run.issues if issue.erp_document is not None)
        onec_docs_count = sum(1 for issue in run.issues if issue.onec_document is not None)
        status = "MATCHED" if run.matched else "HAS_ISSUES"
        with self.connection_factory.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO veda_reconciliation_runs
                        (scope, scope_id, spec_id, client_id, source_mode, onec_docs_count, erp_docs_count, status, summary_json)
                    VALUES
                        ('specification', %(scope_id)s, %(spec_id)s, %(client_id)s, 'api-run',
                         %(onec_docs_count)s, %(erp_docs_count)s, %(status)s, %(summary_json)s)
                    """,
                    {
                        "scope_id": run.delivery.erp_spec_id,
                        "spec_id": run.delivery.erp_spec_id,
                        "client_id": run.delivery.counterparty.erp_id or 0,
                        "onec_docs_count": onec_docs_count,
                        "erp_docs_count": erp_docs_count,
                        "status": status,
                        "summary_json": json.dumps(payload["summary"], ensure_ascii=False),
                    },
                )
                run_db_id = cursor.lastrowid
                for issue in run.issues:
                    erp_doc = issue.erp_document
                    onec_doc = issue.onec_document
                    cursor.execute(
                        """
                        INSERT INTO veda_reconciliation_items
                            (
                                run_id, oper_id, erp_doc_id,
                                erp_code1c, erp_number, erp_date_iso, erp_sum, erp_type,
                                onec_code1c, onec_number, onec_date_iso, onec_sum, onec_type,
                                status, primary_reason, severity, match_confidence,
                                mismatch_fields_json, details_json, note
                            )
                        VALUES
                            (
                                %(run_id)s, %(oper_id)s, %(erp_doc_id)s,
                                %(erp_code1c)s, %(erp_number)s, %(erp_date_iso)s, %(erp_sum)s, %(erp_type)s,
                                %(onec_code1c)s, %(onec_number)s, %(onec_date_iso)s, %(onec_sum)s, %(onec_type)s,
                                %(status)s, %(primary_reason)s, %(severity)s, %(match_confidence)s,
                                %(mismatch_fields_json)s, %(details_json)s, %(note)s
                            )
                        """,
                        {
                            "run_id": run_db_id,
                            "oper_id": erp_doc.operation_id if erp_doc else 0,
                            "erp_doc_id": _source_id_as_int(erp_doc),
                            "erp_code1c": erp_doc.code1c if erp_doc else None,
                            "erp_number": erp_doc.number if erp_doc else None,
                            "erp_date_iso": erp_doc.date.isoformat() if erp_doc and erp_doc.date else None,
                            "erp_sum": _amount(erp_doc),
                            "erp_type": erp_doc.kind.value if erp_doc else None,
                            "onec_code1c": onec_doc.code1c if onec_doc else None,
                            "onec_number": onec_doc.number if onec_doc else None,
                            "onec_date_iso": onec_doc.date.isoformat() if onec_doc and onec_doc.date else None,
                            "onec_sum": _amount(onec_doc),
                            "onec_type": onec_doc.kind.value if onec_doc else None,
                            "status": issue.status.value,
                            "primary_reason": issue.primary_reason,
                            "severity": issue.severity,
                            "match_confidence": issue.match_confidence,
                            "mismatch_fields_json": json.dumps(list(issue.fields), ensure_ascii=False),
                            "details_json": json.dumps(
                                {
                                    "message": issue.message,
                                    "fields": list(issue.fields),
                                    "primary_reason": issue.primary_reason,
                                    "severity": issue.severity,
                                    "match_confidence": issue.match_confidence,
                                },
                                ensure_ascii=False,
                            ),
                            "note": issue.message[:512],
                        },
                    )


def _source_id_as_int(document: AccountingDocument | None) -> int:
    if document is None:
        return 0
    try:
        return int(document.source_id)
    except ValueError:
        return 0


def _amount(document: AccountingDocument | None) -> Decimal | None:
    if document is None:
        return None
    return document.amount.amount
