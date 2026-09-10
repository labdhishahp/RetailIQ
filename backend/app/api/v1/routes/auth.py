from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

import jwt

from app.api.deps import get_current_user, get_db, require_admin
from app.core.config import settings
from app.core.security import (
    create_access_token, create_refresh_token, decode_token, hash_password, verify_password,
)
from app.models import User, UserPreference
from app.schemas.auth import (
    LoginRequest, PasswordChange, PreferenceRead, PreferenceUpdate, RefreshRequest,
    TokenResponse, UserCreate, UserRead, UserUpdate,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _tokens(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(subject=user.email, role=user.role),
        refresh_token=create_refresh_token(subject=user.email),
        expires_in=settings.access_token_minutes * 60,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    return _tokens(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        data = decode_token(payload.refresh_token)
        if data.get("type") != "refresh":
            raise jwt.InvalidTokenError("Wrong token type")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid refresh token") from None
    user = db.scalar(select(User).where(User.email == data["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive")
    return _tokens(user)


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserRead)
def update_me(payload: UserUpdate, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(payload: PasswordChange, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Current password is incorrect")
    user.hashed_password = hash_password(payload.new_password)
    db.commit()


@router.get("/me/preferences", response_model=PreferenceRead)
def get_preferences(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pref = db.scalar(select(UserPreference).where(UserPreference.user_id == user.id))
    if not pref:
        pref = UserPreference(user_id=user.id, settings={}, theme="light")
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref


@router.put("/me/preferences", response_model=PreferenceRead)
def set_preferences(payload: PreferenceUpdate, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    pref = db.scalar(select(UserPreference).where(UserPreference.user_id == user.id))
    if not pref:
        pref = UserPreference(user_id=user.id, settings={}, theme="light")
        db.add(pref)
    if payload.settings is not None:
        pref.settings = payload.settings
    if payload.theme is not None:
        pref.theme = payload.theme
    db.commit()
    db.refresh(pref)
    return pref


@router.get("/users", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return db.scalars(select(User).order_by(User.id)).all()


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db),
                _: User = Depends(require_admin)):
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(
        email=payload.email.lower(), full_name=payload.full_name,
        hashed_password=hash_password(payload.password), role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
