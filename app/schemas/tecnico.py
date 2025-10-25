from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal


class DadosBancarios(BaseModel):
    banco: str
    agencia: str
    conta: str
    pix: Optional[str] = None


UserRole = Literal["admin", "tecnico"]


class TecnicoBase(BaseModel):
    cnpj: str
    inscricao_estadual: str
    nome: str
    telefone: str
    email: EmailStr
    dados_bancarios: DadosBancarios
    is_active: bool = True
    role: UserRole = Field("tecnico", description="Papel do usuário no sistema.")


class TecnicoCreate(TecnicoBase):
    password: str


class Tecnico(TecnicoBase):
    id: int

    class Config:
        from_attributes = True

class DadosBancariosUpdate(BaseModel):
    banco: Optional[str] = None
    agencia: Optional[str] = None
    conta: Optional[str] = None
    pix: Optional[str] = None

class TecnicoUpdate(BaseModel):
    cnpj: Optional[str] = None
    inscricao_estadual: Optional[str] = None
    nome: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[EmailStr] = None
    dados_bancarios: Optional[DadosBancariosUpdate] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None


"""
Ponto de atenção:
    No documento 'Dados para cadastro e instrução tecnica' é dito sobre a inclusão dos dados bancários da conta jurídica
    para pagamento e a menção do número da OS no corpo da nota. Isso é responsabilidade do técnico na hora que ele emite
    a nota fiscal dele. 
"""
