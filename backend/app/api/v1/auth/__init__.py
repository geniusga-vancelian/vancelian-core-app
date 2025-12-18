"""
Authentication API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timedelta
from uuid import UUID
import jwt as pyjwt
import bcrypt

from app.infrastructure.database import get_db
from app.core.users.models import User, UserStatus
from app.schemas.auth import RegisterRequest, RegisterResponse, LoginRequest, LoginResponse
from app.infrastructure.settings import get_settings

router = APIRouter()
settings = get_settings()
# Use bcrypt directly to avoid passlib compatibility issues
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(user_id: UUID, email: str) -> str:
    """Create JWT access token"""
    # Assign roles based on email (DEV: hardcoded admin for gaelitier@gmail.com)
    roles = ["USER"]
    if email.lower() == "gaelitier@gmail.com":
        roles = ["USER", "ADMIN"]
    
    payload = {
        "sub": str(user_id),
        "email": email,
        "roles": roles,
        "exp": datetime.utcnow() + timedelta(hours=24),
        "iat": datetime.utcnow(),
    }
    return pyjwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Register a new user account with email and password",
)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
) -> RegisterResponse:
    """Register a new user"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Hash password using bcrypt directly (72 byte limit)
    password_bytes = request.password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    password_hash = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')
    
    # Create user
    user = User(
        email=request.email,
        password_hash=password_hash,
        first_name=request.first_name,
        last_name=request.last_name,
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return RegisterResponse(
        user_id=str(user.id),
        email=user.email,
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="User login",
    description="Authenticate user with email and password, returns JWT token",
)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """Login user and return JWT token"""
    # DEV: Debug logging
    import logging
    logger = logging.getLogger(__name__)
    if settings.DEV_MODE:
        logger.debug(f"Login attempt for email: {request.email}, password length: {len(request.password)}")
    
    # Find user
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        if settings.DEV_MODE:
            logger.debug(f"User not found for email: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password using bcrypt directly (72 byte limit)
    password_bytes = request.password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    if settings.DEV_MODE:
        logger.debug(f"Verifying password for user {user.email}, password bytes length: {len(password_bytes)}, hash exists: {bool(user.password_hash)}")
    
    password_valid = False
    if user.password_hash:
        try:
            password_valid = bcrypt.checkpw(password_bytes, user.password_hash.encode('utf-8'))
            if settings.DEV_MODE:
                logger.debug(f"Password verification result: {password_valid}")
        except Exception as e:
            if settings.DEV_MODE:
                logger.error(f"Error verifying password: {e}")
            password_valid = False
    
    if not password_valid:
        if settings.DEV_MODE:
            logger.debug(f"Password verification failed for user {user.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check user status
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is suspended"
        )
    
    # Create access token
    access_token = create_access_token(user.id, user.email)
    
    return LoginResponse(
        access_token=access_token,
        user_id=str(user.id),
        email=user.email,
    )
