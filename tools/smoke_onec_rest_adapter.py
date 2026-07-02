#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke test for the target read-only 1C REST adapter skeleton."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from recon_erp_1c.infrastructure.onec_rest.client import OneCRestConfig, OneCRestClient, OneCRestError, onec_rest_status


def main() -> None:
    status = onec_rest_status()
    result = {
        "ok": True,
        "configured": status.get("configured"),
        "missing": status.get("missing", []),
        "snapshot_path": status.get("snapshot_path"),
        "health_path": status.get("health_path"),
    }

    if status.get("configured"):
        try:
            result["health"] = OneCRestClient.from_env().health()
        except OneCRestError as exc:
            result["ok"] = False
            result["error"] = str(exc)
    else:
        cfg = OneCRestConfig.from_env()
        result["base_url_configured"] = bool(cfg.base_url)
        result["auth_configured"] = bool(cfg.token or (cfg.username and cfg.password))

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
