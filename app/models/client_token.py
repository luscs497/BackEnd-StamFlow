from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
# IMPORTANTE: Importamos o tipo específico INET do dialeto PostgreSQL
from sqlalchemy.dialects.postgresql import INET 

from app.db.base import Base


class ClientToken(Base):
    __tablename__ = "client_tokens"

    id = Column(BigInteger, primary_key=True, index=True)

    client_id = Column(
        BigInteger,
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False
    )

    refresh_token_hash = Column(String(64), nullable=False)

    user_agent = Column(String)
    
    # AQUI ESTAVA O ERRO: Mudamos de String para INET
    ip_address = Column(INET)

    expira_em = Column(DateTime(timezone=True), nullable=False)
    revogado = Column(Boolean, nullable=False, default=False)

    criado_em = Column(DateTime(timezone=True), server_default=func.now())