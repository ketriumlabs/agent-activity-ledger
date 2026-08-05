"""12-factor config: everything overridable via env vars, safe local-first defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    host: str = os.environ.get("LEDGER_HOST", "127.0.0.1")
    port: int = int(os.environ.get("LEDGER_PORT", "8420"))
    data_dir: Path = Path(os.environ.get("LEDGER_DATA_DIR", "./data"))
    demo: bool = os.environ.get("DEMO", "").lower() in ("1", "true", "yes")

    smtp_host: str | None = os.environ.get("LEDGER_SMTP_HOST")
    smtp_port: int = int(os.environ.get("LEDGER_SMTP_PORT", "587"))
    smtp_user: str | None = os.environ.get("LEDGER_SMTP_USER")
    smtp_password: str | None = os.environ.get("LEDGER_SMTP_PASSWORD")
    digest_to: str | None = os.environ.get("LEDGER_DIGEST_TO")

    @property
    def db_path(self) -> Path:
        return self.data_dir / "ledger.db"

    def redacted(self) -> dict[str, object]:
        """Effective config with secrets redacted, printed at startup."""
        d = {
            "host": self.host,
            "port": self.port,
            "data_dir": str(self.data_dir),
            "demo": self.demo,
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "smtp_user": self.smtp_user,
            "smtp_password": "***" if self.smtp_password else None,
            "digest_to": self.digest_to,
        }
        return d


def get_settings() -> Settings:
    return Settings()
