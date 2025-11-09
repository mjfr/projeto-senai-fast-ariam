from sqlalchemy import Column, Integer, String, Boolean, Date, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class OrdemServico(Base):
    __tablename__ = "ordem_servico"
    id_os = Column(Integer, primary_key=True, autoincrement=True)
    id_cliente = Column(Integer, ForeignKey("cliente.id_cliente"), nullable=False)
    id_tecnico_atribuido = Column(Integer, ForeignKey("tecnico.id_tecnico"), nullable=True)
    status = Column(String(50), nullable=False, default='Aberto')
    is_cancelled = Column(Boolean, nullable=False, default=False)
    data_abertura = Column(Date, nullable=False)
    data_agendamento = Column(Date)
    data_conclusao = Column(Date)
    descricao_cliente = Column(Text)
    pedido = Column(String(100))
    data_faturamento = Column(Date)
    em_garantia = Column(Boolean, nullable=False, default=True)
    cliente = relationship("Cliente", back_populates="chamados")
    tecnico = relationship("Tecnico", back_populates="chamados")
    visitas = relationship("Visita", back_populates="ordem_servico", cascade="all, delete-orphan")