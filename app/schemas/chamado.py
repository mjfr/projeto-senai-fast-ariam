from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, List, Literal
from .visita import Visita
# from .cliente import Cliente


StatusChamado = Literal["Aberto", "Agendado", "Em Atendimento", "Pendente", "Finalizado"]

class ChamadoBase(BaseModel):
    cliente_id: int = Field(..., gt=0, description="ID do cliente associado ao chamado") # TODO: Lembrar de continuar a validação
    descricao_cliente: str
    numero_serie_equipamento: Optional[str] = None
    pedido: Optional[str] = None
    data_faturamento: Optional[date] = None
    em_garantia: bool = True
    data_conclusao: Optional[date] = None
    status: StatusChamado = "Aberto"


class ChamadoCreate(ChamadoBase):
    pass


class Chamado(ChamadoBase):
    id: int
    data_abertura: date
    id_tecnico_atribuido: Optional[int] = None
    visitas: List[Visita] = List[dict]
    is_cancelled: bool = False

    class Config:
        from_attributes = True


class ChamadoUpdate(BaseModel):
    cliente_id: Optional[int] = Field(None, gt=0, description="Novo ID do cliente para reassociar o chamado")
    descricao_cliente: Optional[str] = None
    numero_serie_equipamento: Optional[str] = None
    id_tecnico_atribuido: Optional[int] = None
    status: Optional[StatusChamado] = None
    is_cancelled: Optional[bool] = None
    data_conclusao: Optional[date] = None
