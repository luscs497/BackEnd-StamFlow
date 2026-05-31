from sqlalchemy import Column, BigInteger, String, SmallInteger
from sqlalchemy.orm import relationship
from app.db.base import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(BigInteger, primary_key=True, index=True)
    nome_fantasia = Column(String(255), nullable=False)
    razao_social = Column(String(255), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    cnpj = Column(String(18), nullable=False, unique=True)
    telefone = Column(String(20), nullable=False, index=True) # Formato +xx (xx) xxxxx-xxxx
    senha_hash = Column(String(255), nullable=False)

    subscription = relationship("Subscription", back_populates="company", uselist=False)
    managers = relationship("Manager", back_populates="company", cascade="all, delete-orphan")
    clients = relationship("Client", back_populates="company", cascade="all, delete-orphan")

    @property
    def active_subscription(self):
        return self.subscription