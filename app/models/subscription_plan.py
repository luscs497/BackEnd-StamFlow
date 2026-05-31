from app.db.base import Base
from sqlalchemy import Column, BigInteger, String, Enum, Boolean
from sqlalchemy.orm import relationship
import enum

class PlanType(str, enum.Enum):
    corporative = "corporative"
    individual = "individual"

class PlanPeriod(str, enum.Enum):
    monthly = "monthly" #Mensal
    quarterly = "quarterly" # Trimestral
    semiannual = "semiannual" # Semestral
    annual = "annual" # Anual

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(250), nullable=True)
    type = Column(Enum(PlanType, name="plan_type", native_enum=True), nullable=False)
    price_in_cents = Column(BigInteger, nullable=False)
    period = Column(Enum(PlanPeriod, name="plan_period", native_enum=True), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    subscriptions = relationship("Subscription", back_populates="plan")