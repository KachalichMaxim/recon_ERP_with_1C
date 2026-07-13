#!/usr/bin/env python3
"""Run one ERP-to-1C delivery reconciliation from configured live sources."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from recon_erp_1c.application.serializers import run_to_dict
from recon_erp_1c.application.use_cases.reconcile_delivery import ReconcileDeliveryCommand, ReconcileDeliveryUseCase
from recon_erp_1c.bootstrap.config import MariaDbConfig
from recon_erp_1c.domain.value_objects import DateRange
from recon_erp_1c.infrastructure.erp_mariadb.connection import MariaDbConnectionFactory
from recon_erp_1c.infrastructure.erp_mariadb.repository import MariaDbErpReadRepository
from recon_erp_1c.infrastructure.export.xlsx import reconciliation_run_xlsx
from recon_erp_1c.infrastructure.onec_rest.client import OneCRestClient
from recon_erp_1c.infrastructure.onec_rest.repository import OneCRestReadRepository
from recon_erp_1c.infrastructure.persistence.mariadb_log_repository import MariaDbReconciliationLogRepository


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec-id", type=int, required=True, help="ERP delivery/specification id")
    parser.add_argument("--date-from", type=date.fromisoformat, required=True, help="Period start, YYYY-MM-DD")
    parser.add_argument("--date-to", type=date.fromisoformat, required=True, help="Period end, YYYY-MM-DD")
    parser.add_argument("--persist-log", action="store_true", help="Save the run to reconciliation log tables")
    parser.add_argument("--json", type=Path, dest="json_path", help="Write the complete canonical result as JSON")
    parser.add_argument("--xlsx", type=Path, dest="xlsx_path", help="Write the reconciliation workbook")
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    if args.spec_id <= 0:
        raise SystemExit("--spec-id must be positive")
    if args.date_from > args.date_to:
        raise SystemExit("--date-from must not be later than --date-to")

    connection_factory = MariaDbConnectionFactory(MariaDbConfig.from_env())
    use_case = ReconcileDeliveryUseCase(
        erp_repository=MariaDbErpReadRepository(connection_factory),
        onec_repository=OneCRestReadRepository(OneCRestClient.from_env()),
        log_repository=MariaDbReconciliationLogRepository(connection_factory) if args.persist_log else None,
    )
    run = use_case.execute(
        ReconcileDeliveryCommand(
            spec_id=args.spec_id,
            period=DateRange(date_from=args.date_from, date_to=args.date_to),
            persist_log=args.persist_log,
        )
    )
    payload = run_to_dict(run)

    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.xlsx_path:
        args.xlsx_path.parent.mkdir(parents=True, exist_ok=True)
        args.xlsx_path.write_bytes(reconciliation_run_xlsx(payload))

    summary = {
        "run_id": payload["run_id"],
        "spec_id": args.spec_id,
        "matched": payload["matched"],
        "by_status": payload["summary"]["by_status"],
        "balance_comparison": payload["balance_comparison"],
        "source_warnings": payload["source_warnings"],
        "metrics": payload["metrics"],
        "json": str(args.json_path) if args.json_path else None,
        "xlsx": str(args.xlsx_path) if args.xlsx_path else None,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if payload["matched"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
