from __future__ import annotations

from typing import Optional, List
from datetime import datetime

import pytz
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from auth_routes import get_current_user_v3
from models import Owner, User, Order, OrderEvent, Cliente

br_tz = pytz.timezone("America/Sao_Paulo")

router = APIRouter(prefix="/v3/orders", tags=["Orders"])


# =========================================================
# SCHEMAS
# =========================================================
class OrderCreate(BaseModel):
    cliente_id: int
    codigo_pacote: str = Field(min_length=1)
    servico: str = Field(min_length=1)
    orders_rua: str
    orders_cep: str


class OrderOut(BaseModel):
    order_id: int
    cliente_id: int
    codigo_pacote: str
    servico: str
    status: int
    orders_rua: str
    orders_cep: str
    criado_em: datetime
    atualizado_em: datetime

    class Config:
        from_attributes = True


class OrderUpdate(BaseModel):
    """
    Payload para o PATCH de atualização de status.

    - codigo_pacote: usado para localizar a order.
    - cliente_id: usado quando queremos associar um PRESTADOR (status 1 -> 2).
    - user_id: usado quando queremos associar um ENTREGADOR (status 1 -> 4).
    - servico: opcional, pode atualizar o tipo de serviço.
    """
    codigo_pacote: str = Field(min_length=1)
    cliente_id: Optional[int] = None
    user_id: Optional[int] = None
    servico: Optional[str] = None

class RegistroEntregaPayload(BaseModel):
    codigo_pacote: str = Field(min_length=1)


# =========================================================
# FUNÇÃO GENÉRICA DE TRANSIÇÃO DE STATUS (AUXILIAR, OPCIONAL)
# =========================================================
def aplicar_transicao_status(
    order: Order,
    owner: Owner,
    current_user: User,
    db: Session,
) -> Order:
    """
    Função genérica de fluxo baseada em slug.
    Mantida como utilitário para uso futuro caso queira.
    Atualmente o PATCH principal usa uma lógica específica
    baseada em status 0, 1 e 3.
    """

    fluxo_1 = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5}
    fluxo_2 = {0: 1, 2: 5}
    fluxo_3 = {1: 1, 4: 5}
    fluxo_4 = {4: 5}

    slug = (owner.slug or "1").strip()

    if slug == "1":
        mapa = fluxo_1
    elif slug == "2":
        mapa = fluxo_2
    elif slug == "3":
        mapa = fluxo_3
    elif slug == "4":
        mapa = fluxo_4
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fluxo de status não configurado para o slug='{slug}'.",
        )

    status_atual = order.status

    if status_atual not in mapa:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Status atual {status_atual} não tem transição definida para o fluxo {slug}.",
        )

    novo_status = mapa[status_atual]
    agora = datetime.now(br_tz)

    order.status = novo_status
    order.atualizado_em = agora
    order.user_id = current_user.user_id

    novo_evento = OrderEvent(
        order_id=order.order_id,
        tipo=order.status,
        actor_user_id=current_user.user_id,
        payload=None,
        data_hora=agora,
        owner_id=owner.id_owner,
    )

    db.add(novo_evento)

    return order


# =========================================================
# POST ANTIGO (RENOMEADO) - VARREDURA ML
# =========================================================
@router.post(
    "/varredura-ml",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma order (varredura ML) - lógica antiga",
)
def criar_order_varredura_ml(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_v3),
):
    """
    POST antigo, mantido para a varredura ML.
    - Evita duplicidade de (owner_id, cliente_id, codigo_pacote)
    - Cria order com status = 0
    """
    owner_id = current_user.owner_id

    existing = db.execute(
        select(Order)
        .where(Order.owner_id == owner_id)
        .where(Order.cliente_id == payload.cliente_id)
        .where(Order.codigo_pacote == payload.codigo_pacote)
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um order com este cliente_id + codigo_pacote.",
        )

    agora = datetime.now(br_tz)

    novo_order = Order(
        owner_id=owner_id,
        cliente_id=payload.cliente_id,
        codigo_pacote=payload.codigo_pacote,
        servico=payload.servico,
        status=0,
        orders_rua=payload.orders_rua,
        orders_cep=payload.orders_cep,
        criado_em=agora,
        atualizado_em=agora,
        user_id=None,
    )

    db.add(novo_order)
    db.commit()
    db.refresh(novo_order)

    primeiro_evento = OrderEvent(
        order_id=novo_order.order_id,
        tipo=novo_order.status,  # 0
        actor_user_id=None,
        payload=None,
        data_hora=agora,
        owner_id=owner_id,
    )

    db.add(primeiro_evento)
    db.commit()

    return novo_order


