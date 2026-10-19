from datetime import timezone
from pydantic import model_validator
from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Имя не должно быть пустым")

        return value


class LoginRequest(BaseModel):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class BraceletCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Название не должно быть пустым")

        return value


class BraceletResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    serial_number: str
    last_seen_at: datetime | None
    created_at: datetime


class BraceletCreatedResponse(BraceletResponse):
    device_key: str

class MeasurementCreate(BaseModel):
    heart_rate: int | None = Field(default=None, gt=0)
    spo2: float | None = Field(default=None, ge=0, le=100)
    battery_level: int | None = Field(default=None, ge=0, le=100)
    measured_at: datetime

    @field_validator("measured_at")
    @classmethod
    def validate_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "Укажи часовой пояс: например +05:00 или Z"
            )

        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_readings(self):
        if all(
            value is None
            for value in (
                self.heart_rate,
                self.spo2,
                self.battery_level,
            )
        ):
            raise ValueError(
                "Передай хотя бы один показатель"
            )

        return self


class MeasurementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bracelet_id: int
    heart_rate: int | None
    spo2: float | None
    battery_level: int | None
    measured_at: datetime
    received_at: datetime

class LocationCreate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0)
    source: Literal["phone", "bracelet"] = "phone"
    recorded_at: datetime

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "Укажи часовой пояс: например +05:00 или Z"
            )

        return value.astimezone(timezone.utc)


class LocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bracelet_id: int
    latitude: float
    longitude: float
    accuracy_m: float | None
    source: Literal["phone", "bracelet"]
    recorded_at: datetime
    received_at: datetime

class AlertRuleCreate(BaseModel):
    metric: Literal["heart_rate", "spo2", "battery_level"]
    min_value: float | None = Field(default=None, allow_inf_nan=False)
    max_value: float | None = Field(default=None, allow_inf_nan=False)
    enabled: bool = True
    cooldown_seconds: int = Field(default=300, ge=0)

    @model_validator(mode="after")
    def validate_boundaries(self):
        if self.min_value is None and self.max_value is None:
            raise ValueError("Укажи хотя бы одну границу")

        if (
            self.min_value is not None
            and self.max_value is not None
            and self.min_value > self.max_value
        ):
            raise ValueError("Минимум не может быть больше максимума")

        if self.metric in ("spo2", "battery_level"):
            for value in (self.min_value, self.max_value):
                if value is not None and not 0 <= value <= 100:
                    raise ValueError("Граница должна быть от 0 до 100")

        if self.metric == "heart_rate":
            for value in (self.min_value, self.max_value):
                if value is not None and value <= 0:
                    raise ValueError("Граница пульса должна быть положительной")

        return self


class AlertRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bracelet_id: int
    metric: str
    min_value: float | None
    max_value: float | None
    enabled: bool
    cooldown_seconds: int
    last_triggered_at: datetime | None

class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    bracelet_id: int
    measurement_id: int | None
    alert_rule_id: int | None
    message: str
    is_read: bool
    created_at: datetime

class AlertRuleUpdate(BaseModel):
    metric: Literal[
        "heart_rate", "spo2", "battery_level"
    ] | None = None

    min_value: float | None = Field(
        default=None,
        allow_inf_nan=False,
    )
    max_value: float | None = Field(
        default=None,
        allow_inf_nan=False,
    )
    enabled: bool | None = None
    cooldown_seconds: int | None = Field(
        default=None,
        ge=0,
    )

class GeofenceSave(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    center_latitude: float = Field(
        ge=-90,
        le=90,
        allow_inf_nan=False,
    )
    center_longitude: float = Field(
        ge=-180,
        le=180,
        allow_inf_nan=False,
    )
    radius_m: float = Field(
        gt=0,
        allow_inf_nan=False,
    )
    enabled: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Название зоны не должно быть пустым")

        return value


class GeofenceResponse(GeofenceSave):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bracelet_id: int
    created_at: datetime

class GeofenceStatusResponse(BaseModel):
    bracelet_id: int
    status: Literal[
        "inside",
        "outside",
        "uncertain",
        "stale",
        "disabled",
        "no_location",
    ]
    distance_m: float | None = None
    radius_m: float
    accuracy_m: float | None = None
    source: Literal["phone", "bracelet"] | None = None
    recorded_at: datetime | None = None

class BraceletRename(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Название не должно быть пустым")

        return value