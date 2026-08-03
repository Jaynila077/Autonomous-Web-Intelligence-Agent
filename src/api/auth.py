# src/api/auth.py
import os
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlmodel import Session, select

from src.api.database import get_session, User
from src.api.schemas import UserRegisterRequest, UserLoginRequest, TokenResponse

# Security Configs
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "awis_dev_secret_key_change_in_production_12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 Hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/auth", tags=["Authentication"])


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str, email: str) -> str:
    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str:
    """
    Decodes and validates a JWT token. Returns the user_id ('sub' claim).
    Raises HTTPException 401 on invalid or expired token.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload: missing sub claim.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate token credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegisterRequest, db: Session = Depends(get_session)):
    statement = select(User).where(User.email == payload.email)
    existing_user = db.exec(statement).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists.",
        )

    new_user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(user_id=new_user.id, email=new_user.email)
    return TokenResponse(access_token=token, token_type="bearer", user_id=new_user.id)


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLoginRequest, db: Session = Depends(get_session)):
    statement = select(User).where(User.email == payload.email)
    user = db.exec(statement).first()
    
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user_id=user.id, email=user.email)
    return TokenResponse(access_token=token, token_type="bearer", user_id=user.id)