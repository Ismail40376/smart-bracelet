from pydantic import ValidationError
from backend.schemas import AlertRuleUpdate
from fastapi import APIRouter, Depends, HTTPException, status

from fastapi import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import AlertRule, Bracelet, User
from backend.schemas import AlertRuleCreate, AlertRuleResponse
from backend.security import get_current_user


router = APIRouter(
    prefix="/bracelets",
    tags=["Правила уведомлений"],
)


def check_owner(
    bracelet_id: int,
    user_id: int,
    db: Session,
):
    bracelet = db.scalar(
        select(Bracelet).where(
            Bracelet.id == bracelet_id,
            Bracelet.user_id == user_id,
        )
    )

    if bracelet is None:
        raise HTTPException(
            status_code=404,
            detail="Браслет не найден",
        )


@router.post(
    "/{bracelet_id}/alert-rules",
    response_model=AlertRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_alert_rule(
    bracelet_id: int,
    data: AlertRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_owner(bracelet_id, current_user.id, db)

    rule = AlertRule(
        bracelet_id=bracelet_id,
        **data.model_dump(),
    )

    db.add(rule)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(rule)

    return rule


@router.get(
    "/{bracelet_id}/alert-rules",
    response_model=list[AlertRuleResponse],
)
def get_alert_rules(
    bracelet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_owner(bracelet_id, current_user.id, db)

    statement = (
        select(AlertRule)
        .where(AlertRule.bracelet_id == bracelet_id)
        .order_by(AlertRule.id)
    )

    return db.scalars(statement).all()

@router.patch(
    "/{bracelet_id}/alert-rules/{rule_id}",
    response_model=AlertRuleResponse,
)
def update_alert_rule(
    bracelet_id: int,
    rule_id: int,
    data: AlertRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_owner(bracelet_id, current_user.id, db)

    rule = db.scalar(
        select(AlertRule).where(
            AlertRule.id == rule_id,
            AlertRule.bracelet_id == bracelet_id,
        )
    )

    if rule is None:
        raise HTTPException(
            status_code=404,
            detail="Правило не найдено",
        )

    current_values = {
        "metric": rule.metric,
        "min_value": rule.min_value,
        "max_value": rule.max_value,
        "enabled": rule.enabled,
        "cooldown_seconds": rule.cooldown_seconds,
    }

    changes = data.model_dump(exclude_unset=True)
    current_values.update(changes)

    try:
        validated = AlertRuleCreate.model_validate(
            current_values
        )
    except ValidationError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        )

    for field, value in validated.model_dump().items():
        setattr(rule, field, value)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(rule)

    return rule

@router.delete(
    "/{bracelet_id}/alert-rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_alert_rule(
    bracelet_id: int,
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_owner(bracelet_id, current_user.id, db)

    rule = db.scalar(
        select(AlertRule).where(
            AlertRule.id == rule_id,
            AlertRule.bracelet_id == bracelet_id,
        )
    )

    if rule is None:
        raise HTTPException(
            status_code=404,
            detail="Правило не найдено",
        )

    db.delete(rule)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return Response(status_code=status.HTTP_204_NO_CONTENT)