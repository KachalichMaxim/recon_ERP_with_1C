from __future__ import annotations

from datetime import date

from recon_erp_1c.infrastructure.erp_mariadb import queries
from recon_erp_1c.infrastructure.erp_mariadb.repository import MariaDbErpReadRepository, _prefer_aggregate_closing_rows
from recon_erp_1c.interfaces.http import api


class _SearchRepository(MariaDbErpReadRepository):
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.last_query = ""
        self.last_params: dict[str, object] = {}

    def _fetch_all(self, query: str, params: dict[str, object]) -> list[dict[str, object]]:
        self.last_query = query
        self.last_params = params
        return self.rows


def _row() -> dict[str, object]:
    return {
        "spec_id": 20334,
        "spec_number": "1051",
        "spec_type_name": "Заявка",
        "spec_date": date(2025, 7, 30),
        "client_handover_date": date(2025, 8, 1),
        "dog_id": 88,
        "base_contract_number": "660/1",
        "organization_abbr": "ВА",
        "client_id": 221,
        "client_name": "АЭРО-ТРЕЙД",
        "client_inn": "7811451960",
        "delivery_full_name": "660/1/1051/ВА/АЭРО-ТРЕЙД",
    }


def test_numeric_delivery_search_uses_primary_spec_id_query() -> None:
    repository = _SearchRepository([_row()])

    result = repository.search_deliveries("20334", limit=12)

    assert repository.last_query == queries.SEARCH_DELIVERY_BY_ID
    assert repository.last_params["spec_id"] == 20334
    assert result[0]["delivery_full_name"] == "660/1/1051/ВА/АЭРО-ТРЕЙД"


def test_full_delivery_name_search_uses_source_tables_and_context_filters() -> None:
    repository = _SearchRepository([_row()])

    result = repository.search_deliveries(
        "660/1/1051",
        client_id=221,
        dog_id=88,
        date_from=date(2025, 1, 1),
        date_to=date(2025, 12, 31),
        client_handover_from=date(2025, 7, 1),
        client_handover_to=date(2025, 8, 31),
    )

    assert repository.last_query == queries.SEARCH_DELIVERIES
    assert "view_specs" not in repository.last_query.lower()
    assert repository.last_params["query_like"] == "%660/1/1051%"
    assert repository.last_params["client_id"] == 221
    assert repository.last_params["dog_id"] == 88
    assert repository.last_params["client_handover_from"] == date(2025, 7, 1)
    assert repository.last_params["client_handover_to"] == date(2025, 8, 31)
    assert result[0]["client_handover_date"] == "2025-08-01"
    assert result[0]["spec_type_name"] == "Заявка"


def test_short_text_delivery_search_does_not_hit_database() -> None:
    repository = _SearchRepository([_row()])

    assert repository.search_deliveries("AB") == []
    assert repository.last_query == ""


def test_exact_delivery_matrix_reuses_page_summary_for_total(monkeypatch) -> None:
    class _MatrixRepository:
        def count_deliveries(self, **_kwargs: object) -> int:
            return 1

        def matrix_total_summary(self, **_kwargs: object) -> dict[str, object]:
            raise AssertionError("Exact spec matrix must not run the all-deliveries summary query")

        def list_deliveries(self, **_kwargs: object) -> list[dict[str, object]]:
            return [{**_row(), "buyer_contract_code": "", "committent_contract_code": ""}]

        def list_documents_and_calculations_for_deliveries(
            self, _spec_ids: list[int]
        ) -> tuple[dict[int, list[object]], dict[int, dict[str, str]]]:
            return {20334: []}, {
                20334: {
                    "payment_sum": "100.00",
                    "reimbursable_sum": "40.00",
                    "non_reimbursable_sum": "10.00",
                    "balance": "50.00",
                }
            }

    monkeypatch.setattr(api, "_erp_repository", lambda: _MatrixRepository())

    payload = api._matrix_payload({"spec_id": ["20334"], "include_total": ["1"]})

    assert payload["total_count"] == 1
    assert payload["total_summary"] == payload["page_summary"]


def test_aggregate_closing_document_hides_children_for_same_operation_and_kind() -> None:
    rows = [
        {"operation_id": 418878, "document_kind": "sale", "source_id": 201378, "is_aggregate": 0},
        {"operation_id": 418878, "document_kind": "sale", "source_id": 201510, "is_aggregate": 1},
        {"operation_id": 418878, "document_kind": "purchase", "source_id": 201511, "is_aggregate": 0},
        {"operation_id": 500000, "document_kind": "sale", "source_id": 201512, "is_aggregate": 0},
    ]

    selected = _prefer_aggregate_closing_rows(rows)

    assert [row["source_id"] for row in selected] == [201510, 201511, 201512]
