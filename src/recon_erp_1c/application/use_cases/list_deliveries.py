from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from recon_erp_1c.application.ports.repositories import ErpReadRepository


@dataclass(frozen=True, slots=True)
class ListDeliveriesCommand:
    spec_id: int | None = None
    client_id: int | None = None
    dog_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    limit: int = 50
    offset: int = 0


class ListDeliveriesUseCase:
    def __init__(self, erp_repository: ErpReadRepository) -> None:
        self.erp_repository = erp_repository

    def execute(self, command: ListDeliveriesCommand) -> list[dict[str, object]]:
        return self.erp_repository.list_deliveries(
            spec_id=command.spec_id,
            client_id=command.client_id,
            dog_id=command.dog_id,
            date_from=command.date_from,
            date_to=command.date_to,
            limit=command.limit,
            offset=command.offset,
        )
