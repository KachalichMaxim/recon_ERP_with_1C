#!/usr/bin/env python3
"""Run a reproducible random ERP-to-1C reconciliation sample."""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

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
from recon_erp_1c.infrastructure.onec_rest.client import OneCRestClient
from recon_erp_1c.infrastructure.onec_rest.repository import OneCRestReadRepository
from recon_erp_1c.infrastructure.persistence.mariadb_log_repository import MariaDbReconciliationLogRepository


ERP_DATA_STATUSES = {"missing_erp_invoice", "missing_erp_closing_document"}
NON_BLOCKING_STATUSES = {"match", "not_comparable"}


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20260714)
    parser.add_argument("--delivery-date-from", type=date.fromisoformat, required=True)
    parser.add_argument("--delivery-date-to", type=date.fromisoformat, required=True)
    parser.add_argument("--document-date-from", type=date.fromisoformat, required=True)
    parser.add_argument("--document-date-to", type=date.fromisoformat, required=True)
    parser.add_argument("--exclude-spec-id", type=int, action="append", default=[])
    parser.add_argument("--closed-only", action="store_true")
    parser.add_argument("--persist-log", action="store_true")
    parser.add_argument("--json", type=Path, dest="json_path", required=True)
    parser.add_argument("--markdown", type=Path, dest="markdown_path", required=True)
    return parser.parse_args()


def _meaningful_code(value: object) -> bool:
    return str(value or "").strip() not in {"", "_", "-", "0"}


def _load_population(
    repository: MariaDbErpReadRepository,
    *,
    date_from: date,
    date_to: date,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    offset = 0
    page_size = 1000
    while True:
        page = repository.list_deliveries(
            date_from=date_from,
            date_to=date_to,
            limit=page_size,
            offset=offset,
        )
        rows.extend(page)
        if len(page) < page_size:
            return rows
        offset += len(page)


def _issue_summary(row: dict[str, Any]) -> dict[str, Any]:
    erp = row.get("erp_document") if isinstance(row.get("erp_document"), dict) else {}
    onec = row.get("onec_document") if isinstance(row.get("onec_document"), dict) else {}
    return {
        "status": row.get("status"),
        "message": row.get("message"),
        "fields": row.get("fields") or [],
        "primary_reason": row.get("primary_reason"),
        "match_basis": row.get("match_basis"),
        "erp": _document_summary(erp),
        "onec": _document_summary(onec),
    }


def _document_summary(document: dict[str, Any]) -> dict[str, Any]:
    amount = document.get("amount") if isinstance(document.get("amount"), dict) else {}
    return {
        "kind": document.get("kind"),
        "code1c": document.get("code1c"),
        "number": document.get("number"),
        "date": document.get("date"),
        "amount": amount.get("amount"),
        "currency": amount.get("currency"),
        "contract_code1c": document.get("contract_code1c"),
        "operation_id": document.get("operation_id"),
        "source_id": document.get("source_id"),
        "vat_rate": document.get("vat_rate"),
        "tax_invoice_number": document.get("tax_invoice_number"),
        "tax_invoice_date": document.get("tax_invoice_date"),
    }


def _run_result(metadata: dict[str, object], payload: dict[str, Any]) -> dict[str, Any]:
    issues = payload.get("issues") if isinstance(payload.get("issues"), list) else []
    statuses = Counter(str(row.get("status") or "unknown") for row in issues if isinstance(row, dict))
    comparison = payload.get("balance_comparison") if isinstance(payload.get("balance_comparison"), dict) else {}
    difference = comparison.get("difference") if isinstance(comparison.get("difference"), dict) else {}
    non_match_statuses = {status for status, count in statuses.items() if count and status not in NON_BLOCKING_STATUSES}
    if str(comparison.get("status") or "") != "match":
        classification = "erp_1c_mismatch"
    elif not non_match_statuses:
        classification = "ok"
    elif non_match_statuses.issubset(ERP_DATA_STATUSES):
        classification = "erp_data_issues"
    else:
        classification = "erp_1c_mismatch"

    onec_sales: dict[tuple[str, str], dict[str, Any]] = {}
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        document = issue.get("onec_document")
        if not isinstance(document, dict) or str(document.get("kind") or "") != "sale":
            continue
        key = (str(document.get("source_id") or ""), str(document.get("number") or document.get("code1c") or ""))
        onec_sales[key] = document

    return {
        **metadata,
        "run_id": payload.get("run_id"),
        "classification": classification,
        "matched": bool(payload.get("matched")),
        "status_counts": dict(sorted(statuses.items())),
        "balance_status": comparison.get("status"),
        "erp_balance": _money_amount(comparison.get("erp_balance")),
        "onec_balance": _money_amount(comparison.get("onec_balance")),
        "balance_difference": str(difference.get("amount") or "") if difference else "",
        "metrics": payload.get("metrics") or {},
        "source_warnings": payload.get("source_warnings") or [],
        "onec_sales": len(onec_sales),
        "onec_sales_with_tax_invoice": sum(1 for document in onec_sales.values() if document.get("tax_invoice_number")),
        "issues": [_issue_summary(row) for row in issues if isinstance(row, dict)],
    }


def _money_amount(value: object) -> str:
    if not isinstance(value, dict):
        return ""
    return str(value.get("amount") or "")


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * percentile + 0.999999)))
    return round(ordered[index], 2)


