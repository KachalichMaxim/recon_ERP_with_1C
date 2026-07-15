from __future__ import annotations

from datetime import date
from decimal import Decimal

from recon_erp_1c.application.use_cases.reconcile_delivery import (
    _classify_global_erp_presence,
    aggregate_documents,
    compare_balances,
    match_documents,
)
from recon_erp_1c.domain.entities import (
    AccountingBalance,
    AccountingDocument,
    DocumentLine,
    PaymentAllocation,
    RelatedDocument,
    ReconciliationIssue,
)
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
    assert aggregated[0].source_id == "bank-doc-1"


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


def test_match_documents_treats_contract_as_context_for_unique_document() -> None:
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
    assert issues[0].status == ReconciliationStatus.MATCH
    assert issues[0].fields == ()
    assert issues[0].onec_document is not None
    assert issues[0].onec_document.contract_code1c == "БП-999999"


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


def test_purchase_matches_unique_document_line_amount() -> None:
    erp_doc = AccountingDocument(
        source=SourceSystem.ERP,
        kind=DocumentKind.PURCHASE,
        code1c="00БП-012300",
        number="13282",
        date=date(2025, 7, 22),
        amount=Money.of("6462.89"),
        contract_code1c="БП-013397",
        vat_rate="0%",
    )
    onec_doc = AccountingDocument(
        source=SourceSystem.ONE_C,
        kind=DocumentKind.PURCHASE,
        code1c="00БП-012300",
        number="13282",
        date=date(2025, 7, 22),
        amount=Money.of("17715.00"),
        contract_code1c="БП-013397",
        lines=(
            DocumentLine("doc-1", "1", Money.of("3486.45"), contract_code1c="БП-013397"),
            DocumentLine("doc-1", "3", Money.of("6462.89"), contract_code1c="БП-013397", vat_rate="0%"),
        ),
    )

    issue = match_documents([erp_doc], [onec_doc])[0]

    assert issue.status == ReconciliationStatus.MATCH
    assert issue.match_basis == "document_line"
    assert issue.matched_detail_id == "3"
    assert issue.onec_document is not None
    assert issue.onec_document.amount.amount == Decimal("6462.89")


def test_duplicate_equal_document_lines_are_ambiguous() -> None:
    erp_doc = AccountingDocument(
        source=SourceSystem.ERP,
        kind=DocumentKind.PURCHASE,
        code1c="00БП-012300",
        number="13282",
        date=date(2025, 7, 22),
        amount=Money.of("6462.89"),
        contract_code1c="БП-013397",
    )
    onec_doc = AccountingDocument(
        source=SourceSystem.ONE_C,
        kind=DocumentKind.PURCHASE,
        code1c="00БП-012300",
        number="00БП-012300",
        date=date(2025, 7, 22),
        amount=Money.of("17715.00"),
        contract_code1c="БП-013397",
        lines=(
            DocumentLine("doc-1", "1", Money.of("6462.89"), contract_code1c="БП-013397"),
            DocumentLine("doc-1", "2", Money.of("6462.89"), contract_code1c="БП-013397"),
        ),
    )

    issue = match_documents([erp_doc], [onec_doc])[0]

    assert issue.status == ReconciliationStatus.AMBIGUOUS_MATCH
    assert issue.primary_reason == "ambiguous_document_detail"


def test_partial_payment_matches_allocation_and_checks_allocation_contract() -> None:
    erp_doc = AccountingDocument(
        source=SourceSystem.ERP,
        kind=DocumentKind.PAYMENT,
        code1c="00БП-010591",
        number="29422",
        date=date(2025, 8, 5),
        amount=Money.of("3765.79"),
        contract_code1c="БП-068418",
    )
    onec_doc = AccountingDocument(
        source=SourceSystem.ONE_C,
        kind=DocumentKind.PAYMENT,
        code1c="00БП-010591",
        number="29422",
        date=date(2025, 8, 5),
        amount=Money.of("9660.68"),
        contract_code1c="БП-068412",
        allocations=(
            PaymentAllocation(Money.of("5894.89"), contract_code1c="БП-068412", invoice_number="ВА-007514"),
            PaymentAllocation(Money.of("3765.79"), contract_code1c="БП-068418", invoice_number="ВА-007517"),
        ),
    )

    issue = match_documents([erp_doc], [onec_doc])[0]

    assert issue.status == ReconciliationStatus.MATCH
    assert issue.match_basis == "payment_allocation"
    assert issue.matched_detail_id == "ВА-007517"


