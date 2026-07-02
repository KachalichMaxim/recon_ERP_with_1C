#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only REST adapter for fetching normalized 1C reconciliation DTOs.

This is the target connector for the reconciliation service. It talks to a
dedicated 1C REST API, not to raw OData objects.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
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
    snapshot_path: str = "/reconciliation/v1/snapshot"
    health_path: str = "/reconciliation/v1/health"

    @classmethod
    def from_env(cls) -> "OneCRestConfig":
        return cls(
            base_url=os.environ.get("RECON_ONEC_REST_BASE_URL", "").strip().rstrip("/"),
            token=os.environ.get("RECON_ONEC_REST_TOKEN", "").strip(),
            username=os.environ.get("RECON_ONEC_REST_USER", "").strip(),
            password=os.environ.get("RECON_ONEC_REST_PASSWORD", "").strip(),
            timeout=int(os.environ.get("RECON_ONEC_REST_TIMEOUT", "60") or "60"),
            snapshot_path=os.environ.get("RECON_ONEC_REST_SNAPSHOT_PATH", "/reconciliation/v1/snapshot").strip()
            or "/reconciliation/v1/snapshot",
            health_path=os.environ.get("RECON_ONEC_REST_HEALTH_PATH", "/reconciliation/v1/health").strip()
            or "/reconciliation/v1/health",
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
        "snapshot_path": config.snapshot_path,
        "health_path": config.health_path,
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
        request = Request(url, data=body, headers=self._headers(), method=method.upper())
        try:
            with urlopen(request, timeout=self.config.timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
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

    def health(self) -> dict[str, Any]:
        return self._request_json("GET", self.config.health_path)

    def get_reconciliation_snapshot(self, request: dict[str, Any]) -> dict[str, Any]:
        payload = self._request_json("GET", self.config.snapshot_path, snapshot_query_params(request))
        if "snapshot" not in payload:
            # Collection-like responses may already be a snapshot object.
            payload = {"ok": payload.get("ok", True), "snapshot": payload}
        return payload


def snapshot_query_params(request: dict[str, Any]) -> dict[str, Any]:
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
        "mode": request.get("mode", "delivery_reconciliation"),
        "contract_version": request.get("contract_version", "reconciliation.v1"),
        "date_from": period.get("date_from", ""),
        "date_to": period.get("date_to", ""),
        "spec_number": delivery.get("spec_number", ""),
        "base_contract": delivery.get("base_contract", ""),
        "buyer_contract_code": delivery.get("buyer_contract_code1c", ""),
        "committent_contract_code": delivery.get("committent_contract_code1c", ""),
    }

    first_org = next((item for item in organizations if isinstance(item, dict)), {})
    params.update(
        {
            "organization_code": first_org.get("code1c", ""),
            "organization_inn": first_org.get("inn", ""),
            "organization_name": first_org.get("name") or first_org.get("abbr") or "",
        }
    )

    first_counterparty = next((item for item in counterparties if isinstance(item, dict)), {})
    params.update(
        {
            "counterparty_code": first_counterparty.get("code1c", ""),
            "counterparty_inn": first_counterparty.get("inn", ""),
            "counterparty_name": first_counterparty.get("name") or first_counterparty.get("abbr") or "",
        }
    )

    query_lists: dict[str, list[Any]] = {
        "contract_code": [],
        "contract_number": [],
        "contract_role": [],
        "document_code": [],
        "document_number": [],
        "document_type": [],
        "include": [],
    }
    for contract in contracts:
        if not isinstance(contract, dict):
            continue
        query_lists["contract_code"].append(contract.get("code1c", ""))
        query_lists["contract_number"].append(contract.get("number", ""))
        query_lists["contract_role"].append(contract.get("role", ""))
    for document in documents:
        if not isinstance(document, dict):
            continue
        query_lists["document_code"].append(document.get("code1c", ""))
        query_lists["document_number"].append(document.get("number", ""))
        query_lists["document_type"].append(document.get("kind", ""))
    for key, enabled in include.items():
        if enabled:
            query_lists["include"].append(key)

    for key, values in query_lists.items():
        clean_values = [value for value in values if value not in (None, "")]
        if clean_values:
            params[key] = clean_values

    return {key: value for key, value in params.items() if value not in (None, "", [])}
