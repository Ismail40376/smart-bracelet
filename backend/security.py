import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User


PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")

SECRET_KEY = os.getenv("JWT_SECRET", "")

if len(SECRET_KEY) < 32:
    raise RuntimeError(
        "Добавь JWT_SECRET длиной минимум 32 символа в .env"
    )

ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 30

password_hasher = PasswordHash.recommended()
bearer_scheme = HTTPBearer(auto_error=False)

DUMMY_HASH = password_hasher.hash(
    "dummy-password-for-login-timing"
)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=TOKEN_EXPIRE_MINUTES),
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Требуется действующий токен доступа",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "iat", "exp"]},
        )

        user_id = int(payload["sub"])

    except (InvalidTokenError, ValueError, TypeError):
        raise unauthorized

    user = db.get(User, user_id)

    if user is None:
        raise unauthorized

    return user