import hashlib
import secrets
from uuid import uuid4


from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Bracelet, User
from backend.schemas import (
    BraceletCreate,
    BraceletCreatedResponse,
    BraceletResponse,
)
from backend.security import get_current_user
from backend.schemas import BraceletRename


router = APIRouter(
    prefix="/bracelets",
    tags=["Браслеты"],
)


@router.post(
    "",
    response_model=BraceletCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_test_bracelet(
    data: BraceletCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device_key = secrets.token_urlsafe(32)

    device_key_hash = hashlib.sha256(
        device_key.encode("utf-8")
    ).hexdigest()

    bracelet = Bracelet(
        user_id=current_user.id,
        serial_number=f"TEST-{uuid4().hex}",
        name=data.name,
        device_key_hash=device_key_hash,
    )

    db.add(bracelet)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(bracelet)

    return BraceletCreatedResponse(
        id=bracelet.id,
        name=bracelet.name,
        serial_number=bracelet.serial_number,
        last_seen_at=bracelet.last_seen_at,
        created_at=bracelet.created_at,
        device_key=device_key,
    )


@router.get(
    "",
    response_model=list[BraceletResponse],
)
def get_my_bracelets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = (
        select(Bracelet)
        .where(Bracelet.user_id == current_user.id)
        .order_by(Bracelet.id.desc())
    )

    return db.scalars(statement).all()

@router.post(
    "/{bracelet_id}/rotate-key",
    response_model=BraceletCreatedResponse,
)
def rotate_device_key(
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

    new_key = secrets.token_urlsafe(32)

    bracelet.device_key_hash = hashlib.sha256(
        new_key.encode("utf-8")
    ).hexdigest()

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(bracelet)

    return BraceletCreatedResponse(
        id=bracelet.id,
        name=bracelet.name,
        serial_number=bracelet.serial_number,
        last_seen_at=bracelet.last_seen_at,
        created_at=bracelet.created_at,
        device_key=new_key,
    )

@router.patch(
    "/{bracelet_id}",
    response_model=BraceletResponse,
)
def rename_bracelet(
    bracelet_id: int,
    data: BraceletRename,
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

    bracelet.name = data.name

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(bracelet)

    return bracelet