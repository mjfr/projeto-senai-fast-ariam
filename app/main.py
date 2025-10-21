import uvicorn
from fastapi import FastAPI
from app.api.router import api_router

app = FastAPI(
    title="Fast Ariam API",
    description="API para o sistema de gerenciamento de Ordens de Serviço da Fast Ariam.",
    version="0.1.0" # Protótipo humildão
)

app.include_router(api_router, prefix="/api")

@app.get("/", tags=["Root"])
def read_root():
    return {"status": "A API da Fast Ariam está no ar!"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)