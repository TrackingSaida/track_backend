# main.py
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import Base, engine

# IMPORTS DOS ROUTERS V3 (vamos criar depois)
# from routes_v3 import orders_router, deliveries_router, financeiro_router, owners_router

app = FastAPI(
    title="Tracking Saídas - API v3",
    version="3.0.0",
    description="API v3 baseada no novo modelo relacional (owner, cliente, orders, deliveries, financeiro, etc).",
)

# CORS (ajuste origens conforme seu front)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # em produção, colocar só seu domínio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Se você **não** usa Base.metadata.create_all (porque cria tudo via migração ou pgAdmin),
# pode comentar as 2 linhas abaixo para evitar tentar criar enum/tabelas de novo.
Base.metadata.bind = engine
# Base.metadata.create_all(engine)


@app.get("/health", tags=["Status"])
def health_check():
    return {"status": "ok", "api": "v3"}


# Quando criarmos os routers v3 é só descomentar:
from auth_routes import router as auth_router
from users_routes import router as users_router
from cliente_routes import router as cliente_router
from upload_routes import router as upload_router
from order_routes import router as order_router


app.include_router(auth_router)
app.include_router(cliente_router)
app.include_router(users_router)
app.include_router(upload_router)
app.include_router(order_router)

# app.include_router(owners_router, prefix="/v3/owners", tags=["Owners v3"])
# app.include_router(orders_router, prefix="/v3/orders", tags=["Orders v3"])
# app.include_router(deliveries_router, prefix="/v3/deliveries", tags=["Deliveries v3"])
# app.include_router(financeiro_router, prefix="/v3/financeiro", tags=["Financeiro v3"])
