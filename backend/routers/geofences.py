from datetime import datetime, timezone
from math import atan2, cos, radians, sin, sqrt

from backend.models import Location
from backend.schemas import GeofenceStatusResponse
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Bracelet, Geofence, User
from backend.schemas import GeofenceResponse, GeofenceSave
from backend.security import get_current_user


router = APIRouter(
    prefix="/bracelets",
    tags=["Безопасная зона"],
)


@router.put(
    "/{bracelet_id}/geofence",
    response_model=GeofenceResponse,
)
def save_geofence(
    bracelet_id: int,
    data: GeofenceSave,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bracelet = db.scalar(
        select(Bracelet)
        .where(
            Bracelet.id == bracelet_id,
            Bracelet.user_id == current_user.id,
        )
        .with_for_update()
    )

    if bracelet is None:
        raise HTTPException(
            status_code=404,
            detail="Браслет не найден",
        )

    geofence = db.scalar(
        select(Geofence).where(
            Geofence.bracelet_id == bracelet_id
        )
    )

    if geofence is None:
        geofence = Geofence(
            bracelet_id=bracelet_id,
            **data.model_dump(),
        )
        db.add(geofence)
    else:
        for field, value in data.model_dump().items():
            setattr(geofence, field, value)
    geofence.outside_count = 0
    geofence.is_outside = False
    geofence.last_evaluated_at = datetime.now(timezone.utc)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(geofence)

    return geofence



@router.get(
    "/{bracelet_id}/geofence",
    response_model=GeofenceResponse,
)
def get_geofence(
    bracelet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bracelet = db.scalar(
        select(Bracelet).where(
            Bracelet.id == bracelet_id,
            Bracelet.user_id == current_user.id,
        )
    )

    if bracelet is None:
        raise HTTPException(
            status_code=404,
            detail="Браслет не найден",
        )

    geofence = db.scalar(
        select(Geofence).where(
            Geofence.bracelet_id == bracelet_id
        )
    )

    if geofence is None:
        raise HTTPException(
            status_code=404,
            detail="Безопасная зона пока не настроена",
        )

    return geofence

def calculate_distance_m(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    earth_radius_m = 6_371_000

    latitude1 = radians(lat1)
    latitude2 = radians(lat2)

    delta_latitude = radians(lat2 - lat1)
    delta_longitude = radians(lon2 - lon1)

    a = (
        sin(delta_latitude / 2) ** 2
        + cos(latitude1)
        * cos(latitude2)
        * sin(delta_longitude / 2) ** 2
    )

    a = max(0.0, min(1.0, a))

    angle = 2 * atan2(sqrt(a), sqrt(1 - a))

    return earth_radius_m * angle


@router.get(
    "/{bracelet_id}/geofence/status",
    response_model=GeofenceStatusResponse,
)
def get_geofence_status(
    bracelet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bracelet = db.scalar(
        select(Bracelet).where(
            Bracelet.id == bracelet_id,
            Bracelet.user_id == current_user.id,
        )
    )

    if bracelet is None:
        raise HTTPException(
            status_code=404,
            detail="Браслет не найден",
        )

    geofence = db.scalar(
        select(Geofence).where(
            Geofence.bracelet_id == bracelet_id
        )
    )

    if geofence is None:
        raise HTTPException(
            status_code=404,
            detail="Безопасная зона пока не настроена",
        )

    result = GeofenceStatusResponse(
        bracelet_id=bracelet_id,
        status="no_location",
        radius_m=geofence.radius_m,
    )

    if not geofence.enabled:
        result.status = "disabled"
        return result

    location = db.scalar(
        select(Location)
        .where(Location.bracelet_id == bracelet_id)
        .order_by(
            Location.recorded_at.desc(),
            Location.id.desc(),
        )
        .limit(1)
    )

    if location is None:
        return result

    distance = calculate_distance_m(
        geofence.center_latitude,
        geofence.center_longitude,
        location.latitude,
        location.longitude,
    )

    result.distance_m = round(distance, 2)
    result.accuracy_m = location.accuracy_m
    result.source = location.source
    result.recorded_at = location.recorded_at

    age_seconds = (
        datetime.now(timezone.utc) - location.recorded_at
    ).total_seconds()

    if age_seconds > 300 or age_seconds < -30:
        result.status = "stale"
        return result

    accuracy = location.accuracy_m

    if accuracy is None:
        result.status = "uncertain"
    elif distance + accuracy <= geofence.radius_m:
        result.status = "inside"
    elif distance - accuracy > geofence.radius_m:
        result.status = "outside"
    else:
        result.status = "uncertain"

    return result