from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from recon_erp_1c.application.serializers import reconciliation_issue_key, run_to_dict
from recon_erp_1c.domain.entities import AccountingDocument, ReconciliationRun
from recon_erp_1c.infrastructure.erp_mariadb.connection import MariaDbConnectionFactory


class MariaDbReconciliationLogRepository:
    def __init__(
        self,
        connection_factory: MariaDbConnectionFactory,
        *,
        user_login: str = "",
        user_name: str = "",
        erp_token_hash: str = "",
    ) -> None:
        self.connection_factory = connection_factory
        self.user_login = user_login
        self.user_name = user_name
        self.erp_token_hash = erp_token_hash

    def save_run(self, run: ReconciliationRun) -> None:
        payload = run_to_dict(run)
        erp_docs_count = sum(1 for issue in run.issues if issue.erp_document is not None)
        onec_docs_count = sum(1 for issue in run.issues if issue.onec_document is not None)
        matched_count = sum(1 for issue in run.issues if issue.status.value == "match")
        unresolved_count = len(run.issues) - matched_count
        status = "MATCHED" if run.matched else "HAS_ISSUES"
        comparison = run.balance_comparison
        period = run.period
        with self.connection_factory.connect() as connection:
            connection.begin()
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                    """
                    INSERT INTO veda_reconciliation_runs
                        (
                            run_external_id, scope, scope_id, spec_id, client_id, source_mode,
                            triggered_by_user, triggered_by_name, erp_token_hash,
                            period_from, period_to, base_contract_number, spec_number,
                            buyer_contract_code, committent_contract_code,
                            onec_docs_count, erp_docs_count, matched_count, unresolved_count,
                            status, execution_status, coverage_status, result_status,
                            ruleset_id, ruleset_version, application_version, git_sha, coverage_json,
                            balance_status, erp_balance, onec_balance, balance_difference,
                            balance_comparable, summary_json, run_json, completed_at
                        )
                    VALUES
                        (
                            %(run_external_id)s, 'specification', %(scope_id)s, %(spec_id)s, %(client_id)s, 'api-run',
                            %(triggered_by_user)s, %(triggered_by_name)s, %(erp_token_hash)s,
                            %(period_from)s, %(period_to)s, %(base_contract_number)s, %(spec_number)s,
                            %(buyer_contract_code)s, %(committent_contract_code)s,
                            %(onec_docs_count)s, %(erp_docs_count)s, %(matched_count)s, %(unresolved_count)s,
                            %(status)s, %(execution_status)s, %(coverage_status)s, %(result_status)s,
                            %(ruleset_id)s, %(ruleset_version)s, %(application_version)s, %(git_sha)s, %(coverage_json)s,
                            %(balance_status)s, %(erp_balance)s, %(onec_balance)s, %(balance_difference)s,
                            %(balance_comparable)s, %(summary_json)s, %(run_json)s, CURRENT_TIMESTAMP
                        )
                    """,
                    {
                        "run_external_id": run.run_id,
                        "scope_id": run.delivery.erp_spec_id,
                        "spec_id": run.delivery.erp_spec_id,
                        "client_id": run.delivery.counterparty.erp_id or 0,
                        "triggered_by_user": self.user_login or None,
                        "triggered_by_name": self.user_name or None,
                        "erp_token_hash": self.erp_token_hash or None,
                        "period_from": period.date_from if period else None,
                        "period_to": period.date_to if period else None,
                        "base_contract_number": run.delivery.base_contract_number,
                        "spec_number": run.delivery.spec_number,
                        "buyer_contract_code": run.delivery.contract_codes.buyer_contract_code,
                        "committent_contract_code": run.delivery.contract_codes.committent_contract_code,
                        "onec_docs_count": onec_docs_count,
                        "erp_docs_count": erp_docs_count,
                        "matched_count": matched_count,
                        "unresolved_count": unresolved_count,
                        "status": status,
                        "execution_status": run.execution_status,
                        "coverage_status": run.coverage_status,
                        "result_status": run.result_status,
                        "ruleset_id": run.ruleset_id,
                        "ruleset_version": run.ruleset_version,
                        "application_version": run.application_version,
                        "git_sha": run.git_sha or None,
                        "coverage_json": json.dumps(payload.get("coverage"), ensure_ascii=False),
                        "balance_status": run.balance_status,
                        "erp_balance": comparison.erp_balance.amount if comparison else None,
                        "onec_balance": comparison.onec_balance.amount if comparison else None,
                        "balance_difference": comparison.difference.amount if comparison else None,
                        "balance_comparable": 1 if comparison is None or comparison.comparable else 0,
                        "summary_json": json.dumps(
                            {**payload["summary"], "metrics": payload.get("metrics", {})}, ensure_ascii=False
                        ),
                        "run_json": json.dumps(payload, ensure_ascii=False),
                    },
                    )
                    run_db_id = cursor.lastrowid
                    for ordinal, issue in enumerate(run.issues):
                        erp_doc = issue.erp_document
                        onec_doc = issue.onec_document
                        cursor.execute(
                        """
                        INSERT INTO veda_reconciliation_items
                            (
                                run_id, oper_id, erp_doc_id,
                                issue_key, erp_source_id, onec_source_id,
                                erp_code1c, erp_number, erp_date_iso, erp_sum, erp_type,
                                onec_code1c, onec_number, onec_date_iso, onec_sum, onec_type,
                                status, primary_reason, severity, match_confidence,
                                mismatch_fields_json, details_json, note
                            )
                        VALUES
                            (
                                %(run_id)s, %(oper_id)s, %(erp_doc_id)s,
                                %(issue_key)s, %(erp_source_id)s, %(onec_source_id)s,
                                %(erp_code1c)s, %(erp_number)s, %(erp_date_iso)s, %(erp_sum)s, %(erp_type)s,
                                %(onec_code1c)s, %(onec_number)s, %(onec_date_iso)s, %(onec_sum)s, %(onec_type)s,
                                %(status)s, %(primary_reason)s, %(severity)s, %(match_confidence)s,
                                %(mismatch_fields_json)s, %(details_json)s, %(note)s
                            )
                        """,
                            {
                                "run_id": run_db_id,
                                "oper_id": (erp_doc.operation_id or 0) if erp_doc else 0,
                                "erp_doc_id": _source_id_as_int(erp_doc),
                                "issue_key": reconciliation_issue_key(issue, ordinal),
                                "erp_source_id": erp_doc.source_id if erp_doc else None,
                                "onec_source_id": onec_doc.source_id if onec_doc else None,
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
                                        "match_basis": issue.match_basis,
                                        "matched_detail_id": issue.matched_detail_id,
                                    },
                                    ensure_ascii=False,
                                ),
                                "note": issue.message[:512],
                            },
                        )
                connection.commit()
            except Exception:
                connection.rollback()
                raise


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
