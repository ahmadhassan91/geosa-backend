"""
API Dependencies

Dependency injection for FastAPI routes.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import User, UserRole
from src.infrastructure.config import settings
from src.infrastructure.database import get_async_session
from src.infrastructure.repositories import SQLAlchemyUserRepository


# Security
security = HTTPBearer(auto_error=False)


async def get_db() -> AsyncSession:
    """Get database session."""
    async for session in get_async_session():
        yield session


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    """Get current user from JWT token (optional)."""
    if credentials is None:
        return None
    
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None
    
    user_repo = SQLAlchemyUserRepository(db)
    user = await user_repo.get_by_id(UUID(user_id))
    
    if user is None or not user.is_active:
        return None
    
    return user


async def get_current_user(
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> User:
    """Get current user (required)."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_hydrographer(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current user with hydrographer or admin role."""
    if not user.can_review():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Hydrographer or Admin role required.",
        )
    return user


async def get_current_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current user with admin role."""
    if not user.can_manage():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Admin role required.",
        )
    return user


# Type aliases for cleaner route signatures
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]
HydrographerUser = Annotated[User, Depends(get_current_hydrographer)]
AdminUser = Annotated[User, Depends(get_current_admin)]