def test_partial_payment_treats_linked_allocation_contract_as_context() -> None:
    erp_doc = AccountingDocument(
        source=SourceSystem.ERP,
        kind=DocumentKind.PAYMENT,
        code1c="00БП-010591",
        number="29422",
        date=date(2025, 8, 5),
        amount=Money.of("3765.79"),
        contract_code1c="БП-068418",
    )
    onec_doc = AccountingDocument(
        source=SourceSystem.ONE_C,
        kind=DocumentKind.PAYMENT,
        code1c="00БП-010591",
        number="29422",
        date=date(2025, 8, 5),
        amount=Money.of("9660.68"),
        contract_code1c="БП-068412",
        allocations=(PaymentAllocation(Money.of("3765.79"), contract_code1c="БП-068412"),),
    )

    issue = match_documents([erp_doc], [onec_doc])[0]

    assert issue.status == ReconciliationStatus.MATCH
    assert issue.match_basis == "payment_allocation"
    assert issue.onec_document is not None
    assert issue.onec_document.contract_code1c == "БП-068412"


def test_payment_aggregation_ignores_operation_contract() -> None:
    documents = [
        AccountingDocument(
            source=SourceSystem.ERP,
            kind=DocumentKind.PAYMENT,
            code1c="00БП-010302",
            number="29191",
            date=date(2025, 7, 30),
            amount=Money.of("176168.31"),
            contract_code1c="БП-068418",
            source_id="100",
        ),
        AccountingDocument(
            source=SourceSystem.ERP,
            kind=DocumentKind.PAYMENT,
            code1c="00БП-010302",
            number="29191",
            date=date(2025, 7, 30),
            amount=Money.of("11309.00"),
            contract_code1c="БП-068417",
            source_id="100",
        ),
    ]

    aggregated = aggregate_documents(documents)

    assert len(aggregated) == 1
    assert aggregated[0].amount.amount == Decimal("187477.31")
    assert aggregated[0].contract_code1c == ""


def test_balance_comparison_uses_credit_minus_debit_for_1c() -> None:
    balances = [
        AccountingBalance(
            contract_code1c="БП-068417",
            opening_debit=Money.of("0"),
            opening_credit=Money.of("0"),
            turnover_debit=Money.of("0"),
            turnover_credit=Money.of("0"),
            closing_debit=Money.of("3327.84"),
            closing_credit=Money.of("0"),
        ),
        AccountingBalance(
            contract_code1c="БП-068418",
            opening_debit=Money.of("0"),
            opening_credit=Money.of("0"),
            turnover_debit=Money.of("0"),
            turnover_credit=Money.of("0"),
            closing_debit=Money.of("2739.06"),
            closing_credit=Money.of("0"),
        ),
    ]

    comparison = compare_balances(Money.of("-6666.82"), balances, ("БП-068417", "БП-068418"))

    assert comparison is not None
    assert comparison.onec_balance.amount == Decimal("-6066.90")
    assert comparison.direct_onec_balance.amount == Decimal("-6066.90")
    assert comparison.allocated_adjustment.amount == Decimal("0.00")
    assert comparison.difference.amount == Decimal("-599.92")
    assert comparison.status == ReconciliationStatus.AMOUNT_MISMATCH
    assert comparison.comparable is True


def test_balance_is_not_comparable_without_erp_closing_documents() -> None:
    balances = [
        AccountingBalance(
            contract_code1c="БП-095697",
            opening_debit=Money.of("0"),
            opening_credit=Money.of("0"),
            turnover_debit=Money.of("0"),
            turnover_credit=Money.of("946696.03"),
            closing_debit=Money.of("0"),
            closing_credit=Money.of("946696.03"),
        )
    ]
    missing_sale = ReconciliationIssue(
        status=ReconciliationStatus.MISSING_ERP_CLOSING_DOCUMENT,
        message="Нет закрывающего документа",
    )

    comparison = compare_balances(
        Money.of("19999.92"),
        balances,
        ("БП-095697", "БП-095698"),
        [missing_sale],
    )

    assert comparison is not None
    assert comparison.status == ReconciliationStatus.NOT_COMPARABLE
    assert comparison.comparable is False
    assert "get_realizsum" in comparison.explanation


