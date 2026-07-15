from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime

from recon_erp_1c.domain.entities import (
    AccountingDocument,
    Counterparty,
    Delivery,
    Organization,
    ReconciliationIssue,
    ReconciliationRun,
)
from recon_erp_1c.domain.value_objects import DocumentKind, Money, OneCContractCodes, ReconciliationStatus, SourceSystem
from recon_erp_1c.infrastructure.persistence.mariadb_log_repository import MariaDbReconciliationLogRepository


class _Cursor:
    def __init__(self, connection: "_Connection") -> None:
        self.connection = connection
        self.lastrowid = 17

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, _sql, params):
        self.connection.params.append(params)


class _Connection:
    def __init__(self) -> None:
        self.params: list[dict[str, object]] = []
        self.begun = False
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return _Cursor(self)

    def begin(self):
        self.begun = True

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class _ConnectionFactory:
    def __init__(self) -> None:
        self.connection = _Connection()

    @contextmanager
    def connect(self):
        yield self.connection


def test_log_repository_persists_missing_operation_id_as_zero_in_one_transaction():
    organization = Organization(erp_id=1, code1c="ORG", inn="1", name="Org")
    counterparty = Counterparty(erp_id=2, code1c="CLIENT", inn="2", name="Client")
    delivery = Delivery(
        erp_spec_id=20334,
        spec_number="1051",
        spec_date=date(2025, 7, 1),
        base_contract_number="660/1",
        organization=organization,
        counterparty=counterparty,
        contract_codes=OneCContractCodes(buyer_contract_code="B", committent_contract_code="C"),
    )
    document = AccountingDocument(
        source=SourceSystem.ERP,
        kind=DocumentKind.SALE,
        code1c="DOC",
        number="DOC",
        date=date(2025, 7, 1),
        amount=Money.of("10"),
        contract_code1c="B",
        operation_id=None,
    )
    run = ReconciliationRun(
        run_id="run-1",
        delivery=delivery,
        created_at=datetime(2025, 7, 1),
        issues=[ReconciliationIssue(status=ReconciliationStatus.MATCH, message="ok", erp_document=document)],
    )
    factory = _ConnectionFactory()

    MariaDbReconciliationLogRepository(factory).save_run(run)

    assert factory.connection.begun
    assert factory.connection.committed
    assert not factory.connection.rolled_back
    assert factory.connection.params[0]["run_external_id"] == "run-1"
    assert factory.connection.params[0]["unresolved_count"] == 0
    assert factory.connection.params[0]["matched_count"] == 1
    assert factory.connection.params[0]["execution_status"] == "completed"
    assert factory.connection.params[0]["coverage_status"] == "unknown"
    assert factory.connection.params[0]["result_status"] == "no_issues_in_available_scope"
    assert factory.connection.params[0]["ruleset_version"] == "0.3.0"
    assert factory.connection.params[1]["oper_id"] == 0
    assert len(factory.connection.params[1]["issue_key"]) == 64
