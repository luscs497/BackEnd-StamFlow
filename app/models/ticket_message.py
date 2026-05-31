import enum
from sqlalchemy import Column, BigInteger, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship # <--- Verifique se importou isso
from sqlalchemy.sql import func

from app.db.base import Base

class MessageAuthor(str, enum.Enum):
    cliente = "cliente"
    gestor = "gestor"

class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id = Column(BigInteger, primary_key=True, index=True)

    ticket_id = Column(
        BigInteger,
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False
    )

    author_type = Column(
        Enum(MessageAuthor, name="message_author", native_enum=True),
        nullable=False
    )

    author_id = Column(BigInteger, nullable=True)

    content = Column(Text, nullable=False)

    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("Ticket", back_populates="messages")