def test_unlinked_erp_sale_rows_match_distinct_1c_document_lines() -> None:
    erp_docs = [
        AccountingDocument(
            source=SourceSystem.ERP,
            kind=DocumentKind.SALE,
            code1c="",
            number="ВА-009585/0",
            date=date(2025, 7, 30),
            amount=Money.of("365.00"),
            contract_code1c="БП-068417",
            vat_rate="20%",
        ),
        AccountingDocument(
            source=SourceSystem.ERP,
            kind=DocumentKind.SALE,
            code1c="",
            number="ВА-009586/1",
            date=date(2025, 7, 30),
            amount=Money.of("3283.00"),
            contract_code1c="БП-068417",
            vat_rate="20%",
        ),
    ]
    onec_doc = AccountingDocument(
        source=SourceSystem.ONE_C,
        kind=DocumentKind.SALE,
        code1c="00БП-003225",
        number="00БП-003225",
        date=date(2025, 7, 30),
        amount=Money.of("14636.84"),
        contract_code1c="БП-068417",
        lines=(
            DocumentLine("sale-guid", "1", Money.of("365"), contract_code1c="БП-068417", vat_rate="20%"),
            DocumentLine("sale-guid", "2", Money.of("3283"), contract_code1c="БП-068417", vat_rate="20%"),
        ),
    )

    issues = match_documents(erp_docs, [onec_doc])

    assert [issue.status for issue in issues] == [ReconciliationStatus.MATCH, ReconciliationStatus.MATCH]
    assert [issue.matched_detail_id for issue in issues] == ["1", "2"]
    assert all(issue.match_basis == "document_line" for issue in issues)


def test_two_erp_rows_with_same_aggregate_code_match_distinct_1c_lines() -> None:
    erp_docs = [
        AccountingDocument(
            source=SourceSystem.ERP,
            kind=DocumentKind.SALE,
            code1c="00БП-003228",
            number="00БП-003228",
            date=date(2025, 7, 30),
            amount=Money.of(amount),
            contract_code1c="БП-068417",
            operation_id=operation_id,
        )
        for amount, operation_id in (("23157.25", 362790), ("599.92", 376754))
    ]
    onec_doc = AccountingDocument(
        source=SourceSystem.ONE_C,
        kind=DocumentKind.SALE,
        code1c="00БП-003228",
        number="00БП-003228",
        date=date(2025, 7, 30),
        amount=Money.of("23757.17"),
        contract_code1c="БП-013397",
        lines=(
            DocumentLine("sale-guid", "1", Money.of("23157.25"), contract_code1c="БП-013397"),
            DocumentLine("sale-guid", "2", Money.of("599.92"), contract_code1c="БП-013397"),
        ),
    )

    issues = match_documents(erp_docs, [onec_doc])

    assert [issue.status for issue in issues] == [
        ReconciliationStatus.MATCH,
        ReconciliationStatus.MATCH,
    ]
    assert [issue.matched_detail_id for issue in issues] == ["1", "2"]
    assert all(issue.onec_document and issue.onec_document.contract_code1c == "БП-013397" for issue in issues)


def test_aggregate_supplier_allocations_remain_separate_until_onec_line_matching() -> None:
    erp_docs = [
        AccountingDocument(
            source=SourceSystem.ERP,
            kind=DocumentKind.PURCHASE,
            code1c="0ЛБП-000788",
            number="2905",
            date=date(2026, 2, 20),
            amount=Money.of(amount),
            contract_code1c="БП-042109",
            source_id="214724",
            operation_id=operation_id,
            parent_operation_id=426784,
            vat_rate="0%",
        )
        for amount, operation_id in (("14798.04", 451087), ("3523.34", 451086))
    ]
    onec_doc = AccountingDocument(
        source=SourceSystem.ONE_C,
        kind=DocumentKind.PURCHASE,
        code1c="0ЛБП-000788",
        number="0ЛБП-000788",
        date=date(2026, 2, 20),
        amount=Money.of("26000.00"),
        contract_code1c="БП-042109",
        vat_rate="0%",
        lines=(
            DocumentLine("purchase-guid", "1", Money.of("1476.66"), contract_code1c="БП-042109", vat_rate="0%"),
            DocumentLine("purchase-guid", "2", Money.of("6201.96"), contract_code1c="БП-042109", vat_rate="0%"),
            DocumentLine("purchase-guid", "3", Money.of("14798.04"), contract_code1c="БП-042109", vat_rate="0%"),
            DocumentLine("purchase-guid", "4", Money.of("3523.34"), contract_code1c="БП-042109", vat_rate="0%"),
        ),
    )

    issues = match_documents(aggregate_documents(erp_docs), aggregate_documents([onec_doc]))

    assert [issue.status for issue in issues] == [ReconciliationStatus.MATCH, ReconciliationStatus.MATCH]
    assert [issue.matched_detail_id for issue in issues] == ["3", "4"]
    assert [issue.erp_document.operation_id for issue in issues if issue.erp_document] == [451087, 451086]


