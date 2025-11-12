from fastapi import FastAPI
from app.routes import auth, users, orders

app = FastAPI(title="Track Backend API")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(orders.router)

@app.get("/health")
def health():
    return {"status": "ok"}
