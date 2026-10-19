from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import AlertRule, Measurement, Notification


def create_measurement_notifications(
    db: Session,
    measurement: Measurement,
    user_id: int,
):
    statement = (
        select(AlertRule)
        .where(
            AlertRule.bracelet_id == measurement.bracelet_id,
            AlertRule.enabled.is_(True),
        )
        .order_by(AlertRule.id)
        .with_for_update()
    )

    rules = db.scalars(statement).all()
    now = datetime.now(timezone.utc)

    labels = {
        "heart_rate": "Пульс",
        "spo2": "SpO₂",
        "battery_level": "Заряд батареи",
    }

    for rule in rules:
        if rule.metric not in labels:
            continue

        value = getattr(measurement, rule.metric)

        if value is None:
            continue

        if rule.last_triggered_at is not None:
            next_allowed_at = (
                rule.last_triggered_at
                + timedelta(seconds=rule.cooldown_seconds)
            )

            if now < next_allowed_at:
                continue

        too_low = (
            rule.min_value is not None
            and value < rule.min_value
        )

        too_high = (
            rule.max_value is not None
            and value > rule.max_value
        )

        if not (too_low or too_high):
            continue

        direction = "ниже" if too_low else "выше"
        boundary = rule.min_value if too_low else rule.max_value

        notification = Notification(
            user_id=user_id,
            bracelet_id=measurement.bracelet_id,
            measurement_id=measurement.id,
            alert_rule_id=rule.id,
            message=(
                f"{labels[rule.metric]}: {value:g} — "
                f"{direction} установленной границы {boundary:g}."
            ),
        )

        db.add(notification)
        rule.last_triggered_at = now