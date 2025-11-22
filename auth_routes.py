# auth_routes_v3.py
from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request,
    Response,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from passlib.context import CryptContext
from passlib.exc import UnknownHashError
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from sqlalchemy import select, or_

from db import get_db
from models import User


# =========================================================
# CONFIGURACOES JWT
# =========================================================
SECRET_KEY = os.getenv("SECRET_KEY", "troque-esta-chave-em-producao")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REMEMBER_ME_EXPIRE_DAYS = int(os.getenv("REMEMBER_ME_EXPIRE_DAYS", "30"))

ACCESS_COOKIE_NAME = os.getenv("ACCESS_COOKIE_NAME", "access_token")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() in ("1", "true", "yes")
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN")  # ex.: ".seudominio.com"


# =========================================================
# SENHAS (bcrypt)
# =========================================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# =========================================================
# SECURITY BEARER
# =========================================================
security = HTTPBearer(auto_error=False)

router = APIRouter(prefix="/v3/auth", tags=["Auth v3"])


# =========================================================
# SCHEMAS
# =========================================================
class Token(BaseModel):
    access_token: str
    token_type: str


class LoginPayload(BaseModel):
    identifier: str = Field(min_length=1, description="email ou username")
    password: str
    remember: bool = False


class UserMe(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_user: int
    email: Optional[str]
    username: Optional[str]
    owner_id: int
    nome: str
    tipo: str


# =========================================================
# JWT UTILS
# =========================================================
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=60))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# =========================================================
# FUNÇÕES DE USUÁRIO
# =========================================================
def get_user_by_identifier(db: Session, identifier: str) -> Optional[User]:
    identifier = (identifier or "").strip()
    if not identifier:
        return None

    stmt = select(User).where(
        or_(
            User.email == identifier,
            User.username == identifier
        )
    )
    return db.scalars(stmt).first()


def authenticate_user(db: Session, identifier: str, password: str) -> Optional[User]:
    user = get_user_by_identifier(db, identifier)
    if not user:
        return None

    stored = user.password_hash
    if not stored:
        return None

    # Tenta bcrypt
    try:
        if verify_password(password, stored):
            return user
    except UnknownHashError:
        # fallback: texto puro (apenas se ainda estiver usando hash antigo)
        if password == stored:
            return user
        return None

    return None


# =========================================================
# DEPENDÊNCIA get_current_user_v3
# =========================================================
async def get_current_user_v3(
    request: Request,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    """
    1. Lê token do cookie OU do header Authorization: Bearer
    2. Decodifica e valida
    3. Busca user no DB
    4. Retorna User ORM
    """

    # token via cookie
    token: Optional[str] = request.cookies.get(ACCESS_COOKIE_NAME)

    # token via header Authorization
    if not token and credentials and credentials.scheme.lower() == "bearer":
        token = credentials.credentials

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Token ausente",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Token inválido (sem 'sub').")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")

    user = get_user_by_identifier(db, sub)
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.")

    return user


# =========================================================
# AUTH ROUTES
# =========================================================
@router.post("/token", response_model=Token)
async def login_return_token(
    login_payload: LoginPayload,
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, login_payload.identifier, login_payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Login ou senha incorretos.")

    subject = user.email or user.username
    expires = timedelta(days=REMEMBER_ME_EXPIRE_DAYS) if login_payload.remember else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    access_token = create_access_token(data={"sub": subject}, expires_delta=expires)

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login")
async def login_set_cookie(
    login_payload: LoginPayload,
    response: Response,
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, login_payload.identifier, login_payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Login ou senha incorretos.")

    subject = user.email or user.username

    expires = timedelta(days=REMEMBER_ME_EXPIRE_DAYS) if login_payload.remember else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    token = create_access_token(data={"sub": subject}, expires_delta=expires)
    samesite = "None" if COOKIE_SECURE else "Lax"

    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=samesite,
        max_age=int(expires.total_seconds()),
        path="/",
        domain=COOKIE_DOMAIN,
    )

    return {
        "ok": True,
        "user": {
            "id_user": user.id_user,
            "owner_id": user.owner_id,
            "email": user.email,
            "username": user.username,
            "nome": user.nome,
            "tipo": user.tipo,
        }
    }


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key=ACCESS_COOKIE_NAME,
        path="/",
        domain=COOKIE_DOMAIN,
    )
    return {"ok": True}


@router.get("/me", response_model=UserMe)
async def read_me(current_user: User = Depends(get_current_user_v3)):
    return current_user
