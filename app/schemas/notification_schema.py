from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.models.notification import NotificationType


# --- CRIAÇÃO ---

class NotificationCreate(BaseModel):
    """
    Usado tanto internamente (eventos de sistema) quanto pelo frontend,
    que persiste alertas de bem-estar (postura/pausa) gerados pela câmera
    para que apareçam no histórico do sino.
    """
    tipo: NotificationType
    titulo: str = Field(..., max_length=120)
    mensagem: str = Field(..., max_length=500)
    link_destino: Optional[str] = Field(default=None, max_length=255)


# --- LEITURA (o que o frontend recebe) ---

class NotificationResponse(BaseModel):
    id: int
    tipo: NotificationType
    titulo: str
    mensagem: str
    link_destino: Optional[str] = None
    lida: bool
    criada_em: datetime
    lida_em: Optional[datetime] = None

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    """Lista paginada + contador de não lidas, em uma resposta só."""
    items: List[NotificationResponse]
    nao_lidas: int
    total: int


class UnreadCountResponse(BaseModel):
    """Resposta enxuta para o polling do contador do sino."""
    nao_lidas: int
