from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(
        String(254),
        unique=True,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )


class Bracelet(Base):
    __tablename__ = "bracelets"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )
    serial_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
    )
    name: Mapped[str] = mapped_column(String(100))
    device_key_hash: Mapped[str] = mapped_column(String(255))
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )


class Measurement(Base):
    __tablename__ = "measurements"
    __table_args__ = (
        CheckConstraint(
            "heart_rate > 0",
            name="ck_measurements_heart_rate",
        ),
        CheckConstraint(
            "spo2 BETWEEN 0 AND 100",
            name="ck_measurements_spo2",
        ),
        CheckConstraint(
            "battery_level BETWEEN 0 AND 100",
            name="ck_measurements_battery",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )
    bracelet_id: Mapped[int] = mapped_column(
        ForeignKey("bracelets.id"),
        index=True,
    )
    heart_rate: Mapped[int | None] = mapped_column(Integer)
    spo2: Mapped[float | None] = mapped_column(Float)
    battery_level: Mapped[int | None] = mapped_column(Integer)
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = (
        CheckConstraint(
            "latitude BETWEEN -90 AND 90",
            name="ck_locations_latitude",
        ),
        CheckConstraint(
            "longitude BETWEEN -180 AND 180",
            name="ck_locations_longitude",
        ),
        CheckConstraint(
            "accuracy_m >= 0",
            name="ck_locations_accuracy",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )
    bracelet_id: Mapped[int] = mapped_column(
        ForeignKey("bracelets.id"),
        index=True,
    )
    source: Mapped[str] = mapped_column(
        String(20),
        default="phone",
        server_default="phone",
    )
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    accuracy_m: Mapped[float | None] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )


class AlertRule(Base):
    __tablename__ = "alert_rules"
    __table_args__ = (
        CheckConstraint(
            "metric IN ('heart_rate', 'spo2', 'battery_level')",
            name="ck_alert_rules_metric",
        ),
        CheckConstraint(
            "min_value IS NOT NULL OR max_value IS NOT NULL",
            name="ck_alert_rules_has_boundary",
        ),
        CheckConstraint(
            "min_value <= max_value",
            name="ck_alert_rules_boundary_order",
        ),
        CheckConstraint(
            "cooldown_seconds >= 0",
            name="ck_alert_rules_cooldown",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )
    bracelet_id: Mapped[int] = mapped_column(
        ForeignKey("bracelets.id"),
        index=True,
    )
    metric: Mapped[str] = mapped_column(String(30))
    min_value: Mapped[float | None] = mapped_column(Float)
    max_value: Mapped[float | None] = mapped_column(Float)
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )
    cooldown_seconds: Mapped[int] = mapped_column(
        Integer,
        default=300,
    )
    last_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )
    bracelet_id: Mapped[int] = mapped_column(
        ForeignKey("bracelets.id"),
        index=True,
    )
    measurement_id: Mapped[int | None] = mapped_column(
        ForeignKey("measurements.id"),
    )
    alert_rule_id: Mapped[int | None] = mapped_column(
        ForeignKey("alert_rules.id", ondelete="SET NULL"),
    )
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )


class Geofence(Base):
    __tablename__ = "geofences"

    __table_args__ = (
        CheckConstraint(
            "center_latitude BETWEEN -90 AND 90",
            name="ck_geofences_latitude",
        ),
        CheckConstraint(
            "center_longitude BETWEEN -180 AND 180",
            name="ck_geofences_longitude",
        ),
        CheckConstraint(
            "radius_m > 0",
            name="ck_geofences_radius",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )
    bracelet_id: Mapped[int] = mapped_column(
        ForeignKey("bracelets.id"),
        unique=True,
    )
    name: Mapped[str] = mapped_column(String(100))
    center_latitude: Mapped[float] = mapped_column(Float)
    center_longitude: Mapped[float] = mapped_column(Float)
    radius_m: Mapped[float] = mapped_column(Float)
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    outside_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )
    is_outside: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )
    last_evaluated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )