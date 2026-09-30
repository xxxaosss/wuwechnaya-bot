from fastapi import FastAPI

app = FastAPI()

@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "bot-gateway"}

@app.get("/")
def root():
    return {"message": "Hello from Raspberry Pi 4"}
