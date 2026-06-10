from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    MONGO_URI: str = os.getenv("OACHKATZL_MONGO_URI", "mongodb://localhost:27017/oachkatzl")
    REDIS_URL: str = os.getenv("OACHKATZL_REDIS_URL", "redis://localhost:6379/0")
    JWT_SECRET: str = os.getenv("OACHKATZL_JWT_SECRET", "dev-secret-change-in-prod")
    JWT_EXPIRY_HOURS: int = int(os.getenv("OACHKATZL_JWT_EXPIRY_HOURS", "24"))
    JWT_2FA_PENDING_EXPIRY_MINUTES: int = 5
    ENCRYPTION_KEY: str = os.getenv("OACHKATZL_ENCRYPTION_KEY", "")
    ADMIN_USER: str = os.getenv("OACHKATZL_ADMIN_USER", "admin")
    ADMIN_PASSWORD: str = os.getenv("OACHKATZL_ADMIN_PASSWORD", "changeme")
    ADMIN_EMAIL: str = os.getenv("OACHKATZL_ADMIN_EMAIL", "admin@localhost")
    TOTP_ISSUER: str = os.getenv("OACHKATZL_TOTP_ISSUER", "Oachkatzl")
    REQUIRE_2FA: bool = os.getenv("OACHKATZL_REQUIRE_2FA", "false").lower() == "true"
    CORS_ORIGINS: list[str] = os.getenv(
        "OACHKATZL_CORS_ORIGINS", "http://localhost:5173"
    ).split(",")
    GIT_WORKDIR: str = os.getenv("OACHKATZL_GIT_WORKDIR", "/tmp/oachkatzl")

    # LDAP / Active Directory — optional bootstrap via env vars
    LDAP_SERVER_URL: str  = os.getenv("OACHKATZL_LDAP_URL", "")
    LDAP_BIND_DN: str     = os.getenv("OACHKATZL_LDAP_BIND_DN", "")
    LDAP_BIND_PASSWORD: str = os.getenv("OACHKATZL_LDAP_BIND_PASSWORD", "")
    LDAP_BASE_DN: str     = os.getenv("OACHKATZL_LDAP_BASE_DN", "")
    LDAP_USER_FILTER: str = os.getenv("OACHKATZL_LDAP_USER_FILTER", "(sAMAccountName={username})")
    CELERY_BROKER_URL: str = os.getenv(
        "OACHKATZL_CELERY_BROKER_URL", os.getenv("OACHKATZL_REDIS_URL", "redis://localhost:6379/0")
    )
    CELERY_RESULT_BACKEND: str = os.getenv(
        "OACHKATZL_CELERY_RESULT_BACKEND",
        os.getenv("OACHKATZL_REDIS_URL", "redis://localhost:6379/0"),
    )

    def validate_production(self) -> None:
        """Raise RuntimeError when insecure defaults are detected at startup."""
        if self.JWT_SECRET in {"dev-secret-change-in-prod", ""}:
            raise RuntimeError(
                "OACHKATZL_JWT_SECRET is not set or uses the insecure default. "
                "Set a long random secret before starting in production."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
