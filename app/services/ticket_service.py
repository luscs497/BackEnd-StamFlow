from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, desc
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.ticket import Ticket, TicketStatus
from app.models.ticket_message import TicketMessage, MessageAuthor
from app.models.client import Client
from app.models.manager import Manager
from app.schemas.ticket import TicketCreate

class TicketService:

    @staticmethod
    async def create_ticket(session: AsyncSession, user: Client, data: TicketCreate) -> Ticket:
        # Regra: Avulso não cria ticket
        if not user.company_id:
            raise HTTPException(status_code=400, detail="Usuários avulsos não podem criar tickets.")

        # 1. Cria o Ticket
        new_ticket = Ticket(
            client_id=user.id,
            company_id=user.company_id,
            assunto=data.assunto,
            status=TicketStatus.aberto
        )
        session.add(new_ticket)
        await session.flush() # Para gerar o ID do ticket antes de criar a mensagem

        # 2. Cria a primeira mensagem (vinculada ao ticket)
        first_message = TicketMessage(
            ticket_id=new_ticket.id,
            author_type=MessageAuthor.cliente,
            author_id=user.id,
            content=data.mensagem_inicial
        )
        session.add(first_message)
        
        await session.commit()
        await session.refresh(new_ticket)
        # Carrega as mensagens para retornar completo
        query = select(Ticket).options(selectinload(Ticket.messages)).where(Ticket.id == new_ticket.id)
        result = await session.execute(query)
        return result.scalar_one()

    @staticmethod
    async def get_tickets_by_client(session: AsyncSession, client_id: int):
        """Retorna todos os tickets de um cliente específico com suas mensagens."""
        query = (
            select(Ticket)
            .where(Ticket.client_id == client_id)
            .options(selectinload(Ticket.messages))
            .order_by(desc(Ticket.atualizado_em))
        )
        result = await session.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_tickets_for_manager(session: AsyncSession, company_id: int):
        """
        Retorna tickets da empresa do gestor.
        NOTA: Não fazemos 'join' com Client para manter anonimidade no nível da query se desejado,
        ou simplesmente não retornamos o objeto cliente no Schema.
        """
        query = (
            select(Ticket)
            .where(Ticket.company_id == company_id)
            .options(selectinload(Ticket.messages))
            .order_by(desc(Ticket.atualizado_em))
        )
        result = await session.execute(query)
        return result.scalars().all()

    @staticmethod
    async def reply_ticket(session: AsyncSession, ticket_id: int, content: str, author_type: MessageAuthor, author_id: int):
        # Busca o ticket para validar existência
        ticket = await session.get(Ticket, ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket não encontrado")

        # Verifica permissões (Básico)
        if author_type == MessageAuthor.cliente and ticket.client_id != author_id:
            raise HTTPException(status_code=403, detail="Este ticket não pertence a você.")
        
        # Se for gestor, teria que verificar se o ticket é da empresa dele (validaremos na rota)

        # Adiciona mensagem
        new_msg = TicketMessage(
            ticket_id=ticket_id,
            author_type=author_type,
            author_id=author_id,
            content=content
        )
        session.add(new_msg)

        # Atualiza a data de 'atualizado_em' do ticket
        ticket.status = TicketStatus.em_andamento # Opcional: Mudar status ao responder? Vc decide.
        # O SQLAlchemy atualiza o 'atualizado_em' sozinho devido ao onupdate=func.now() no model

        await session.commit()
        return new_msg

    @staticmethod
    async def update_last_message(session: AsyncSession, ticket_id: int, client_id: int, new_content: str):
        ticket = await session.get(Ticket, ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket não encontrado")

        if ticket.client_id != client_id:
            raise HTTPException(status_code=403, detail="Não autorizado")

        # Regra: Só pode editar se estiver aberto
        if ticket.status != TicketStatus.aberto:
            raise HTTPException(status_code=400, detail="Só é possível editar mensagens em tickets abertos.")

        # Busca a última mensagem desse ticket feita pelo cliente
        query = (
            select(TicketMessage)
            .where(
                TicketMessage.ticket_id == ticket_id,
                TicketMessage.author_type == MessageAuthor.cliente,
                TicketMessage.author_id == client_id
            )
            .order_by(desc(TicketMessage.criado_em))
            .limit(1)
        )
        result = await session.execute(query)
        last_message = result.scalar_one_or_none()

        if not last_message:
            raise HTTPException(status_code=404, detail="Nenhuma mensagem para editar.")

        last_message.content = new_content
        await session.commit()
        return ticket

    @staticmethod
    async def delete_ticket(session: AsyncSession, ticket_id: int, client_id: int):
        ticket = await session.get(Ticket, ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket não encontrado")
        
        if ticket.client_id != client_id:
            raise HTTPException(status_code=403, detail="Este ticket não é seu.")

        await session.delete(ticket)
        await session.commit()