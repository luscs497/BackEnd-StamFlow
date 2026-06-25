from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, desc
from fastapi import HTTPException, status

from app.models.notification import Notification, NotificationType
from app.schemas.notification import NotificationCreate


class NotificationService:

    # ------------------------------------------------------------------
    # CRIAÇÃO
    # ------------------------------------------------------------------
    @staticmethod
    async def create(
        session: AsyncSession,
        client_id: int,
        tipo: NotificationType,
        titulo: str,
        mensagem: str,
        link_destino: Optional[str] = None,
        commit: bool = True,
    ) -> Notification:
        """
        Cria uma notificação para um client.

        Uso interno por gatilhos de sistema (passar commit=False quando já
        estiver dentro de outra transação que fará o commit) e pela rota de
        persistência usada pelo frontend (alertas de bem-estar).
        """
        notif = Notification(
            client_id=client_id,
            tipo=tipo,
            titulo=titulo,
            mensagem=mensagem,
            link_destino=link_destino,
        )
        session.add(notif)
        if commit:
            await session.commit()
            await session.refresh(notif)
        else:
            await session.flush()
        return notif

    @staticmethod
    async def create_from_schema(
        session: AsyncSession,
        client_id: int,
        data: NotificationCreate,
    ) -> Notification:
        return await NotificationService.create(
            session=session,
            client_id=client_id,
            tipo=data.tipo,
            titulo=data.titulo,
            mensagem=data.mensagem,
            link_destino=data.link_destino,
        )

    # ------------------------------------------------------------------
    # LEITURA
    # ------------------------------------------------------------------
    @staticmethod
    async def list_for_client(
        session: AsyncSession,
        client_id: int,
        limit: int = 30,
        offset: int = 0,
    ) -> tuple[List[Notification], int, int]:
        """Retorna (itens, nao_lidas, total) para um client."""
        # Itens paginados, mais recentes primeiro. Desempata por id (monotônico)
        # para ordenação determinística mesmo quando dois registros têm o
        # mesmo timestamp de criação.
        q_items = (
            select(Notification)
            .where(Notification.client_id == client_id)
            .order_by(desc(Notification.criada_em), desc(Notification.id))
            .limit(limit)
            .offset(offset)
        )
        items = (await session.execute(q_items)).scalars().all()

        # Total geral.
        q_total = select(func.count()).select_from(Notification).where(
            Notification.client_id == client_id
        )
        total = (await session.execute(q_total)).scalar_one()

        # Não lidas.
        nao_lidas = await NotificationService.unread_count(session, client_id)

        return items, nao_lidas, total

    @staticmethod
    async def unread_count(session: AsyncSession, client_id: int) -> int:
        q = select(func.count()).select_from(Notification).where(
            Notification.client_id == client_id,
            Notification.lida.is_(False),
        )
        return (await session.execute(q)).scalar_one()

    # ------------------------------------------------------------------
    # MARCAR COMO LIDA
    # ------------------------------------------------------------------
    @staticmethod
    async def mark_read(
        session: AsyncSession,
        client_id: int,
        notification_id: int,
    ) -> Notification:
        q = select(Notification).where(
            Notification.id == notification_id,
            Notification.client_id == client_id,
        )
        notif = (await session.execute(q)).scalar_one_or_none()
        if not notif:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notificação não encontrada.",
            )
        if not notif.lida:
            notif.lida = True
            notif.lida_em = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(notif)
        return notif

    @staticmethod
    async def mark_all_read(session: AsyncSession, client_id: int) -> int:
        """Marca todas as não lidas como lidas. Retorna quantas foram afetadas."""
        agora = datetime.now(timezone.utc)
        q = (
            update(Notification)
            .where(
                Notification.client_id == client_id,
                Notification.lida.is_(False),
            )
            .values(lida=True, lida_em=agora)
        )
        result = await session.execute(q)
        await session.commit()
        return result.rowcount or 0
