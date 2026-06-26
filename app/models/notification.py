import enum
from sqlalchemy import (
    Column, BigInteger, String, Boolean, DateTime, ForeignKey, Enum, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class NotificationType(str, enum.Enum):
    """
    Tipos de notificação da v1.

    Eventos de SISTEMA (nascem no backend):
      - report_respondido: o gestor respondeu/leu um report do colaborador.
      - relatorio_semanal: o resumo semanal do colaborador ficou pronto.
      - convite_expirado:  um convite vinculado à conta expirou.

    Alertas de BEM-ESTAR (nascem no frontend, via câmera, e são
    persistidos aqui para o histórico do sino sobreviver a um refresh):
      - pausa_recomendada: tempo prolongado sentado em frente ao PC.
      - postura_critica:   tempo prolongado em postura crítica.
      - postura_atencao:   tempo prolongado em postura de atenção.
    """
    report_respondido = "report_respondido"
    relatorio_semanal = "relatorio_semanal"
    convite_expirado = "convite_expirado"
    pausa_recomendada = "pausa_recomendada"
    postura_critica = "postura_critica"
    postura_atencao = "postura_atencao"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(BigInteger, primary_key=True, index=True)

    # Destinatário. Foco da v1 é o client (avulso/user), que é quem usa a
    # câmera e recebe tanto alertas de bem-estar quanto eventos de sistema.
    client_id = Column(
        BigInteger,
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )

    tipo = Column(
        Enum(
            NotificationType,
            name="notification_type",
            native_enum=True,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )

    titulo = Column(String(120), nullable=False)
    mensagem = Column(String(500), nullable=False)

    # Rota/seção do app para onde o clique na notificação leva.
    # Ex.: "pausa-mental", "relatorios", "checkup". Pode ser nulo para
    # notificações puramente informativas.
    link_destino = Column(String(255), nullable=True)

    lida = Column(Boolean, nullable=False, server_default="false")

    criada_em = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    lida_em = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # Acelera a consulta mais comum: notificações de um usuário,
        # ordenadas da mais recente para a mais antiga.
        Index("ix_notifications_client_criada", "client_id", "criada_em"),
    )

    client = relationship("Client", back_populates="notifications")
