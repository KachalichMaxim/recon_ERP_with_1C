from __future__ import annotations

import json
import os
from decimal import Decimal
from pathlib import Path
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from recon_erp_1c.application.serializers import run_to_dict
from recon_erp_1c.application.use_cases.list_deliveries import ListDeliveriesCommand, ListDeliveriesUseCase
from recon_erp_1c.application.use_cases.reconcile_delivery import ReconcileDeliveryCommand, ReconcileDeliveryUseCase
from recon_erp_1c.bootstrap.config import AppConfig
from recon_erp_1c.domain.entities import AccountingDocument
from recon_erp_1c.domain.value_objects import DateRange, DocumentKind
from recon_erp_1c.infrastructure.erp_mariadb.connection import MariaDbConnectionFactory
from recon_erp_1c.infrastructure.erp_mariadb.repository import ErpDataNotFound, MariaDbErpReadRepository
from recon_erp_1c.infrastructure.export.xlsx import reconciliation_matrix_xlsx, reconciliation_run_xlsx
from recon_erp_1c.infrastructure.onec_rest.client import OneCRestClient, OneCRestConfig, onec_rest_status
from recon_erp_1c.infrastructure.onec_rest.repository import OneCRestReadRepository
from recon_erp_1c.infrastructure.persistence.mariadb_log_repository import MariaDbReconciliationLogRepository
from recon_erp_1c.interfaces.http.auth import AuthenticationError, create_session_token, request_context


def _app_config() -> AppConfig:
    return AppConfig.from_env()


class ReconciliationHttpHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        try:
            if parsed.path in {"/", "/reconciliation.html", "/reconciliation.css", "/reconciliation.js"}:
                self._static(parsed.path)
                return
            if parsed.path == "/health":
                self._health()
                return
            if parsed.path == "/api/config/status":
                self._config_status()
                return
            if parsed.path == "/api/auth/me":
                self._auth_me()
                return
            if parsed.path == "/api/reconciliation/specifications":
                self._list_specifications(query)
                return
            if parsed.path == "/api/reconciliation/clients":
                self._search_clients(query)
                return
            if parsed.path == "/api/reconciliation/matrix":
                self._list_matrix(query)
                return
            if parsed.path == "/api/reconciliation/matrix.xlsx":
                self._matrix_xlsx(query)
                return
            if parsed.path == "/api/reconciliation/run":
                self._run_reconciliation(query)
                return
            if parsed.path == "/api/reconciliation/run.xlsx":
                self._run_reconciliation_xlsx(query)
                return
            self._json(
                HTTPStatus.NOT_FOUND,
                {
                    "ok": False,
                    "error": "not_found",
                    "message": "Unknown endpoint",
                },
            )
        except AuthenticationError as exc:
            self._json(exc.status, {"ok": False, "error": "unauthorized", "message": str(exc)})
        except ValueError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "bad_request", "message": str(exc)})
        except ErpDataNotFound as exc:
            self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "erp_not_found", "message": str(exc)})
        except RuntimeError as exc:
            self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"ok": False, "error": "service_unavailable", "message": str(exc)})

    def do_POST(self) -> None:  # noqa: N802 - stdlib callback name
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/auth/login":
                self._login()
                return
            if parsed.path == "/api/reconciliation/run":
                payload = self._json_body()
                query = {key: [str(value)] for key, value in payload.items() if value is not None}
                self._run_reconciliation(query)
                return
            if parsed.path == "/api/reconciliation/run.xlsx":
                payload = self._json_body()
                run_payload = payload.get("run") if isinstance(payload.get("run"), dict) else payload
                self._run_payload_xlsx(run_payload)
                return
            if parsed.path == "/api/reconciliation/matrix.xlsx":
                payload = self._json_body()
                matrix_payload = payload.get("matrix") if isinstance(payload.get("matrix"), dict) else payload
                self._matrix_payload_xlsx(matrix_payload)
                return
            self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found", "message": "Unknown endpoint"})
        except AuthenticationError as exc:
            self._json(exc.status, {"ok": False, "error": "unauthorized", "message": str(exc)})
        except ValueError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "bad_request", "message": str(exc)})
        except RuntimeError as exc:
            self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"ok": False, "error": "service_unavailable", "message": str(exc)})

    def _health(self) -> None:
        config = _app_config()
        self._json(
            HTTPStatus.OK,
            {
                "ok": True,
                "service": "recon-erp-1c",
                "architecture": "clean-architecture-ddd",
                "erp_db_configured": config.erp_db.configured,
                "onec_rest_configured": onec_rest_status()["configured"],
                "auth": {
                    "mode": "erp_token_passthrough_or_direct_erp_login",
                    "required": config.require_erp_token,
                },
            },
        )

    def _config_status(self) -> None:
        config = _app_config()
        self._json(
            HTTPStatus.OK,
            {
                "ok": True,
                "erp_db": config.erp_db.safe_status(),
                "onec_rest": onec_rest_status(),
                "auth": {
                    "mode": "erp_token_passthrough_or_direct_erp_login",
                    "required": config.require_erp_token,
                },
            },
        )

    def _login(self) -> None:
        payload = self._json_body()
        login = str(payload.get("login") or payload.get("username") or "").strip()
        password = str(payload.get("password") or "")
        if not login or not password:
            raise ValueError("login and password are required")
        dev_profile = _dev_auth_profile(login, password)
        if dev_profile is not None:
            token = create_session_token(dev_profile)
            self._json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "token": token,
                    "profile": {
                        "user_id": dev_profile.get("user_id"),
                        "login": dev_profile.get("login"),
                        "name": dev_profile.get("name"),
                        "structure_code": dev_profile.get("structure_code"),
                    },
                },
            )
            return
        profile = _erp_repository().authenticate_user(login, password)
        if profile is None:
            raise AuthenticationError("Invalid ERP login or password")
        token = create_session_token(profile)
        self._json(
            HTTPStatus.OK,
            {
                "ok": True,
                "token": token,
                "profile": {
                    "user_id": profile.get("user_id"),
                    "login": profile.get("login"),
                    "name": profile.get("name"),
                    "structure_code": profile.get("structure_code"),
                },
            },
        )

    def _auth_me(self) -> None:
        context = self._require_context()
        self._json(
            HTTPStatus.OK,
            {
                "ok": True,
                "profile": {
                    "user_id": context.user_id,
                    "login": context.user_email,
                    "name": context.user_name,
                    "auth_source": context.auth_source,
                },
            },
        )

    def _list_specifications(self, query: dict[str, list[str]]) -> None:
        self._require_context()
        repository = _erp_repository()
        command = ListDeliveriesCommand(
            client_id=_optional_int(query, "client_id"),
            dog_id=_optional_int(query, "dog_id"),
            date_from=_optional_date(query, "date_from"),
            date_to=_optional_date(query, "date_to"),
            limit=_optional_int(query, "limit") or 50,
            offset=_optional_int(query, "offset") or 0,
        )
        deliveries = ListDeliveriesUseCase(repository).execute(command)
        self._json(HTTPStatus.OK, {"ok": True, "items": deliveries, "count": len(deliveries)})

    def _list_matrix(self, query: dict[str, list[str]]) -> None:
        self._require_context()
        self._json(HTTPStatus.OK, _matrix_payload(query))

    def _search_clients(self, query: dict[str, list[str]]) -> None:
        self._require_context()
        text = (query.get("q") or [""])[0].strip()
        limit = max(1, min(_optional_int(query, "limit") or 12, 30))
        if len(text) < 3:
            self._json(HTTPStatus.OK, {"ok": True, "items": [], "count": 0, "min_query_length": 3})
            return
        if os.environ.get("RECON_UI_DEMO", "").strip() == "1":
            items = _demo_client_search(text, limit)
        else:
            items = _erp_repository().search_clients(text, limit=limit)
        self._json(HTTPStatus.OK, {"ok": True, "items": items, "count": len(items), "min_query_length": 3})

    def _run_reconciliation(self, query: dict[str, list[str]]) -> None:
        self._require_context()
        run = _execute_reconciliation(query)
        self._json(HTTPStatus.OK, {"ok": True, "run": run_to_dict(run)})

    def _run_reconciliation_xlsx(self, query: dict[str, list[str]]) -> None:
        self._require_context()
        run = _execute_reconciliation(query, default_persist_log=False)
        payload = run_to_dict(run)
        self._run_payload_xlsx(payload)

    def _run_payload_xlsx(self, payload: dict[str, object]) -> None:
        self._require_context()
        if not isinstance(payload, dict) or not isinstance(payload.get("delivery"), dict):
            raise ValueError("run payload is required")
        body = reconciliation_run_xlsx(payload)
        delivery = payload["delivery"]
        filename = f"reconciliation-spec-{delivery.get('erp_spec_id') or 'run'}.xlsx"
        self._bytes(
            HTTPStatus.OK,
            body,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=filename,
        )

    def _matrix_xlsx(self, query: dict[str, list[str]]) -> None:
        self._require_context()
        payload = _matrix_payload(query)
        self._matrix_payload_xlsx(payload)

    def _matrix_payload_xlsx(self, payload: dict[str, object]) -> None:
        self._require_context()
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            raise ValueError("matrix payload is required")
        body = reconciliation_matrix_xlsx(payload)
        self._bytes(
            HTTPStatus.OK,
            body,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="akt-sverki-matrix.xlsx",
        )

    def _require_context(self):
        config = _app_config()
        return request_context(self.headers, require_token=config.require_erp_token)

    def _json_body(self) -> dict[str, object]:
        raw_len = int(self.headers.get("Content-Length", "0") or "0")
        if raw_len <= 0:
            return {}
        raw = self.rfile.read(raw_len).decode("utf-8")
        try:
            parsed = json.loads(raw or "{}")
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON body") from exc
        if not isinstance(parsed, dict):
            raise ValueError("JSON body must be an object")
        return parsed

    def _static(self, path: str) -> None:
        web_root = Path(__file__).resolve().parents[1] / "web"
        names = {
            "/": "reconciliation.html",
            "/reconciliation.html": "reconciliation.html",
            "/reconciliation.css": "reconciliation.css",
            "/reconciliation.js": "reconciliation.js",
        }
        name = names[path]
        file_path = web_root / name
        if not file_path.exists():
            self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found", "message": "Static file not found"})
            return
        body = file_path.read_bytes()
        content_type = _static_content_type(name)
        self._bytes(HTTPStatus.OK, body, content_type=content_type)

    def _bytes(self, status: HTTPStatus, body: bytes, *, content_type: str, filename: str | None = None) -> None:
        self.send_response(status.value)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _execute_reconciliation(query: dict[str, list[str]], *, default_persist_log: bool = True):
    spec_id = _required_int(query, "spec_id")
    date_from = _required_date(query, "date_from")
    date_to = _required_date(query, "date_to")
    persist_log = _optional_bool(query, "persist_log", default=default_persist_log)
    erp_repository = _erp_repository()
    connection_factory = _connection_factory()
    use_case = ReconcileDeliveryUseCase(
        erp_repository=erp_repository,
        onec_repository=OneCRestReadRepository(OneCRestClient(OneCRestConfig.from_env())),
        log_repository=MariaDbReconciliationLogRepository(connection_factory) if persist_log else None,
    )
    run = use_case.execute(
        ReconcileDeliveryCommand(
            spec_id=spec_id,
            period=DateRange(date_from=date_from, date_to=date_to),
            persist_log=persist_log,
        )
    )
    return run


