from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services.db import get_db
from app.models.mt_models import Order
from typing import List
from datetime import datetime

router = APIRouter(prefix="/orders", tags=["orders"])

@router.get("/", response_model=List[dict])
def list_orders(db: Session = Depends(get_db)):
    """Lista todos os pedidos"""
    orders = db.query(Order).order_by(Order.criado_em.desc()).all()
    return [
        {
            "id": o.id_order,
            "codigo": o.codigo_pacote,
            "status": o.status,
            "servico": o.servico,
            "criado_em": o.criado_em,
        }
        for o in orders
    ]

@router.post("/")
def create_order(order: dict, db: Session = Depends(get_db)):
    """Cria um novo pedido"""
    novo = Order(
        empresa_id=order["empresa_id"],
        cliente_id=order.get("cliente_id"),
        codigo_pacote=order["codigo_pacote"],
        servico=order["servico"],
        status=order.get("status", "ENTRADA"),
        holder_tipo=order.get("holder_tipo", "EMPRESA"),
        holder_id=order.get("holder_id"),
        criado_em=datetime.utcnow(),
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return {"msg": "Pedido criado com sucesso", "id_order": novo.id_order}
