import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Bracelet, Measurement, User
from backend.schemas import (
    MeasurementCreate,
    MeasurementResponse,
)
from backend.security import get_current_user
from backend.services import create_measurement_notifications


router = APIRouter(
    prefix="/bracelets",
    tags=["Измерения"],
)


@router.post(
    "/{bracelet_id}/measurements",
    response_model=MeasurementResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_measurement(
    bracelet_id: int,
    data: MeasurementCreate,
    device_key: str | None = Header(
        default=None,
        alias="X-Device-Key",
    ),
    db: Session = Depends(get_db),
):
    bracelet = db.get(Bracelet, bracelet_id)

    provided_hash = hashlib.sha256(
        (device_key or "").encode("utf-8")
    ).hexdigest()

    expected_hash = (
        bracelet.device_key_hash
        if bracelet is not None
        else "0" * 64
    )

    key_is_valid = secrets.compare_digest(
        provided_hash,
        expected_hash,
    )

    if not device_key or bracelet is None or not key_is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный ID браслета или ключ устройства",
        )

    measurement = Measurement(
        bracelet_id=bracelet.id,
        heart_rate=data.heart_rate,
        spo2=data.spo2,
        battery_level=data.battery_level,
        measured_at=data.measured_at,
    )

    bracelet.last_seen_at = datetime.now(timezone.utc)

    db.add(measurement)

    try:
        db.flush()

        create_measurement_notifications(
            db=db,
            measurement=measurement,
            user_id=bracelet.user_id,
        )

        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(measurement)

    return measurement


@router.get(
    "/{bracelet_id}/measurements/latest",
    response_model=MeasurementResponse,
)
def get_latest_measurement(
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Браслет не найден",
        )

    statement = (
        select(Measurement)
        .where(Measurement.bracelet_id == bracelet.id)
        .order_by(
            Measurement.measured_at.desc(),
            Measurement.id.desc(),
        )
        .limit(1)
    )

    measurement = db.scalar(statement)

    if measurement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="У браслета пока нет измерений",
        )

    return measurement

@router.get(
    "/{bracelet_id}/measurements",
    response_model=list[MeasurementResponse],
)
def get_measurement_history(
    bracelet_id: int,
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for date in (date_from, date_to):
        if date is not None:
            if date.tzinfo is None or date.utcoffset() is None:
                raise HTTPException(
                    status_code=422,
                    detail="Укажи часовой пояс в датах",
                )

    if (
        date_from is not None
        and date_to is not None
        and date_from > date_to
    ):
        raise HTTPException(
            status_code=422,
            detail="Начальная дата должна быть не позже конечной",
        )

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

    statement = select(Measurement).where(
        Measurement.bracelet_id == bracelet.id
    )

    if date_from is not None:
        statement = statement.where(
            Measurement.measured_at >= date_from
        )

    if date_to is not None:
        statement = statement.where(
            Measurement.measured_at <= date_to
        )

    statement = (
        statement
        .order_by(
            Measurement.measured_at.desc(),
            Measurement.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    )

    return db.scalars(statement).all()