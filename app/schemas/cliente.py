from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


# noinspection PyArgumentList
class ContatoCliente(BaseModel):
    nome: str = Field(..., example="Karina Silva")
    telefone: str = Field(..., example="27996439718")


# noinspection PyArgumentList
class ClienteBase(BaseModel):
    razao_social: str = Field(..., example="AUTO SERVICO PEIXOTO LTDA")
    contato_principal: ContatoCliente
    telefone: str = Field(..., example="2732511264")
    endereco: str = Field(..., example="PRACA JOAO MIGUEL")
    numero: str = Field(..., example="132")
    bairro: str = Field(..., example="SERRA CENTRO")
    cidade: str = Field(..., example="SERRA")
    uf: str = Field(..., example="ES", min_length=2, max_length=2)
    codigo: Optional[int] = Field(None, example=55835)
    is_active: bool = True

class ClienteCreate(ClienteBase):
    pass

class Cliente(ClienteBase):
    id: int

    class Config:
        from_attributes = True

class ContatoClienteUpdate(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None

class ClienteUpdate(BaseModel):
    razao_social: Optional[str] = None
    contato_principal: Optional[ContatoClienteUpdate] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    codigo: Optional[int] = None
    is_active: Optional[bool] = None