def _aggregate(results: list[dict[str, Any]], errors: list[dict[str, Any]]) -> dict[str, Any]:
    classifications = Counter(str(row.get("classification") or "unknown") for row in results)
    statuses: Counter[str] = Counter()
    for row in results:
        statuses.update({str(key): int(value) for key, value in (row.get("status_counts") or {}).items()})
    total_times = [float((row.get("metrics") or {}).get("total_ms") or 0) for row in results]
    erp_times = [float((row.get("metrics") or {}).get("erp_read_ms") or 0) for row in results]
    onec_times = [float((row.get("metrics") or {}).get("onec_rest_ms") or 0) for row in results]
    return {
        "completed": len(results),
        "technical_errors": len(errors),
        "classifications": dict(sorted(classifications.items())),
        "status_counts": dict(sorted(statuses.items())),
        "balance_matches": sum(1 for row in results if row.get("balance_status") == "match"),
        "balance_mismatches": sum(1 for row in results if row.get("balance_status") != "match"),
        "onec_sales": sum(int(row.get("onec_sales") or 0) for row in results),
        "onec_sales_with_tax_invoice": sum(int(row.get("onec_sales_with_tax_invoice") or 0) for row in results),
        "performance_ms": {
            "total_p50": round(statistics.median(total_times), 2) if total_times else 0,
            "total_p95": _percentile(total_times, 0.95),
            "erp_p50": round(statistics.median(erp_times), 2) if erp_times else 0,
            "erp_p95": _percentile(erp_times, 0.95),
            "onec_p50": round(statistics.median(onec_times), 2) if onec_times else 0,
            "onec_p95": _percentile(onec_times, 0.95),
        },
    }


def _markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    config = report["config"]
    lines = [
        "# E2E ERP–1С: воспроизводимая случайная выборка",
        "",
        f"Дата запуска: `{report['generated_at']}`  ",
        f"Seed: `{config['seed']}`  ",
        f"Период поставок: `{config['delivery_date_from']}..{config['delivery_date_to']}`  ",
        f"Период документов: `{config['document_date_from']}..{config['document_date_to']}`  ",
        f"Популяция после критериев: `{report['population']['eligible']}`; выбрано: `{len(report['sample'])}`.",
        "",
        "## Итог",
        "",
        f"- Выполнено: **{summary['completed']}**, технических ошибок: **{summary['technical_errors']}**.",
        f"- Сальдо совпало: **{summary['balance_matches']}**, разошлось: **{summary['balance_mismatches']}**.",
        f"- Классификация: `{json.dumps(summary['classifications'], ensure_ascii=False)}`.",
        f"- Статусы документов: `{json.dumps(summary['status_counts'], ensure_ascii=False)}`.",
        f"- Реализаций 1С со счетом-фактурой: **{summary['onec_sales_with_tax_invoice']} из {summary['onec_sales']}**.",
        f"- Время p50/p95: **{summary['performance_ms']['total_p50']} / {summary['performance_ms']['total_p95']} мс**.",
        "",
        "## Поставки",
        "",
        "| # | spec_id | Поставка | Тип | Клиент | Базовый договор | Результат | Статусы | ERP сальдо | 1С сальдо | Δ | Время, мс |",
        "|---:|---:|---|---|---|---|---|---|---:|---:|---:|---:|",
    ]
    for index, row in enumerate(report["sample"], start=1):
        lines.append(
            "| {index} | {spec_id} | {spec_number} | {spec_type} | {client} | {contract} | {classification} | {statuses} | {erp} | {onec} | {difference} | {time} |".format(
                index=index,
                spec_id=row.get("spec_id") or "",
                spec_number=_md(row.get("spec_number")),
                spec_type=_md(row.get("spec_type_name")),
                client=_md(row.get("client_name")),
                contract=_md(row.get("base_contract_number")),
                classification=row.get("classification") or "technical_error",
                statuses=_md(json.dumps(row.get("status_counts") or {}, ensure_ascii=False)),
                erp=row.get("erp_balance") or "",
                onec=row.get("onec_balance") or "",
                difference=row.get("balance_difference") or "",
                time=(row.get("metrics") or {}).get("total_ms") or "",
            )
        )
    if report["errors"]:
        lines.extend(["", "## Технические ошибки", ""])
        for row in report["errors"]:
            lines.append(f"- `spec_id={row['spec_id']}`: `{row['type']}` — {_md(row['message'])}")
    lines.extend(
        [
            "",
            "## Критерии выборки",
            "",
            "1. Поставка находится в заданном периоде.",
            "2. В ERP заполнен код договора с покупателем `veda_specs.f_kod1cb`.",
            "3. При `closed_only=true` заполнена дата закрытия `veda_specs.f_dtclose`.",
            "4. Из выборки исключены явно перечисленные контрольные `spec_id`.",
            "5. Выбор выполняется `random.sample` с зафиксированным seed; список `spec_id` сохранен в JSON.",
            "6. Каждый элемент проходит полный production pipeline чтения ERP MariaDB и 1С REST без подмены источников.",
            "",
        ]
    )
    return "\n".join(lines)


