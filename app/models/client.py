from sqlalchemy import Column, BigInteger, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(BigInteger, primary_key=True, index=True)

    company_id = Column(
        BigInteger,
        ForeignKey("companies.id"),
        nullable=True
    )

    manager_id = Column(
        BigInteger,
        ForeignKey("managers.id"),
        nullable=True
    )

    nome_completo = Column(String(100))
    cpf = Column(String(14), unique=True)
    telefone = Column(String(20), index=True) # Formato +xx (xx) xxxxx-xxxx
    email = Column(String(100), nullable=False, unique=True, index=True)
    senha_hash = Column(String(255), nullable=False)

    tempo_ativo_segundos = Column(BigInteger, nullable=False, default=0)

    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    # Teste grátis de 7 dias: data em que a conta CONSUMIU o trial.
    # Fica NULL para quem nunca usou; ao iniciar o trial vira a data atual.
    # É o que garante a regra "1 trial por vida por conta".
    trial_used_at = Column(DateTime(timezone=True), nullable=True)

    reports = relationship("DailyReport", back_populates="client", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="client", cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="client", uselist=False)
    company = relationship("Company", back_populates="clients")
    manager = relationship("Manager", back_populates="clients")

    @property
    def active_subscription(self):
        """Retorna a assinatura própria (se tiver) ou a da empresa."""
        if self.subscription:
            return self.subscription
        if self.company and self.company.subscription:
            return self.company.subscription
        return None
