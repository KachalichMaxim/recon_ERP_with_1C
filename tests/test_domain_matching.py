from __future__ import annotations

from datetime import date
from decimal import Decimal

from recon_erp_1c.application.use_cases.reconcile_delivery import aggregate_documents, match_documents
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
            source_id="bank-doc-1",
        ),
        AccountingDocument(
            source=SourceSystem.ERP,
            kind=DocumentKind.PAYMENT,
            code1c="00БП-010299",
            number="29195",
            date=date(2025, 7, 30),
            amount=Money.of("390296.92"),
            contract_code1c="БП-051945",
            source_id="bank-doc-1",
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


def test_match_documents_without_erp_code1c_by_number_date_amount_contract() -> None:
    erp_doc = AccountingDocument(
        source=SourceSystem.ERP,
        kind=DocumentKind.CUSTOMER_INVOICE,
        code1c="",
        number="№ ВА-0007703",
        date=date(2025, 7, 9),
        amount=Money.of("21000.00"),
        contract_code1c="БП-051945",
    )
    onec_doc = AccountingDocument(
        source=SourceSystem.ONE_C,
        kind=DocumentKind.CUSTOMER_INVOICE,
        code1c="ВА-007703",
        number="ВА-7703",
        date=date(2025, 7, 9),
        amount=Money.of("21000.00"),
        contract_code1c="БП-051945",
    )

    issues = match_documents([erp_doc], [onec_doc])

    assert len(issues) == 1
    assert issues[0].status == ReconciliationStatus.MATCH
    assert issues[0].match_confidence == "strong"


def test_match_documents_detects_duplicate_1c_candidates_by_code_date_contract() -> None:
    erp_doc = AccountingDocument(
        source=SourceSystem.ERP,
        kind=DocumentKind.PAYMENT,
        code1c="00БП-010299",
        number="29195",
        date=date(2025, 7, 30),
        amount=Money.of("442296.92"),
        contract_code1c="БП-051945",
    )
    onec_docs = [
        AccountingDocument(
            source=SourceSystem.ONE_C,
            kind=DocumentKind.PAYMENT,
            code1c="00БП-010299",
            number="29195",
            date=date(2025, 7, 30),
            amount=Money.of("442296.92"),
            contract_code1c="БП-051945",
            source_id="1",
        ),
        AccountingDocument(
            source=SourceSystem.ONE_C,
            kind=DocumentKind.PAYMENT,
            code1c="00БП-010299",
            number="29195",
            date=date(2025, 7, 30),
            amount=Money.of("442296.92"),
            contract_code1c="БП-051945",
            source_id="2",
        ),
    ]

    issues = match_documents([erp_doc], onec_docs)

    assert len(issues) == 1
    assert issues[0].status == ReconciliationStatus.DUPLICATE_IN_1C
    assert issues[0].match_confidence == "exact"


def test_match_documents_reports_contract_mismatch_for_same_code_date_with_different_contract() -> None:
    erp_doc = AccountingDocument(
        source=SourceSystem.ERP,
        kind=DocumentKind.PAYMENT,
        code1c="00БП-010299",
        number="29195",
        date=date(2025, 7, 30),
        amount=Money.of("442296.92"),
        contract_code1c="БП-051945",
    )
    onec_doc = AccountingDocument(
        source=SourceSystem.ONE_C,
        kind=DocumentKind.PAYMENT,
        code1c="00БП-010299",
        number="29195",
        date=date(2025, 7, 30),
        amount=Money.of("442296.92"),
        contract_code1c="БП-999999",
    )

    issues = match_documents([erp_doc], [onec_doc])

    assert len(issues) == 1
    assert issues[0].status == ReconciliationStatus.CONTRACT_MISMATCH
    assert issues[0].fields == ("contract_code1c",)


def test_match_documents_reports_missing_contract_context() -> None:
    erp_doc = AccountingDocument(
        source=SourceSystem.ERP,
        kind=DocumentKind.SALE,
        code1c="00БП-000198",
        number="00БП-000198",
        date=date(2025, 8, 9),
        amount=Money.of("67055.99"),
        contract_code1c="БП-051945",
    )
    onec_doc = AccountingDocument(
        source=SourceSystem.ONE_C,
        kind=DocumentKind.SALE,
        code1c="00БП-000198",
        number="00БП-000198",
        date=date(2025, 8, 9),
        amount=Money.of("67055.99"),
        contract_code1c="",
    )

    issues = match_documents([erp_doc], [onec_doc])

    assert len(issues) == 1
    assert issues[0].status == ReconciliationStatus.CONTRACT_CONTEXT_MISSING
    assert issues[0].fields == ("contract_context",)


def test_aggregation_preserves_distinct_1c_documents_with_same_code_date_contract() -> None:
    erp_doc = AccountingDocument(
        source=SourceSystem.ERP,
        kind=DocumentKind.SALE,
        code1c="00БП-000198",
        number="00БП-000198",
        date=date(2025, 8, 9),
        amount=Money.of("67055.99"),
        contract_code1c="БП-051945",
        source_id="erp-akt-1",
    )
    onec_docs = [
        AccountingDocument(
            source=SourceSystem.ONE_C,
            kind=DocumentKind.SALE,
            code1c="00БП-000198",
            number="00БП-000198",
            date=date(2025, 8, 9),
            amount=Money.of("67055.99"),
            contract_code1c="БП-051945",
            source_id="onec-doc-1",
        ),
        AccountingDocument(
            source=SourceSystem.ONE_C,
            kind=DocumentKind.SALE,
            code1c="00БП-000198",
            number="00БП-000198",
            date=date(2025, 8, 9),
            amount=Money.of("67055.99"),
            contract_code1c="БП-051945",
            source_id="onec-doc-2",
        ),
    ]

    issues = match_documents(aggregate_documents([erp_doc]), aggregate_documents(onec_docs))

    assert len(issues) == 1
    assert issues[0].status == ReconciliationStatus.DUPLICATE_IN_1C


def test_compare_documents_number_mismatch() -> None:
    erp_doc = AccountingDocument(
        source=SourceSystem.ERP,
        kind=DocumentKind.CUSTOMER_INVOICE,
        code1c="ВА-007703",
        number="ВА-007703",
        date=date(2025, 7, 9),
        amount=Money.of("21000.00"),
        contract_code1c="БП-051945",
    )
    onec_doc = AccountingDocument(
        source=SourceSystem.ONE_C,
        kind=DocumentKind.CUSTOMER_INVOICE,
        code1c="ВА-007703",
        number="ВА-007704",
        date=date(2025, 7, 9),
        amount=Money.of("21000.00"),
        contract_code1c="БП-051945",
    )

    issue = compare_documents(erp_doc, onec_doc)

    assert issue.status == ReconciliationStatus.NUMBER_MISMATCH
    assert issue.primary_reason == "number"
    assert issue.fields == ("number",)


def test_compare_documents_code_mismatch_is_identifier_issue() -> None:
    erp_doc = AccountingDocument(
        source=SourceSystem.ERP,
        kind=DocumentKind.CUSTOMER_INVOICE,
        code1c="ВА-007703",
        number="ВА-007703",
        date=date(2025, 7, 9),
        amount=Money.of("21000.00"),
        contract_code1c="БП-051945",
    )
    onec_doc = AccountingDocument(
        source=SourceSystem.ONE_C,
        kind=DocumentKind.CUSTOMER_INVOICE,
        code1c="ВА-007704",
        number="ВА-007703",
        date=date(2025, 7, 9),
        amount=Money.of("21000.00"),
        contract_code1c="БП-051945",
    )

    issue = compare_documents(erp_doc, onec_doc)

    assert issue.status == ReconciliationStatus.NUMBER_MISMATCH
    assert issue.primary_reason == "code1c"
    assert issue.fields == ("code1c",)


def test_compare_documents_amount_has_priority_over_date_and_vat() -> None:
    erp_doc = AccountingDocument(
        source=SourceSystem.ERP,
        kind=DocumentKind.SALE,
        code1c="00БП-000198",
        number="00БП-000198",
        date=date(2025, 8, 9),
        amount=Money.of("67055.99"),
        contract_code1c="БП-051945",
        vat_rate="0%",
    )
    onec_doc = AccountingDocument(
        source=SourceSystem.ONE_C,
        kind=DocumentKind.SALE,
        code1c="00БП-000198",
        number="00БП-000198",
        date=date(2025, 8, 10),
        amount=Money.of("67056.00"),
        contract_code1c="БП-051945",
        vat_rate="20%",
    )

    issue = compare_documents(erp_doc, onec_doc)

    assert issue.status == ReconciliationStatus.AMOUNT_MISMATCH
    assert issue.primary_reason == "amount"
    assert issue.fields == ("date", "amount", "vat_rate")