def _matrix_payload(query: dict[str, list[str]]) -> dict[str, object]:
    if os.environ.get("RECON_UI_DEMO", "").strip() == "1":
        return _demo_matrix_payload()
    repository = _erp_repository()
    limit = max(1, min(_optional_int(query, "limit") or 20, 100))
    command = ListDeliveriesCommand(
        client_id=_optional_int(query, "client_id"),
        dog_id=_optional_int(query, "dog_id"),
        date_from=_optional_date(query, "date_from"),
        date_to=_optional_date(query, "date_to"),
        limit=limit,
        offset=_optional_int(query, "offset") or 0,
    )
    deliveries = ListDeliveriesUseCase(repository).execute(command)
    items = [_matrix_row(repository, delivery) for delivery in deliveries]
    return {
        "ok": True,
        "mode": "erp_live",
        "items": items,
        "count": len(items),
        "summary": _matrix_summary(items),
        "limit": limit,
    }


def _matrix_row(repository: MariaDbErpReadRepository, delivery_row: dict[str, object]) -> dict[str, object]:
    spec_id = int(delivery_row["spec_id"] or 0)
    documents = repository.list_delivery_documents(spec_id)
    buyer_code = str(delivery_row.get("buyer_contract_code") or "")
    invoices = [doc for doc in documents if doc.kind == DocumentKind.CUSTOMER_INVOICE]
    payments = [doc for doc in documents if doc.kind == DocumentKind.PAYMENT]
    sales = [doc for doc in documents if doc.kind == DocumentKind.SALE]
    non_reimbursable = [doc for doc in sales if buyer_code and doc.contract_code1c == buyer_code]
    reimbursable = [doc for doc in sales if doc not in non_reimbursable]
    invoice_sum = _sum_docs(invoices)
    payment_sum = _sum_docs(payments)
    reimbursable_sum = _sum_docs(reimbursable)
    non_reimbursable_sum = _sum_docs(non_reimbursable)
    balance = payment_sum - reimbursable_sum - non_reimbursable_sum
    return {
        **delivery_row,
        "invoice_sum": _decimal_text(invoice_sum),
        "payment_sum": _decimal_text(payment_sum),
        "reimbursable_sum": _decimal_text(reimbursable_sum),
        "non_reimbursable_sum": _decimal_text(non_reimbursable_sum),
        "balance": _decimal_text(balance),
        "balance_kind": _balance_kind(balance),
        "balance_label": _balance_label(balance),
        "invoice_numbers": _doc_numbers(invoices),
        "invoice_rows": _doc_rows(invoices),
        "payment_numbers": _doc_numbers(payments),
        "sf_numbers": _doc_numbers(sales),
        "sf_rows": _doc_rows(sales),
        "documents_count": len(documents),
    }