def test_erp_rows_are_combined_when_onec_has_only_aggregate_header_line() -> None:
    erp_docs = [
        AccountingDocument(
            source=SourceSystem.ERP,
            kind=DocumentKind.SALE,
            code1c="00БП-002193",
            number="00БП-002193",
            date=date(2024, 6, 4),
            amount=Money.of(amount),
            contract_code1c="БП-043369",
            source_id=source_id,
            operation_id=operation_id,
            vat_rate="20%",
        )
        for amount, source_id, operation_id in (
            ("13500", "105644", 208848),
            ("247630", "105645", 208849),
            ("56500", "105646", 208850),
            ("25042", "105647", 208852),
            ("23500", "105648", 208853),
            ("17100", "105649", 208854),
        )
    ]
    onec_doc = AccountingDocument(
        source=SourceSystem.ONE_C,
        kind=DocumentKind.SALE,
        code1c="00БП-002193",
        number="00БП-002193",
        date=date(2024, 6, 4),
        amount=Money.of("383272"),
        contract_code1c="БП-043369",
        vat_rate="20%",
        lines=(
            DocumentLine("sale-guid", "1", Money.of("383272"), contract_code1c="БП-043369", vat_rate="20%"),
        ),
    )

    issues = match_documents(erp_docs, [onec_doc])

    assert [issue.status for issue in issues] == [ReconciliationStatus.MATCH]
    assert issues[0].erp_document is not None
    assert issues[0].erp_document.amount == Money.of("383272")
    assert issues[0].erp_document.source_id == "105644,105645,105646,105647,105648,105649"


def test_same_code_and_amount_with_different_dates_reports_date_mismatch() -> None:
    erp_doc = AccountingDocument(
        source=SourceSystem.ERP,
        kind=DocumentKind.PURCHASE,
        code1c="0ЛБП-000770",
        number="000029129/000091898/Р",
        date=date(2024, 7, 24),
        amount=Money.of("88020.60"),
        contract_code1c="БП-048195",
    )
    onec_docs = [
        AccountingDocument(
            source=SourceSystem.ONE_C,
            kind=DocumentKind.PURCHASE,
            code1c="0ЛБП-000770",
            number="0ЛБП-000770",
            date=date(2024, 9, 19),
            amount=Money.of("88020.60"),
            contract_code1c="БП-048195",
        ),
        AccountingDocument(
            source=SourceSystem.ONE_C,
            kind=DocumentKind.PURCHASE,
            code1c="0ЛБП-000770",
            number="0ЛБП-000770",
            date=date(2025, 3, 5),
            amount=Money.of("592897.83"),
            contract_code1c="БП-051780",
        ),
    ]

    issues = match_documents([erp_doc], onec_docs)

    assert issues[0].status == ReconciliationStatus.DATE_MISMATCH
    assert issues[0].fields == ("date",)
    assert issues[0].match_confidence == "code_only"
    assert issues[1].status == ReconciliationStatus.NOT_LINKED_TO_DELIVERY_IN_ERP


def test_operation_link_makes_header_contract_informational() -> None:
    erp_doc = AccountingDocument(
        source=SourceSystem.ERP,
        kind=DocumentKind.PAYMENT,
        code1c="00БП-010302",
        number="29191",
        date=date(2025, 7, 30),
        amount=Money.of("176168.31"),
        contract_code1c="БП-068417",
        operation_id=362790,
    )
    onec_doc = AccountingDocument(
        source=SourceSystem.ONE_C,
        kind=DocumentKind.PAYMENT,
        code1c="00БП-010302",
        number="29191",
        date=date(2025, 7, 30),
        amount=Money.of("176168.31"),
        contract_code1c="БП-068418",
    )

    issue = match_documents([erp_doc], [onec_doc])[0]

    assert issue.status == ReconciliationStatus.MATCH
    assert issue.match_basis == "document_header"
    assert issue.onec_document is not None
    assert issue.onec_document.contract_code1c == "БП-068418"


