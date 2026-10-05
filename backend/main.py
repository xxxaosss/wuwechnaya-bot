from fastapi import FastAPI
from auth.router import router as auth_router
from inventory.router import router as inventory_router

app = FastAPI()
app.include_router(auth_router)
app.include_router(inventory_router)

@app.get("/healthz")
def healthz():
    return {"status": "ok"}
