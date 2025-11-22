from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from enum import Enum

from db import get_db
from auth_routes import get_current_user_v3
from models import Cliente, Owner, User
from datetime import datetime
import pytz

br_tz = pytz.timezone("America/Sao_Paulo")

router = APIRouter(prefix="/v3/cliente", tags=["Cliente"])


# =========================================================
# ENUMS
# =========================================================
class TipoClienteEnum(str, Enum):
    VENDEDOR = "VENDEDOR"
    PRESTADOR = "PRESTADOR"


# =========================================================
# SCHEMAS
# =========================================================
class ClienteCreate(BaseModel):
    nome: str = Field(min_length=1)

    endereco_cep: Optional[str] = None
    endereco_cidade: Optional[str] = None
    endereco_estado: Optional[str] = None

    preco_shopee: Optional[float] = None
    preco_ml: Optional[float] = None
    preco_avulso: Optional[float] = None

    endereco_rua: Optional[str] = None
    endereco_numero: Optional[str] = None
    endereco_complemento: Optional[str] = None
    endereco_bairro: Optional[str] = None

    documento_cliente: Optional[str] = None
    email_cliente: Optional[str] = None
    telefone_cliente: Optional[str] = None

    # ENUM cliente_tipo (VENDEDOR / PRESTADOR)
    tipo_cliente: Optional[TipoClienteEnum] = None


class ClienteOut(BaseModel):
    id_cliente: int
    nome: str

    endereco_cep: Optional[str] = None
    endereco_cidade: Optional[str] = None
    endereco_estado: Optional[str] = None

    endereco_rua: Optional[str] = None
    endereco_numero: Optional[str] = None
    endereco_complemento: Optional[str] = None
    endereco_bairro: Optional[str] = None

    documento_cliente: Optional[str] = None
    email_cliente: Optional[str] = None
    telefone_cliente: Optional[str] = None

    tipo_cliente: Optional[TipoClienteEnum] = None

    preco_shopee: Optional[float] = None
    preco_ml: Optional[float] = None
    preco_avulso: Optional[float] = None

    ativo: bool
    criado_em: datetime

    class Config:
        from_attributes = True


class ClientePatch(BaseModel):
    nome: Optional[str] = None

    endereco_cep: Optional[str] = None
    endereco_cidade: Optional[str] = None
    endereco_estado: Optional[str] = None

    endereco_rua: Optional[str] = None
    endereco_numero: Optional[str] = None
    endereco_complemento: Optional[str] = None
    endereco_bairro: Optional[str] = None

    documento_cliente: Optional[str] = None
    email_cliente: Optional[str] = None
    telefone_cliente: Optional[str] = None

    tipo_cliente: Optional[TipoClienteEnum] = None

    preco_shopee: Optional[float] = None
    preco_ml: Optional[float] = None
    preco_avulso: Optional[float] = None

    ativo: Optional[bool] = None


# =========================================================
# POST — CRIAR CLIENTE
# =========================================================
@router.post(
    "/create-cliente",
    response_model=ClienteOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um cliente para um owner vinculado",
)
def criar_cliente(
    payload: ClienteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_v3),
):
    now = datetime.now(br_tz)

    novo = Cliente(
        owner_id=current_user.owner_id,
        nome=payload.nome,

        # endereço básico
        endereco_cep=payload.endereco_cep,
        endereco_cidade=payload.endereco_cidade,
        endereco_estado=payload.endereco_estado,

        # preços
        preco_shopee=payload.preco_shopee,
        preco_ml=payload.preco_ml,
        preco_avulso=payload.preco_avulso,

        # endereço detalhado
        endereco_rua=payload.endereco_rua,
        endereco_numero=payload.endereco_numero,
        endereco_complemento=payload.endereco_complemento,
        endereco_bairro=payload.endereco_bairro,

        # dados do cliente
        documento_cliente=payload.documento_cliente,
        email_cliente=payload.email_cliente,
        telefone_cliente=payload.telefone_cliente,
        tipo_cliente=payload.tipo_cliente,  # ENUM

        criado_em=now,
        # ativo_cliente usa o default do banco (provavelmente TRUE)
    )

    db.add(novo)
    db.commit()
    db.refresh(novo)

    return novo


# =========================================================
# GET — LISTA TODOS OS CLIENTES DO OWNER
# =========================================================
@router.get("/", response_model=List[ClienteOut])
def listar_clientes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_v3),
):
    clientes = (
        db.query(Cliente)
        .filter(Cliente.owner_id == current_user.owner_id)
        .order_by(Cliente.id_cliente.desc())
        .all()
    )
    return clientes


# =========================================================
# PATCH — ATUALIZAR CLIENTE
# =========================================================
@router.patch("/{id_cliente}", response_model=ClienteOut)
def atualizar_cliente(
    id_cliente: int,
    payload: ClientePatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_v3),
):
    cliente = (
        db.query(Cliente)
        .filter(
            Cliente.id_cliente == id_cliente,
            Cliente.owner_id == current_user.owner_id,
        )
        .first()
    )

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(cliente, campo, valor)

    db.commit()
    db.refresh(cliente)
    return cliente


# =========================================================
# DELETE — DELETAR CLIENTE
# =========================================================
@router.delete("/{id_cliente}")
def deletar_cliente(
    id_cliente: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_v3),
):
    cliente = (
        db.query(Cliente)
        .filter(
            Cliente.id_cliente == id_cliente,
            Cliente.owner_id == current_user.owner_id,
        )
        .first()
    )

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    db.delete(cliente)
    db.commit()

    return {"detail": "Cliente deletado com sucesso."}
