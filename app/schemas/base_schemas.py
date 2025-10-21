from pydantic import BaseModel

class Material(BaseModel):
    nome: str
    quantidade: int
    valor: float