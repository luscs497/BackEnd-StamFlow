from sqlalchemy import (
    Column, BigInteger, Integer, String, Text, DateTime, Enum, ForeignKey
)
from sqlalchemy.sql import func
import enum

from app.db.base import Base


class EnterpriseRequestStatus(str, enum.Enum):
    """Funil da solicitação de plano empresarial (negociado por humano)."""
    pendente_proposta = "pendente_proposta"  # acabou de entrar, aguardando contato
    negociando = "negociando"                # em conversa de preço/condições
    aprovado = "aprovado"                    # fechado, aguardando provisionamento
    provisionado = "provisionado"            # licenças criadas e vinculadas
    recusado = "recusado"                    # não seguiu


class EnterpriseRequest(Base):
    """
    Pedido de plano empresarial. NÃO tem preço fixo nem checkout automático:
    é registrado aqui (funil) e a negociação acontece por WhatsApp/humano.
    Quando 'aprovado', um admin provisiona Company + Subscription (N+M licenças).
    """
    __tablename__ = "enterprise_requests"

    id = Column(BigInteger, primary_key=True, index=True)

    nome_empresa = Column(String(255), nullable=False)
    contato_nome = Column(String(120), nullable=False)
    contato_email = Column(String(120), nullable=True)
    contato_whatsapp = Column(String(20), nullable=True)

    qtd_colaboradores = Column(Integer, nullable=False, default=1, server_default="1")
    qtd_gestores = Column(Integer, nullable=False, default=1, server_default="1")

    observacoes = Column(Text, nullable=True)

    status = Column(
        Enum(EnterpriseRequestStatus, name="enterprise_request_status", native_enum=True),
        nullable=False,
        default=EnterpriseRequestStatus.pendente_proposta,
    )

    # Preenchido quando o pedido é provisionado (vira uma empresa de verdade)
    company_id = Column(
        BigInteger,
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )

    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
