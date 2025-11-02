from pydantic import BaseModel, Field
from datetime import date
from typing import List, Optional
from .base_schemas import Material, TipoDefeitoPrincipal, SubDefeitoRefrigeracao, SubDefeitoCompressor, \
    SubDefeitoVazamento, SubDefeitoOutros, SubDefeitoIluminacao, SubDefeitoEstrutura


# noinspection PyArgumentList
class VisitaBase(BaseModel):
    """
    Schema base para uma visita técnica.
    Captura os dados brutos para o cálculo de custos.
    """
    data_visita: date = Field(..., example="2025-10-21")
    hora_inicio_deslocamento: str = Field(..., example="08:00")
    hora_chegada_cliente: str = Field(..., example="09:15")
    hora_inicio_atendimento: str = Field(..., example="09:30")
    hora_fim_atendimento: str = Field(..., example="11:00")
    km_total: int = Field(..., gt=0, description="Total de KMs rodados (ida + volta).", example=55)
    valor_pedagio: float = Field(0.0, ge=0, description="Custo total de pedágios na rota.", example=9.80)
    valor_frete_devolucao: float = Field(0.0, ge=0, description="Custo de frete para devolução de peças.",
                                         example=16.35)
    descricao_servico_executado: str = Field(..., description="Descrição do serviço executado e observações.",
                                             example="Troca do filtro secador e reoperação de vácuo.")
    materiais_utilizados: List[Material] = Field(
        example=[
            {"nome": "Filtro Secador XYZ", "quantidade": 1, "valor": 85.00},
            {"nome": "Gás R-134a", "quantidade": 2, "valor": 50.00}
        ]
    )
    servico_finalizado: bool = Field(..., description="O serviço neste chamado foi concluído nesta visita?",
                                     example=True)
    pendencia: Optional[str] = Field(None, description="Se o serviço não foi finalizado, qual a pendência?",
                                     example="Aguardando peça X.")
    nome_ajudante: Optional[str] = Field(None, example="Carlos Silva", description="Nome do ajudante, se houver.")
    telefone_ajudante: Optional[str] = Field(None, example="27998887766",
                                             description="Telefone do ajudante, se houver.")
    defeitos_principais: List[TipoDefeitoPrincipal] = Field(default=[],
                                                            description="Lista de categorias principais do defeito.")
    defeito_outros_descricao: Optional[str] = Field(None,
                                                    description="Descrição se 'Outros' for selecionado em defeitos_principais")
    sub_defeitos_refrigeracao: List[SubDefeitoRefrigeracao] = Field(default=[],
                                                                    description="Sub-defeitos de Refrigeração")
    sub_defeitos_compressor: List[SubDefeitoCompressor] = Field(default=[],
                                                                description="Detalhes do defeito de Compressor")
    sub_defeitos_vazamento: List[SubDefeitoVazamento] = Field(default=[],
                                                              description="Detalhes do defeito de Vazamento")
    vazamento_ponto_descricao: Optional[str] = Field(None,
                                                     description="Descrição por extenso dos pontos de vazamento")
    sub_defeitos_outros: List[SubDefeitoOutros] = Field(default=[],
                                                        description="Detalhes de 'Outros' em Refrigeração")
    sub_defeitos_iluminacao: List[SubDefeitoIluminacao] = Field(default=[],
                                                                description="Detalhes do defeito de Iluminação")
    sub_defeitos_estrutura: List[SubDefeitoEstrutura] = Field(default=[],
                                                              description="Detalhes do defeito de Estrutura")


class VisitaCreate(VisitaBase):
    """
    Schema de entrada de uma visita.
    """
    pass


class Visita(VisitaBase):
    """
    Schema de saída de uma visita.
    """
    id: int
    odometro_inicio_url: Optional[str] = Field(None, description="URL da foto do odômetro no início do deslocamento.")
    odometro_fim_url: Optional[str] = Field(None, description="URL da foto do odômetro no fim do deslocamento.")
    comprovante_pedagio_urls: List[str] = Field(default=[], description="Lista de URLs dos comprovantes de pedágio.")
    comprovante_frete_urls: List[str] = Field(default=[],
                                              description="Lista de URLs dos comprovantes de frete para devolução de peças.")
    assinatura_cliente_url: Optional[str] = Field(None, description="URL da imagem da assinatura digital do cliente.")

    class Config:
        from_attributes = True


# TODO: Tratar futuramente o PEDÁGIO para ter comprovante para reembolso
# TODO: Tratar futuramente Controlador, compressor, fonte e micromotor são devolvidos à Fast, para fazer o reembolso do frete é preciso ter o comprovante

class VisitaUpdate(BaseModel):
    """
    Schema para atualizar uma visita, possibilitando editar e/ou adicionar informações e URLs de arquivos pós-upload.
    Todos os campos são opcionais.
    """
    data_visita: Optional[date] = None
    hora_saida_empresa: Optional[str] = None
    hora_chegada_cliente: Optional[str] = None
    hora_inicio_servico: Optional[str] = None
    hora_fim_servico: Optional[str] = None
    km_total: Optional[int] = None
    valor_pedagio: Optional[float] = None
    valor_frete_devolucao: Optional[float] = None
    descricao_tecnico: Optional[str] = None
    materiais_utilizados: Optional[List[Material]] = None
    servico_finalizado: Optional[bool] = None
    pendencia: Optional[str] = None
    nome_ajudante: Optional[str] = None
    telefone_ajudante: Optional[str] = None
    defeitos_principais: Optional[List[TipoDefeitoPrincipal]] = None
    defeito_outros_descricao: Optional[str] = None
    sub_defeitos_refrigeracao: Optional[List[SubDefeitoRefrigeracao]] = None
    sub_defeitos_compressor: Optional[List[SubDefeitoCompressor]] = None
    sub_defeitos_vazamento: Optional[List[SubDefeitoVazamento]] = None
    vazamento_ponto_descricao: Optional[str] = None
    sub_defeitos_outros: Optional[List[SubDefeitoOutros]] = None
    sub_defeitos_iluminacao: Optional[List[SubDefeitoIluminacao]] = None
    sub_defeitos_estrutura: Optional[List[SubDefeitoEstrutura]] = None
    odometro_inicio_url: Optional[str] = None
    odometro_fim_url: Optional[str] = None
    comprovante_pedagio_urls: Optional[List[str]] = None
    comprovante_frete_urls: Optional[List[str]] = None
    assinatura_cliente_url: Optional[str] = None
