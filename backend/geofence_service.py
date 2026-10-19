from datetime import datetime, timezone
from math import atan2, cos, radians, sin, sqrt

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Geofence, Location, Notification


def distance_m(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)

    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1_rad)
        * cos(lat2_rad)
        * sin(delta_lon / 2) ** 2
    )

    a = max(0.0, min(1.0, a))

    return 6_371_000 * 2 * atan2(sqrt(a), sqrt(1 - a))


def evaluate_location(
    db: Session,
    location: Location,
    user_id: int,
):
    zone = db.scalar(
        select(Geofence)
        .where(Geofence.bracelet_id == location.bracelet_id)
        .with_for_update()
    )

    if zone is None or not zone.enabled:
        return

    recorded_at = location.recorded_at
    now = datetime.now(timezone.utc)

    age_seconds = (now - recorded_at).total_seconds()

    # Старые точки и точки из будущего не подтверждают выход.
    if age_seconds > 300 or age_seconds < -30:
        return

    previous_time = zone.last_evaluated_at

    # Повторное время и запоздавшие записи не увеличивают счётчик.
    if previous_time is not None and recorded_at <= previous_time:
        return

    if previous_time is not None:
        gap_seconds = (recorded_at - previous_time).total_seconds()

        if gap_seconds > 300:
            zone.outside_count = 0

    zone.last_evaluated_at = recorded_at

    accuracy = location.accuracy_m

    if accuracy is None:
        zone.outside_count = 0
        return

    distance = distance_m(
        zone.center_latitude,
        zone.center_longitude,
        location.latitude,
        location.longitude,
    )

    definitely_inside = distance + accuracy <= zone.radius_m
    definitely_outside = distance - accuracy > zone.radius_m

    if definitely_inside:
        zone.outside_count = 0
        zone.is_outside = False
        return

    if not definitely_outside:
        zone.outside_count = 0
        return

    if zone.is_outside:
        return

    zone.outside_count = min(zone.outside_count + 1, 3)

    if zone.outside_count < 3:
        return

    zone.is_outside = True

    source_label = (
        "телефона"
        if location.source == "phone"
        else "браслета"
    )

    notification = Notification(
        user_id=user_id,
        bracelet_id=location.bracelet_id,
        message=(
            f'Выход из зоны «{zone.name}» подтверждён '
            f'по координатам {source_label}. '
            f'Расстояние до центра: {distance:.0f} м. '
            f'Радиус зоны: {zone.radius_m:g} м.'
        ),
    )

    db.add(notification)