"""Request bodies. Every numeric field has bounds and refuses NaN/inf, so bad input is a 422
before it reaches the simulation or the wallets."""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field

from app.services.auth import MAX_PASSWORD_BYTES


def _fits_bcrypt(password: str) -> str:
    """bcrypt reads at most 72 bytes; a 72-character password with diacritics can be longer."""
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError(f"parola nu poate depasi {MAX_PASSWORD_BYTES} de octeti")
    return password


Username = Annotated[str, Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")]
Password = Annotated[str, Field(min_length=3, max_length=MAX_PASSWORD_BYTES), AfterValidator(_fits_bcrypt)]
Mode = Literal["Eco", "Profit"]


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_BYTES)


class RegisterRequest(BaseModel):
    username: Username
    password: Password


class CreateUserRequest(BaseModel):
    username: Username
    password: Password
    house_id: int | None = Field(default=None, ge=1)
    is_admin: bool = False


class UpdateUserRequest(BaseModel):
    password: Password | None = None
    house_id: int | None = Field(default=None, ge=0, description="0 = fara casa")
    is_admin: bool | None = None


class ModeRequest(BaseModel):
    mode: Mode


class DeviceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    power_w: float = Field(gt=0, le=50_000, allow_inf_nan=False)
    critical: bool = False
    status_on: bool = False


class DeviceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    power_w: float | None = Field(default=None, gt=0, le=50_000, allow_inf_nan=False)
    critical: bool | None = None
    status_on: bool | None = None


class SettingsUpdate(BaseModel):
    mode: Mode | None = None
    backup_reserve_percent: float | None = Field(default=None, ge=0, le=60, allow_inf_nan=False)


class TradingPreferencesUpdate(BaseModel):
    selling_enabled: bool | None = None
    buying_enabled: bool | None = None
    price_mode: Literal["fixed", "discount"] | None = None
    fixed_price_lei_kwh: float | None = Field(default=None, ge=0, le=10, allow_inf_nan=False)
    discount_percent: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    min_sell_price_lei_kwh: float | None = Field(default=None, ge=0, le=10, allow_inf_nan=False)


class TransferToVPPRequest(BaseModel):
    energy_kwh: float = Field(gt=0, le=1000, allow_inf_nan=False)


class ManualTradeRequest(BaseModel):
    seller_house_id: int = Field(ge=1)
    buyer_house_id: int = Field(ge=1)
    energy_kwh: float = Field(gt=0, le=1000, allow_inf_nan=False)
    price_lei_kwh: float = Field(ge=0, le=10, allow_inf_nan=False)


class SpeedRequest(BaseModel):
    tick_seconds: float = Field(ge=0.2, le=60, allow_inf_nan=False)


class ConfigUpdate(BaseModel):
    controller: Literal["reguli", "mpc"] | None = None
    tick_seconds: float | None = Field(default=None, ge=0.2, le=60, allow_inf_nan=False)
    import_max_kw: float | None = Field(default=None, ge=0, le=100_000, allow_inf_nan=False)
    export_max_kw: float | None = Field(default=None, ge=0, le=100_000, allow_inf_nan=False)
    internal_line_kw: float | None = Field(default=None, ge=0, le=100_000, allow_inf_nan=False)
    p2p_price_factor: float | None = Field(default=None, gt=0, le=1, allow_inf_nan=False)
    min_p2p_balance_lei: float | None = Field(default=None, ge=0, le=10_000, allow_inf_nan=False)
    seed: int | None = Field(default=None, ge=0)


class HouseSpecRequest(BaseModel):
    description: str = Field(default="", max_length=200)
    people: int = Field(ge=1, le=12)
    home_daytime: bool
    heating: str = Field(min_length=1, max_length=50)
    insulation: str = Field(min_length=1, max_length=10)
    devices: list[str] = Field(default_factory=list, max_length=50)
