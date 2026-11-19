"""Auth endpoints: register, login, refresh."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm  # noqa: F401 (docs)
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from ..dependencies import get_db
from ..models import User
from ..security import (hash_password, verify_password, make_access_token,
                        make_refresh_token, decode_token, AuthError)

router = APIRouter(prefix="/api/auth", tags=["auth"])

ROLE_WEIGHTS = {"customer": 0, "agent": 1, "admin": 2}


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(default="customer", pattern="^(customer|agent|admin)$")


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class RefreshIn(BaseModel):
    refresh_token: str


def _pair(user: User) -> TokenPair:
    return TokenPair(
        access_token=make_access_token(user.id, user.role),
        refresh_token=make_refresh_token(user.id, user.role),
        user={"id": user.id, "email": user.email, "name": user.name, "role": user.role},
    )


@router.post("/register", response_model=TokenPair, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    # Self-serve registration may only create customers; staff accounts are
    # seeded by operators. Prevents trivial privilege escalation.
    if body.role != "customer":
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "self-serve signup is customer-only; staff accounts are provisioned by admins")
    if db.query(User).filter(User.email == body.email.lower()).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")
    user = User(email=body.email.lower(),
                password_hash=hash_password(body.password),
                name=body.name, role="customer")
    db.add(user)
    db.commit()
    db.refresh(user)
    return _pair(user)


@router.post("/login", response_model=TokenPair)
def login(body: dict, db: Session = Depends(get_db)):
    email = (body.get("email") or "").lower().strip()
    password = body.get("password") or ""
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "invalid email or password")
    return _pair(user)


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshIn, db: Session = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token, expected_type="refresh")
    except AuthError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    user = db.get(User, payload["sub"])
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unknown user")
    return _pair(user)
