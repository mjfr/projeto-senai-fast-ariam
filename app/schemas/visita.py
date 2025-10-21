from pydantic import BaseModel
from datetime import date
from typing import List, Optional
from .base_schemas import Material


class VisitaBase(BaseModel):
    data_visita: date
    hora_inicio_deslocamento: str
    hora_chegada_cliente: str
    hora_inicio_atendimento: str
    hora_fim_atendimento: str

    km_total: int
    valor_pedagio: float = 0.0
    valor_frete_devolucao: float = 0.0

    descricao_servico_executado: str
    materiais_utilizados: List[Material] = []


class VisitaCreate(VisitaBase):
    pass


class Visita(VisitaBase):
    id: int
    # Aqui poderíamos ter um custo_total_visita calculado se quiséssemos

# TODO: Tratar futuramente o PEDÁGIO para ter comprovante para reembolso
# TODO: Tratar futuramente Controlador, compressor, fonte e micromotor são devolvidos à Fast, para fazer o reembolso do frete é preciso ter o comprovante