def _matrix_summary(items: list[dict[str, object]]) -> dict[str, object]:
    invoice_sum = sum((_decimal_value(row.get("invoice_sum")) for row in items), Decimal("0.00"))
    payment_sum = sum((_decimal_value(row.get("payment_sum")) for row in items), Decimal("0.00"))
    reimbursable_sum = sum((_decimal_value(row.get("reimbursable_sum")) for row in items), Decimal("0.00"))
    non_reimbursable_sum = sum((_decimal_value(row.get("non_reimbursable_sum")) for row in items), Decimal("0.00"))
    balance = sum((_decimal_value(row.get("balance")) for row in items), Decimal("0.00"))
    return {
        "deliveries": len(items),
        "invoice_sum": _decimal_text(invoice_sum),
        "payment_sum": _decimal_text(payment_sum),
        "reimbursable_sum": _decimal_text(reimbursable_sum),
        "non_reimbursable_sum": _decimal_text(non_reimbursable_sum),
        "balance": _decimal_text(balance),
        "debts": sum(1 for row in items if row.get("balance_kind") == "debt"),
        "overpayments": sum(1 for row in items if row.get("balance_kind") == "overpayment"),
    }


def _sum_docs(documents: list[AccountingDocument]) -> Decimal:
    return sum((doc.amount.amount for doc in documents), Decimal("0.00"))


def _doc_numbers(documents: list[AccountingDocument]) -> list[str]:
    seen: set[str] = set()
    numbers: list[str] = []
    for doc in documents:
        value = doc.code1c or doc.number
        if value and value not in seen:
            seen.add(value)
            numbers.append(value)
    return numbers


def _doc_rows(documents: list[AccountingDocument]) -> list[dict[str, object]]:
    return [
        {
            "number": doc.number or doc.code1c,
            "code1c": doc.code1c,
            "date": doc.date.isoformat() if doc.date else "",
            "amount": _decimal_text(doc.amount.amount),
            "currency": doc.amount.currency,
        }
        for doc in documents
    ]


def _balance_kind(balance: Decimal) -> str:
    if balance > 0:
        return "overpayment"
    if balance < 0:
        return "debt"
    return "closed"


def _balance_label(balance: Decimal) -> str:
    if balance > 0:
        return "Переплата"
    if balance < 0:
        return "Долг"
    return "Закрыто"


def _decimal_value(value: object) -> Decimal:
    return Decimal(str(value or "0")).quantize(Decimal("0.01"))