def test_missing_operation_invoice_is_a_precondition_error() -> None:
    expected_invoice = AccountingDocument(
        source=SourceSystem.ERP,
        kind=DocumentKind.CUSTOMER_INVOICE,
        code1c="",
        number="",
        date=None,
        amount=Money.of("599.92"),
        contract_code1c="БП-068417",
        operation_id=376754,
    )

    issue = match_documents([expected_invoice], [])[0]

    assert issue.status == ReconciliationStatus.MISSING_ERP_INVOICE
    assert issue.primary_reason == "missing_erp_invoice"


def test_missing_direct_invoice_link_reports_unique_delivery_candidate() -> None:
    expected_invoice = AccountingDocument(
        source=SourceSystem.ERP,
        kind=DocumentKind.CUSTOMER_INVOICE,
        code1c="",
        number="",
        date=None,
        amount=Money.of("5937.54"),
        contract_code1c="БП-078924",
        operation_id=451088,
        related_documents=(
            RelatedDocument(source_id="272946", number="ВЛ-000576", operation_id=457606),
        ),
    )

    issue = match_documents([expected_invoice], [])[0]

    assert issue.status == ReconciliationStatus.MISSING_ERP_INVOICE
    assert issue.primary_reason == "erp_invoice_link_missing_candidate_found"
    assert issue.severity == "warning"
    assert "ВЛ-000576" in issue.message
    assert "457606" in issue.message


def test_missing_operation_closing_document_is_a_precondition_error() -> None:
    expected_sale = AccountingDocument(
        source=SourceSystem.ERP,
        kind=DocumentKind.SALE,
        code1c="",
        number="",
        date=None,
        amount=Money.of("1200.00"),
        contract_code1c="БП-068417",
        operation_id=500001,
    )

    issue = match_documents([expected_sale], [])[0]

    assert issue.status == ReconciliationStatus.MISSING_ERP_CLOSING_DOCUMENT
    assert issue.primary_reason == "missing_erp_closing_document"


def test_missing_onec_document_explains_the_attempted_search_key() -> None:
    erp_document = AccountingDocument(
        source=SourceSystem.ERP,
        kind=DocumentKind.PURCHASE,
        code1c="00БП-019539",
        number="б/н",
        date=date(2024, 11, 2),
        amount=Money.of("103.37", "USD"),
        contract_code1c="БП-055292",
    )

    issue = match_documents([erp_document], [])[0]

    assert issue.status == ReconciliationStatus.NOT_FOUND_IN_1C
    assert issue.primary_reason == "onec_document_absent_by_kind_code_date_and_exact_amount"
    assert issue.fields == ("kind", "code1c", "date", "amount", "currency")


def test_missing_erp_code_is_reported_separately_from_onec_absence() -> None:
    erp_document = AccountingDocument(
        source=SourceSystem.ERP,
        kind=DocumentKind.SALE,
        code1c="",
        number="SNKO042240400038",
        date=date(2024, 4, 29),
        amount=Money.of("5300", "USD"),
        contract_code1c="БП-008928",
        source_id="105434",
    )

    issue = match_documents([erp_document], [])[0]

    assert issue.status == ReconciliationStatus.ERP_CODE1C_MISSING
    assert issue.primary_reason == "erp_code1c_missing_onec_lookup_not_possible"
    assert "erp_code1c" in issue.fields


def test_unmatched_onec_document_means_not_linked_to_selected_delivery() -> None:
    onec_doc = AccountingDocument(
        source=SourceSystem.ONE_C,
        kind=DocumentKind.PAYMENT,
        code1c="00БП-010213",
        number="374",
        date=date(2025, 6, 11),
        amount=Money.of("103953.30", "CNY"),
        contract_code1c="БП-068417",
    )

    issue = match_documents([], [onec_doc])[0]

    assert issue.status == ReconciliationStatus.NOT_LINKED_TO_DELIVERY_IN_ERP
    assert issue.primary_reason == "not_linked_to_delivery_in_erp"


def test_zero_onec_document_is_not_reported_as_globally_missing_in_erp() -> None:
    onec_doc = AccountingDocument(
        source=SourceSystem.ONE_C,
        kind=DocumentKind.PAYMENT,
        code1c="00БП-009994",
        number="00БП-009994",
        date=date(2025, 6, 9),
        amount=Money.of("0.00", "USD"),
        contract_code1c="БП-068417",
    )
    issue = match_documents([], [onec_doc])[0]

    class Repository:
        @staticmethod
        def document_exists_globally(_document: AccountingDocument) -> bool:
            return False

    classified = _classify_global_erp_presence([issue], Repository())

    assert classified[0].status == ReconciliationStatus.NOT_COMPARABLE
    assert classified[0].primary_reason == "zero_amount_onec_document"


