from sqlalchemy import Column, BigInteger, Integer, ForeignKey
from app.db.base import Base


class ClientAchievement(Base):
    __tablename__ = "client_achievements"

    client_id = Column(
        BigInteger,
        ForeignKey("clients.id", ondelete="CASCADE"),
        primary_key=True
    )

    exercicios_realizados = Column(Integer, nullable=False, default=0)
    pausas_realizadas = Column(Integer, nullable=False, default=0)
