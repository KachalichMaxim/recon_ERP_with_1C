from __future__ import annotations

from datetime import date
from decimal import Decimal

from recon_erp_1c.application.use_cases.reconcile_delivery import aggregate_documents, compare_balances, match_documents
from recon_erp_1c.domain.entities import (
    AccountingBalance,
    AccountingDocument,
    DocumentLine,
    PaymentAllocation,
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