def _decimal_text(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))


def _demo_matrix_payload() -> dict[str, object]:
    items = [
        {
            "spec_id": 20334,
            "spec_number": "921",
            "spec_type_name": "Заявка",
            "spec_date": "2025-08-09",
            "buyer_contract_code": "БП-051945",
            "committent_contract_code": "БП-051946",
            "dog_id": 88,
            "base_contract_number": "660/1",
            "client_id": 221,
            "client_name": "ООО «АЭРО-ТРЕЙД»",
            "client_inn": "7811451960",
            "invoice_sum": "166901.52",
            "payment_sum": "833921.00",
            "reimbursable_sum": "829165.90",
            "non_reimbursable_sum": "67055.99",
            "balance": "-62300.89",
            "balance_kind": "debt",
            "balance_label": "Долг",
            "invoice_numbers": ["ВА-015695", "ВА-015696", "ВА-015697"],
            "invoice_rows": [
                {"number": "ВА-015695", "amount": "21000.00", "currency": "RUB"},
                {"number": "ВА-015696", "amount": "4700.00", "currency": "RUB"},
                {"number": "ВА-015697", "amount": "141201.52", "currency": "RUB"},
            ],
            "payment_numbers": ["00БП-010299"],
            "sf_numbers": ["00БП-000198"],
            "documents_count": 9,
        },
        {
            "spec_id": 20341,
            "spec_number": "1076",
            "spec_type_name": "Заявка",
            "spec_date": "2025-08-12",
            "buyer_contract_code": "БП-052031",
            "committent_contract_code": "БП-052032",
            "dog_id": 88,
            "base_contract_number": "660/1",
            "client_id": 221,
            "client_name": "ООО «АЭРО-ТРЕЙД»",
            "client_inn": "7811451960",
            "invoice_sum": "21000.00",
            "payment_sum": "21000.00",
            "reimbursable_sum": "445565.75",
            "non_reimbursable_sum": "48725.61",
            "balance": "-473291.36",
            "balance_kind": "debt",
            "balance_label": "Долг",
            "invoice_numbers": ["ВА-007688", "ВА-007689"],
            "invoice_rows": [
                {"number": "ВА-007688", "amount": "21000.00", "currency": "RUB"},
                {"number": "ВА-007689", "amount": "0.00", "currency": "RUB"},
            ],
            "payment_numbers": ["00БП-003300"],
            "sf_numbers": ["00БП-003300"],
            "documents_count": 7,
        },
        {
            "spec_id": 20348,
            "spec_number": "1068",
            "spec_type_name": "Заявка",
            "spec_date": "2025-08-14",
            "buyer_contract_code": "БП-052101",
            "committent_contract_code": "БП-052102",
            "dog_id": 88,
            "base_contract_number": "660/1",
            "client_id": 221,
            "client_name": "ООО «АЭРО-ТРЕЙД»",
            "client_inn": "7811451960",
            "invoice_sum": "55800.00",
            "payment_sum": "390296.92",
            "reimbursable_sum": "416239.47",
            "non_reimbursable_sum": "36648.04",
            "balance": "-62590.59",
            "balance_kind": "debt",
            "balance_label": "Долг",
            "invoice_numbers": ["ВА-007713", "ВА-007714"],
            "invoice_rows": [
                {"number": "ВА-007713", "amount": "4700.00", "currency": "RUB"},
                {"number": "ВА-007714", "amount": "51100.00", "currency": "RUB"},
            ],
            "payment_numbers": ["00БП-003301"],
            "sf_numbers": ["00БП-003301"],
            "documents_count": 8,
        },
        {
            "spec_id": 20350,
            "spec_number": "1081",
            "spec_type_name": "Заявка",
            "spec_date": "2025-08-16",
            "buyer_contract_code": "БП-052145",
            "committent_contract_code": "БП-052146",
            "dog_id": 88,
            "base_contract_number": "660/1",
            "client_id": 221,
            "client_name": "ООО «АЭРО-ТРЕЙД»",
            "client_inn": "7811451960",
            "invoice_sum": "124500.00",
            "payment_sum": "150000.00",
            "reimbursable_sum": "110200.00",
            "non_reimbursable_sum": "14300.00",
            "balance": "25500.00",
            "balance_kind": "overpayment",
            "balance_label": "Переплата",
            "invoice_numbers": ["ВА-007901"],
            "invoice_rows": [
                {"number": "ВА-007901", "amount": "124500.00", "currency": "RUB"},
            ],
            "payment_numbers": ["00БП-003410"],
            "sf_numbers": ["00БП-003410"],
            "documents_count": 5,
        },
    ]
    return {
        "ok": True,
        "mode": "ui_demo",
        "items": items,
        "count": len(items),
        "summary": _matrix_summary(items),
        "limit": len(items),
    }