# =========================================================
# NOVO POST - CRIAR ORDER (APENAS PARA SUB_BASE, STATUS 3)
# =========================================================
@router.post(
    "/create-order",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma order",
)
def criar_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_v3),
):
    owner_id = current_user.owner_id

    # Verificar duplicidade de cliente_id + codigo_pacote
    existing = db.execute(
        select(Order)
        .where(Order.owner_id == owner_id)
        .where(Order.cliente_id == payload.cliente_id)
        .where(Order.codigo_pacote == payload.codigo_pacote)
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um order com este cliente_id + codigo_pacote.",
        )

    agora = datetime.now(br_tz)

    # Criar Order — agora SEMPRE com user_id = current_user.user_id
    novo_order = Order(
        owner_id=owner_id,
        cliente_id=payload.cliente_id,
        codigo_pacote=payload.codigo_pacote,
        servico=payload.servico,
        status=3,  # conforme sua nova regra
        orders_rua=payload.orders_rua,
        orders_cep=payload.orders_cep,
        criado_em=agora,
        atualizado_em=agora,
        user_id=current_user.user_id,  # AMARRADO AO USUÁRIO LOGADO
    )

    db.add(novo_order)
    db.commit()
    db.refresh(novo_order)

    # Criar primeiro OrderEvent já com tipo = 3
    primeiro_evento = OrderEvent(
        order_id=novo_order.order_id,
        tipo=3,
        actor_user_id=current_user.user_id,  # AMARRADO AO USUÁRIO LOGADO
        payload=None,
        data_hora=agora,
        owner_id=owner_id,
    )

    db.add(primeiro_evento)
    db.commit()

    return novo_order

# =========================================================
# PATCH - ATUALIZAR ORDER (STATUS) E REGISTRAR EVENTO
# =========================================================
@router.patch(
    "/update-order",
    response_model=OrderOut,
    status_code=status.HTTP_200_OK,
    summary="Atualiza status da order conforme nova lógica e registra evento",
)
def atualizar_order(
    payload: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_v3),
):
    owner_id = current_user.owner_id

    # Buscar a order principal (do owner atual) pelo codigo_pacote
    order = db.execute(
        select(Order)
        .where(Order.owner_id == owner_id)
        .where(Order.codigo_pacote == payload.codigo_pacote)
    ).scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Encomenda não foi encontrada para este owner + codigo_pacote.",
        )

    agora = datetime.now(br_tz)

    # Atualizar servico se vier
    if payload.servico is not None:
        order.servico = payload.servico

    # -------------------------
    # CASO 1: status atual = 0 -> vira 1
    # -------------------------
    if order.status == 0:
        order.status = 1
        order.atualizado_em = agora
        order.user_id = current_user.user_id

        novo_evento = OrderEvent(
            order_id=order.order_id,
            tipo=order.status,  # 1
            actor_user_id=current_user.user_id,
            payload=None,
            data_hora=agora,
            owner_id=owner_id,
        )

        db.add(novo_evento)
        db.commit()
        db.refresh(order)
        return order

    # -------------------------
    # CASO 2: status atual = 1
    # - cliente_id PRESTADOR -> status 2
    # - user_id ENTREGADOR   -> status 4
    # -------------------------
    if order.status == 1:
        # 2A) cliente_id preenchido e user_id em branco
        if payload.cliente_id is not None and payload.user_id is None:
            cliente = db.execute(
                select(Cliente)
                .where(Cliente.id_cliente == payload.cliente_id)
                .where(Cliente.owner_id == owner_id)
            ).scalar_one_or_none()

            if not cliente:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Cliente não encontrado para este owner.",
                )

            if (cliente.tipo_cliente or "").upper() != "PRESTADOR":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cliente informado não é do tipo PRESTADOR.",
                )

            order.cliente_id = payload.cliente_id
            order.status = 2
            order.atualizado_em = agora
            order.user_id = current_user.user_id

            novo_evento = OrderEvent(
                order_id=order.order_id,
                tipo=order.status,  # 2
                actor_user_id=current_user.user_id,
                payload=None,
                data_hora=agora,
                owner_id=owner_id,
            )

            db.add(novo_evento)
            db.commit()
            db.refresh(order)
            return order

        # 2B) cliente_id em branco e user_id preenchido
        if payload.cliente_id is None and payload.user_id is not None:
            user_entregador = db.execute(
                select(User)
                .where(User.user_id == payload.user_id)
                .where(User.owner_id == owner_id)
            ).scalar_one_or_none()

            if not user_entregador:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuário (user_id) não encontrado para este owner.",
                )

            if (user_entregador.tipo or "").upper() != "ENTREGADOR":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Usuário informado não é do tipo ENTREGADOR.",
                )

            order.user_id = payload.user_id
            order.status = 4
            order.atualizado_em = agora

            novo_evento = OrderEvent(
                order_id=order.order_id,
                tipo=order.status,  # 4
                actor_user_id=current_user.user_id,
                payload=None,
                data_hora=agora,
                owner_id=owner_id,
            )

            db.add(novo_evento)
            db.commit()
            db.refresh(order)
            return order

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Para status 1, envie cliente_id OU user_id (mas não ambos).",
        )

    # -------------------------
    # CASO 3: status atual = 3
    # - user_id OBRIGATÓRIO
    # - user_id deve ser ENTREGADOR do mesmo owner
    # - atualizar TODAS as orders com esse codigo_pacote para 4
    #   (inclusive outras owners) e criar eventos para cada uma
    # -------------------------
    if order.status == 3:
        if payload.user_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Para status 3, é obrigatório informar user_id (entregador).",
            )

        # valida entregador do mesmo owner
        user_entregador = db.execute(
            select(User)
            .where(User.user_id == payload.user_id)
            .where(User.owner_id == owner_id)
        ).scalar_one_or_none()

        if not user_entregador:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário (user_id) não encontrado para este owner.",
            )

        if (user_entregador.tipo or "").upper() != "ENTREGADOR":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usuário informado não é do tipo ENTREGADOR.",
            )

        # Busca TODAS as orders com o mesmo codigo_pacote (todas as owners)
        orders_mesmo_codigo = db.execute(
            select(Order).where(Order.codigo_pacote == payload.codigo_pacote)
        ).scalars().all()

        if not orders_mesmo_codigo:
            # em teoria não deveria acontecer, pois já temos 'order' acima
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nenhuma order encontrada com esse codigo_pacote.",
            )

        for o in orders_mesmo_codigo:
            o.status = 4
            o.atualizado_em = agora

            # apenas na order do owner atual gravamos o entregador
            if o.owner_id == owner_id:
                o.user_id = payload.user_id

            novo_evento = OrderEvent(
                order_id=o.order_id,
                tipo=4,
                actor_user_id=current_user.user_id,
                payload=None,
                data_hora=agora,
                owner_id=o.owner_id,
            )
            db.add(novo_evento)

        db.commit()
        db.refresh(order)  # atualiza a order principal desse owner
        return order

    # -------------------------
    # OUTROS STATUS NÃO SUPORTADOS
    # -------------------------
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Status atual {order.status} não permite este PATCH.",
    )


