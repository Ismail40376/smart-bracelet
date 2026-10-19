from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Bracelet, Location, User
from backend.schemas import LocationCreate, LocationResponse
from backend.security import get_current_user
from backend.geofence_service import evaluate_location


router = APIRouter(
    prefix="/bracelets",
    tags=["Локация"],
)


def get_owned_bracelet(
    bracelet_id: int,
    user_id: int,
    db: Session,
) -> Bracelet:
    bracelet = db.scalar(
        select(Bracelet).where(
            Bracelet.id == bracelet_id,
            Bracelet.user_id == user_id,
        )
    )

    if bracelet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Браслет не найден",
        )

    return bracelet


@router.post(
    "/{bracelet_id}/locations",
    response_model=LocationResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_location(
    bracelet_id: int,
    data: LocationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bracelet = get_owned_bracelet(
        bracelet_id,
        current_user.id,
        db,
    )

    location = Location(
        bracelet_id=bracelet.id,
        latitude=data.latitude,
        longitude=data.longitude,
        accuracy_m=data.accuracy_m,
        source=data.source,
        recorded_at=data.recorded_at,
    )

    db.add(location)

    try:
        db.flush()

        evaluate_location(
            db=db,
            location=location,
            user_id=current_user.id,
        )

        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(location)

    return location


@router.get(
    "/{bracelet_id}/locations/latest",
    response_model=LocationResponse,
)
def get_latest_location(
    bracelet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bracelet = get_owned_bracelet(
        bracelet_id,
        current_user.id,
        db,
    )

    statement = (
        select(Location)
        .where(Location.bracelet_id == bracelet.id)
        .order_by(
            Location.recorded_at.desc(),
            Location.id.desc(),
        )
        .limit(1)
    )

    location = db.scalar(statement)

    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="У браслета пока нет координат",
        )

    return location

@router.get(
    "/{bracelet_id}/locations",
    response_model=list[LocationResponse],
)
def get_location_history(
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

    bracelet = get_owned_bracelet(
        bracelet_id,
        current_user.id,
        db,
    )

    statement = select(Location).where(
        Location.bracelet_id == bracelet.id
    )

    if date_from is not None:
        statement = statement.where(
            Location.recorded_at >= date_from
        )

    if date_to is not None:
        statement = statement.where(
            Location.recorded_at <= date_to
        )

    statement = (
        statement
        .order_by(
            Location.recorded_at.desc(),
            Location.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    )

    return db.scalars(statement).all()