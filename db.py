# db.py
from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()
# Use o que você já tem no Render.
# Se você já usa só DATABASE_URL, pode remover o or.
DATABASE_URL = os.getenv("TRACKING_DB_URL") or os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("Variável de ambiente TRACKING_DB_URL ou DATABASE_URL não definida.")

# future=True deixa o engine compatível com a API 2.0
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)

Base = declarative_base()


def get_db():
    """Dependency para usar em Depends(get_db)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