# =========================================================
# PATCH - REGISTRO ENTREGA (4 -> 5) POR ENTREGADOR
# =========================================================


# =========================================================
# PATCH - REGISTRO DE ENTREGA (2 ➜ 5 OU 4 ➜ 5)
# =========================================================

# =========================================================
# PATCH - REGISTRO DE ENTREGA (2 ➜ 5 OU 4 ➜ 5)
# =========================================================
@router.patch(
    "/registro-entrega",
    response_model=OrderOut,
    status_code=status.HTTP_200_OK,
    summary="Registra a entrega (status 5) e propaga para todos os owners do mesmo código",
)
def registro_entrega(
    payload: RegistroEntregaPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_v3),
):
    owner_id = current_user.owner_id

    if (current_user.tipo or "").upper() != "ENTREGADOR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas usuários ENTREGADOR podem registrar entrega.",
        )

    agora = datetime.now(br_tz)

    # Buscar todas as orders do código
    orders_mesmo_codigo = db.execute(
        select(Order).where(Order.codigo_pacote == payload.codigo_pacote)
    ).scalars().all()

    if not orders_mesmo_codigo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma order encontrada com esse codigo_pacote."
        )

    # Verifica se existe pelo menos uma em status 2 OU 4
    if not any(o.status in (2, 4) for o in orders_mesmo_codigo):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Entrega só pode ser registrada se alguma linha estiver em status 2 ou 4."
        )

    # Order principal: usa a do owner atual se existir, senão a primeira
    order_principal = next(
        (o for o in orders_mesmo_codigo if o.owner_id == owner_id),
        orders_mesmo_codigo[0]
    )

    # Atualizar todas as orders para status 5 e amarrar user_id = current_user
    for o in orders_mesmo_codigo:
        o.status = 5
        o.atualizado_em = agora
        o.user_id = current_user.user_id   # AGORA É SEMPRE current_user

        novo_evento = OrderEvent(
            order_id=o.order_id,
            tipo=5,
            actor_user_id=current_user.user_id,  # SEMPRE current_user
            payload=None,
            data_hora=agora,
            owner_id=o.owner_id,
        )
        db.add(novo_evento)

    db.commit()
    db.refresh(order_principal)

    return order_principal

# =========================================================
# GET - LISTAR TODOS
# =========================================================
@router.get("/", response_model=List[OrderOut])
def listar_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_v3),
):
    owner_id = current_user.owner_id

    results = db.execute(
        select(Order).where(Order.owner_id == owner_id)
    ).scalars().all()

    return results


# =========================================================
# GET - POR ID
# =========================================================
@router.get("/{order_id}", response_model=OrderOut)
def obter_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_v3),
):
    owner_id = current_user.owner_id

    order = db.execute(
        select(Order)
        .where(Order.owner_id == owner_id)
        .where(Order.order_id == order_id)
    ).scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order não encontrado.")

    return order

