from __future__ import annotations

from datetime import date
from typing import Protocol

from recon_erp_1c.domain.entities import AccountingDocument, Contract, Delivery, OneCSnapshot, ReconciliationRun
from recon_erp_1c.domain.value_objects import Money
from recon_erp_1c.domain.value_objects import DateRange


class ErpReadRepository(Protocol):
    def list_deliveries(
        self,
        *,
        spec_id: int | None = None,
        client_id: int | None = None,
        dog_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, object]]:
        ...

    def get_delivery(self, spec_id: int) -> Delivery:
        ...

    def list_delivery_documents(self, spec_id: int) -> list[AccountingDocument]:
        ...

    def get_delivery_documents_and_balance(self, spec_id: int) -> tuple[list[AccountingDocument], Money]:
        ...

    def list_delivery_contracts(self, spec_id: int) -> list[Contract]:
        ...

    def get_delivery_balance(self, spec_id: int) -> Money:
        ...

    def document_exists_globally(self, document: AccountingDocument) -> bool:
        ...


class OneCReadRepository(Protocol):
    def fetch_snapshot(
        self,
        *,
        delivery: Delivery,
        period: DateRange,
        contracts: list[Contract],
        erp_documents: list[AccountingDocument],
    ) -> OneCSnapshot:
        ...


class ReconciliationLogRepository(Protocol):
    def save_run(self, run: ReconciliationRun) -> None:
        ...
