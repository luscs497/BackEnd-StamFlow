# app/models/daily_report.py

from sqlalchemy import Column, Integer, Date, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True, index=True)

    client_id = Column(
        Integer,
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False
    )

    report_date = Column(Date, nullable=False)

    # JSONB com posture/emotion etc.
    metrics = Column(JSONB, nullable=False, default=dict)

    # Tempo em segundos
    tempo_uso_segundos = Column(Integer, nullable=False, default=0, server_default="0")

    # ==========================
    # CONQUISTAS (somente as colunas que EXISTEM no banco)
    # ==========================
    pausas_mentais_feitas = Column(Integer, nullable=False, default=0, server_default="0")
    exercicios_feitos = Column(Integer, nullable=False, default=0, server_default="0")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relacionamento com o Cliente
    client = relationship("Client", back_populates="reports")
