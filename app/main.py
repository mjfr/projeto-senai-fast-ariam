import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.router import api_router

# TODO: Lembrar de documentar melhor as classes, métodos e utilizar as docstrings para melhorar as descrições no Swagger
# TODO: A visita é a parte mais complicada até o momento do desenvolvimento, logo, ela recebe um cuidado maior nas documentações, depois, fazer o mesmo para todo o resto.

app = FastAPI(
    title="Fast Ariam API",
    description="API para o sistema de gerenciamento de Ordens de Serviço da Fast Ariam.",
    version="0.1.0" # Protótipo humildão
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(api_router, prefix="/api")

@app.get("/", tags=["Root"])
def read_root():
    return {"status": "A API da Fast Ariam está no ar!"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)