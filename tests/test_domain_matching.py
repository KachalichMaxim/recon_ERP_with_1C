from __future__ import annotations

from datetime import date
from decimal import Decimal

from recon_erp_1c.application.use_cases.reconcile_delivery import aggregate_documents
from recon_erp_1c.domain.entities import AccountingDocument
from recon_erp_1c.domain.services import compare_documents
from recon_erp_1c.domain.value_objects import DocumentKind, Money, ReconciliationStatus, SourceSystem


def test_compare_documents_match() -> None:
    erp_doc = AccountingDocument(
        source=SourceSystem.ERP,
        kind=DocumentKind.CUSTOMER_INVOICE,
        code1c="ВА-007703",
        number="ВА-007703",
        date=date(2025, 7, 9),
        amount=Money.of("21000.00"),
        contract_code1c="БП-051945",
        vat_rate="0%",
    )
    onec_doc = AccountingDocument(
        source=SourceSystem.ONE_C,
        kind=DocumentKind.CUSTOMER_INVOICE,
        code1c="ВА-007703",
        number="ВА-007703",
        date=date(2025, 7, 9),
        amount=Money.of("21000.00"),
        contract_code1c="БП-051945",
        vat_rate="0%",
    )

    issue = compare_documents(erp_doc, onec_doc)

    assert issue.status == ReconciliationStatus.MATCH
    assert issue.fields == ()


def test_compare_documents_contract_mismatch() -> None:
    erp_doc = AccountingDocument(
        source=SourceSystem.ERP,
        kind=DocumentKind.CLOSING_DOCUMENT,
        code1c="00БП-013433",
        number="14617",
        date=date(2025, 8, 9),
        amount=Money.of("21000.00"),
        contract_code1c="БП-051945",
    )
    onec_doc = AccountingDocument(
        source=SourceSystem.ONE_C,
        kind=DocumentKind.CLOSING_DOCUMENT,
        code1c="00БП-013433",
        number="14617",
        date=date(2025, 8, 9),
        amount=Money.of("21000.00"),
        contract_code1c="БП-051946",
    )

    issue = compare_documents(erp_doc, onec_doc)

    assert issue.status == ReconciliationStatus.CONTRACT_MISMATCH
    assert issue.fields == ("contract_code1c",)


def test_documents_are_aggregated_by_kind_and_1c_code() -> None:
    docs = [
        AccountingDocument(
            source=SourceSystem.ERP,
            kind=DocumentKind.PAYMENT,
            code1c="00БП-010299",
            number="29195",
            date=date(2025, 7, 30),
            amount=Money.of("21000.00"),
            contract_code1c="БП-051945",
            source_id="1",
        ),
        AccountingDocument(
            source=SourceSystem.ERP,
            kind=DocumentKind.PAYMENT,
            code1c="00БП-010299",
            number="29195",
            date=date(2025, 7, 30),
            amount=Money.of("390296.92"),
            contract_code1c="БП-051945",
            source_id="2",
        ),
    ]

    aggregated = aggregate_documents(docs)

    assert len(aggregated) == 1
    assert aggregated[0].amount.amount == Decimal("411296.92")


def test_compare_documents_currency_mismatch_is_amount_issue() -> None:
    erp_doc = AccountingDocument(
        source=SourceSystem.ERP,
        kind=DocumentKind.CUSTOMER_INVOICE,
        code1c="ВА-007703",
        number="ВА-007703",
        date=date(2025, 7, 9),
        amount=Money.of("21000.00", "RUB"),
        contract_code1c="БП-051945",
    )
    onec_doc = AccountingDocument(
        source=SourceSystem.ONE_C,
        kind=DocumentKind.CUSTOMER_INVOICE,
        code1c="ВА-007703",
        number="ВА-007703",
        date=date(2025, 7, 9),
        amount=Money.of("21000.00", "USD"),
        contract_code1c="БП-051945",
    )

    issue = compare_documents(erp_doc, onec_doc)

    assert issue.status == ReconciliationStatus.AMOUNT_MISMATCH
    assert issue.fields == ("currency",)
