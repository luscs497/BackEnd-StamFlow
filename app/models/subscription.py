from app.db.base import Base
from sqlalchemy import Column, BigInteger, Integer, String, ForeignKey, DateTime, Enum, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

class SubscriptionStatus(str, enum.Enum):
    trialing = "TRIALING"
    active = "ACTIVE"
    overdue = "OVERDUE"
    unpaid = "UNPAID"
    canceled = "CANCELED"
    incomplete = "INCOMPLETE"
    # DEMO (nova decisão de produto): versão gratuita de 7 dias, DELIBERADAMENTE
    # limitada (sem Pausa Mental, Foco, University ou Relatórios; exercícios
    # guiados restritos) e sem persistir métricas de uso reais. Distinto de
    # TRIALING (reservado para um eventual teste grátis do produto completo).
    demo = "DEMO"

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(BigInteger, primary_key=True, index=True)
    plan_id = Column(BigInteger, ForeignKey("subscription_plans.id", ondelete="CASCADE"), nullable=False)
    client_id = Column(BigInteger, ForeignKey("clients.id", ondelete="CASCADE"), nullable=True)
    company_id = Column(BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True)
    status = Column(Enum(SubscriptionStatus, name="subscription_status", native_enum=True), nullable=False, default=SubscriptionStatus.incomplete)
    initial_date = Column(DateTime(timezone=True), server_default=func.now())
    end_date = Column(DateTime(timezone=True))
    license_quantity = Column(Integer, nullable=False, default=1)
    mp_subscription_id = Column(String, index=True)
    price_at_purchase = Column(Numeric(10,2), nullable=False)
    max_managers_purchased = Column(Integer, nullable=False, default=0)
    max_employees_purchased = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")
    client = relationship("Client", back_populates="subscription")
    company = relationship("Company", back_populates="subscription")