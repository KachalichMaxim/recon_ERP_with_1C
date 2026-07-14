from __future__ import annotations

from datetime import date

from recon_erp_1c.infrastructure.erp_mariadb import queries
from recon_erp_1c.infrastructure.erp_mariadb.repository import MariaDbErpReadRepository


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
    )

    assert repository.last_query == queries.SEARCH_DELIVERIES
    assert "view_specs" not in repository.last_query.lower()
    assert repository.last_params["query_like"] == "%660/1/1051%"
    assert repository.last_params["client_id"] == 221
    assert repository.last_params["dog_id"] == 88
    assert result[0]["spec_type_name"] == "Заявка"


def test_short_text_delivery_search_does_not_hit_database() -> None:
    repository = _SearchRepository([_row()])

    assert repository.search_deliveries("AB") == []
    assert repository.last_query == ""
