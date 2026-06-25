from typing import Annotated
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_client
from app.models.client import Client
from app.schemas.notification import (
    NotificationCreate,
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    current_client: Annotated[Client, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Lista paginada de notificações do usuário logado (mais recentes primeiro)."""
    items, nao_lidas, total = await NotificationService.list_for_client(
        db, current_client.id, limit=limit, offset=offset
    )
    return NotificationListResponse(
        items=items,
        nao_lidas=nao_lidas,
        total=total,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_client: Annotated[Client, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Apenas o número de não lidas — resposta enxuta para o polling do sino."""
    nao_lidas = await NotificationService.unread_count(db, current_client.id)
    return UnreadCountResponse(nao_lidas=nao_lidas)


@router.post("", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notification(
    data: NotificationCreate,
    current_client: Annotated[Client, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Persiste uma notificação para o próprio usuário logado.

    Usado pelo frontend para registrar os alertas de bem-estar (pausa e
    postura) gerados ao vivo pela câmera, garantindo que apareçam no
    histórico do sino mesmo após um refresh da página.
    """
    notif = await NotificationService.create_from_schema(
        db, current_client.id, data
    )
    return notif


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: int,
    current_client: Annotated[Client, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Marca uma notificação específica como lida."""
    notif = await NotificationService.mark_read(
        db, current_client.id, notification_id
    )
    return notif


@router.post("/read-all", status_code=status.HTTP_200_OK)
async def mark_all_notifications_read(
    current_client: Annotated[Client, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Marca todas as notificações não lidas do usuário como lidas."""
    afetadas = await NotificationService.mark_all_read(db, current_client.id)
    return {"marcadas_como_lidas": afetadas}
