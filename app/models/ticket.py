import enum
from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship # <--- IMPORTANTE
from sqlalchemy.sql import func

from app.db.base import Base

class TicketStatus(str, enum.Enum):
    aberto = "aberto"
    em_andamento = "em_andamento"
    concluido = "concluido"

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(BigInteger, primary_key=True, index=True)

    client_id = Column(
        BigInteger,
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False
    )

    company_id = Column(
        BigInteger,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False
    )

    assunto = Column(String(120), nullable=False)
    
    status = Column(
        Enum(TicketStatus, name="ticket_status", native_enum=True), 
        nullable=False, 
        server_default="aberto"
    )

    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    
    atualizado_em = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    messages = relationship("TicketMessage", back_populates="ticket", cascade="all, delete-orphan")