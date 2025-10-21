from pydantic import BaseModel, EmailStr
from typing import Optional


class DadosBancarios(BaseModel):
    banco: str
    agencia: str
    conta: str
    pix: Optional[str] = None


class TecnicoBase(BaseModel):
    cnpj: str
    inscricao_estadual: str
    nome: str
    telefone: str
    email: EmailStr
    dados_bancarios: DadosBancarios
    is_active: bool = True


class TecnicoCreate(TecnicoBase):
    password: str


class Tecnico(TecnicoBase):
    id: int

    class Config:
        from_attributes = True


"""
Ponto de atenção:
    No documento 'Dados para cadastro e instrução tecnica' é dito sobre a inclusão dos dados bancários da conta jurídica
    para pagamento e a menção do número da OS no corpo da nota. Isso é responsabilidade do técnico na hora que ele emite
    a nota fiscal dele. 
"""
