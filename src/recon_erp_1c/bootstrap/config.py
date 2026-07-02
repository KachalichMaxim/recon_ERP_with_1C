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
    listen_host: str = "0.0.0.0"
    listen_port: int = 8780
    require_erp_token: bool = False

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            erp_db=MariaDbConfig.from_env(),
            onec_rest=OneCRestConfig.from_env(),
            listen_host=os.environ.get("RECON_API_HOST", "0.0.0.0"),
            listen_port=int(os.environ.get("RECON_API_PORT", "8780")),
            require_erp_token=os.environ.get("RECON_REQUIRE_ERP_TOKEN", "0").strip().lower() in {"1", "true", "yes"},
        )
