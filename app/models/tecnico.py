import enum
from sqlalchemy import Column, Integer, String, Boolean, JSON, Enum
from sqlalchemy.orm import relationship
from app.db.database import Base


class UserRole(enum.Enum):
    admin = "admin"
    tecnico = "tecnico"


class Tecnico(Base):
    __tablename__ = "tecnico"
    id_tecnico = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False)
    cnpj = Column(String(20), nullable=False, unique=True)
    inscricao_estadual = Column(String(50))
    email = Column(String(100), nullable=False, unique=True)
    telefone = Column(String(20))
    password_hash = Column(String(100), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.tecnico)
    is_active = Column(Boolean, nullable=False, default=True)
    dados_bancarios = Column(JSON)
    chamados = relationship("OrdemServico", back_populates="tecnico")
