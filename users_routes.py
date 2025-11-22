from __future__ import annotations
from datetime import datetime
import pytz

br_tz = pytz.timezone("America/Sao_Paulo")

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from sqlalchemy.orm import Session

from db import get_db
from models import Owner, User
from auth_routes import get_current_user_v3, get_password_hash  # <-- usa o auth v3


router = APIRouter(prefix="/v3/users", tags=["Users v3"])


# =========================================================
# SCHEMAS COMUNS
# =========================================================
class OwnerCreatePayload(BaseModel):
    nome_empresa: str = Field(min_length=1)
    documento_empresa: Optional[str] = None
    email_contato: Optional[EmailStr] = None
    telefone_empresa: Optional[str] = None


class UserBasePayload(BaseModel):
    nome: str = Field(min_length=1)
    email: Optional[EmailStr] = None
    username: str = Field(min_length=1)
    password_hash: str = Field(
        min_length=1,
        description="Senha em texto plano, será hasheada",
    )
    sobrenome: Optional[str] = None
    documento: Optional[str] = None
    telefone: Optional[str] = None
    endereco_rua: Optional[str] = None
    endereco_numero: Optional[str] = None
    endereco_complemento: Optional[str] = None
    endereco_bairro: Optional[str] = None
    endereco_cidade: Optional[str] = None
    endereco_estado: Optional[str] = None
    endereco_cep: Optional[str] = None


class CreateUserRequest(BaseModel):
    """
    Payload para criar:
    - um OWNER (tipo BASE)
    - um USER ADMIN vinculado a esse OWNER
    """
    owner: OwnerCreatePayload
    user: UserBasePayload


class OwnerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_owner: int
    nome_empresa: str
    tipo_empresa: str
    email_contato: Optional[str] = None
    telefone_empresa: Optional[str] = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # 🔁 aqui ajustamos para bater com models.User.user_id
    user_id: int
    owner_id: int
    nome: str
    email: Optional[str] = None
    username: Optional[str] = None
    tipo: str
    ativo: bool
    coletador: bool


class CreateUserResponse(BaseModel):
    owner: OwnerOut
    user: UserOut


# --------- Schemas específicos para ENTREGADOR ---------
class EntregadorCreatePayload(UserBasePayload):
    """
    Mesmos campos do UserBasePayload, mas o tipo será forçado para ENTREGADOR
    e owner_id virá do usuário logado.
    """
    pass


class CreateEntregadorResponse(BaseModel):
    user: UserOut


# =========================================================
# ENDPOINT: CRIAR OWNER + USER ADMIN
# =========================================================
@router.post(
    "/create-user",
    response_model=CreateUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um OWNER (BASE) e um USER ADMIN vinculado",
)
def create_owner_and_admin(
    payload: CreateUserRequest,
    db: Session = Depends(get_db),
):

    now = datetime.now(br_tz)

    # Cria OWNER (tipo_empresa = EMPRESA)
    owner = Owner(
        nome_empresa=payload.owner.nome_empresa,
        tipo_empresa="BASE",
        documento_empresa=payload.owner.documento_empresa,
        email_contato=payload.owner.email_contato,
        telefone_empresa=payload.owner.telefone_empresa,
        criado_em=now,
        atualizado_em=now,
    )
    db.add(owner)
    db.flush()  # garante que owner.id_owner foi preenchido

    # Cria USER ADMIN vinculado a esse OWNER
    u = payload.user

    hashed = get_password_hash(u.password_hash)

    user = User(
        owner_id=owner.id_owner,
        nome=u.nome,
        email=u.email,
        username=u.username,
        password_hash=hashed,
        tipo="ADMIN",       # enum mt.user_tipo
        ativo=True,
        coletador=False,
        sobrenome=u.sobrenome,
        documento=u.documento,
        telefone=u.telefone,
        endereco_rua=u.endereco_rua,
        endereco_numero=u.endereco_numero,
        endereco_complemento=u.endereco_complemento,
        endereco_bairro=u.endereco_bairro,
        endereco_cidade=u.endereco_cidade,
        endereco_estado=u.endereco_estado,
        endereco_cep=u.endereco_cep,
        criado_em=now,
        atualizado_em=now,
    )
    db.add(user)
    db.commit()
    db.refresh(owner)
    db.refresh(user)

    return CreateUserResponse(owner=owner, user=user)


# =========================================================
# ENDPOINT: CRIAR ENTREGADOR (usa owner_id do usuário logado)
# =========================================================
@router.post(
    "/create-entregador",
    response_model=CreateEntregadorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um ENTREGADOR vinculado ao mesmo owner do usuário logado",
)
def create_entregador(
    payload: EntregadorCreatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_v3),
):
    """
    - Descobre quem enviou o POST via get_current_user_v3
    - Usa current_user.owner_id como owner_id do novo ENTREGADOR
    - Força:
        tipo = 'ENTREGADOR'
        ativo = True
        coletador = True
    """

    if not current_user.owner_id:
        raise HTTPException(
            status_code=400,
            detail="Usuário atual não possui owner_id vinculado.",
        )

    now = datetime.now(br_tz)
    # Hash da senha
    hashed = get_password_hash(payload.password_hash)

    new_user = User(
        owner_id=current_user.owner_id,
        nome=payload.nome,
        email=payload.email,
        username=payload.username,
        password_hash=hashed,
        tipo="ENTREGADOR",   # enum mt.user_tipo
        ativo=True,
        coletador=True,
        sobrenome=payload.sobrenome,
        documento=payload.documento,
        telefone=payload.telefone,
        endereco_rua=payload.endereco_rua,
        endereco_numero=payload.endereco_numero,
        endereco_complemento=payload.endereco_complemento,
        endereco_bairro=payload.endereco_bairro,
        endereco_cidade=payload.endereco_cidade,
        endereco_estado=payload.endereco_estado,
        endereco_cep=payload.endereco_cep,
        criado_em=now,
        atualizado_em=now,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return CreateEntregadorResponse(user=new_user)
