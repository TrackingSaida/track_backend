from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services.db import get_db
from app.models.mt_models import User
from app.schemas.user_schema import UserCreate, UserResponse
from app.core.security import hash_password
from typing import List

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db)):
    """Lista todos os usuários"""
    return db.query(User).all()

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Retorna um usuário específico"""
    user = db.query(User).filter(User.id_user == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user

@router.post("/", response_model=UserResponse)
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    """Cria um novo usuário com hash de senha"""
    existing_user = db.query(User).filter(User.username == data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username já existe")

    hashed = hash_password(data.password)
    novo = User(
        nome=data.nome,
        email=data.email,
        username=data.username,
        password_hash=hashed,
        tipo=data.tipo,
        owner_id=data.owner_id,
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo
