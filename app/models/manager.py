from sqlalchemy import Column, BigInteger, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base


class Manager(Base):
    __tablename__ = "managers"

    id = Column(BigInteger, primary_key=True, index=True)

    company_id = Column(
        BigInteger,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False
    )

    nome = Column(String(100), nullable=False)
    cpf = Column(String(14), nullable=False, unique=True)
    telefone = Column(String(20), nullable=False, index=True) # Formato +xx (xx) xxxxx-xxxx
    email = Column(String(100), nullable=False, unique=True)
    senha_hash = Column(String(255), nullable=False)

    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="managers")
    clients = relationship("Client", back_populates="manager")

    @property
    def active_subscription(self):
        """Retorna a assinatura da empresa."""
        if self.company and self.company.subscription:
            return self.company.subscription
        return None
