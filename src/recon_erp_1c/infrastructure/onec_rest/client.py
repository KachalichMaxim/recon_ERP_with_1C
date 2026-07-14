#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only REST adapter for fetching normalized 1C reconciliation DTOs.

This is the target connector for the reconciliation service. It talks to a
dedicated 1C REST API, not to raw OData objects.
"""

from __future__ import annotations

import base64
import http.client
import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


class OneCRestError(RuntimeError):
    """Raised when the 1C REST source is unavailable or returns invalid data."""


@dataclass(frozen=True)
class OneCRestConfig:
    base_url: str
    token: str = ""
    username: str = ""
    password: str = ""
    timeout: int = 60
    bind_address: str = ""
    snapshot_path: str = "/reconciliation/v1/snapshot"
    health_path: str = "/reconciliation/v1/health"
    delivery_scope_enabled: bool = False

    @classmethod
    def from_env(cls) -> "OneCRestConfig":
        return cls(
            base_url=os.environ.get("RECON_ONEC_REST_BASE_URL", "").strip().rstrip("/"),
            token=os.environ.get("RECON_ONEC_REST_TOKEN", "").strip(),
            username=os.environ.get("RECON_ONEC_REST_USER", "").strip(),
            password=os.environ.get("RECON_ONEC_REST_PASSWORD", "").strip(),
            timeout=int(os.environ.get("RECON_ONEC_REST_TIMEOUT", "60") or "60"),
            bind_address=os.environ.get("RECON_ONEC_REST_BIND_ADDRESS", "").strip(),
            snapshot_path=os.environ.get("RECON_ONEC_REST_SNAPSHOT_PATH", "/reconciliation/v1/snapshot").strip()
            or "/reconciliation/v1/snapshot",
            health_path=os.environ.get("RECON_ONEC_REST_HEALTH_PATH", "/reconciliation/v1/health").strip()
            or "/reconciliation/v1/health",
            delivery_scope_enabled=os.environ.get("RECON_ONEC_DELIVERY_SCOPE_ENABLED", "0").strip().lower()
            in {"1", "true", "yes", "on"},
        )

    def missing_fields(self) -> list[str]:
        missing: list[str] = []
        if not self.base_url:
            missing.append("RECON_ONEC_REST_BASE_URL")
        if not self.token and not (self.username and self.password):
            missing.append("RECON_ONEC_REST_TOKEN or RECON_ONEC_REST_USER/RECON_ONEC_REST_PASSWORD")
        return missing

    @property
    def configured(self) -> bool:
        return not self.missing_fields()

    def url(self, path: str) -> str:
        normalized = "/" + path.strip("/")
        contract_root = "/reconciliation/v1"
        if self.base_url.endswith(contract_root) and normalized.startswith(contract_root + "/"):
            normalized = normalized[len(contract_root) :]
        return f"{self.base_url}{normalized}"


def onec_rest_status(config: OneCRestConfig | None = None) -> dict[str, Any]:
    config = config or OneCRestConfig.from_env()
    return {
        "configured": config.configured,
        "missing": config.missing_fields(),
        "base_url_configured": bool(config.base_url),
        "token_configured": bool(config.token),
        "basic_auth_configured": bool(config.username and config.password),
        "timeout": config.timeout,
        "bind_address_configured": bool(config.bind_address),
        "snapshot_path": config.snapshot_path,
        "health_path": config.health_path,
        "delivery_scope_enabled": config.delivery_scope_enabled,
    }


class OneCRestClient:
    def __init__(self, config: OneCRestConfig | None = None):
        self.config = config or OneCRestConfig.from_env()

    @classmethod
    def from_env(cls) -> "OneCRestClient":
        return cls(OneCRestConfig.from_env())

    def _assert_ready(self) -> None:
        missing = self.config.missing_fields()
        if missing:
            raise OneCRestError("1C REST is not configured: " + ", ".join(missing))

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
        }
        if self.config.token:
            headers["Authorization"] = f"Bearer {self.config.token}"
        elif self.config.username and self.config.password:
            raw = f"{self.config.username}:{self.config.password}".encode("utf-8")
            headers["Authorization"] = "Basic " + base64.b64encode(raw).decode("ascii")
        if extra:
            headers.update(extra)
        return headers

    def _request_json(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self._assert_ready()
        body = None
        url = self.config.url(path)
        if method.upper() == "GET" and payload:
            url = f"{url}?{urlencode(payload, doseq=True)}"
        elif payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = self._headers()
        try:
            if self.config.bind_address:
                raw = self._request_bound_source(method, url, body, headers)
            else:
                request = Request(url, data=body, headers=headers, method=method.upper())
                with urlopen(request, timeout=self.config.timeout) as response:
                    raw = response.read().decode("utf-8", errors="replace")
        except OneCRestError:
            raise
        except Exception as exc:
            raise OneCRestError(f"1C REST request failed: {exc}") from exc
        try:
            parsed = json.loads(raw or "{}")
        except json.JSONDecodeError as exc:
            raise OneCRestError(f"1C REST returned invalid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise OneCRestError("1C REST JSON response must be an object")
        if parsed.get("ok") is False:
            raise OneCRestError(str(parsed.get("message") or parsed.get("error") or "1C returned ok=false"))
        return parsed

    def _request_bound_source(self, method: str, url: str, body: bytes | None, headers: dict[str, str]) -> str:
        """Execute request from a specific local VPN address.

        Some 1C/MariaDB networks are reachable only through a split-tunnel VPN.
        macOS routing can pick another tunnel for the same 10.x destination, so
        local smoke tests may need to bind the source address explicitly.
        """
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise OneCRestError(f"Unsupported 1C REST URL: {url}")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        connection_class = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
        connection = connection_class(
            parsed.hostname,
            port,
            timeout=self.config.timeout,
            source_address=(self.config.bind_address, 0),
        )
        try:
            connection.request(method.upper(), path, body=body, headers=headers)
            response = connection.getresponse()
            raw = response.read().decode("utf-8-sig", errors="replace")
            if response.status >= 400:
                raise OneCRestError(f"1C REST returned HTTP {response.status}: {raw[:500]}")
            return raw
        finally:
            connection.close()

    def health(self) -> dict[str, Any]:
        return self._request_json("GET", self.config.health_path)

    def get_reconciliation_snapshot(self, request: dict[str, Any]) -> dict[str, Any]:
        payload = self._request_json(
            "GET",
            self.config.snapshot_path,
            snapshot_query_params(request, include_delivery_context=self.config.delivery_scope_enabled),
        )
        if "snapshot" not in payload:
            # Collection-like responses may already be a snapshot object.
            payload = {"ok": payload.get("ok", True), "snapshot": payload}
        return payload


def snapshot_query_params(request: dict[str, Any], *, include_delivery_context: bool = False) -> dict[str, Any]:
    """Flatten Python snapshot request into the GET query contract expected by 1C."""
    period = request.get("period") if isinstance(request.get("period"), dict) else {}
    delivery = request.get("delivery") if isinstance(request.get("delivery"), dict) else {}
    organizations = request.get("organizations") if isinstance(request.get("organizations"), list) else []
    counterparties = request.get("counterparties") if isinstance(request.get("counterparties"), list) else []
    contracts = request.get("contracts") if isinstance(request.get("contracts"), list) else []
    documents = request.get("documents") if isinstance(request.get("documents"), list) else []
    include = request.get("include") if isinstance(request.get("include"), dict) else {}

    params: dict[str, Any] = {
        "request_id": request.get("request_id", ""),
        "date_from": period.get("date_from", ""),
        "date_to": period.get("date_to", ""),
        "buyer_contract_code": delivery.get("buyer_contract_code1c", ""),
        "committent_contract_code": delivery.get("committent_contract_code1c", ""),
    }
    if include_delivery_context:
        params["scope"] = "delivery"
    has_contract_filter = bool(params["buyer_contract_code"] or params["committent_contract_code"])

    first_org = next((item for item in organizations if isinstance(item, dict)), {})
    params.update(
        {
            "organization_code": first_org.get("code1c", ""),
            "organization_inn": first_org.get("inn", ""),
        }
    )

    first_counterparty = next((item for item in counterparties if isinstance(item, dict)), {})
    params.update(
        {
            "counterparty_code": first_counterparty.get("code1c", ""),
            "counterparty_inn": first_counterparty.get("inn", ""),
        }
    )

    query_lists: dict[str, list[Any]] = {
        "contract_code": [],
        "document_code": [],
        "document_type": [],
        "include": [],
    }
    for contract in contracts:
        if not isinstance(contract, dict):
            continue
        if not has_contract_filter:
            query_lists["contract_code"].append(contract.get("code1c", ""))
    for document in documents:
        if not isinstance(document, dict):
            continue
        if not has_contract_filter:
            query_lists["document_code"].append(document.get("code1c") or document.get("number") or "")
            query_lists["document_type"].append(document.get("kind", ""))
    for key, enabled in include.items():
        if enabled:
            query_lists["include"].append(key)

    for key, values in query_lists.items():
        clean_values = [value for value in values if value not in (None, "")]
        if clean_values:
            # Current 1C HTTP service accepts include as one comma-separated value.
            # Other repeated filters are used only for future contract compatibility;
            # known documents are queried one by one by the repository.
            params[key] = ",".join(str(value) for value in clean_values) if key == "include" else clean_values

    return {key: value for key, value in params.items() if _meaningful_query_value(value)}


def _meaningful_query_value(value: Any) -> bool:
    if value in (None, "", []):
        return False
    if isinstance(value, str) and value.strip() in {"", "-", "—", "0"}:
        return False
    if isinstance(value, list):
        return any(_meaningful_query_value(item) for item in value)
    return True
