from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

from openpyxl import load_workbook

from recon_erp_1c.infrastructure.export.xlsx import reconciliation_matrix_xlsx, reconciliation_run_xlsx
from recon_erp_1c.interfaces.http.auth import create_session_token, verify_session_token


def test_session_token_roundtrip() -> None:
    token = create_session_token({"user_id": 7, "login": "user@example.com", "name": "User Name"})

    payload = verify_session_token(token)

    assert payload is not None
    assert payload["sub"] == "7"
    assert payload["email"] == "user@example.com"
    assert payload["name"] == "User Name"


def test_reconciliation_xlsx_is_valid_zip_package() -> None:
    raw = reconciliation_run_xlsx(
        {
            "run_id": "test",
            "created_at": "2026-07-02T00:00:00",
            "delivery": {
                "erp_spec_id": 20334,
                "spec_number": "921",
                "base_contract_number": "660/1",
                "contract_codes": {"buyer_contract_code": "БП-051945", "committent_contract_code": "БП-051946"},
            },
            "summary": {"issues_total": 1},
            "issues": [
                {
                    "status": "match",
                    "message": "Документ совпал",
                    "fields": [],
                    "erp_document": {
                        "kind": "payment",
                        "code1c": "00БП-010299",
                        "number": "29195",
                        "date": "2025-07-30",
                        "amount": {"amount": "442296.92", "currency": "RUB"},
                    },
                    "onec_document": {
                        "kind": "payment",
                        "code1c": "00БП-010299",
                        "number": "29195",
                        "date": "2025-07-30",
                        "amount": {"amount": "442296.92", "currency": "RUB"},
                    },
                }
            ],
        }
    )

    with ZipFile(BytesIO(raw)) as workbook:
        names = set(workbook.namelist())

    assert "[Content_Types].xml" in names
    assert "xl/workbook.xml" in names
    assert "xl/worksheets/sheet1.xml" in names


def test_matrix_xlsx_is_valid_zip_package() -> None:
    raw = reconciliation_matrix_xlsx(
        {
            "mode": "test",
            "summary": {"deliveries": 1, "balance": "-100.00"},
            "items": [
                {
                    "spec_id": 20334,
                    "spec_number": "921",
                    "client_id": 221,
                    "client_name": "ООО АЭРО-ТРЕЙД",
                    "dog_id": 88,
                    "base_contract_number": "660/1",
                    "invoice_numbers": ["ВА-015695", "ВА-015696"],
                    "sf_numbers": ["00БП-000198"],
                    "invoice_sum": "100.00",
                    "payment_sum": "50.00",
                    "reimbursable_sum": "100.00",
                    "non_reimbursable_sum": "50.00",
                    "balance": "-100.00",
                    "balance_label": "Долг",
                }
            ],
        }
    )

    with ZipFile(BytesIO(raw)) as workbook:
        names = set(workbook.namelist())
        workbook_xml = workbook.read("xl/workbook.xml").decode("utf-8")
        export_sheet_xml = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")

    assert "[Content_Types].xml" in names
    assert "xl/workbook.xml" in names
    assert "xl/worksheets/sheet1.xml" in names
    assert "Выгрузка" in workbook_xml
    assert "Правила" in workbook_xml
    assert "<mergeCells" in export_sheet_xml
    assert '<mergeCell ref="A2:A' in export_sheet_xml

    parsed = load_workbook(BytesIO(raw))
    ws = parsed["Выгрузка"]
    assert ws.max_row > 1
    assert ws["A1"].value == "№ спецификации"
    assert ws["A2"].value == "Поставка №921"