def test_onec_document_found_globally_remains_not_linked_to_delivery() -> None:
    onec_doc = AccountingDocument(
        source=SourceSystem.ONE_C,
        kind=DocumentKind.PAYMENT,
        code1c="00БП-010001",
        number="00БП-010001",
        date=date(2025, 6, 9),
        amount=Money.of("12999.20"),
        contract_code1c="БП-068417",
    )
    issue = match_documents([], [onec_doc])[0]

    class Repository:
        @staticmethod
        def document_exists_globally(_document: AccountingDocument) -> bool:
            return True

    classified = _classify_global_erp_presence([issue], Repository())

    assert classified[0].status == ReconciliationStatus.NOT_LINKED_TO_DELIVERY_IN_ERP
    assert classified[0].primary_reason == "erp_document_exists_but_delivery_link_missing"


def test_onec_document_absent_globally_is_reported_missing_in_erp() -> None:
    onec_doc = AccountingDocument(
        source=SourceSystem.ONE_C,
        kind=DocumentKind.PAYMENT,
        code1c="00БП-099999",
        number="00БП-099999",
        date=date(2025, 6, 9),
        amount=Money.of("100.00"),
        contract_code1c="БП-068417",
    )
    issue = match_documents([], [onec_doc])[0]

    class Repository:
        @staticmethod
        def document_exists_globally(_document: AccountingDocument) -> bool:
            return False

    classified = _classify_global_erp_presence([issue], Repository())

    assert classified[0].status == ReconciliationStatus.NOT_FOUND_IN_ERP
    assert classified[0].primary_reason == "onec_document_absent_in_erp_by_kind_code_date"


def test_balance_includes_allocated_lines_on_external_1c_contracts() -> None:
    balances = [
        AccountingBalance(
            contract_code1c="БП-068417",
            opening_debit=Money.of("0"),
            opening_credit=Money.of("0"),
            turnover_debit=Money.of("0"),
            turnover_credit=Money.of("0"),
            closing_debit=Money.of("3327.84"),
            closing_credit=Money.of("0"),
        ),
        AccountingBalance(
            contract_code1c="БП-068418",
            opening_debit=Money.of("0"),
            opening_credit=Money.of("0"),
            turnover_debit=Money.of("0"),
            turnover_credit=Money.of("0"),
            closing_debit=Money.of("2739.06"),
            closing_credit=Money.of("0"),
        ),
    ]

    def external_issue(kind: DocumentKind, amount: str, operation_id: int, basis: str) -> ReconciliationIssue:
        erp = AccountingDocument(
            source=SourceSystem.ERP,
            kind=kind,
            code1c="DOC",
            number="DOC",
            date=date(2025, 7, 30),
            amount=Money.of(amount),
            contract_code1c="БП-068417",
            operation_id=operation_id,
        )
        onec = AccountingDocument(
            source=SourceSystem.ONE_C,
            kind=kind,
            code1c="DOC",
            number="DOC",
            date=date(2025, 7, 30),
            amount=Money.of(amount),
            contract_code1c="БП-013397",
        )
        return ReconciliationIssue(
            status=ReconciliationStatus.CONTRACT_MISMATCH,
            message="contract",
            erp_document=erp,
            onec_document=onec,
            match_basis=basis,
        )

    issues = [
        external_issue(DocumentKind.SALE, "23157.25", 362790, "document_line"),
        external_issue(DocumentKind.PAYMENT, "23157.25", 362790, "payment_allocation"),
        external_issue(DocumentKind.SALE, "599.92", 376754, "document_line"),
    ]

    comparison = compare_balances(Money.of("-6666.82"), balances, ("БП-068417", "БП-068418"), issues)

    assert comparison is not None
    assert comparison.direct_onec_balance.amount == Decimal("-6066.90")
    assert comparison.allocated_adjustment.amount == Decimal("-599.92")
    assert comparison.onec_balance.amount == Decimal("-6666.82")
    assert comparison.difference.amount == Decimal("0.00")
    assert comparison.status == ReconciliationStatus.MATCH


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
        incoming_number="ВА-007704",
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