def _demo_client_search(query: str, limit: int) -> list[dict[str, object]]:
    needle = query.strip().lower()
    seen: set[int] = set()
    result: list[dict[str, object]] = []
    for item in _demo_matrix_payload()["items"]:
        client_id = int(item.get("client_id") or 0)
        if client_id in seen:
            continue
        haystack = " ".join(
            [
                str(item.get("client_id") or ""),
                str(item.get("client_name") or ""),
                str(item.get("client_inn") or ""),
            ]
        ).lower()
        if needle in haystack:
            seen.add(client_id)
            result.append(
                {
                    "client_id": client_id,
                    "client_name": item.get("client_name") or "",
                    "client_inn": item.get("client_inn") or "",
                }
            )
        if len(result) >= limit:
            break
    return result


def _static_content_type(name: str) -> str:
    if name.endswith(".html"):
        return "text/html; charset=utf-8"
    if name.endswith(".css"):
        return "text/css; charset=utf-8"
    if name.endswith(".js"):
        return "application/javascript; charset=utf-8"
    return "application/octet-stream"


def _dev_auth_profile(login: str, password: str) -> dict[str, object] | None:
    if os.environ.get("RECON_DEV_AUTH", "").strip() != "1":
        return None
    expected_login = os.environ.get("RECON_DEV_AUTH_LOGIN", "demo@local.test").strip()
    expected_password = os.environ.get("RECON_DEV_AUTH_PASSWORD", "demo").strip()
    if login != expected_login or password != expected_password:
        return None
    return {
        "user_id": 0,
        "login": expected_login,
        "name": os.environ.get("RECON_DEV_AUTH_NAME", "Локальный тест"),
        "structure_code": "DEV",
    }


def main() -> None:
    host = os.environ.get("RECON_API_HOST", "0.0.0.0")
    port = int(os.environ.get("RECON_API_PORT", "8780"))
    server = ThreadingHTTPServer((host, port), ReconciliationHttpHandler)
    server.serve_forever()


def _connection_factory() -> MariaDbConnectionFactory:
    config = _app_config().erp_db
    missing = config.missing_fields()
    if missing:
        raise RuntimeError("ERP MariaDB is not configured: " + ", ".join(missing))
    return MariaDbConnectionFactory(config)


def _erp_repository() -> MariaDbErpReadRepository:
    return MariaDbErpReadRepository(_connection_factory())


def _first(query: dict[str, list[str]], key: str) -> str:
    values = query.get(key) or []
    return values[0].strip() if values else ""


def _required_int(query: dict[str, list[str]], key: str) -> int:
    value = _first(query, key)
    if not value:
        raise ValueError(f"Missing required query parameter: {key}")
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid integer query parameter: {key}") from exc


def _optional_int(query: dict[str, list[str]], key: str) -> int | None:
    value = _first(query, key)
    if not value:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid integer query parameter: {key}") from exc


def _required_date(query: dict[str, list[str]], key: str):
    value = _first(query, key)
    if not value:
        raise ValueError(f"Missing required query parameter: {key}")
    return _parse_iso_date(value, key)


def _optional_date(query: dict[str, list[str]], key: str):
    value = _first(query, key)
    if not value:
        return None
    return _parse_iso_date(value, key)


def _parse_iso_date(value: str, key: str):
    from datetime import datetime

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"Invalid date query parameter {key}; expected YYYY-MM-DD") from exc


def _optional_bool(query: dict[str, list[str]], key: str, *, default: bool) -> bool:
    value = _first(query, key)
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "y"}


if __name__ == "__main__":
    main()