def _md(value: object) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def main() -> int:
    args = _arguments()
    if args.sample_size < 1:
        raise SystemExit("--sample-size must be positive")
    if args.delivery_date_from > args.delivery_date_to or args.document_date_from > args.document_date_to:
        raise SystemExit("date_from must not be later than date_to")

    factory = MariaDbConnectionFactory(MariaDbConfig.from_env())
    erp_repository = MariaDbErpReadRepository(factory)
    population = _load_population(
        erp_repository,
        date_from=args.delivery_date_from,
        date_to=args.delivery_date_to,
    )
    excluded = set(args.exclude_spec_id)
    eligible = [
        row
        for row in population
        if int(row.get("spec_id") or 0) not in excluded
        and _meaningful_code(row.get("buyer_contract_code"))
        and (not args.closed_only or bool(str(row.get("closure_date") or "").strip()))
    ]
    if len(eligible) < args.sample_size:
        raise SystemExit(f"eligible population {len(eligible)} is smaller than sample {args.sample_size}")

    selected = random.Random(args.seed).sample(eligible, args.sample_size)
    use_case = ReconcileDeliveryUseCase(
        erp_repository=erp_repository,
        onec_repository=OneCRestReadRepository(OneCRestClient.from_env()),
        log_repository=MariaDbReconciliationLogRepository(factory) if args.persist_log else None,
    )
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    period = DateRange(args.document_date_from, args.document_date_to)
    started = perf_counter()

    for index, metadata in enumerate(selected, start=1):
        spec_id = int(metadata.get("spec_id") or 0)
        print(f"[{index}/{len(selected)}] spec_id={spec_id}", file=sys.stderr, flush=True)
        try:
            run = use_case.execute(
                ReconcileDeliveryCommand(spec_id=spec_id, period=period, persist_log=args.persist_log)
            )
            results.append(_run_result(metadata, run_to_dict(run)))
        except Exception as exc:  # noqa: BLE001 - the sample must continue after one failed delivery
            errors.append(
                {
                    **metadata,
                    "spec_id": spec_id,
                    "classification": "technical_error",
                    "type": exc.__class__.__name__,
                    "message": str(exc),
                }
            )

    result_by_spec = {int(row["spec_id"]): row for row in results}
    error_by_spec = {int(row["spec_id"]): row for row in errors}
    ordered_sample = [result_by_spec.get(int(row["spec_id"])) or error_by_spec[int(row["spec_id"])] for row in selected]
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "config": {
            "sample_size": args.sample_size,
            "seed": args.seed,
            "delivery_date_from": args.delivery_date_from.isoformat(),
            "delivery_date_to": args.delivery_date_to.isoformat(),
            "document_date_from": args.document_date_from.isoformat(),
            "document_date_to": args.document_date_to.isoformat(),
            "excluded_spec_ids": sorted(excluded),
            "closed_only": args.closed_only,
            "persist_log": args.persist_log,
        },
        "population": {
            "all_in_period": len(population),
            "eligible": len(eligible),
            "criteria": "meaningful veda_specs.f_kod1cb"
            + (" and non-empty veda_specs.f_dtclose" if args.closed_only else ""),
        },
        "summary": {
            **_aggregate(results, errors),
            "wall_time_ms": round((perf_counter() - started) * 1000, 2),
        },
        "sample_spec_ids": [int(row["spec_id"]) for row in selected],
        "sample": ordered_sample,
        "errors": errors,
    }
    args.json_path.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_path.parent.mkdir(parents=True, exist_ok=True)
    args.json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    args.markdown_path.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps({"summary": report["summary"], "json": str(args.json_path), "markdown": str(args.markdown_path)}, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
