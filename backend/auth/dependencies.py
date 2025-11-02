from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from db.models import User
from db.base import get_db
from .utils import decode_token


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the current autenticated user from the token"""

    token = credentials.credentials
    payload = decode_token(token=token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="could not validate credentials",
        )

    user_id: Optional[int] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="could not validate credentials",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    return user


async def get_current_user_ws(
    token: str = Query(..., description="JWT access token"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency to get current user for WebSocket connections"""

    payload = decode_token(token=token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    user_id: Optional[int] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    return user


async def check_usage_limit(
    # Depends: Used for dependency injection — lets you “inject” logic like authentication into routes automatically.
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency to check if user have credit"""

    if not current_user.can_create_project:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usage limit reached. Please upgrade your plan.",
        )

    current_user.increment_usage()
    await db.commit()
    await db.refresh(current_user)

    return current_user
