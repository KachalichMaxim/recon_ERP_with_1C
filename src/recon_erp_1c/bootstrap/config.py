from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MariaDbConfig:
    host: str = ""
    port: int = 3306
    database: str = ""
    user: str = ""
    password: str = ""
    connect_timeout_seconds: int = 5
    read_timeout_seconds: int = 30
    write_timeout_seconds: int = 30

    @classmethod
    def from_env(cls) -> "MariaDbConfig":
        return cls(
            host=os.environ.get("RECON_ERP_DB_HOST", ""),
            port=int(os.environ.get("RECON_ERP_DB_PORT", "3306")),
            database=os.environ.get("RECON_ERP_DB_NAME", ""),
            user=os.environ.get("RECON_ERP_DB_USER", ""),
            password=os.environ.get("RECON_ERP_DB_PASSWORD", ""),
            connect_timeout_seconds=int(os.environ.get("RECON_ERP_DB_CONNECT_TIMEOUT", "5")),
            read_timeout_seconds=int(os.environ.get("RECON_ERP_DB_READ_TIMEOUT", "30")),
            write_timeout_seconds=int(os.environ.get("RECON_ERP_DB_WRITE_TIMEOUT", "30")),
        )

    def missing_fields(self) -> list[str]:
        missing: list[str] = []
        if not self.host:
            missing.append("RECON_ERP_DB_HOST")
        if not self.database:
            missing.append("RECON_ERP_DB_NAME")
        if not self.user:
            missing.append("RECON_ERP_DB_USER")
        if not self.password:
            missing.append("RECON_ERP_DB_PASSWORD")
        return missing

    @property
    def configured(self) -> bool:
        return not self.missing_fields()

    def safe_status(self) -> dict[str, object]:
        return {
            "configured": self.configured,
            "missing": self.missing_fields(),
            "host_configured": bool(self.host),
            "database_configured": bool(self.database),
            "user_configured": bool(self.user),
            "password_configured": bool(self.password),
            "port": self.port,
            "connect_timeout_seconds": self.connect_timeout_seconds,
            "read_timeout_seconds": self.read_timeout_seconds,
            "write_timeout_seconds": self.write_timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class OneCRestConfig:
    base_url: str = ""
    token: str = ""
    timeout_seconds: int = 60

    @classmethod
    def from_env(cls) -> "OneCRestConfig":
        return cls(
            base_url=os.environ.get("RECON_ONEC_REST_BASE_URL", "").rstrip("/"),
            token=os.environ.get("RECON_ONEC_REST_TOKEN", ""),
            timeout_seconds=int(os.environ.get("RECON_ONEC_REST_TIMEOUT", "60")),
        )


@dataclass(frozen=True, slots=True)
class AppConfig:
    erp_db: MariaDbConfig
    onec_rest: OneCRestConfig
    environment: str = "development"
    listen_host: str = "0.0.0.0"
    listen_port: int = 8780
    require_erp_token: bool = False
    allow_direct_erp_login: bool = False
    ui_demo: bool = False
    dev_auth: bool = False
    erp_token_validate_url: str = ""
    erp_token_validate_timeout_seconds: int = 10

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            erp_db=MariaDbConfig.from_env(),
            onec_rest=OneCRestConfig.from_env(),
            environment=os.environ.get("RECON_ENV", "development").strip().lower() or "development",
            listen_host=os.environ.get("RECON_API_HOST", "0.0.0.0"),
            listen_port=int(os.environ.get("RECON_API_PORT", "8780")),
            require_erp_token=os.environ.get("RECON_REQUIRE_ERP_TOKEN", "0").strip().lower() in {"1", "true", "yes"},
            allow_direct_erp_login=os.environ.get("RECON_ALLOW_DIRECT_ERP_LOGIN", "0").strip().lower() in {"1", "true", "yes"},
            ui_demo=os.environ.get("RECON_UI_DEMO", "0").strip().lower() in {"1", "true", "yes"},
            dev_auth=os.environ.get("RECON_DEV_AUTH", "0").strip().lower() in {"1", "true", "yes"},
            erp_token_validate_url=os.environ.get("RECON_ERP_TOKEN_VALIDATE_URL", "").strip(),
            erp_token_validate_timeout_seconds=int(os.environ.get("RECON_ERP_TOKEN_VALIDATE_TIMEOUT", "10")),
        )

    @property
    def production(self) -> bool:
        return self.environment in {"prod", "production"} or self.require_erp_token

    @property
    def direct_login_enabled(self) -> bool:
        return self.allow_direct_erp_login or self.dev_auth
