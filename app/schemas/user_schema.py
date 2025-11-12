from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    nome: str
    email: EmailStr
    username: str
    password: str
    tipo: str = "OPERADOR"
    owner_id: int

class UserResponse(BaseModel):
    id_user: int
    nome: Optional[str]
    email: Optional[EmailStr]
    username: Optional[str]
    tipo: str

    class Config:
        orm_mode = True
