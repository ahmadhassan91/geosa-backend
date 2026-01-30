"""
Authentication Routes

API endpoints for authentication and user management.
"""

from datetime import datetime, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from jose import jwt
from passlib.context import CryptContext

from src.api.dependencies import AdminUser, CurrentUser, DbSession
from src.application.dtos import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from src.domain.entities import User, UserRole
from src.infrastructure.config import settings
from src.infrastructure.repositories import SQLAlchemyUserRepository

router = APIRouter(prefix="/auth", tags=["auth"])

# Password hashing
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(user_id: UUID) -> tuple[str, int]:
    """Create a JWT access token."""
    expire_minutes = settings.jwt_access_token_expire_minutes
    expire = datetime.utcnow() + timedelta(minutes=expire_minutes)
    
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    
    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    
    return token, expire_minutes * 60


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserCreate,
    db: DbSession,
):
    """
    Register a new user.
    
    For PoC, registration is open. In production, this should require admin approval.
    """
    user_repo = SQLAlchemyUserRepository(db)
    
    # Check if username exists
    existing = await user_repo.get_by_username(request.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )
    
    # Create user
    try:
        role = UserRole(request.role)
    except ValueError:
        role = UserRole.VIEWER
    
    user = User(
        id=uuid4(),
        username=request.username,
        email=request.email,
        hashed_password=hash_password(request.password),
        role=role,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    created = await user_repo.create(user)
    
    return UserResponse(
        id=created.id,
        username=created.username,
        email=created.email,
        role=created.role.value,
        is_active=created.is_active,
        created_at=created.created_at,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: DbSession,
):
    """
    Login with username and password.
    
    Returns a JWT token for subsequent API calls.
    """
    # Trim whitespace from username (handles copy-paste with spaces)
    username = request.username.strip()
    
    user_repo = SQLAlchemyUserRepository(db)
    
    # Get user
    user = await user_repo.get_by_username(username)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    
    # Verify password
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    
    # Check if active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    # Create token
    token, expires_in = create_access_token(user.id)
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user: CurrentUser,
):
    """Get current authenticated user info."""
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: DbSession,
    user: AdminUser,
    page: int = 1,
    page_size: int = 20,
):
    """List all users (admin only)."""
    user_repo = SQLAlchemyUserRepository(db)
    users, _ = await user_repo.list_all(page=page, page_size=page_size)
    
    return [
        UserResponse(
            id=u.id,
            username=u.username,
            email=u.email,
            role=u.role.value,
            is_active=u.is_active,
            created_at=u.created_at,
        )
        for u in users
    ]
