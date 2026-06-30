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

    # Demo de 7 dias (versão limitada, sem cartão — decisão de produto):
    # mesma lógica do trial_used_at, mas para o status DEMO. A unicidade por
    # CPF (cpf é unique=True acima) já impede criar múltiplas contas demo
    # com o mesmo CPF; este campo impede reiniciar o demo na MESMA conta.
    demo_used_at = Column(DateTime(timezone=True), nullable=True)

    # Última atividade da conta (login, sync de relatório, etc). Usado pelo
    # job scripts/cleanup_inactive_demo_accounts.py para excluir contas demo
    # inativas há mais de 90 dias.
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now())

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
