from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
from pathlib import Path
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from recon_erp_1c.application.serializers import run_to_dict
from recon_erp_1c.application.use_cases.list_deliveries import ListDeliveriesCommand, ListDeliveriesUseCase
from recon_erp_1c.application.use_cases.reconcile_delivery import ReconcileDeliveryCommand, ReconcileDeliveryUseCase
from recon_erp_1c.bootstrap.config import AppConfig
from recon_erp_1c.domain.entities import AccountingDocument
from recon_erp_1c.domain.value_objects import DateRange, DocumentKind, Money
from recon_erp_1c.infrastructure.erp_mariadb.connection import MariaDbConnectionFactory
from recon_erp_1c.infrastructure.erp_mariadb.repository import ErpDataNotFound, MariaDbErpReadRepository
from recon_erp_1c.infrastructure.export.xlsx import reconciliation_matrix_xlsx, reconciliation_run_xlsx
from recon_erp_1c.infrastructure.onec_rest.client import OneCRestClient, OneCRestConfig, onec_rest_status
from recon_erp_1c.infrastructure.onec_rest.repository import OneCRestReadRepository
from recon_erp_1c.infrastructure.persistence.mariadb_log_repository import MariaDbReconciliationLogRepository
from recon_erp_1c.interfaces.http.auth import AuthenticationError, create_session_token, request_context


_BATCH_JOBS: dict[str, dict[str, object]] = {}
_BATCH_LOCK = threading.Lock()


def _app_config() -> AppConfig:
    return AppConfig.from_env()


class ReconciliationHttpHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        try:
            if parsed.path in {
                "/",
                "/reconciliation.html",
                "/reconciliation.css",
                "/reconciliation.js",
                "/akt_sverki/index.html",
                "/akt_sverki/reconciliation.html",
                "/akt_sverki/reconciliation.css",
                "/akt_sverki/reconciliation.js",
            }:
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
            if parsed.path == "/api/reconciliation/contracts":
                self._search_contracts(query)
                return
            if parsed.path == "/api/reconciliation/deliveries":
                self._search_deliveries(query)
                return
            if parsed.path == "/api/reconciliation/matrix":
                self._list_matrix(query)
                return
            if parsed.path == "/api/reconciliation/matrix.xlsx":
                self._matrix_xlsx(query)
                return
            if parsed.path == "/api/reconciliation/history":
                self._history(query)
                return
            if parsed.path.startswith("/api/reconciliation/batch/"):
                self._batch_status(parsed.path)
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
        except Exception as exc:  # noqa: BLE001 - HTTP handler must not drop the connection on infrastructure errors
            self.log_error("Unhandled GET error: %s", exc)
            self._json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {
                    "ok": False,
                    "error": "service_unavailable",
                    "message": "ERP temporarily unavailable. Please retry the request.",
                },
            )

    def do_POST(self) -> None:  # noqa: N802 - stdlib callback name
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/auth/login":
                self._login()
                return
            if parsed.path == "/api/auth/erp-launch":
                self._erp_launch()
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
            if parsed.path == "/api/reconciliation/comments":
                self._save_comment()
                return
            if parsed.path == "/api/reconciliation/batch":
                self._batch_reconciliation()
                return
            self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found", "message": "Unknown endpoint"})
        except AuthenticationError as exc:
            self._json(exc.status, {"ok": False, "error": "unauthorized", "message": str(exc)})
        except ValueError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "bad_request", "message": str(exc)})
        except RuntimeError as exc:
            self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"ok": False, "error": "service_unavailable", "message": str(exc)})
        except Exception as exc:  # noqa: BLE001 - HTTP handler must not drop the connection on infrastructure errors
            self.log_error("Unhandled POST error: %s", exc)
            self._json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {
                    "ok": False,
                    "error": "service_unavailable",
                    "message": "ERP temporarily unavailable. Please retry the request.",
                },
            )

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
                    "mode": "erp_launch_token",
                    "required": config.require_erp_token,
                    "direct_login_enabled": config.direct_login_enabled,
                    "demo": config.ui_demo,
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
                    "mode": "erp_launch_token",
                    "required": config.require_erp_token,
                    "direct_login_enabled": config.direct_login_enabled,
                    "demo": config.ui_demo,
                    "session_secret_configured": bool(os.environ.get("RECON_SESSION_SECRET", "").strip()),
                    "launch_token_validation_configured": bool(config.erp_token_validate_url),
                },
            },
        )

    def _login(self) -> None:
        config = _app_config()
        if not config.direct_login_enabled:
            raise AuthenticationError("Direct ERP login is disabled; open reconciliation from ERP launch token")
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

    def _erp_launch(self) -> None:
        payload = self._json_body()
        launch_token = str(payload.get("launch_token") or payload.get("token") or "").strip()
        if not launch_token:
            raise ValueError("launch_token is required")
        profile = _validate_erp_launch_token(launch_token)
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
            spec_id=_optional_int(query, "spec_id"),
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

    def _search_contracts(self, query: dict[str, list[str]]) -> None:
        self._require_context()
        text = (query.get("q") or [""])[0].strip()
        limit = max(1, min(_optional_int(query, "limit") or 12, 30))
        client_id = _optional_int(query, "client_id")
        if len(text) < 2:
            self._json(HTTPStatus.OK, {"ok": True, "items": [], "count": 0, "min_query_length": 2})
            return
        if _app_config().ui_demo:
            items = _demo_contract_search(text, limit)
        else:
            items = _erp_repository().search_contracts(text, client_id=client_id, limit=limit)
        self._json(HTTPStatus.OK, {"ok": True, "items": items, "count": len(items), "min_query_length": 2})

    def _search_deliveries(self, query: dict[str, list[str]]) -> None:
        self._require_context()
        text = (query.get("q") or [""])[0].strip()
        limit = max(1, min(_optional_int(query, "limit") or 12, 30))
        min_length = 1 if text.isdigit() else 3
        if len(text) < min_length:
            self._json(
                HTTPStatus.OK,
                {"ok": True, "items": [], "count": 0, "min_query_length": min_length},
            )
            return
        if _app_config().ui_demo:
            items = _demo_delivery_search(text, limit)
        else:
            items = _erp_repository().search_deliveries(
                text,
                client_id=_optional_int(query, "client_id"),
                dog_id=_optional_int(query, "dog_id"),
                date_from=_optional_date(query, "date_from"),
                date_to=_optional_date(query, "date_to"),
                limit=limit,
            )
        self._json(
            HTTPStatus.OK,
            {"ok": True, "items": items, "count": len(items), "min_query_length": min_length},
        )

    def _run_reconciliation(self, query: dict[str, list[str]]) -> None:
        self._require_context()
        started = time.perf_counter()
        run = _execute_reconciliation(query)
        payload = run_to_dict(run)
        payload["metrics"] = {
            **payload.get("metrics", {}),
            "http_total_ms": round((time.perf_counter() - started) * 1000, 2),
        }
        self._json(HTTPStatus.OK, {"ok": True, "run": payload})

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

    def _save_comment(self) -> None:
        context = self._require_context()
        payload = self._json_body()
        comment_key = str(payload.get("key") or "").strip()
        if not comment_key:
            raise ValueError("comment key is required")
        reason = str(payload.get("reason") or "").strip()
        comment = str(payload.get("comment") or "").strip()
        if _app_config().ui_demo:
            self._json(HTTPStatus.OK, {"ok": True, "mode": "ui_demo"})
            return
        with _connection_factory().connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO veda_reconciliation_comments
                        (comment_key, run_external_id, spec_id, status, reason_code, comment_text, user_login, user_name)
                    VALUES
                        (%(comment_key)s, %(run_external_id)s, %(spec_id)s, %(status)s, %(reason_code)s, %(comment_text)s, %(user_login)s, %(user_name)s)
                    ON DUPLICATE KEY UPDATE
                        run_external_id = VALUES(run_external_id),
                        spec_id = VALUES(spec_id),
                        status = VALUES(status),
                        reason_code = VALUES(reason_code),
                        comment_text = VALUES(comment_text),
                        user_login = VALUES(user_login),
                        user_name = VALUES(user_name)
                    """,
                    {
                        "comment_key": comment_key,
                        "run_external_id": str(payload.get("run_id") or "")[:128],
                        "spec_id": int(payload.get("spec_id") or 0),
                        "status": str(payload.get("status") or "")[:64],
                        "reason_code": reason[:64],
                        "comment_text": comment,
                        "user_login": context.user_email,
                        "user_name": context.user_name,
                    },
                )
        self._json(HTTPStatus.OK, {"ok": True})

    def _history(self, query: dict[str, list[str]]) -> None:
        self._require_context()
        limit = max(1, min(_optional_int(query, "limit") or 20, 100))
        spec_id = _optional_int(query, "spec_id")
        client_id = _optional_int(query, "client_id")
        if _app_config().ui_demo:
            self._json(HTTPStatus.OK, {"ok": True, "items": [], "count": 0, "mode": "ui_demo"})
            return
        conditions = []
        params: dict[str, object] = {"limit": limit}
        if spec_id is not None:
            conditions.append("spec_id = %(spec_id)s")
            params["spec_id"] = spec_id
        if client_id is not None:
            conditions.append("client_id = %(client_id)s")
            params["client_id"] = client_id
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        with _connection_factory().connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT
                        id, scope, scope_id, spec_id, client_id, source_mode,
                        onec_docs_count, erp_docs_count, status, summary_json, created_at
                    FROM veda_reconciliation_runs
                    {where}
                    ORDER BY id DESC
                    LIMIT %(limit)s
                    """,
                    params,
                )
                rows = list(cursor.fetchall())
        items = []
        for row in rows:
            summary = {}
            try:
                summary = json.loads(row.get("summary_json") or "{}")
            except json.JSONDecodeError:
                summary = {}
            items.append(
                {
                    "id": row.get("id"),
                    "scope": row.get("scope"),
                    "scope_id": row.get("scope_id"),
                    "spec_id": row.get("spec_id"),
                    "client_id": row.get("client_id"),
                    "source_mode": row.get("source_mode"),
                    "onec_docs_count": row.get("onec_docs_count"),
                    "erp_docs_count": row.get("erp_docs_count"),
                    "status": row.get("status"),
                    "summary": summary,
                    "created_at": str(row.get("created_at") or ""),
                }
            )
        self._json(HTTPStatus.OK, {"ok": True, "items": items, "count": len(items)})

    def _batch_reconciliation(self) -> None:
        self._require_context()
        payload = self._json_body()
        raw_spec_ids = payload.get("spec_ids")
        if not isinstance(raw_spec_ids, list) or not raw_spec_ids:
            raise ValueError("spec_ids array is required")
        spec_ids = []
        for value in raw_spec_ids:
            spec_id = int(value)
            if spec_id > 0 and spec_id not in spec_ids:
                spec_ids.append(spec_id)
        if len(spec_ids) > 50:
            raise ValueError("batch size is limited to 50 spec_ids")
        date_from = str(payload.get("date_from") or "").strip()
        date_to = str(payload.get("date_to") or "").strip()
        if not date_from or not date_to:
            raise ValueError("date_from and date_to are required")
        job_id = str(uuid4())
        job = {
            "job_id": job_id,
            "status": "queued",
            "total": len(spec_ids),
            "done": 0,
            "runs": [],
            "errors": [],
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        with _BATCH_LOCK:
            _BATCH_JOBS[job_id] = job
        thread = threading.Thread(
            target=_execute_batch_job,
            args=(job_id, spec_ids, date_from, date_to, str(payload.get("persist_log", "1"))),
            daemon=True,
        )
        thread.start()
        self._json(HTTPStatus.ACCEPTED, {"ok": True, "job_id": job_id, "status": "queued", "total": len(spec_ids)})

    def _batch_status(self, path: str) -> None:
        self._require_context()
        job_id = path.rstrip("/").rsplit("/", 1)[-1]
        with _BATCH_LOCK:
            job = dict(_BATCH_JOBS.get(job_id) or {})
        if not job:
            self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found", "message": "Batch job not found"})
            return
        self._json(HTTPStatus.OK, {"ok": True, "job": job})

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
            "/akt_sverki/index.html": "reconciliation.html",
            "/akt_sverki/reconciliation.html": "reconciliation.html",
            "/akt_sverki/reconciliation.css": "reconciliation.css",
            "/akt_sverki/reconciliation.js": "reconciliation.js",
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
        return _demo_matrix_payload(query)
    repository = _erp_repository()
    export_all = _optional_bool(query, "all", default=False)
    include_total = _optional_bool(query, "include_total", default=False)
    requested_limit = _optional_int(query, "limit") or 50
    limit = max(1, min(requested_limit, 2000 if export_all else 500))
    offset = 0 if export_all else (_optional_int(query, "offset") or 0)
    client_id = _optional_int(query, "client_id")
    dog_id = _optional_int(query, "dog_id")
    spec_id = _optional_int(query, "spec_id")
    date_from = _optional_date(query, "date_from")
    date_to = _optional_date(query, "date_to")
    started = time.perf_counter()
    total_count = repository.count_deliveries(
        spec_id=spec_id,
        client_id=client_id,
        dog_id=dog_id,
        date_from=date_from,
        date_to=date_to,
    )
    total_summary = (
        repository.matrix_total_summary(
            spec_id=spec_id,
            client_id=client_id,
            dog_id=dog_id,
            date_from=date_from,
            date_to=date_to,
        )
        if include_total and spec_id is None
        else None
    )
    if export_all:
        limit = max(1, min(total_count or limit, 2000))
    command = ListDeliveriesCommand(
        spec_id=spec_id,
        client_id=client_id,
        dog_id=dog_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    deliveries = ListDeliveriesUseCase(repository).execute(command)
    documents_by_spec, calculations_by_spec = repository.list_documents_and_calculations_for_deliveries(
        [int(delivery.get("spec_id") or 0) for delivery in deliveries]
    )
    items = [
        _matrix_row(
            repository,
            delivery,
            documents_by_spec.get(int(delivery.get("spec_id") or 0), []),
            calculations_by_spec.get(int(delivery.get("spec_id") or 0)),
        )
        for delivery in deliveries
    ]
    if include_total and spec_id is not None:
        total_summary = _matrix_summary(items)
    return {
        "ok": True,
        "mode": "erp_live",
        "items": items,
        "count": len(items),
        "total_count": total_count,
        "offset": offset,
        "has_more": offset + len(items) < total_count,
        "summary": _matrix_summary(items),
        "total_summary": total_summary,
        "summary_scope": "all_filtered" if total_summary else "page",
        "page_summary": _matrix_summary(items),
        "limit": limit,
        "all_export_limited": export_all and total_count > limit,
        "metrics": {"erp_sql_ms": round((time.perf_counter() - started) * 1000, 2)},
    }


def _matrix_row(
    repository: MariaDbErpReadRepository,
    delivery_row: dict[str, object],
    documents: list[AccountingDocument] | None = None,
    calculation: dict[str, str] | None = None,
) -> dict[str, object]:
    spec_id = int(delivery_row["spec_id"] or 0)
    documents = documents if documents is not None else repository.list_delivery_documents(spec_id)
    buyer_code = str(delivery_row.get("buyer_contract_code") or "")
    invoices = [doc for doc in documents if doc.kind == DocumentKind.CUSTOMER_INVOICE]
    payments = [doc for doc in documents if doc.kind == DocumentKind.PAYMENT]
    sales = [doc for doc in documents if doc.kind == DocumentKind.SALE]
    payments_by_operation: dict[int, Money] = {}
    for payment in payments:
        if not payment.operation_id:
            continue
        current = payments_by_operation.get(payment.operation_id)
        if current is None:
            payments_by_operation[payment.operation_id] = payment.amount
        else:
            payments_by_operation[payment.operation_id] = Money.of(
                current.amount + payment.amount.amount,
                current.currency if current.currency == payment.amount.currency else "RUB",
            )
    non_reimbursable = [
        doc
        for doc in sales
        if doc.reimbursement_type == "non_reimbursable"
        or (doc.reimbursement_type in {"", "unknown"} and buyer_code and doc.contract_code1c == buyer_code)
    ]
    reimbursable = [
        doc
        for doc in sales
        if doc.reimbursement_type == "reimbursable"
        or (doc.reimbursement_type in {"", "unknown"} and doc not in non_reimbursable)
    ]
    invoice_sum = _sum_docs(invoices)
    payment_sum = _decimal_value(calculation.get("payment_sum")) if calculation else _sum_docs(payments)
    reimbursable_sum = (
        _decimal_value(calculation.get("reimbursable_sum")) if calculation else _sum_docs(reimbursable)
    )
    non_reimbursable_sum = (
        _decimal_value(calculation.get("non_reimbursable_sum")) if calculation else _sum_docs(non_reimbursable)
    )
    balance = (
        _decimal_value(calculation.get("balance"))
        if calculation
        else payment_sum - reimbursable_sum - non_reimbursable_sum
    )
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
        "invoice_rows": _doc_rows(invoices, payments_by_operation),
        "payment_numbers": _doc_numbers(payments),
        "payment_rows": _doc_rows(payments),
        "sf_numbers": _doc_numbers(sales),
        "sf_rows": _doc_rows(sales),
        "documents_count": len(documents),
        "erp_url": f"http://erp.vedagent/veda/?pgid=15&obid={spec_id}&typeid=1#tabs-0" if spec_id else "",
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


def _doc_rows(
    documents: list[AccountingDocument],
    payments_by_operation: dict[int, Money] | None = None,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for doc in documents:
        linked_payment = payments_by_operation.get(doc.operation_id) if payments_by_operation and doc.operation_id else None
        rows.append(
            {
                "number": doc.number or doc.code1c,
                "code1c": doc.code1c,
                "date": doc.date.isoformat() if doc.date else "",
                "amount": _decimal_text(doc.amount.amount),
                "currency": doc.amount.currency,
                "operation_id": doc.operation_id,
                "source_id": doc.source_id,
                "kind": doc.kind.value,
                "erp_url": _erp_document_url(doc),
                "operation_url": (
                    f"http://erp.vedagent/veda/?pgid=35&invtb=145&obid={doc.operation_id}#"
                    if doc.operation_id
                    else ""
                ),
                "paid_amount": _decimal_text(linked_payment.amount)
                if linked_payment
                else (_decimal_text(doc.payment_amount.amount) if doc.payment_amount else ""),
                "paid_currency": linked_payment.currency
                if linked_payment
                else (doc.payment_amount.currency if doc.payment_amount else ""),
            }
        )
    return rows


def _erp_document_url(document: AccountingDocument) -> str:
    if not document.source_id or not document.source_id.isdigit():
        return ""
    if document.kind == DocumentKind.CUSTOMER_INVOICE:
        return f"http://erp.vedagent/veda/?pgid=17&obid={document.source_id}#"
    if document.kind in {DocumentKind.SALE, DocumentKind.PURCHASE, DocumentKind.CLOSING_DOCUMENT}:
        return f"http://erp.vedagent/veda/?pgid=83&obid={document.source_id}"
    return ""


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


def _demo_matrix_payload(query: dict[str, list[str]] | None = None) -> dict[str, object]:
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
            "payment_rows": [
                {"number": "00БП-010299", "amount": "833921.00", "currency": "RUB", "date": "2025-07-30"},
            ],
            "sf_numbers": ["00БП-000198"],
            "sf_rows": [
                {"number": "00БП-000198", "amount": "67055.99", "currency": "RUB", "date": "2025-01-21"},
            ],
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
            "payment_rows": [
                {"number": "00БП-003300", "amount": "21000.00", "currency": "RUB", "date": "2025-08-12"},
            ],
            "sf_numbers": ["00БП-003300"],
            "sf_rows": [
                {"number": "00БП-003300", "amount": "494291.36", "currency": "RUB", "date": "2025-08-12"},
            ],
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
            "payment_rows": [
                {"number": "00БП-003301", "amount": "390296.92", "currency": "RUB", "date": "2025-08-14"},
            ],
            "sf_numbers": ["00БП-003301"],
            "sf_rows": [
                {"number": "00БП-003301", "amount": "452887.51", "currency": "RUB", "date": "2025-08-14"},
            ],
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
            "payment_rows": [
                {"number": "00БП-003410", "amount": "150000.00", "currency": "RUB", "date": "2025-08-16"},
            ],
            "sf_numbers": ["00БП-003410"],
            "sf_rows": [
                {"number": "00БП-003410", "amount": "124500.00", "currency": "RUB", "date": "2025-08-16"},
            ],
            "documents_count": 5,
        },
    ]
    for item in items:
        item["organization_abbr"] = "ВА"
        item["delivery_full_name"] = "/".join(
            [
                str(item.get("base_contract_number") or ""),
                str(item.get("spec_number") or ""),
                str(item.get("organization_abbr") or ""),
                str(item.get("client_name") or ""),
            ]
        )
        item["main_client_id"] = 115
        item["main_client_name"] = "АЭРО-ТРЕЙД ООО"
    query = query or {}
    spec_id = _optional_int(query, "spec_id")
    client_id = _optional_int(query, "client_id")
    dog_id = _optional_int(query, "dog_id")
    if spec_id is not None:
        items = [item for item in items if int(item.get("spec_id") or 0) == spec_id]
    if client_id is not None:
        items = [item for item in items if int(item.get("client_id") or 0) == client_id]
    if dog_id is not None:
        items = [item for item in items if int(item.get("dog_id") or 0) == dog_id]
    return {
        "ok": True,
        "mode": "ui_demo",
        "items": items,
        "count": len(items),
        "summary": _matrix_summary(items),
        "limit": len(items),
        "total_count": len(items),
        "offset": 0,
        "has_more": False,
        "metrics": {"erp_sql_ms": 0},
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


def _demo_delivery_search(query: str, limit: int) -> list[dict[str, object]]:
    needle = query.strip().lower()
    result: list[dict[str, object]] = []
    for item in _demo_matrix_payload()["items"]:
        exact_id = needle.isdigit() and int(item.get("spec_id") or 0) == int(needle)
        haystack = " ".join(
            [
                str(item.get("spec_number") or ""),
                str(item.get("spec_type_name") or ""),
                str(item.get("delivery_full_name") or ""),
            ]
        ).lower()
        if exact_id or (not needle.isdigit() and needle in haystack):
            result.append(
                {
                    "spec_id": item.get("spec_id"),
                    "spec_number": item.get("spec_number") or "",
                    "spec_type_name": item.get("spec_type_name") or "",
                    "spec_date": item.get("spec_date") or "",
                    "dog_id": item.get("dog_id"),
                    "base_contract_number": item.get("base_contract_number") or "",
                    "organization_abbr": item.get("organization_abbr") or "",
                    "client_id": item.get("client_id"),
                    "client_name": item.get("client_name") or "",
                    "client_inn": item.get("client_inn") or "",
                    "delivery_full_name": item.get("delivery_full_name") or "",
                }
            )
        if len(result) >= limit:
            break
    return result


def _demo_contract_search(query: str, limit: int) -> list[dict[str, object]]:
    needle = query.strip().lower()
    seen: set[int] = set()
    result: list[dict[str, object]] = []
    for item in _demo_matrix_payload()["items"]:
        dog_id = int(item.get("dog_id") or 0)
        if dog_id in seen:
            continue
        haystack = " ".join(
            [
                str(item.get("dog_id") or ""),
                str(item.get("base_contract_number") or ""),
                str(item.get("buyer_contract_code") or ""),
                str(item.get("committent_contract_code") or ""),
            ]
        ).lower()
        if needle in haystack:
            seen.add(dog_id)
            result.append(
                {
                    "dog_id": dog_id,
                    "contract_number": item.get("base_contract_number") or "",
                    "contract_code1c": item.get("buyer_contract_code") or "",
                    "client_id": item.get("client_id"),
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


def _validate_erp_launch_token(launch_token: str) -> dict[str, object]:
    config = _app_config()
    if config.ui_demo and launch_token in {"demo", "ui-demo", "local-demo"}:
        return {
            "user_id": 0,
            "login": "demo@local.test",
            "name": "Локальный тест",
            "structure_code": "DEV",
        }
    if not config.erp_token_validate_url:
        raise RuntimeError("ERP launch token validation endpoint is not configured")

    request_body = json.dumps(
        {"token": launch_token, "audience": "reconciliation"},
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        config.erp_token_validate_url,
        data=request_body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=config.erp_token_validate_timeout_seconds) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise AuthenticationError(f"ERP launch token validation failed: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"ERP launch token validation is unavailable: {exc.reason}") from exc

    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError("ERP launch token validation returned invalid JSON") from exc

    ok = bool(payload.get("ok", payload.get("success", payload.get("valid", False)))) if isinstance(payload, dict) else False
    if isinstance(payload, list) and payload:
        ok = bool(payload[0])
    if not ok:
        message = payload.get("message") if isinstance(payload, dict) else ""
        raise AuthenticationError(str(message or "Invalid ERP launch token"))

    dict_payload = payload if isinstance(payload, dict) else {}
    profile = dict_payload.get("profile") or dict_payload.get("user") or dict_payload.get("data") or {}
    if not isinstance(profile, dict):
        profile = {}
    login = profile.get("login") or profile.get("email") or dict_payload.get("login") or dict_payload.get("email")
    name = profile.get("name") or profile.get("fio") or dict_payload.get("name") or dict_payload.get("fio") or login
    user_id = profile.get("user_id") or profile.get("id") or dict_payload.get("user_id") or dict_payload.get("id")
    if not login:
        raise AuthenticationError("ERP launch token validation did not return user login")
    return {
        "user_id": user_id,
        "login": login,
        "name": name,
        "structure_code": profile.get("structure_code") or dict_payload.get("structure_code") or "",
    }


def _execute_batch_job(job_id: str, spec_ids: list[int], date_from: str, date_to: str, persist_log: str) -> None:
    _update_batch_job(job_id, status="running")
    started = time.perf_counter()
    if _app_config().ui_demo:
        for spec_id in spec_ids:
            run = {
                "run_id": f"ui-demo-batch-{spec_id}",
                "delivery": {"erp_spec_id": spec_id},
                "summary": {"issues_total": 0, "by_status": {"match": 0}},
                "issues": [],
                "metrics": {"total_ms": 0},
            }
            _append_batch_result(job_id, run=run)
        _update_batch_job(job_id, status="completed", metrics={"total_ms": round((time.perf_counter() - started) * 1000, 2)})
        return

    worker_count = max(1, min(4, int(os.environ.get("RECON_BATCH_WORKERS", "2") or "2"), len(spec_ids)))
    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        futures = {
            pool.submit(_execute_batch_spec, spec_id, date_from, date_to, persist_log): spec_id
            for spec_id in spec_ids
        }
        for future in as_completed(futures):
            spec_id = futures[future]
            try:
                _append_batch_result(job_id, run=future.result())
            except Exception as exc:  # noqa: BLE001 - background job must keep processing remaining specs
                _append_batch_result(
                    job_id,
                    error={"spec_id": spec_id, "message": str(exc), "type": exc.__class__.__name__},
                )
    _update_batch_job(
        job_id,
        status="completed",
        metrics={
            "total_ms": round((time.perf_counter() - started) * 1000, 2),
            "workers": worker_count,
        },
    )


def _execute_batch_spec(spec_id: int, date_from: str, date_to: str, persist_log: str) -> dict[str, object]:
    query = {
        "spec_id": [str(spec_id)],
        "date_from": [date_from],
        "date_to": [date_to],
        "persist_log": [persist_log],
    }
    return run_to_dict(_execute_reconciliation(query))


def _append_batch_result(job_id: str, *, run: dict[str, object] | None = None, error: dict[str, object] | None = None) -> None:
    with _BATCH_LOCK:
        job = _BATCH_JOBS.get(job_id)
        if not job:
            return
        if run is not None:
            runs = job.setdefault("runs", [])
            if isinstance(runs, list):
                runs.append(run)
        if error is not None:
            errors = job.setdefault("errors", [])
            if isinstance(errors, list):
                errors.append(error)
        job["done"] = int(job.get("done") or 0) + 1
        job["updated_at"] = time.time()


def _update_batch_job(job_id: str, **fields: object) -> None:
    with _BATCH_LOCK:
        job = _BATCH_JOBS.get(job_id)
        if not job:
            return
        job.update(fields)
        job["updated_at"] = time.time()


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
