from __future__ import annotations
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, users, orders

# ─────────── Configuração geral
API_PREFIX = os.getenv("API_PREFIX", "/api")

_env_origins = os.getenv("ALLOWED_ORIGINS")
if _env_origins:
    ALLOWED_ORIGINS = [o.strip() for o in _env_origins.split(",") if o.strip()]
else:
    ALLOWED_ORIGINS = [
        "https://track-saidas-html.onrender.com",
        "https://empresa_log_express.com.br",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

# ─────────── Criação da aplicação
app = FastAPI(
    title="Track Backend API",
    version="1.0.0",
    description="API multi-empresa para tracking e entregas",
    openapi_url=f"{API_PREFIX}/openapi.json",
    docs_url=f"{API_PREFIX}/docs",
    redoc_url=f"{API_PREFIX}/redoc",
    swagger_ui_parameters={"persistAuthorization": True},
)

# ─────────── CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────── Rotas
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(orders.router, prefix=API_PREFIX)

# ─────────── Healthcheck
@app.get(f"{API_PREFIX}/health", tags=["Health"])
def health():
    return {"status": "ok"}

# ─────────── Execução local
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
