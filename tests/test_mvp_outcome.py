from __future__ import annotations

from datetime import date, datetime

from recon_erp_1c.application.serializers import run_to_dict
from recon_erp_1c.application.use_cases.reconcile_delivery import _automatic_delivery_period
from recon_erp_1c.domain.entities import (
    Counterparty,
    Delivery,
    Organization,
    ReconciliationIssue,
    ReconciliationRun,
    SnapshotCoverage,
)
from recon_erp_1c.domain.value_objects import OneCContractCodes, ReconciliationStatus


def _delivery() -> Delivery:
    return Delivery(
        erp_spec_id=20334,
        spec_number="1051",
        spec_date=date(2025, 7, 1),
        base_contract_number="660/1",
        organization=Organization(1, "ORG", "", "АО ВЭД Агент"),
        counterparty=Counterparty(221, "CLIENT", "7811451960", "АЭРО-ТРЕЙД"),
        contract_codes=OneCContractCodes("БП-068417", "БП-068418"),
    )


def test_run_exposes_independent_outcome_coverage_and_status_groups() -> None:
    run = ReconciliationRun(
        run_id="run-coverage",
        delivery=_delivery(),
        created_at=datetime(2026, 7, 15, 10, 0),
        issues=[
            ReconciliationIssue(status=ReconciliationStatus.MATCH, message="ok"),
            ReconciliationIssue(status=ReconciliationStatus.MISSING_ERP_INVOICE, message="invoice"),
            ReconciliationIssue(status=ReconciliationStatus.NOT_FOUND_IN_1C, message="1c"),
            ReconciliationIssue(status=ReconciliationStatus.NOT_LINKED_TO_DELIVERY_IN_ERP, message="link"),
            ReconciliationIssue(status=ReconciliationStatus.ERP_INVOICE_LINK_MISSING, message="invoice link"),
            ReconciliationIssue(status=ReconciliationStatus.VAT_MISMATCH, message="vat"),
        ],
        coverage=SnapshotCoverage(
            requested_scope="delivery_snapshot",
            date_from=date(2025, 7, 1),
            date_to=date(2025, 8, 31),
            filters={"buyer_contract_code1c": "БП-068417"},
            returned_blocks={"sales": 2, "document_lines": 4},
            warnings=(),
            complete=None,
            retrieved_at=datetime(2026, 7, 15, 10, 0),
            contract_version="reconciliation.v1",
        ),
    )

    payload = run_to_dict(run)

    assert payload["execution_status"] == "completed"
    assert payload["coverage_status"] == "delivery_snapshot"
    assert payload["result_status"] == "issues_found"
    assert payload["balance_status"] == "not_checked"
    assert payload["summary"]["by_group"] == {
        "matched": 1,
        "cannot_check": 1,
        "not_found": 1,
        "link_problem": 2,
        "attribute_mismatch": 1,
    }
    assert payload["coverage"]["complete"] is None
    assert payload["ruleset"] == {
        "id": "delivery-document-control",
        "version": "0.3.0",
        "status": "experimental",
    }


def test_no_issue_result_is_limited_to_available_scope() -> None:
    run = ReconciliationRun(
        run_id="run-ok",
        delivery=_delivery(),
        created_at=datetime(2026, 7, 15, 10, 0),
        issues=[ReconciliationIssue(status=ReconciliationStatus.MATCH, message="ok")],
    )

    payload = run_to_dict(run)

    assert payload["result_status"] == "no_issues_in_available_scope"
    assert payload["matched"] is True


def test_delivery_period_is_derived_without_user_date_filter() -> None:
    period = _automatic_delivery_period(_delivery(), [])

    assert period.date_from == date(2025, 5, 31)
    assert period.date_to == date(2025, 8, 1)
