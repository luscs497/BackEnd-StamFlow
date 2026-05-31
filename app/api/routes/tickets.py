from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
# --- IMPORTAÇÕES NECESSÁRIAS PARA CORRIGIR O ERRO ---
from sqlalchemy import select
from sqlalchemy.orm import selectinload
# ----------------------------------------------------

from app.db.session import get_db
from app.api.deps import get_current_user, get_current_client, get_current_manager
from app.models.client import Client
from app.models.manager import Manager
from app.models.ticket import Ticket, TicketStatus
from app.models.ticket_message import MessageAuthor
from app.schemas.ticket import (
    TicketCreate, TicketResponse, TicketReply, 
    TicketUpdateMessage, TicketUpdateStatus
)
from app.services.ticket_service import TicketService

router = APIRouter()

# --- ROTAS PARA CLIENTES ---

@router.post("/", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    ticket_data: TicketCreate,
    current_client: Annotated[Client, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    return await TicketService.create_ticket(db, current_client, ticket_data)

@router.get("/my-tickets", response_model=List[TicketResponse])
async def read_my_tickets(
    current_client: Annotated[Client, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    return await TicketService.get_tickets_by_client(db, current_client.id)

@router.put("/{ticket_id}/message", response_model=TicketResponse)
async def edit_last_message(
    ticket_id: int,
    data: TicketUpdateMessage,
    current_client: Annotated[Client, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    ticket = await TicketService.update_last_message(db, ticket_id, current_client.id, data.content)
    return ticket

@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(
    ticket_id: int,
    current_client: Annotated[Client, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    await TicketService.delete_ticket(db, ticket_id, current_client.id)


# --- ROTAS PARA GESTORES ---

@router.get("/company-tickets", response_model=List[TicketResponse])
async def read_company_tickets(
    current_manager: Annotated[Manager, Depends(get_current_manager)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    return await TicketService.get_tickets_for_manager(db, current_manager.company_id)

@router.patch("/{ticket_id}/status", response_model=TicketResponse)
async def update_ticket_status(
    ticket_id: int,
    status_data: TicketUpdateStatus,
    current_manager: Annotated[Manager, Depends(get_current_manager)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    # 1. Busca Simples para verificar permissão
    ticket = await db.get(Ticket, ticket_id)
    
    if not ticket or ticket.company_id != current_manager.company_id:
        raise HTTPException(status_code=404, detail="Ticket não encontrado na sua empresa")
    
    # 2. Atualiza e Salva
    ticket.status = status_data.status
    await db.commit()
    
    # 3. O PULO DO GATO (Correção do Erro):
    # Precisamos recarregar o ticket trazendo as mensagens junto,
    # senão o response_model quebra ao tentar ler ticket.messages
    query = (
        select(Ticket)
        .options(selectinload(Ticket.messages)) # Carrega as mensagens explicitamente
        .where(Ticket.id == ticket_id)
    )
    result = await db.execute(query)
    ticket_atualizado = result.scalars().first()
    
    return ticket_atualizado


# --- ROTA COMUM (RESPONDER) ---

@router.post("/{ticket_id}/reply", status_code=status.HTTP_201_CREATED)
async def reply_ticket(
    ticket_id: int,
    reply_data: TicketReply,
    current_user = Depends(get_current_user),
    db: Annotated[AsyncSession, Depends(get_db)] = None # type: ignore
):
    if isinstance(current_user, Client):
        author_type = MessageAuthor.cliente
        author_id = current_user.id
    elif isinstance(current_user, Manager):
        author_type = MessageAuthor.gestor
        author_id = current_user.id
        
        ticket = await db.get(Ticket, ticket_id)
        if not ticket or ticket.company_id != current_user.company_id:
             raise HTTPException(status_code=403, detail="Não autorizado")
    else:
        raise HTTPException(status_code=401)

    return await TicketService.reply_ticket(db, ticket_id, reply_data.content, author_type, author_id)