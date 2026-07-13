from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

from recon_erp_1c.bootstrap.config import MariaDbConfig


class MariaDbDependencyError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MariaDbConnectionFactory:
    config: MariaDbConfig

    @contextmanager
    def connect(self) -> Iterator[Any]:
        try:
            import pymysql
            from pymysql.cursors import DictCursor
        except ModuleNotFoundError as exc:
            raise MariaDbDependencyError("Install pymysql to use the ERP MariaDB adapter") from exc

        connection_kwargs = {
            "host": self.config.host,
            "port": self.config.port,
            "user": self.config.user,
            "password": self.config.password,
            "database": self.config.database,
            "charset": "utf8mb4",
            "cursorclass": DictCursor,
            "read_timeout": self.config.read_timeout_seconds,
            "write_timeout": self.config.write_timeout_seconds,
            "connect_timeout": self.config.connect_timeout_seconds,
            "autocommit": True,
        }
        if self.config.bind_address:
            connection_kwargs["bind_address"] = self.config.bind_address

        connection = pymysql.connect(**connection_kwargs)
        try:
            yield connection
        finally:
            connection.close()
