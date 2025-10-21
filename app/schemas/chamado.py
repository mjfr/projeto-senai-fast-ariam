from pydantic import BaseModel
from datetime import date
from typing import Optional, List
from .visita import Visita

# TODO: Quando tudo estiver funcionando tranquilamente, passar o Cliente para um schema próprio e tratar como um cadastro (evitar repetições e erros futuros)

class ContatoCliente(BaseModel):
    nome: str
    telefone: str

class ClienteInfo(BaseModel):
    razao_social: str
    contato_principal: ContatoCliente
    telefone: str
    endereco: str
    numero: str
    bairro: str
    cidade: str
    uf: str
    codigo: str
    pedido: Optional[str] = None
    data_faturamento: Optional[date] = None
    em_garantia: bool = True

class Custos(BaseModel):
    custo_deslocamento_rs: float = 0.0
    custo_hora_trabalhada_rs: float = 0.0
    custo_km_rs: float = 0.0
    custo_materiais_rs: float = 0.0

class ChamadoBase(BaseModel):
    cliente: ClienteInfo
    descricao_cliente: str
    numero_serie_equipamento: Optional[str] = None

class ChamadoCreate(ChamadoBase):
    pass

class Chamado(ChamadoBase):
    id: int
    data_abertura: date
    status: str
    id_tecnico_atribuido: Optional[int] = None
    visitas: List[Visita] = []
    is_cancelled: bool = False

    class Config:
        from_attributes = True

class ContatoClienteUpdate(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None


class ClienteInfoUpdate(BaseModel):
    razao_social: Optional[str] = None
    contato_principal: Optional[ContatoClienteUpdate] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    codigo: Optional[int] = None
    pedido: Optional[str] = None
    data_faturamento: Optional[date] = None
    em_garantia: Optional[bool] = None

class ChamadoUpdate(BaseModel):
    cliente: Optional[ClienteInfoUpdate] = None
    descricao_cliente: Optional[str] = None
    numero_serie_equipamento: Optional[str] = None
    id_tecnico_atribuido: Optional[int] = None
    status: Optional[str] = None
    is_cancelled: Optional[bool] = False