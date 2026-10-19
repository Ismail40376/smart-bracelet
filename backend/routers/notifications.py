from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Notification, User
from backend.schemas import NotificationResponse
from backend.security import get_current_user


router = APIRouter(
    prefix="/notifications",
    tags=["Уведомления"],
)


@router.get(
    "",
    response_model=list[NotificationResponse],
)
def get_notifications(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = (
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(
            Notification.created_at.desc(),
            Notification.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    )

    return db.scalars(statement).all()

@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )

    if notification is None:
        raise HTTPException(
            status_code=404,
            detail="Уведомление не найдено",
        )

    notification.is_read = True

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(notification)

    return notification