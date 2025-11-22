from __future__ import annotations

from typing import Optional, List, Dict, Any
from datetime import datetime

import pytz
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db import get_db
from auth_routes import get_current_user_v3
from models import User, Contract  # <-- ajuste aqui para o nome real do modelo

br_tz = pytz.timezone("America/Sao_Paulo")

router = APIRouter(prefix="/v3/contracts", tags=["Contracts"])


# =========================================================
# SCHEMAS
# =========================================================
class ContractCreate(BaseModel):
    empresa_id: int = Field(..., description="ID da empresa (cliente)")
    prestador_id: int = Field(..., description="ID do prestador de serviço")
    espelhar_status: Optional[bool] = False
    regras_json: Optional[Dict[str, Any]] = None
    preco_shopee: Optional[float] = None
    preco_ml: Optional[float] = None
    preco_avulso: Optional[float] = None


class ContractOut(BaseModel):
    id_contract: int
    empresa_id: int
    prestador_id: int
    ativo: bool
    espelhar_status: bool
    regras_json: Optional[Dict[str, Any]]
    criado_em: datetime
    preco_shopee: Optional[float]
    preco_ml: Optional[float]
    preco_avulso: Optional[float]

    class Config:
        from_attributes = True


class ContractPatch(BaseModel):
    empresa_id: Optional[int] = None
    prestador_id: Optional[int] = None
    ativo: Optional[bool] = None
    espelhar_status: Optional[bool] = None
    regras_json: Optional[Dict[str, Any]] = None
    preco_shopee: Optional[float] = None
    preco_ml: Optional[float] = None
    preco_avulso: Optional[float] = None


# =========================================================
# POST — CRIAR CONTRACT
# =========================================================

@router.post(
    "/create-contracts",
    response_model=ContractCreate,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um contracts",
)
def criar_contract(
    payload: ContractCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_v3),
):
    now = datetime.now(br_tz)

    novo = Contract(
        owner_id=current_user.owner_id,
        empresa_id=payload.empresa_id,
        prestador_id=payload.prestador_id,
        ativo=True,  # default ao criar
        espelhar_status=payload.espelhar_status if payload.espelhar_status is not None else False,
        regras_json=payload.regras_json,
        preco_shopee=payload.preco_shopee,
        preco_ml=payload.preco_ml,
        preco_avulso=payload.preco_avulso,
        criado_em=now,
    )

    db.add(novo)
    db.commit()
    db.refresh(novo)

    return novo


# =========================================================
# GET — LISTA TODOS OS CONTRACTS DO OWNER
# =========================================================
@router.get(
    "/",
    response_model=List[ContractOut],
    summary="Lista todos os contratos do owner do usuário logado",
)
def listar_contracts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_v3),
):
    contracts = (
        db.query(Contract)
        .filter(Contract.owner_id == current_user.owner_id)
        .order_by(Contract.id_contract.desc())
        .all()
    )
    return contracts


# =========================================================
# PATCH — ATUALIZAR CONTRACT
# =========================================================
@router.patch(
    "/{id_contract}",
    response_model=ContractOut,
    summary="Atualiza um contrato do owner do usuário logado",
)
def atualizar_contract(
    id_contract: int,
    payload: ContractPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_v3),
):
    contract = (
        db.query(Contract)
        .filter(
            Contract.id_contract == id_contract,
            Contract.owner_id == current_user.owner_id,
        )
        .first()
    )

    if not contract:
        raise HTTPException(status_code=404, detail="Contrato não encontrado.")

    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(contract, campo, valor)

    db.commit()
    db.refresh(contract)
    return contract


# =========================================================
# DELETE — DELETAR CONTRACT
# =========================================================
@router.delete(
    "/{id_contract}",
    summary="Deleta um contrato do owner do usuário logado",
)
def deletar_contract(
    id_contract: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_v3),
):
    contract = (
        db.query(Contract)
        .filter(
            Contract.id_contract == id_contract,
            Contract.owner_id == current_user.owner_id,
        )
        .first()
    )

    if not contract:
        raise HTTPException(status_code=404, detail="Contrato não encontrado.")

    db.delete(contract)
    db.commit()

    return {"detail": "Contrato deletado com sucesso."}
