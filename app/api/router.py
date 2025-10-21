from fastapi import APIRouter
from app.api.endpoints import chamados, tecnicos

api_router = APIRouter()

api_router.include_router(chamados.router, prefix="/chamados", tags=["Chamados"])

api_router.include_router(tecnicos.router, prefix="/tecnicos", tags=["Técnicos"])
