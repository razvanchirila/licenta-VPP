"""Settings read once from backend/.env (see .env.example)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

DEFAULT_DATABASE_URL = "postgresql+asyncpg://vpp:vpp@localhost:15432/vpp"
DEFAULT_CORS_ORIGINS = "http://localhost:13000,http://localhost:5173"
MIN_SECRET_LENGTH = 16


def _env_float(name: str, default: float) -> float:
    return float(os.getenv(name, default))


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_date(name: str) -> date:
    raw = os.getenv(name)
    return date.fromisoformat(raw) if raw else date.today()


@dataclass
class Settings:
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development").strip().lower())
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL))
    jwt_secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET_KEY", ""))
    jwt_expire_hours: float = field(default_factory=lambda: _env_float("JWT_EXPIRE_HOURS", 24))
    host: str = field(default_factory=lambda: os.getenv("HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    cors_origins: list[str] = field(default_factory=lambda: [
        o.strip() for o in os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",") if o.strip()
    ])
    sim_controller: str = field(default_factory=lambda: os.getenv("SIM_CONTROLLER", "reguli"))
    sim_tick_seconds: float = field(default_factory=lambda: _env_float("SIM_TICK_SECONDS", 2.0))
    sim_step_minutes: int = field(default_factory=lambda: int(os.getenv("SIM_STEP_MINUTES", "5")))
    sim_seed: int = field(default_factory=lambda: int(os.getenv("SIM_SEED", "42")))
    sim_start_date: date = field(default_factory=lambda: _env_date("SIM_START_DATE"))
    sim_autostart: bool = field(default_factory=lambda: _env_bool("SIM_AUTOSTART", True))
    sim_data: str = field(default_factory=lambda: os.getenv("SIM_DATA", "real").strip().lower())
    sim_price_year: int = field(default_factory=lambda: int(os.getenv("SIM_PRICE_YEAR", "2025")))
    initial_wallet_lei: float = field(default_factory=lambda: _env_float("INITIAL_WALLET_LEI", 100.0))
    operator_wallet_lei: float = field(default_factory=lambda: _env_float("OPERATOR_WALLET_LEI", 10000.0))
    login_max_failures: int = field(default_factory=lambda: int(os.getenv("LOGIN_MAX_FAILURES", "5")))
    register_max_per_hour: int = field(default_factory=lambda: int(os.getenv("REGISTER_MAX_PER_HOUR", "30")))

    def __post_init__(self) -> None:
        if not 1 <= self.sim_step_minutes <= 60 or 1440 % self.sim_step_minutes:
            raise ValueError(f"SIM_STEP_MINUTES = {self.sim_step_minutes}: trebuie sa imparta exact ziua "
                             "(1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30 sau 60)")

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def sim_dt_hours(self) -> float:
        return self.sim_step_minutes / 60

    def require_secret(self) -> None:
        if len(self.jwt_secret) < MIN_SECRET_LENGTH:
            raise RuntimeError(
                f"JWT_SECRET_KEY lipseste sau e prea scurt (minim {MIN_SECRET_LENGTH} caractere). "
                "Copiaza backend/.env.example in backend/.env si completeaza-l."
            )


settings = Settings()
